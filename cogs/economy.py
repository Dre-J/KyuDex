import datetime
import random
import discord
from discord.ext import commands
import sqlite3
from utils.constants import DB_FILE, EQUIPMENT_CATALOG, TM_SHOP
from utils import checks
import math

class BackpackPaginator(discord.ui.View):
    def __init__(self, user, inventory_data, catalog):
        super().__init__(timeout=120) # 2 minute timeout
        self.user = user
        self.inventory_data = inventory_data
        self.catalog = catalog
        
        # UI Settings
        self.items_per_page = 5
        self.total_pages = math.ceil(len(inventory_data) / self.items_per_page)
        self.current_page = 1
        
        self.update_buttons()

    def update_buttons(self):
        """Disables navigation buttons if at the start or end of the catalog."""
        self.children[0].disabled = self.current_page <= 1
        self.children[1].disabled = self.current_page >= self.total_pages

    def generate_embed(self):
        """Slices the inventory list and builds the UI for the current page."""
        embed = discord.Embed(
            title=f"🎒 {self.user.name}'s Field Equipment", 
            color=discord.Color.orange(),
            description=f"**Page {self.current_page} of {self.total_pages}**"
        )
        
        # Calculate the slice indices (e.g., Page 1: 0 to 5, Page 2: 5 to 10)
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.inventory_data[start_idx:end_idx]
        
        for raw_item_name, quantity in page_items:
            # 1. DATA SANITIZATION
            clean_key = raw_item_name.lower().replace(" ", "").replace("-", "")
            
            # 2. Safe Dictionary Lookup
            item_data = self.catalog.get(clean_key)
            
            if item_data:
                display_name = item_data.get('name', raw_item_name.title())
                emoji = item_data.get('emoji', '📦')
                desc = item_data.get('desc', '*No description available.*')
            else:
                display_name = raw_item_name.title()
                emoji = "📦"
                desc = "*Archived/Unknown Anomaly*"
                
            embed.add_field(
                name=f"{emoji} {display_name}", 
                value=f"**Quantity:** {quantity}\n{desc}", 
                inline=False
            )
            
        return embed

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.primary, custom_id="bp_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ This is not your field pack!", ephemeral=True)
            
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary, custom_id="bp_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ This is not your field pack!", ephemeral=True)
            
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

class MarketPaginator(discord.ui.View):
    def __init__(self, ctx, listings):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.listings = listings # Array of dictionaries containing the listing data
        self.current_page = 0
        self.items_per_page = 5 # 5 items per page keeps the UI clean and readable
        
        self.max_pages = max(1, math.ceil(len(listings) / self.items_per_page))
        self.update_buttons()

    def update_buttons(self):
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page >= self.max_pages - 1

    def create_embed(self):
        embed = discord.Embed(title="🌐 Global Transfer Station", color=discord.Color.gold())
        embed.description = "Active biological assets available for procurement."

        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        chunk = self.listings[start:end]

        if not chunk:
            embed.description = "The market is currently empty. Use `!gts sell` to list an asset!"
        else:
            for item in chunk:
                shiny_icon = "🌟" if item['is_shiny'] else "🌿"
                
                # Format the time remaining cleanly
                embed.add_field(
                    name=f"Listing #{item['list_id']} | {shiny_icon} {item['name'].capitalize()} (Lv. {item['level']})",
                    value=f"**Price:** 🪙 {item['price']:,} Tokens\n**Seller ID:** `{item['seller']}`\n**Listed Pokemon ID:** `{item['uuid'][:8]}`",
                    inline=False
                )

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} | Use !gts buy [Listing ID]")
        return embed

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Please run your own `!gts view` command to browse.", ephemeral=True)
            
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Please run your own `!gts view` command to browse.", ephemeral=True)
            
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_daily_shop(self):
        """Generates a shop that remains static for 24 hours and changes at midnight."""
        # 1. Get today's date as a unique integer
        today = datetime.date.today().toordinal()
        
        # 2. Lock the randomizer to today's date
        random.seed(today) 

        # 3. Define the supply lines
        standard_items = [
            ("greatball", 25), 
            ("potion", 20), 
            ("purifier", 50)
        ]
        
        exclusive_items = [
            ("ultraball", 75), ("full-restore", 100), 
            ("rare-candy", 500), ("masterball", 5000)
        ]

        # 4. Generate today's inventory
        # Shuffle prices slightly for a dynamic economy (+/- 10%)
        shop_inventory = []
        selected_standards = random.sample(standard_items, 3)
        
        for item, base_price in selected_standards:
            dynamic_price = int(base_price * random.uniform(0.9, 1.1))
            shop_inventory.append({"name": item, "price": dynamic_price, "type": "standard"})

        # 25% chance for a rare black-market/exclusive item to appear!
        if random.random() <= 0.25:
            exclusive = random.choice(exclusive_items)
            dynamic_price = int(exclusive[1] * random.uniform(0.95, 1.2))
            shop_inventory.append({"name": exclusive[0], "price": dynamic_price, "type": "exclusive"})

        # 5. CRITICAL: Reset the randomizer so we don't break combat RNG!
        random.seed() 

        return shop_inventory

        
    @commands.command(name="shop", aliases=["daily"])
    @checks.has_started()
    async def view_shop(self, ctx):
        """Views the revolving daily supply drop."""
        inventory = self.get_daily_shop()
        
        embed = discord.Embed(title="🛒 Daily Supply Outpost", color=discord.Color.gold())
        embed.description = "New supplies arrive at midnight. Spend your Eco-Tokens wisely!"
        
        for item in inventory:
            icon = "🌟" if item['type'] == "exclusive" else "📦"
            embed.add_field(
                name=f"{icon} {item['name'].replace('-', ' ').title()}", 
                value=f"**Price:** 🪙 {item['price']} Tokens", 
                inline=False
            )
            
        embed.set_footer(text="Use !buy [item_name] [quantity] to purchase.")
        await ctx.send(embed=embed)
    
    # This creates the base command group. If they just type !gts, it shows them the help menu.
    @commands.group(name="gts", invoke_without_command=True)
    @checks.has_started()
    @checks.is_authorized()
    async def global_trade_station(self, ctx):
        """Base command for the Global Trade Station."""
        embed = discord.Embed(title="🌐 Global Transfer Station", color=discord.Color.blue())
        embed.description = (
            "`!gts sell [Tag ID] [Price]` - List a specimen on the market.\n"
            "`!gts view` - Browse available assets.\n"
            "`!gts buy [Listing ID]` - Procure a specimen."
        )
        await ctx.send(embed=embed)

    @global_trade_station.command(name="sell")
    @checks.has_started()
    @checks.is_authorized()
    async def gts_sell(self, ctx, tag_id: str, price: int):
        """Lists a specimen on the global market for 48 hours."""
        user_id = str(ctx.author.id)
        
        if price <= 0:
            return await ctx.send("⚠️ You must request a conservation grant of at least 1 Eco-Token.")
            
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. Verify Ownership & Retrieve Specimen Data (Box Number or UUID)
            if tag_id.isdigit() and len(tag_id) <= 6:
                cursor.execute("""
                    WITH Roster AS (
                        SELECT cp.instance_id, s.name, cp.level, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ?
                    ) SELECT instance_id, name, level FROM Roster WHERE box_number = ?
                """, (user_id, int(tag_id)))
            else:
                cursor.execute("""
                    SELECT cp.instance_id, s.name, cp.level 
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.instance_id LIKE ? AND cp.user_id = ?
                """, (f"{tag_id}%", user_id))
            
            pokemon_data = cursor.fetchone()
            
            if not pokemon_data:
                conn.close()
                return await ctx.send("❌ Could not locate that specimen in your survey notebook.")
                
            actual_tag, name, level = pokemon_data
            
            # 2. Security Check: Prevent selling active party members
            cursor.execute("SELECT slot FROM user_party WHERE instance_id = ?", (actual_tag,))
            if cursor.fetchone():
                conn.close()
                return await ctx.send("⚠️ You cannot transfer a specimen that is currently assigned to your active field roster! Remove it from your party first.")
                
            # 3. Security Check: Prevent duplicate listings
            cursor.execute("SELECT listing_id FROM global_market WHERE instance_id = ?", (actual_tag,))
            if cursor.fetchone():
                conn.close()
                return await ctx.send("⚠️ This specimen is already listed on the open market!")
                
            # 4. Process the Listing (Generate a 48-hour expiration timestamp)
            expiration_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=48)
            
            cursor.execute("""
                INSERT INTO global_market (seller_id, instance_id, price, expires_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, actual_tag, price, expiration_date.strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            
            # 5. Confirmation UI
            embed = discord.Embed(title="🌐 Global Transfer Authorized", color=discord.Color.gold())
            embed.description = f"**{ctx.author.name}** has listed a **Level {level} {name.capitalize()}** on the open market."
            embed.add_field(name="Requested Grant", value=f"🪙 {price:,} Eco-Tokens", inline=True)
            embed.add_field(name="Expiration", value="⏳ 48 Hours", inline=True)
            embed.set_footer(text=f"Tag ID: {actual_tag[:8]}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"GTS Sell Error: {e}")
            await ctx.send("❌ A database error occurred while processing the transfer.")
        finally:
            conn.close()

    @global_trade_station.command(name="view", aliases=["browse", "market"])
    @checks.has_started()
    @checks.is_authorized()
    async def gts_view(self, ctx):
        """Browses all active listings on the Global Trade Station."""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. GARBAGE COLLECTION: Delete expired listings automatically!
            cursor.execute("DELETE FROM global_market WHERE expires_at < CURRENT_TIMESTAMP")
            conn.commit()
            
            # 2. Fetch all active listings, joining the biological data AND fetching instance_id
            cursor.execute("""
                SELECT gm.listing_id, gm.price, gm.seller_id,
                       s.name, cp.level, cp.is_shiny, gm.instance_id
                FROM global_market gm
                JOIN caught_pokemon cp ON gm.instance_id = cp.instance_id
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                ORDER BY gm.listed_at DESC
            """)
            
            rows = cursor.fetchall()
            
            # 3. Package the data for the UI
            market_data = []
            for row in rows:
                market_data.append({
                    'list_id': row[0],
                    'price': row[1],
                    'seller': row[2],
                    'name': row[3],
                    'level': row[4],
                    'is_shiny': row[5],
                    'uuid': row[6] 
                })
                
            # 4. Boot up the Paginator
            view = MarketPaginator(ctx, market_data)
            await ctx.send(embed=view.create_embed(), view=view)
            
        except Exception as e:
            print(f"GTS View Error: {e}")
            await ctx.send("❌ A database error occurred while accessing the market network.")
        finally:
            conn.close()

    @global_trade_station.command(name="inspect", aliases=["info", "view_listing"])
    @checks.has_started()
    @checks.is_authorized()
    async def gts_inspect(self, ctx, listing_id: int):
        """Runs a complete genetic and tactical assay on a specific market listing."""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. The Deep Dive Query (Now pulling the gmax_factor)
            cursor.execute("""
                SELECT gm.price, gm.seller_id, gm.expires_at,
                       cp.pokedex_id, s.name, cp.level, cp.nature, cp.is_shiny, cp.ability,
                       cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                       cp.gmax_factor
                FROM global_market gm
                JOIN caught_pokemon cp ON gm.instance_id = cp.instance_id
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                WHERE gm.listing_id = ?
            """, (listing_id,))
            
            data = cursor.fetchone()
            
            if not data:
                return await ctx.send(f"❌ Listing `#{listing_id}` does not exist or has already expired.")
                
            # Unpack the massive data payload, including the new marker
            price, seller_id, expires_at, p_id, name, level, nature, is_shiny, ability, iv_hp, iv_atk, iv_def, iv_spa, iv_spd, iv_spe, gmax_factor = data
            
            # 2. Calculate Genetic Potential (IVs)
            iv_total = iv_hp + iv_atk + iv_def + iv_spa + iv_spd + iv_spe
            iv_percentage = int((iv_total / 186.0) * 100)
            
            # 3. Handle the Expiration Timestamp for Discord's UI
            dt_obj = datetime.datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
            dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)
            unix_timestamp = int(dt_obj.timestamp())
            
            # 4. Construct the Image URL
            base_url = "https://raw.githubusercontent.com/Dre-J/pokebotsprites/refs/heads/master/sprites/pokemon/other/official-artwork"
            img_url = f"{base_url}/shiny/{p_id}.png" if is_shiny else f"{base_url}/{p_id}.png"
            
            # 5. Build the UI
            shiny_icon = "🌟" if is_shiny else "🌿"
            gmax_marker = " 🌀 **(G-Max Capable)**" if gmax_factor else ""
            
            embed = discord.Embed(title=f"📋 Market Assay: Listing #{listing_id}", color=discord.Color.teal())
            
            # Seller & Price Info
            embed.add_field(name="Seller ID", value=f"`{seller_id}`", inline=True)
            embed.add_field(name="Procurement Cost", value=f"🪙 **{price:,}** Tokens", inline=True)
            embed.add_field(name="Time Remaining", value=f"<t:{unix_timestamp}:R>", inline=True)
            
            # Biological Specs
            embed.add_field(
                name=f"Biological Profile", 
                value=f"**Species:** {shiny_icon} {name.capitalize()}{gmax_marker}\n**Level:** {level}\n**Nature:** {nature.capitalize()}\n**Ability:** {ability.replace('-', ' ').title() if ability else 'Unknown'}", 
                inline=False
            )
            
            # Genetic Assay (IVs formatted neatly in a code block)
            iv_block = f"""```text
HP:  {iv_hp:<2} | SpA: {iv_spa:<2}
Atk: {iv_atk:<2} | SpD: {iv_spd:<2}
Def: {iv_def:<2} | Spe: {iv_spe:<2}
```"""
            embed.add_field(name=f"🧬 Genetic Potential ({iv_percentage}%)", value=iv_block, inline=False)
            
            # Display the actual asset
            embed.set_image(url=img_url)
            embed.set_footer(text=f"Use !gts buy {listing_id} to authorize this transfer.")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"GTS Inspect Error: {e}")
            await ctx.send("A database error occurred while running the genetic assay.")
        finally:
            if conn:
                conn.close()
    
    @global_trade_station.command(name="buy", aliases=["procure", "purchase"])
    @checks.is_not_in_combat()
    @checks.has_started()
    @checks.is_not_in_trade()
    @checks.is_authorized()
    async def gts_buy(self, ctx, listing_id: int):
        """Procures a specimen from the global market."""
        buyer_id = str(ctx.author.id)
  
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. Fetch and Verify the Listing
            cursor.execute("""
                SELECT seller_id, instance_id, price 
                FROM global_market 
                WHERE listing_id = ? AND expires_at >= CURRENT_TIMESTAMP
            """, (listing_id,))
            listing = cursor.fetchone()
            
            if not listing:
                conn.close()
                return await ctx.send(f"❌ Listing `#{listing_id}` does not exist or has expired.")
                
            seller_id, instance_id, price = listing
            
            if buyer_id == seller_id:
                conn.close()
                return await ctx.send("⚠️ You cannot procure your own asset! (We will build a `!gts cancel` command to retrieve these).")
                
            # 2. Check the Buyer's Funding
            cursor.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (buyer_id,))
            buyer_data = cursor.fetchone()
            buyer_balance = buyer_data[0] if buyer_data else 0
            
            if buyer_balance < price:
                conn.close()
                return await ctx.send(f"🪙 Grant denied. You need **{price:,}** Eco-Tokens to procure this asset (Current Balance: {buyer_balance:,}).")
                
            # ==========================================
            # 3. EXECUTE THE ATOMIC TRANSACTION
            # ==========================================
            # Explicitly start the transaction!
            cursor.execute("BEGIN TRANSACTION")
            
            # A. Deduct funds from the buyer
            cursor.execute("UPDATE users SET eco_tokens = eco_tokens - ? WHERE user_id = ?", (price, buyer_id))
            
            # B. Transfer funds to the seller (Using UPSERT in case they don't have a wallet yet)
            cursor.execute("""
                INSERT INTO users (user_id, eco_tokens) 
                VALUES (?, ?) 
                ON CONFLICT(user_id) DO UPDATE SET eco_tokens = eco_tokens + ?
            """, (seller_id, price, price))
            
            # C. Reassign biological ownership
            cursor.execute("UPDATE caught_pokemon SET user_id = ? WHERE instance_id = ?", (buyer_id, instance_id))
            
            # D. Destroy the market listing
            cursor.execute("DELETE FROM global_market WHERE listing_id = ?", (listing_id,))
            
            # E. Fetch species name for the receipt
            cursor.execute("""
                SELECT s.name FROM caught_pokemon cp 
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id 
                WHERE cp.instance_id = ?
            """, (instance_id,))
            species_name = cursor.fetchone()[0]
            
            # COMMIT locks in all 5 steps permanently!
            conn.commit()
            
            # 4. Generate the Transaction Receipt
            embed = discord.Embed(title="🤝 Procurement Successful!", color=discord.Color.green())
            embed.description = f"**{ctx.author.name}** successfully secured the **{species_name.capitalize()}**!"
            embed.add_field(name="Conservation Grant Paid", value=f"🪙 {price:,} Tokens", inline=True)
            embed.add_field(name="Remaining Balance", value=f"🪙 {buyer_balance - price:,} Tokens", inline=True)
            embed.set_footer(text=f"Tag ID: {instance_id[:8]} | Seller ID: {seller_id}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            # CRITICAL SAFETY NET: Undo the entire transaction if it crashed midway!
            if conn.in_transaction:
                conn.rollback() 
            print(f"GTS Buy Error: {e}")
            await ctx.send("❌ A critical database error occurred. The transaction has been securely aborted and no tokens were lost.")
        finally:
            conn.close()

    @global_trade_station.command(name="cancel", aliases=["remove", "delist", "retrieve"])
    async def gts_cancel(self, ctx, listing_id: int):
        """Removes your own specimen from the global market."""
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. Security Check: Verify existence and ownership
            cursor.execute("""
                SELECT seller_id, instance_id 
                FROM global_market 
                WHERE listing_id = ?
            """, (listing_id,))
            
            listing = cursor.fetchone()
            
            if not listing:
                return await ctx.send(f"❌ Listing `#{listing_id}` does not exist. It may have already expired or been purchased.")
                
            seller_id, instance_id = listing
            
            if seller_id != user_id:
                return await ctx.send("⚠️ Security Alert: You can only delist your own ecological assets!")
                
            # 2. Fetch the species name for the UI before we delete the record
            cursor.execute("""
                SELECT s.name 
                FROM caught_pokemon cp
                JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                WHERE cp.instance_id = ?
            """, (instance_id,))
            species_data = cursor.fetchone()
            species_name = species_data[0] if species_data else "Unknown Specimen"

            # 3. Destroy the Escrow Record
            cursor.execute("DELETE FROM global_market WHERE listing_id = ?", (listing_id,))
            conn.commit()
            
            # 4. Confirmation UI
            embed = discord.Embed(title="📥 Asset Retrieved", color=discord.Color.dark_gray())
            embed.description = f"**{ctx.author.name}** has safely recalled their **{species_name.capitalize()}** from the open market."
            embed.set_footer(text="The specimen is now available for field deployment.")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"GTS Cancel Error: {e}")
            await ctx.send("A database error occurred while trying to retrieve your asset.")
        finally:
            conn.close()

    @commands.command(name="equip")
    @checks.has_started()
    @checks.is_not_in_combat()
    @checks.is_authorized()
    async def equip_item(self, ctx, instance_id: str, *, item_name: str):
        """Attaches a symbiotic item or tactical gear to a specific specimen."""
        user_id = str(ctx.author.id)
        formatted_item = item_name.lower().replace(" ", "-") 

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            # 1. START ATOMIC TRANSACTION
            cursor.execute("BEGIN TRANSACTION")

            # 2. Verify Specimen Ownership (Box Number or UUID)
            if instance_id.isdigit() and len(instance_id) <= 6:
                cursor.execute("""
                    WITH Roster AS (
                        SELECT cp.instance_id, s.name, cp.held_item, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ?
                    ) SELECT instance_id, name, held_item FROM Roster WHERE box_number = ?
                """, (user_id, int(instance_id)))
            else:
                cursor.execute("""
                    SELECT cp.instance_id, s.name, cp.held_item 
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.instance_id LIKE ? AND cp.user_id = ?
                """, (f"{instance_id}%", user_id))
            
            specimen = cursor.fetchone()
            
            if not specimen:
                conn.rollback()
                return await ctx.send("❌ Specimen not found. Ensure you are using the correct Box Number or Tag ID.")
                
            full_instance_id, raw_specimen_name, current_held_item = specimen
            specimen_name = raw_specimen_name.capitalize()

            # 3. UNEQUIP LOGIC (If they type "!equip [ID] none")
            if formatted_item in ["none", "unequip"]:
                if current_held_item == "none" or not current_held_item:
                    conn.rollback()
                    return await ctx.send(f"⚠️ **{specimen_name}** is not currently holding any equipment.")
                
                cursor.execute("""
                    INSERT INTO user_inventory (user_id, item_name, quantity) 
                    VALUES (?, ?, 1) 
                    ON CONFLICT(user_id, item_name) 
                    DO UPDATE SET quantity = quantity + 1
                """, (user_id, current_held_item))
                
                cursor.execute("UPDATE caught_pokemon SET held_item = 'none' WHERE instance_id = ?", (full_instance_id,))
                conn.commit()
                
                return await ctx.send(f"🎒 You detached the `{current_held_item.replace('-', ' ').title()}` from **{specimen_name}** and returned it to your pack.")

            # 4. Verify Inventory Ownership for the New Item
            cursor.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, formatted_item))
            inv_data = cursor.fetchone()
            
            if not inv_data or inv_data[0] < 1:
                conn.rollback()
                return await ctx.send(f"⚠️ **Logistics Error:** You do not have any `{formatted_item.replace('-', ' ').title()}` in your field backpack.")

            # 5. EXECUTE THE ATOMIC SWAP
            cursor.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, formatted_item))
            
            if current_held_item and current_held_item != 'none':
                cursor.execute("""
                    INSERT INTO user_inventory (user_id, item_name, quantity) 
                    VALUES (?, ?, 1) 
                    ON CONFLICT(user_id, item_name) 
                    DO UPDATE SET quantity = quantity + 1
                """, (user_id, current_held_item))
                swap_msg = f"\n*The previously held `{current_held_item.replace('-', ' ').title()}` was returned to your pack.*"
            else:
                swap_msg = ""

            cursor.execute("UPDATE caught_pokemon SET held_item = ? WHERE instance_id = ?", (formatted_item, full_instance_id))
            conn.commit()

            embed = discord.Embed(title="🎒 Tactical Equipment Assigned", color=discord.Color.green())
            embed.description = f"**{ctx.author.name}** equipped `{formatted_item.replace('-', ' ').title()}` to **{specimen_name}**!{swap_msg}"
            embed.set_footer(text=f"Tag ID: {full_instance_id[:8]}")
            
            await ctx.send(embed=embed)

        except Exception as e:
            if conn.in_transaction:  
                conn.rollback()
            print(f"Equip Error: {e}")
            await ctx.send("❌ A database error occurred while assigning the equipment. No items were lost.")
        finally:
            conn.close()

    @commands.command(name="unequip", aliases=["remove_item", "detach"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat()
    @checks.is_not_in_trade()
    async def unequip_item(self, ctx, instance_id: str):
        """Safely removes tactical gear from a specimen and returns it to the backpack."""
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        try:
            # 1. RETRIEVE THE SPECIMEN & HELD ITEM (Box Number or UUID)
            if instance_id.isdigit() and len(instance_id) <= 6:
                cursor.execute("""
                    WITH Roster AS (
                        SELECT cp.instance_id, s.name, cp.held_item, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ?
                    ) SELECT instance_id, name, held_item FROM Roster WHERE box_number = ?
                """, (user_id, int(instance_id)))
            else:
                cursor.execute("""
                    SELECT cp.instance_id, s.name, cp.held_item 
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.instance_id LIKE ? AND cp.user_id = ?
                """, (f"{instance_id}%", user_id))
            
            specimen = cursor.fetchone()
            
            if not specimen:
                return await ctx.send("❌ Specimen not found. Ensure you are using the correct Box Number or Tag ID.")

            full_instance_id, raw_name, held_item = specimen
            specimen_name = raw_name.capitalize()

            # 2. CHECK IF IT ACTUALLY HAS AN ITEM
            if not held_item or held_item == 'none':
                return await ctx.send(f"⚠️ **{specimen_name}** is not currently equipped with any tactical gear.")

            # 3. ATOMIC TRANSACTION
            cursor.execute("BEGIN TRANSACTION")

            # A. Push the item safely back into the user's inventory
            cursor.execute("""
                INSERT INTO user_inventory (user_id, item_name, quantity) 
                VALUES (?, ?, 1) 
                ON CONFLICT(user_id, item_name) 
                DO UPDATE SET quantity = quantity + 1
            """, (user_id, held_item))

            # B. Wipe the held item slot on the specimen
            cursor.execute("UPDATE caught_pokemon SET held_item = 'none' WHERE instance_id = ?", (full_instance_id,))

            conn.commit()

            # 4. UI OUTPUT
            embed = discord.Embed(title="🎒 Equipment Recovered", color=discord.Color.green())
            embed.description = f"**{ctx.author.name}** safely detached the `{held_item.replace('-', ' ').title()}` from **{specimen_name}** and stowed it in the field backpack."
            embed.set_footer(text=f"Tag ID: {full_instance_id[:8]}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            if conn.in_transaction:
                conn.rollback()
            print(f"Unequip Error: {e}")
            await ctx.send("❌ A critical database error occurred while recovering the equipment. No items were lost.")
        finally:
            conn.close()

    @commands.command(name="market", aliases=["store"])
    @checks.has_started()
    @checks.is_authorized()
    async def view_market(self, ctx):
        """Displays available field equipment for purchase."""
        embed = discord.Embed(title="🛒 Ecological Supply Market", color=discord.Color.green())
        embed.description = "Use `!buy [quantity] [item_name]` to requisition supplies."
        
        print("embed made")
        for item_key, data in EQUIPMENT_CATALOG.items():
            # Explicitly grab the exact keys from the dictionary
            name = data['name']
            price = data['price']
            desc = data['desc']
            emoji = data['emoji']
            
            embed.add_field(
                name=f"{emoji} {name} (🪙 {price})", 
                value=desc, 
                inline=False
            )

        #print("sending embed")
        await ctx.send(embed=embed)
        #print("embed sent")

    @commands.command(name="tmshop", aliases=["tms"])
    @checks.has_started()
    @checks.is_authorized()
    async def tm_shop(self, ctx):
        """Displays the Technical Machines available for research funding."""
        embed = discord.Embed(
            title="💿 Genetic Requisition: TM Shop",
            description="Use `!buy <quantity> <tm name>` to acquire these items with your Eco Tokens.",
            color=discord.Color.teal()
        )
        
        # A lightweight UI map to add visual flair without cluttering the main economy ledger
        ui_emojis = {
            'ice-beam': '🧊',
            'flamethrower': '🔥',
            'thunderbolt': '⚡',
            'toxic': '☣️',
            'rest': '💤',
            'swords-dance': '⚔️',
            'protect': '🛡️'
        }
        
        shop_list = ""
        # Iterate through the flat dictionary (tm_key = 'ice-beam', price = 2000)
        for tm_key, price in TM_SHOP.items():
            
            # 1. Format the raw string into a beautiful title
            display_name = f"TM {tm_key.replace('-', ' ').title()}"
            
            # 2. Grab the specific elemental emoji, defaulting to a standard TM disc if missing
            icon = ui_emojis.get(tm_key, '💿')
            
            # 3. Assemble the payload!
            shop_list += f"{icon} **{display_name}** — {price} Tokens\n"
            
        embed.add_field(name="Available Inventory", value=shop_list, inline=False)
        embed.set_footer(text="TMs can be equipped using the !tm command.")
        
        await ctx.send(embed=embed)

    @commands.command(name="buy", aliases=["purchase"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_trade()
    @checks.is_not_in_combat()
    async def buy_item(self, ctx, quantity: int, *, item_name: str):
        """Securely purchases items using an atomic database transaction."""
        user_id = str(ctx.author.id)

        if quantity < 1:
            return await ctx.send("⚠️ You must purchase at least one item.")

        # Format 1: Standard Equipment (e.g., "Great Ball" -> "greatball")
        formatted_equip = item_name.lower().replace(" ", "").replace("-", "")
        
        # Format 2: TMs (e.g., "Ice Beam" -> "ice-beam")
        formatted_tm = item_name.lower().replace(" ", "-")
        
        # --- THE SMART ROUTER ---
        is_tm = False
        if formatted_equip in EQUIPMENT_CATALOG:
            item_data = EQUIPMENT_CATALOG[formatted_equip]
            item_display_name = item_data['name']
            unit_cost = item_data['price']
            emoji = item_data.get('emoji', '📦')
            db_item_name = formatted_equip
        elif formatted_tm in TM_SHOP:
            # Parse the flat dictionary and generate the UI variables dynamically!
            item_display_name = f"TM {formatted_tm.replace('-', ' ').title()}"
            unit_cost = TM_SHOP[formatted_tm]
            emoji = '💿'
            db_item_name = formatted_tm
            is_tm = True
        else:
            return await ctx.send("❌ That item or TM is not available in the supply market.")

        print("Did this pass sucessfully?")
        
        total_cost = unit_cost * quantity
        user_id = str(ctx.author.id)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            # 1. START ATOMIC TRANSACTION
            cursor.execute("BEGIN TRANSACTION")

            # 2. Check User Funds
            cursor.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (user_id,))
            user_data = cursor.fetchone()
            
            # If the user doesn't exist in the DB yet, treat their balance as 0
            current_balance = user_data[0] if user_data else 0
            
            if current_balance < total_cost:
                await ctx.send(f"⚠️ Insufficient funds! You need **{total_cost}** Eco-Tokens, but you only have **{current_balance}**.")
                conn.rollback() # Abort transaction
                return

            # 3. Deduct Funds
            cursor.execute("UPDATE users SET eco_tokens = eco_tokens - ? WHERE user_id = ?", (total_cost, user_id))

            # ==========================================
            # 4. DYNAMIC INVENTORY ROUTING
            # ==========================================
            if is_tm:
                # Route to the TM Ledger!
                cursor.execute("""
                    INSERT INTO user_tms (user_id, tm_name, quantity) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(user_id, tm_name) 
                    DO UPDATE SET quantity = quantity + ?
                """, (user_id, db_item_name, quantity, quantity))
                print("Executed succesfully")
            else:
                # Route to the Standard Backpack Ledger!
                cursor.execute("""
                    INSERT INTO user_inventory (user_id, item_name, quantity) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(user_id, item_name) 
                    DO UPDATE SET quantity = quantity + ?
                """, (user_id, db_item_name, quantity, quantity))
            # ==========================================

            # 5. COMMIT TRANSACTION (Lock the changes in permanently)
            conn.commit()
            
            embed = discord.Embed(title="✅ Requisition Successful!", color=discord.Color.blue())
            embed.description = f"Purchased **{quantity}x {item_display_name}** {emoji} for **{total_cost}** Eco-Tokens.\nNew Balance: **{current_balance - total_cost}**"
            await ctx.send(embed=embed)

        except Exception as e:
            # 6. ROLLBACK ON ERROR (If the database crashes, refund the money automatically)
            conn.rollback()
            await ctx.send("❌ A critical database error occurred. The transaction has been aborted and no funds were deducted.")
            print(f"Transaction Error in !buy: {e}")
            
        finally:
            conn.close()
                
    @commands.command(name="backpack", aliases=["gear", "items"])
    @checks.has_started()
    @checks.is_authorized()
    async def backpack(self, ctx):
        user_id = str(ctx.author.id)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Fetch everything where quantity > 0
        cursor.execute("SELECT item_name, quantity FROM user_inventory WHERE user_id = ? AND quantity > 0", (user_id,))
        inventory = cursor.fetchall()
        conn.close()
        
        if not inventory:
            return await ctx.send("🎒 Your field backpack is completely empty! Visit the `!market` to stock up on gear.")
            
        # Instantiate the UI, passing in the user, the raw database rows, and your constant dictionary
        # Make sure EQUIPMENT_CATALOG is accessible from where this command lives!
        view = BackpackPaginator(ctx.author, inventory, EQUIPMENT_CATALOG)
        
        # Generate the first page and send it with the View attached
        initial_embed = view.generate_embed()
        await ctx.send(embed=initial_embed, view=view)
async def setup(bot):
    await bot.add_cog(Economy(bot))