import discord
from discord.ext import commands
import sqlite3
from utils.constants import DB_FILE
from utils import checks
import time

class HelpPaginator(discord.ui.View):
    def __init__(self, user, pages):
        super().__init__(timeout=120)
        self.user = user
        self.pages = pages
        self.current_page = 0
        self.total_pages = len(pages)
        self.update_buttons()

    def update_buttons(self):
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page == self.total_pages - 1

    def generate_embed(self):
        # Unpack the current category dictionary
        page_data = self.pages[self.current_page]
        
        embed = discord.Embed(
            title=f"📟 Ecological Terminal: {page_data['title']}",
            description=page_data['description'],
            color=discord.Color.teal()
        )
        
        for cmd_name, cmd_desc in page_data['commands'].items():
            embed.add_field(name=cmd_name, value=cmd_desc, inline=False)
            
        embed.set_footer(text=f"Module {self.current_page + 1} of {self.total_pages} | Authorized Access Only")
        return embed

    @discord.ui.button(label="◀️ Prev Module", style=discord.ButtonStyle.secondary, custom_id="help_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ This terminal is in use.", ephemeral=True)
            
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="Next Module ▶️", style=discord.ButtonStyle.secondary, custom_id="help_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ This terminal is in use.", ephemeral=True)
            
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

class RemoveSpecimenModal(discord.ui.Modal, title="Remove Specimen from Exchange"):
    tag_input = discord.ui.TextInput(
        label="Specimen Tag ID to Remove", 
        placeholder="e.g. 123e4567", 
        min_length=4, 
        max_length=36
    )

    def __init__(self, trade_view, user):
        super().__init__()
        self.trade_view = trade_view
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        tag_to_remove = self.tag_input.value.strip().lower()
        
        # 1. Determine which list to look at
        if self.user == self.trade_view.player1:
            offer_list = self.trade_view.p1_offer
        else:
            offer_list = self.trade_view.p2_offer

        # 2. Search for the specimen in their current offer
        # We use startswith() to be forgiving if they only type the first few characters
        specimen_to_remove = next((p for p in offer_list if p['tag'].startswith(tag_to_remove)), None)

        if not specimen_to_remove:
            return await interaction.response.send_message(f"⚠️ Could not find a specimen starting with `{tag_to_remove}` in your current offer.", ephemeral=True)

        # 3. Remove it from the array
        offer_list.remove(specimen_to_remove)

        # 4. CRITICAL SECURITY: Un-ready both players!
        # If Player A removes a specimen while Player B is ready, Player B's ready status must be revoked so they aren't scammed.
        self.trade_view.p1_ready = False
        self.trade_view.p2_ready = False
        
        # 5. Refresh the Trading Room UI
        await self.trade_view.update_ui(interaction)

class AddSpecimenModal(discord.ui.Modal, title="Add Specimen to Exchange"):
    tag_input = discord.ui.TextInput(
        label="Specimen Tag ID", 
        placeholder="e.g. 123e4567", 
        min_length=4, 
        max_length=36
    )

    def __init__(self, trade_view, user):
        super().__init__()
        self.trade_view = trade_view
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        tag = self.tag_input.value.strip()
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Verify ownership and fetch details
        cursor.execute("""
            SELECT s.name, cp.level, cp.instance_id
            FROM caught_pokemon cp
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            WHERE cp.user_id = ? AND cp.instance_id LIKE ?
        """, (str(self.user.id), f"{tag}%"))
        
        pokemon = cursor.fetchone()
        conn.close()

        if not pokemon:
            await interaction.response.send_message(f"Could not find a specimen with Tag `{tag}` in your survey.", ephemeral=True)
            return

        # Check if they already offered it
        if self.user == self.trade_view.player1 and any(p['tag'] == pokemon[2] for p in self.trade_view.p1_offer):
            return await interaction.response.send_message("You already offered that specimen!", ephemeral=True)
        if self.user == self.trade_view.player2 and any(p['tag'] == pokemon[2] for p in self.trade_view.p2_offer):
            return await interaction.response.send_message("You already offered that specimen!", ephemeral=True)

        # Add to the correct player's offer list
        offer_data = {"name": pokemon[0], "level": pokemon[1], "tag": pokemon[2]}
        if self.user == self.trade_view.player1:
            self.trade_view.p1_offer.append(offer_data)
        else:
            self.trade_view.p2_offer.append(offer_data)

        # Safety Feature: If the trade changes, un-ready both players
        self.trade_view.p1_ready = False
        self.trade_view.p2_ready = False
        
        await self.trade_view.update_ui(interaction)


class ActiveTradeView(discord.ui.View):
    def __init__(self, player1, player2, active_trades):
        super().__init__(timeout=300) # 5 minute timeout
        self.player1 = player1
        self.player2 = player2
        self.active_trades = active_trades # Store the memory lock!
        self.message = None
        
        # Trade State
        self.p1_offer = []
        self.p2_offer = []
        self.p1_ready = False
        self.p2_ready = False

    async def on_timeout(self):
        # 1. RELEASE THE LOCKS!
        self.active_trades.discard(self.player1.id)
        self.active_trades.discard(self.player2.id)
        
        for child in self.children:
            child.disabled = True
            
        timeout_embed = self.generate_embed()
        timeout_embed.color = discord.Color.dark_grey()
        timeout_embed.title = "⏳ Exchange Session Timed Out"
        
        if self.message:
            await self.message.edit(embed=timeout_embed, view=self)

    async def execute_trade(self, interaction: discord.Interaction):
            user_a_id = str(self.player1.id)
            user_b_id = str(self.player2.id)
            
            # If both arrays are empty, there's nothing to trade!
            if not self.p1_offer and not self.p2_offer:
                return await interaction.response.edit_message(content="⚠️ Trade canceled: No biological data was offered.", view=None)
                
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()

            try:
                # 1. LOCK THE ECOSYSTEM (Start Transaction)
                cursor.execute("BEGIN TRANSACTION")

                # 2. TRANSFER P1's SPECIMENS TO P2
                for p in self.p1_offer:
                    tag = p['tag'] # Extract the tag from your dictionary!
                    cursor.execute("UPDATE caught_pokemon SET user_id = ? WHERE instance_id = ? AND user_id = ?", (user_b_id, tag, user_a_id))
                    
                    # Validation check!
                    if cursor.rowcount == 0:
                        raise ValueError(f"Validation failed for Specimen `{tag[:8]}`. It may have been modified.")

                # 3. TRANSFER P2's SPECIMENS TO P1
                for p in self.p2_offer:
                    tag = p['tag']
                    cursor.execute("UPDATE caught_pokemon SET user_id = ? WHERE instance_id = ? AND user_id = ?", (user_a_id, tag, user_b_id))
                    
                    if cursor.rowcount == 0:
                        raise ValueError(f"Validation failed for Specimen `{tag[:8]}`. It may have been modified.")

                # 4. ACTIVE PARTNER SAFETY SWEEP
                # Extract lists of just the tags so we can check them easily
                p1_tags = [p['tag'] for p in self.p1_offer]
                p2_tags = [p['tag'] for p in self.p2_offer]
                
                cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_a_id,))
                a_partner = cursor.fetchone()
                if a_partner and a_partner[0] in p1_tags:
                    cursor.execute("UPDATE users SET active_partner = NULL WHERE user_id = ?", (user_a_id,))

                cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_b_id,))
                b_partner = cursor.fetchone()
                if b_partner and b_partner[0] in p2_tags:
                    cursor.execute("UPDATE users SET active_partner = NULL WHERE user_id = ?", (user_b_id,))

                # 5. COMMIT THE BATCH TRANSFER
                conn.commit()

                # 6. RENDER YOUR BEAUTIFUL SUCCESS UI
                for child in self.children:
                    child.disabled = True
                    
                final_embed = self.generate_embed()
                final_embed.color = discord.Color.green()
                final_embed.title = "✅ Exchange Completed Successfully!"
                
                await interaction.response.edit_message(embed=final_embed, view=self)

            except ValueError as ve:
                conn.rollback()
                # If the custom error trips, safely abort and tell them why
                await interaction.response.edit_message(content=f"❌ **Trade Aborted:** {ve}", view=None, embed=None)
                
            except Exception as e:
                conn.rollback()
                await interaction.response.edit_message(content="❌ A critical database error occurred. No data was lost.", view=None, embed=None)
                print(f"Atomic Trade Error: {e}")
                
            finally:
                conn.close()
                # UNLOCK NO MATTER WHAT HAPPENS
                self.active_trades.discard(self.player1.id)
                self.active_trades.discard(self.player2.id)

    def generate_embed(self):
        embed = discord.Embed(title="🤝 Active Specimen Exchange", color=discord.Color.blue())
        
        # Format Player 1's side
        p1_status = "✅ READY" if self.p1_ready else "⏳ Deciding..."
        p1_text = ""
        for p in self.p1_offer:
            p1_text += f"• **{p['name'].capitalize()}** (Lvl {p['level']}) | `{p['tag'][:8]}`\n"
        if not p1_text: p1_text = "*Nothing offered yet.*"
        
        # Format Player 2's side
        p2_status = "✅ READY" if self.p2_ready else "⏳ Deciding..."
        p2_text = ""
        for p in self.p2_offer:
            p2_text += f"• **{p['name'].capitalize()}** (Lvl {p['level']}) | `{p['tag'][:8]}`\n"
        if not p2_text: p2_text = "*Nothing offered yet.*"

        embed.add_field(name=f"{self.player1.display_name} ({p1_status})", value=p1_text, inline=True)
        embed.add_field(name=f"{self.player2.display_name} ({p2_status})", value=p2_text, inline=True)
        return embed

    async def update_ui(self, interaction: discord.Interaction):
        # Update button colors based on ready status
        if self.p1_ready and self.p2_ready:
            await self.execute_trade(interaction)
        else:
            await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="➖ Remove Specimen", style=discord.ButtonStyle.secondary, row=0)
    async def remove_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Security Check
        if interaction.user not in [self.player1, self.player2]:
            return await interaction.response.send_message("You are not part of this exchange.", ephemeral=True)
            
        # Open the removal modal
        await interaction.response.send_modal(RemoveSpecimenModal(self, interaction.user))

    @discord.ui.button(label="➕ Add Specimen", style=discord.ButtonStyle.secondary)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in [self.player1, self.player2]:
            return await interaction.response.send_message("You are not part of this exchange.", ephemeral=True)
            
        # Open the modal so they can type the tag
        await interaction.response.send_modal(AddSpecimenModal(self, interaction.user))

    @discord.ui.button(label="✔️ Toggle Ready", style=discord.ButtonStyle.primary)
    async def ready_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in [self.player1, self.player2]:
            return await interaction.response.send_message("You are not part of this exchange.", ephemeral=True)
            
        if interaction.user == self.player1:
            self.p1_ready = not self.p1_ready
        else:
            self.p2_ready = not self.p2_ready
            
        await self.update_ui(interaction)

    @discord.ui.button(label="❌ Cancel Trade", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in [self.player1, self.player2]:
            return await interaction.response.send_message("You are not part of this exchange.", ephemeral=True)
            
        # RELEASE THE LOCKS!
        self.active_trades.discard(self.player1.id)
        self.active_trades.discard(self.player2.id)
            
        for child in self.children:
            child.disabled = True
            
        cancel_embed = self.generate_embed()
        cancel_embed.color = discord.Color.red()
        cancel_embed.title = "❌ Exchange Cancelled"
        
        await interaction.response.edit_message(embed=cancel_embed, view=self)

class TradeProposalView(discord.ui.View):
    def __init__(self, proposer, target, active_trades):
        super().__init__(timeout=120)
        self.proposer = proposer
        self.target = target
        self.active_trades = active_trades # Store the memory lock!
        self.message = None # This gets set in the command!

    async def on_timeout(self):
        """Fires automatically when the timer runs out."""
        # 1. RELEASE THE LOCKS!
        self.active_trades.discard(self.proposer.id)
        self.active_trades.discard(self.target.id)
        
        # 2. Disable buttons and update the UI
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(content="⏳ **Trade Request Expired:** The biological transfer window closed.", view=self)

    @discord.ui.button(label="Accept Request", style=discord.ButtonStyle.success)
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            return await interaction.response.send_message("Only the requested researcher can accept this.", ephemeral=True)
            
        # Pass the lock forward into the ActiveTradeView!
        active_session = ActiveTradeView(self.proposer, self.target, self.active_trades)
        
        await interaction.response.edit_message(
            content="Transfer protocols engaged.", 
            embed=active_session.generate_embed(), 
            view=active_session
        )
        # Note: We assign the message to the new view so IT can handle timeouts now!
        active_session.message = interaction.message

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in [self.proposer, self.target]:
            return await interaction.response.send_message("Not your request.", ephemeral=True)
            
        # RELEASE THE LOCKS!
        self.active_trades.discard(self.proposer.id)
        self.active_trades.discard(self.target.id)
            
        for child in self.children:
            child.disabled = True
            
        await interaction.response.edit_message(content="❌ Trade request declined.", view=self)


class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # A memory set to track the Discord IDs of users currently trading
        self.active_trades = set()

    @commands.command(name="help", aliases=["commands", "terminal"])
    @checks.has_started()
    async def custom_help(self, ctx):
        """Access the centralized bot command directory."""
        
        # You can easily expand these pages as you build new features!
        help_pages = [
            {
                "title": "Field Navigation",
                "description": "Commands for traversing the local ecosystem and acquiring specimens.",
                "commands": {
                    "`!expedition [biome]`": "Embark on a solo journey to isolate a native biological signal.",
                    "`!catch [pokemon] [ball]`": "Attempt to tag an active specimen using field equipment.",
                    "`!hint`": "Receive a message helping with the spawned pokemon's name.",
                }
            },
            {
                "title": "Laboratory & Research",
                "description": "Modify genetic traits and synthesize equipment.",
                "commands": {
                    "`!tutor [ID] [move]`": "Expend a Memory Spore to reawaken dormant neural combat pathways.",
                    "`!refine [blueprint]`": "Synthesize raw anomalies into specialized UI gear (e.g., Z-Ring).",
                    "`!analyze`": "Scans notes to assign field directives/quests.",
                    "`!survey`": "View available assigned field directives.",
                    "`!abandon`": "Gets rid of an assigned field directive/quest.",
                    "`!claim`": "Get rewards for all completed field directives/quests.",
                    "`!inventory`": "View all your caught pokemon.",
                    "`!view [ID]`": "Inspect a specimen's biometrics, statistics, and genetic footprint.",
                    "`!nickname`": "Assign your pokemon a custom name",
                    "`!settag`": "Give your pokemon a special tag to help sorting.",
                    "`!release`": "Re-Home a pokemon in exchange for Eco-Tokens.",
                    "`!partner`": "Set a specific pokemon to be your partner.",
                    "`!equip`": "Assign an owned item to a specific pokemon.",
                    "`!unequip`": "Remove an owned item to a specific pokemon.",
                    "`!evolve`": "Manually evolve a pokemon with an item.",

                }
            },
            {
                "title": "Logistics & Commerce",
                "description": "Manage your inventory, economy, and trades.",
                "commands": {
                    "`!profile`": "View your Ecological Visas, Eco-Tokens, and active Field Energy.",
                    "`!backpack`": "Open your paginated inventory of field equipment and materials.",
                    "`!techmoves`": "View all your available Technical Machines (TMs).",
                    "`!market`": "View the supply catalog for equipment.",
                    "`!tmshop`": "View the market for Technical Machines (TMs).",
                    "`!shop`": "Displays items from a rotating daily market.",
                    "`!gts`": "Access the Global Trade System to buy globally sold pokemon.",
                    "`!buy [qty] [item]`": "Securely requisition items using Eco-Tokens.",
                    "`!trade @user`": "Initiate an atomic, multi-specimen transfer with another researcher."
                }
            },
            {
                "title": "Battling & Sector Wardens",
                "description": "Test your might against highly intelligent players and Sector Wardens.",
                "commands": {
                    "`!npcduel`": "Battle NPCs with a party.",
                    "`!challenge`": "Start a battle with a biome's Sector Warden.",
                    "`!movedex`": "Check all available moves for one of your pokemon.",
                    "`!moves`": "Check a species 4 current moves.",
                    "`!party`": "Customise and view your battle ready team.",
                    "`!learn`": "Teach an owned specified species a level up move",
                    "`!duel`": "Battle other players with a party.",
                }
            },
            {
                "title": "Ecosystem Support",
                "description": "Commands to help maintain your server's ecosystem.",
                "commands": {
                    "`!sethabitat`": "Choose where the server spawns pokemon",
                    "`!habitat`": "View your server's habitat status.",
                    "`!use`": "Use items such as purifiers to clean up a major disaster event.",
                    "`!deploy`": "Send out your pokemon to complete environmental cleanup fieldwork.",
                    "`!clean`": "Work together with your pokemon to raise the server's ecosystem health.",
                    "`!plant`": "Sow seeds and grow plants to raise the sever's ecosystem health.",
                    "`!reforest`": "Shift the biome to a forest with a major terraforming project.",
                    "`!purify`": "Shift the biome to a Coastal one with a major terraforming project.",
                    "`!terraform`": "Start a major terraforming project to change the current biome.",
                    "`!intervene`": "Interact with special disaster events with a specific pokemon.",
                }
            }
        ]
        
        view = HelpPaginator(ctx.author, help_pages)
        await ctx.send(embed=view.generate_embed(), view=view)

    @commands.command(name="wipe", aliases=["purge_user", "eradicate"])
    @commands.is_owner() # <--- Administrative Firewall!
    async def wipe_user_data(self, ctx, target_user: discord.User):
        """[ADMIN] Completely eradicates a user's biological and financial records from the database."""
        user_id = str(target_user.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. Verify the subject actually exists in the database
            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            if not cursor.fetchone():
                conn.close()
                return await ctx.send(f"⚠️ **Target Not Found:** `{target_user.name}` is not registered in the ecological database.")
            
            # ==========================================
            # 2. THE CASCADING DATA PURGE
            # ==========================================
            # Remove active market listings
            cursor.execute("DELETE FROM global_market WHERE seller_id = ?", (user_id,))
            
            # Clear financial and material assets
            cursor.execute("DELETE FROM user_inventory WHERE user_id = ?", (user_id,))
            
            # Wipe active and completed research tasks
            cursor.execute("DELETE FROM field_directives WHERE user_id = ?", (user_id,))
            
            # Erase local sector contributions
            cursor.execute("DELETE FROM guild_members WHERE user_id = ?", (user_id,))
            
            # Terminate the tactical roster bindings
            cursor.execute("DELETE FROM user_party WHERE user_id = ?", (user_id,))
            
            # Release all captured specimens back into the void
            cursor.execute("DELETE FROM caught_pokemon WHERE user_id = ?", (user_id,))
            
            # Finally, execute the core profile
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            # ==========================================
            
            # 3. Commit the eradication
            conn.commit()
            
            embed = discord.Embed(
                title="☣️ ECOLOGICAL PURGE AUTHORIZED",
                description=f"All biometric, financial, and tactical records belonging to **{target_user.name}** (`{user_id}`) have been completely eradicated from the system.",
                color=discord.Color.dark_red()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Data Eradication Error: {e}")
            await ctx.send("❌ A critical failure occurred during the database purge. Check the terminal.")
        finally:
            if conn:
                conn.close()

    @commands.command(name="ban", aliases=["revoke_license"])
    @commands.is_owner()
    async def ban_user(self, ctx, target_user: discord.User, *, reason: str = "Violation of Ecological Directives."):
        """[ADMIN] Revokes a user's research license, locking them out of the ecosystem."""
        user_id = str(target_user.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO banned_personnel (user_id, reason) 
                VALUES (?, ?)
            """, (user_id, reason))
            conn.commit()
            
            embed = discord.Embed(
                title="⚖️ License Revoked", 
                description=f"**{target_user.name}** (`{user_id}`) has been permanently banned from the simulation.\n**Reason:** {reason}",
                color=discord.Color.dark_red()
            )
            await ctx.send(embed=embed)
            
        except sqlite3.IntegrityError:
            await ctx.send(f"⚠️ **{target_user.name}** is already on the banned personnel list.")
        except Exception as e:
            print(f"Ban Error: {e}")
            await ctx.send("❌ A database error occurred while updating the security ledger.")
        finally:
            conn.close()

    @commands.command(name="unban", aliases=["restore_license"])
    @commands.is_owner()
    async def unban_user(self, ctx, target_user: discord.User):
        """[ADMIN] Restores a user's research license."""
        user_id = str(target_user.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM banned_personnel WHERE user_id = ?", (user_id,))
            if cursor.rowcount > 0:
                conn.commit()
                await ctx.send(f"✅ **License Restored:** **{target_user.name}** (`{user_id}`) has been cleared for fieldwork.")
            else:
                await ctx.send(f"⚠️ **{target_user.name}** is not currently on the banned list.")
                
        except Exception as e:
            print(f"Unban Error: {e}")
        finally:
            conn.close()

    @commands.command(name="trade", aliases=["exchange"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat() # Can't trade while fighting!
    # Note: We don't put @is_not_in_trade here, because we handle the check manually below to check BOTH users!
    async def start_trade(self, ctx, target_user: discord.Member):
        author_id = ctx.author.id
        target_id = target_user.id

        if ctx.author == target_user:
            return await ctx.send("⚠️ You cannot trade with yourself!")
        if target_user.bot:
            return await ctx.send("🤖 Automated drones do not participate in biological exchanges.")

        # 1. Check if EITHER user is already in a trade
        if author_id in self.active_trades:
            return await ctx.send("🛑 You are already in an active trade negotiation!")
        if target_id in self.active_trades:
            return await ctx.send(f"🛑 **{target_user.display_name}** is currently busy in another exchange.")

        # 2. Lock BOTH users into the trading state
        self.active_trades.add(author_id)
        self.active_trades.add(target_id)

        # 3. Pass the active_trades reference to the View so it can unlock them later!
        # Pass the active_trades memory set into the View!
        view = TradeProposalView(ctx.author, target_user, self.active_trades)
        
        # Save the message to the view so on_timeout can edit it!
        view.message = await ctx.send(f"📡 {target_user.mention}, **{ctx.author.display_name}** is requesting an ecological specimen exchange.", view=view)

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    @checks.has_started()
    @checks.is_authorized()
    async def leaderboard(self, ctx, scope: str = "local"):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        scope = scope.lower()
        
        if scope in ["global", "world", "all"]:
            # --- GLOBAL LEADERBOARD ---
            cursor.execute("""
                SELECT user_id, SUM(contribution_points) as total_cp 
                FROM guild_members 
                GROUP BY user_id 
                ORDER BY total_cp DESC 
                LIMIT 10
            """)
            results = cursor.fetchall()
            
            embed = discord.Embed(title="🌍 Global Ecologist Rankings", color=discord.Color.blue())
            embed.description = "The top 10 environmental researchers across all known habitats!"
            
        else:
            # --- LOCAL LEADERBOARD ---
            guild_id = str(ctx.guild.id)
            cursor.execute("""
                SELECT user_id, contribution_points 
                FROM guild_members 
                WHERE guild_id = ? 
                ORDER BY contribution_points DESC 
                LIMIT 10
            """, (guild_id,))
            results = cursor.fetchall()
            
            embed = discord.Embed(title=f"📍 Local Ecosystem Leaders: {ctx.guild.name}", color=discord.Color.green())
            embed.description = "The top 10 researchers maintaining this specific server's habitat."

        conn.close()

        if not results:
            await ctx.send("No environmental data has been recorded for this leaderboard yet!")
            return

        # Build the leaderboard text
        board_text = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for index, row in enumerate(results):
            user_id = row[0]
            points = row[1]
            
            # Try to get the user's actual Discord name
            user_obj = await commands.fetch_user(int(user_id))
            username = user_obj.name if user_obj else f"Unknown Researcher ({user_id[-4:]})"
            
            # Assign medals to the top 3, and numbers to the rest
            rank_icon = medals[index] if index < 3 else f"**{index + 1}.**"
            
            board_text += f"{rank_icon} **{username}** — ⭐ {points} Points\n"
            
        embed.add_field(name="Rankings", value=board_text, inline=False)
        
        # Add a fun footer
        if scope in ["global", "world", "all"]:
            embed.set_footer(text="Keep deploying your partners and clearing hazards to climb the global ranks!")
        else:
            embed.set_footer(text="Use `!leaderboard global` to see the worldwide rankings!")

        await ctx.send(embed=embed)

    @commands.command(name="profile", aliases=["impact"])
    @checks.has_started()
    @checks.is_authorized()
    async def profile(self, ctx):
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # --- UPDATED: Added current_energy and last_energy_tick to the SELECT query ---
        cursor.execute("SELECT eco_tokens, unlocked_visas, current_energy, last_energy_tick FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        
        tokens = user_data[0] if user_data else 0
        visas_raw = user_data[1] if user_data and len(user_data) > 1 and user_data[1] else "canopy"
        
        # Safely extract energy data (defaults to 100 energy, 0 tick if not found)
        db_energy = user_data[2] if user_data and len(user_data) > 2 else 100
        last_tick = user_data[3] if user_data and len(user_data) > 3 else 0
        
        # Get local contribution points
        cursor.execute("SELECT contribution_points FROM guild_members WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        member_data = cursor.fetchone()
        contribution = member_data[0] if member_data else 0
        
        # Get total catches
        cursor.execute("SELECT COUNT(*) FROM caught_pokemon WHERE user_id = ?", (user_id,))
        total_catches = cursor.fetchone()[0]
        
        conn.close()
        
        # ==========================================
        # LAZY-EVALUATION ENERGY MATH
        # ==========================================
        MAX_ENERGY = 100
        REGEN_PER_HOUR = 10
        SECONDS_IN_HOUR = 3600
        
        now = int(time.time())
        display_energy = db_energy
        regen_text = "(MAX)"
        
        if db_energy < MAX_ENERGY:
            seconds_passed = now - last_tick
            hours_passed = seconds_passed // SECONDS_IN_HOUR
            
            # Calculate what their energy is *right now* based on time passed
            energy_gained = int(hours_passed * REGEN_PER_HOUR)
            display_energy = min(MAX_ENERGY, db_energy + energy_gained)
            
            if display_energy < MAX_ENERGY:
                # How many seconds until the NEXT hour rolls over?
                # We use modulo to find the remainder of the current hour!
                next_tick_in = SECONDS_IN_HOUR - (seconds_passed % SECONDS_IN_HOUR)
                mins, secs = divmod(next_tick_in, 60)
                regen_text = f"(+10 in {mins}m {secs}s)"
        # ==========================================
        
        # Format the Visas beautifully for the UI
        biome_emojis = {
            'canopy': '🌲 Canopy',
            'trench': '🌊 Trench',
            'core': '🌋 Core',
            'sprawl': '🏙️ Sprawl'
        }
        
        unlocked_list = [biome_emojis.get(b.strip(), b.title()) for b in visas_raw.split(',') if b.strip()]
        visas_display = " • ".join(unlocked_list)
        
        # Build the Embed
        embed = discord.Embed(title=f"🌿 {ctx.author.name}'s Ecological Profile", color=discord.Color.green())
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        
        # --- Inject the Stamina row ---
        embed.add_field(name="🔋 Field Energy", value=f"**{display_energy} / {MAX_ENERGY}**\n*{regen_text}*", inline=False)
        
        embed.add_field(name="Global Eco-Tokens", value=f"🪙 {tokens:,}", inline=True)
        embed.add_field(name="Local Contribution", value=f"⭐ {contribution:,} points", inline=True)
        embed.add_field(name="Specimens Rescued", value=f"🐾 {total_catches} total", inline=True)
        
        # Inject the Sector Clearance row at the bottom
        embed.add_field(name="🛂 Sector Clearance (Visas)", value=f"**{visas_display}**", inline=False)
        
        embed.set_footer(text=f"Server: {ctx.guild.name}")
        
        await ctx.send(embed=embed)



async def setup(bot):
    await bot.add_cog(Social(bot))