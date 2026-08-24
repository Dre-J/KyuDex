import discord
from discord.ext import commands
from utils.constants import DB_FILE
from utils.accounts import wipe_user
from utils.trading import (announce_trade, blocked_from_trading, first_blocked,
                           log_trade, snapshot)
from utils.limits import (ENERGY_MAX, ENERGY_BANK_CAP, ENERGY_REGEN_PER_HOUR,
                          describe_energy, regenerate_energy)
from utils.constants import BIOME_ORDER, biome_label, current_skies
from utils.prefs import (CARD_IMAGE, SOURCE_USER, describe_zone, get_card_biome,
                         get_card_style, nudge_if_default, now_in,
                         resolve_card_biome, resolve_timezone)
from utils.levels import (contribution_for_level, energy_bank_cap,
                          trainer_level)
from utils.regions import DEFAULT_REGION, region_label, trainer_region
from utils.roster import party_filter
from profile_card import build_profile_card, render_profile_card_async
import io
from utils.roster import bump_to_end_of_box
from utils import checks, trading
import asyncio
import datetime
import time
from collections import OrderedDict
import aiosqlite
import re

# The green the profile embed is drawn in. `discord.Colour.green()` is the palette's
# flat green and sits oddly beside the card's artwork; this is the deeper one used in
# the mock the embed was rebuilt from.
PROFILE_COLOUR = discord.Colour(0x41F097)


# ==========================================
# 🖼️ AVATARS
# ==========================================
# The card wears the trainer's own Discord picture, which means one HTTP fetch to
# Discord's CDN per render. Two things are worth guarding.
#
# FIRST, THE FETCH IS BOUNDED. `!profile` is a command somebody is waiting on, and an
# unbounded await against a third-party CDN is how a command that normally answers in
# 200ms occasionally takes thirty seconds. A timeout costs the picture, not the card.
#
# SECOND, THE BYTES ARE CACHED, keyed on the asset URL - which contains Discord's own
# hash of the image, so the key changes exactly when the picture does and never has to
# be invalidated. Without this the render cache would still work but every hit would be
# paid for with a round trip first, which defeats most of the point of having one.
_AVATAR_PX = 256
_AVATAR_TIMEOUT = 5.0
_AVATAR_CACHE_MAX = 64
_AVATAR_CACHE = OrderedDict()


async def _avatar_bytes(user):
    """`(bytes|None, key)` for a member's avatar. NEVER raises.

    A missing picture is a fallback on the card - the trainer sprite, then the sector
    crest - so every failure here returns `(None, '')` rather than propagating. Nobody
    should lose their profile because a CDN had a bad minute.
    """
    asset = getattr(user, 'display_avatar', None)
    if asset is None:
        return None, ''
    try:
        # 256px: the card draws it at 172, and asking for the next size up leaves room
        # to enlarge the tile later without every cached card going stale.
        asset = asset.with_size(_AVATAR_PX)
    except Exception:
        pass                            # a default avatar, or a discord.py that differs
    key = str(getattr(asset, 'url', '') or '')
    if not key:
        return None, ''

    if (hit := _AVATAR_CACHE.get(key)) is not None:
        _AVATAR_CACHE.move_to_end(key)
        return hit, key
    try:
        blob = await asyncio.wait_for(asset.read(), timeout=_AVATAR_TIMEOUT)
    except Exception as e:
        print(f"⚠️ Avatar fetch failed ({type(e).__name__}); card falls back to sprite.")
        return None, ''

    _AVATAR_CACHE[key] = blob
    while len(_AVATAR_CACHE) > _AVATAR_CACHE_MAX:
        _AVATAR_CACHE.popitem(last=False)
    return blob, key


# A mapping of species to their specific trade evolution requirements
SPECIAL_TRADE_EVOS = {
    "Poliwhirl": {"type": "item", "value": "kings-rock", "target": "Politoed"},
    "Slowpoke": {"type": "item", "value": "kings-rock", "target": "Slowking"},
    "Onix": {"type": "item", "value": "metal-coat", "target": "Steelix"},
    "Rhydon": {"type": "item", "value": "protector", "target": "Rhyperior"},
    "Seadra": {"type": "item", "value": "dragon-scale", "target": "Kingdra"},
    "Scyther": {"type": "item", "value": "metal-coat", "target": "Scizor"},
    "Electabuzz": {"type": "item", "value": "electirizer", "target": "Electivire"},
    "Magmar": {"type": "item", "value": "magmarizer", "target": "Magmortar"},
    "Porygon": {"type": "item", "value": "upgrade", "target": "Porygon2"},
    "Feebas": {"type": "item", "value": "prism-scale", "target": "Milotic"},
    "Dusclops": {"type": "item", "value": "reaper-cloth", "target": "Dusknoir"},
    "Spritzee": {"type": "item", "value": "sachet", "target": "Aromatisse"},
    "Swirlix": {"type": "item", "value": "whipped-dream", "target": "Slurpuff"},
    
    # Symbiotic partner evolutions
    "Karrablast": {"type": "partner", "value": "Shelmet", "target": "Escavalier"},
    "Shelmet": {"type": "partner", "value": "Karrablast", "target": "Accelgor"},
    
    # Branching item evolution
    "Clamperl": {
        "type": "multi_item",
        "options": {
            "deep-sea-tooth": "Huntail",
            "deep-sea-scale": "Gorebyss"
        }
    }
}

class GiftPokemonView(discord.ui.View):
    def __init__(self, author, target, specimen_data, db_file):
        super().__init__(timeout=60)
        self.author = author
        self.target = target
        self.specimen = specimen_data  # Dictionary containing name, level, instance_id
        self.db_file = db_file

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if hasattr(self, 'message') and self.message:
            await self.message.edit(content="⏳ **Gift Request Expired:** The transfer window closed.", view=self)

    @discord.ui.button(label="Confirm Transfer", style=discord.ButtonStyle.success)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("Only the sender can confirm this gift.", ephemeral=True)

        for child in self.children:
            child.disabled = True
        
        author_id = str(self.author.id)
        target_id = str(self.target.id)
        tag = self.specimen['instance_id']

        try:
            async with aiosqlite.connect(self.db_file) as db:
                # 0. A starter does not leave. Checked HERE rather than only when the
                #    gift was proposed, because the proposal is a message that keeps
                #    working - and a gift is the simplest way to move a farmed bundle.
                refusal = await blocked_from_trading(db, tag, author_id)
                if refusal:
                    for child in self.children:
                        child.disabled = True
                    return await interaction.response.edit_message(
                        content=refusal, embed=None, view=self)

                # 1. Snapshot BEFORE the transfer, while it is still the sender's.
                given = await snapshot(db, [tag])

                # 2. Update the specimen's owner
                await db.execute(
                    "UPDATE caught_pokemon SET user_id = ? WHERE instance_id = ? AND user_id = ?",
                    (target_id, tag, author_id)
                )

                # 3. And put it at the END of their box. Without this it arrives
                #    wearing the rowid it was CAUGHT with, which is very often lower
                #    than the recipient's starter's - so the gift becomes their Box #1
                #    and everything they own shifts up by one. See bump_to_end_of_box.
                await bump_to_end_of_box(db, tag)

                # 3. Safety Sweep: Remove from active partner if applicable
                async with db.execute("SELECT active_partner FROM users WHERE user_id = ?", (author_id,)) as cursor:
                    partner = await cursor.fetchone()
                    if partner and partner[0] == tag:
                        await db.execute("UPDATE users SET active_partner = NULL WHERE user_id = ?", (author_id,))

                await log_trade(db, trade_type='gift', user_a=author_id, user_b=target_id,
                                side_a=given, side_b=[],
                                guild_id=getattr(interaction.guild, 'id', None))

                await db.commit()

            await announce_trade(interaction.client, trade_type='gift',
                                 user_a=self.author, user_b=self.target,
                                 side_a=given, side_b=[])

            embed = discord.Embed(
                title="🎁 Specimen Transferred!",
                description=f"Successfully transferred **{self.specimen['name'].capitalize()}** (Lvl {self.specimen['level']}) to {self.target.mention}.",
                color=discord.Color.green()
            )
            await interaction.response.edit_message(content=None, embed=embed, view=self)

        except Exception as e:
            print(f"Error in Gift Pokemon: {e}")
            await interaction.response.edit_message(content="❌ A critical database error occurred during transfer.", view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("Only the sender can cancel this gift.", ephemeral=True)
            
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Gift cancelled. The specimen remains in your PC.", embed=None, view=self)


class GiftTokensView(discord.ui.View):
    def __init__(self, author, target, amount, db_file):
        super().__init__(timeout=60)
        self.author = author
        self.target = target
        self.amount = amount
        self.db_file = db_file

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if hasattr(self, 'message') and self.message:
            await self.message.edit(content="⏳ **Gift Request Expired:** The transfer window closed.", view=self)

    @discord.ui.button(label="Confirm Transfer", style=discord.ButtonStyle.success)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("Only the sender can confirm this gift.", ephemeral=True)

        for child in self.children:
            child.disabled = True
        
        author_id = str(self.author.id)
        target_id = str(self.target.id)

        try:
            async with aiosqlite.connect(self.db_file) as db:
                await db.execute("BEGIN TRANSACTION")
                
                # Verify sender still has enough tokens just in case they spent them while the menu was open
                async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (author_id,)) as cursor:
                    balance = await cursor.fetchone()
                
                if not balance or balance[0] < self.amount:
                    await db.rollback()
                    return await interaction.response.edit_message(content="❌ Transfer failed: Insufficient Eco-Tokens.", view=self)

                # Deduct from Sender
                await db.execute("UPDATE users SET eco_tokens = eco_tokens - ? WHERE user_id = ?", (self.amount, author_id))
                # Add to Receiver
                await db.execute("UPDATE users SET eco_tokens = eco_tokens + ? WHERE user_id = ?", (self.amount, target_id))

                # Inside the transaction, like every other transfer: a gift that rolls
                # back must not leave a record of money that never moved.
                await trading.log_trade(
                    db, trade_type='tokens', user_a=author_id, user_b=target_id,
                    side_a=trading.token_side(self.amount), side_b=[],
                    guild_id=getattr(getattr(interaction, 'guild', None), 'id', None),
                    detail=f"{self.amount} Eco Tokens gifted")

                await db.commit()

            # After the commit, and every failure swallowed - the money has moved, and
            # a Discord outage must not turn that into an error the sender has to
            # interpret. The authoritative record is the row above.
            await trading.announce_trade(
                interaction.client, trade_type='tokens',
                user_a=self.author, user_b=self.target,
                side_a=trading.token_side(self.amount), side_b=[],
                detail="Direct gift")

            embed = discord.Embed(
                title="💳 Funds Transferred!",
                description=f"Successfully transferred **{self.amount:,} Eco-Tokens** to {self.target.mention}.",
                color=discord.Color.gold()
            )
            await interaction.response.edit_message(content=None, embed=embed, view=self)

        except Exception as e:
            print(f"Error in Gift Tokens: {e}")
            await interaction.response.edit_message(content="❌ A critical database error occurred during transfer.", view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            return await interaction.response.send_message("Only the sender can cancel this gift.", ephemeral=True)
            
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Gift cancelled. Your funds have not been deducted.", embed=None, view=self)

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

class RemoveSpecimenModal(discord.ui.Modal, title="Remove Specimen(s) from Exchange"):
    box_input = discord.ui.TextInput(
        label="Box Numbers to Remove", 
        placeholder="e.g. 15, 22, 4", 
        min_length=1, 
        max_length=50 # Increased to allow a list of numbers
    )

    def __init__(self, trade_view, user):
        super().__init__()
        self.trade_view = trade_view
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        # Extract all numbers from the input string (ignores commas, spaces, etc.)
        boxes_to_remove = [int(x) for x in re.findall(r'\d+', self.box_input.value)]
        
        if not boxes_to_remove:
            return await interaction.response.send_message("⚠️ Please enter valid numerical Box Numbers.", ephemeral=True)
        
        # Determine which list to look at
        offer_list = self.trade_view.p1_offer if self.user == self.trade_view.player1 else self.trade_view.p2_offer

        # Filter out the specimens that match the requested box numbers
        initial_count = len(offer_list)
        offer_list[:] = [p for p in offer_list if p.get('box') not in boxes_to_remove]
        removed_count = initial_count - len(offer_list)

        if removed_count == 0:
            return await interaction.response.send_message(f"⚠️ Could not find those Box numbers in your current offer.", ephemeral=True)

        # Un-ready both players and update UI
        self.trade_view.p1_ready = False
        self.trade_view.p2_ready = False
        await self.trade_view.update_ui(interaction)

class AddSpecimenModal(discord.ui.Modal, title="Add Specimen(s) to Exchange"):
    box_input = discord.ui.TextInput(
        label="Specimen Box Numbers", 
        placeholder="e.g. 15, 22, 4", 
        min_length=1, 
        max_length=50 # Increased to allow multiple numbers
    )

    def __init__(self, trade_view, user):
        super().__init__()
        self.trade_view = trade_view
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Parse all integers from the input using Regex
        box_nums = [int(x) for x in re.findall(r'\d+', self.box_input.value)]
        
        if not box_nums:
            return await interaction.response.send_message("⚠️ Please enter valid numerical Box Numbers.", ephemeral=True)
            
        # Optional: Set a hard limit to prevent Discord embed overflow (e.g., max 10 at once)
        if len(box_nums) > 10:
            return await interaction.response.send_message("⚠️ You can only add up to 10 specimens at a time.", ephemeral=True)

        user_id = str(self.user.id)
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # 2. Dynamically build the SQL 'IN' clause based on how many numbers were given
                placeholders = ','.join('?' * len(box_nums))
                
                query = f"""
                    WITH NumberedPC AS (
                        SELECT 
                            cp.instance_id, 
                            cp.level, 
                            s.name,
                            cp.pokedex_id,
                            cp.held_item,
                            ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ? 
                          AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                          AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                    )
                    SELECT name, level, instance_id, pokedex_id, held_item, box_number 
                    FROM NumberedPC 
                    WHERE box_number IN ({placeholders})
                """
                
                # Execute the query passing the user_id followed by unpacked box numbers
                async with db.execute(query, (user_id, *box_nums)) as cursor:
                    found_pokemon = await cursor.fetchall()

            if not found_pokemon:
                return await interaction.response.send_message("Could not find any valid specimens matching those Box numbers.", ephemeral=True)

            # 3. Add each fetched specimen to the offer list
            added_count = 0
            refused = []
            for pokemon in found_pokemon:
                poke_name, poke_level, exact_tag, pokedex_id, held_item, box_num = pokemon

                # A starter never reaches the table. Refused as it is OFFERED rather
                # than when the trade is confirmed, so the other player never sees a
                # specimen appear and then vanish.
                async with aiosqlite.connect(DB_FILE) as guard_db:
                    refusal = await blocked_from_trading(guard_db, exact_tag, user_id)
                if refusal:
                    refused.append(refusal)
                    continue

                # Check if already offered
                if self.user == self.trade_view.player1 and any(p['tag'] == exact_tag for p in self.trade_view.p1_offer):
                    continue # Skip duplicates silently
                if self.user == self.trade_view.player2 and any(p['tag'] == exact_tag for p in self.trade_view.p2_offer):
                    continue

                # Add to offer list 
                offer_data = {
                    "name": poke_name, 
                    "level": poke_level, 
                    "tag": exact_tag, 
                    "box": box_num,
                    "pokedex_id": pokedex_id,
                    "held_item": held_item
                }
                
                if self.user == self.trade_view.player1:
                    self.trade_view.p1_offer.append(offer_data)
                else:
                    self.trade_view.p2_offer.append(offer_data)
                    
                added_count += 1

            if added_count == 0:
                 return await interaction.response.send_message(
                     refused[0] if refused
                     else "All of those specimens are already in your offer!",
                     ephemeral=True)

            # 4. Un-ready players and update UI
            self.trade_view.p1_ready = False
            self.trade_view.p2_ready = False
            await self.trade_view.update_ui(interaction)

        except Exception as e:
            print("\n🚨 CRASH IN TRADE MODAL SUBMISSION 🚨")
            import traceback
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ A critical database error occurred while processing your offer.", ephemeral=True)

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

    async def process_evolution(self, cursor, specimen, partner_offers):
        """Analyzes a specimen to determine if the trade triggers an evolution."""
        current_species = specimen['name'].strip().capitalize()
        held_item = specimen['held_item']
        
        # Handle the literal 'none' string to prevent false positive item reads
        if not held_item or str(held_item).strip().lower() == 'none':
            held_item_clean = ""
        else:
            held_item_clean = str(held_item).strip().lower()
            
        base_pokedex_id = specimen['pokedex_id']

        # Biological Stasis Lock (Everstone Check)
        if held_item_clean == "everstone":
            return {"evolved": False}
        
        partner_species_list = [p['name'].strip().capitalize() for p in partner_offers]

        new_species_name = None
        new_dex_id = None
        consume_item = False

        # Step 1: Check Hard-coded Catalysts
        if current_species in SPECIAL_TRADE_EVOS:
            rules = SPECIAL_TRADE_EVOS[current_species]
            
            if rules["type"] == "item" and held_item_clean == rules["value"].lower():
                new_species_name = rules["target"]
                consume_item = True
            elif rules["type"] == "multi_item" and held_item_clean in [k.lower() for k in rules["options"].keys()]:
                for key, target in rules["options"].items():
                    if key.lower() == held_item_clean:
                        new_species_name = target
                        consume_item = True
                        break
            elif rules["type"] == "partner" and rules["value"] in partner_species_list:
                new_species_name = rules["target"]

        # Step 2: Fallback to Database for standard trades
        if not new_species_name:
            # COALESCE, because a trade evolution's requirement lives in `held_item` and
            # this read only ever looked at `item_name` - which is NULL for every single
            # trade rule in the table. The `if required_item` below was therefore always
            # false and every trade evolution fired with empty hands: a Scyther became a
            # Scizor on any trade at all, no Metal Coat involved. `item_name` is kept in
            # the read because a trade rule is allowed to name one, and one day might.
            await cursor.execute(
                "SELECT evolved_species_id, COALESCE(held_item, item_name) "
                "FROM evolution_rules WHERE base_species_id = ? AND trigger_name = 'trade'",
                (base_pokedex_id,)
            )
            db_evo = await cursor.fetchone()

            if db_evo:
                potential_dex_id = db_evo[0]
                required_item = db_evo[1]

                if required_item:
                    if held_item_clean == str(required_item).strip().lower():
                        new_dex_id = potential_dex_id
                        consume_item = True
                else:
                    new_dex_id = potential_dex_id

        # Step 3: Standardize the output (FIXED: Using LOWER to prevent case-mismatches)
        if new_species_name and not new_dex_id:
            # We force both the database column and your variable to lowercase for a guaranteed match
            await cursor.execute(
                "SELECT pokedex_id FROM base_pokemon_species WHERE LOWER(name) = LOWER(?)", 
                (new_species_name,)
            )
            new_dex_row = await cursor.fetchone()
            
            if new_dex_row:
                new_dex_id = new_dex_row[0]
            else:
                # Adding a debug print here. If it still fails, check your bot console to see exactly which name is missing!
                print(f"🚨 DB Lookup Failed: Could not find Pokedex ID for '{new_species_name}'")
                
        if new_dex_id:
            return {
                "evolved": True,
                "new_pokedex_id": new_dex_id,
                "consume_item": consume_item
            }

        return {"evolved": False}
    
    async def execute_trade(self, interaction: discord.Interaction):
            user_a_id = str(self.player1.id)
            user_b_id = str(self.player2.id)
            
            # If both arrays are empty, there's nothing to trade!
            if not self.p1_offer and not self.p2_offer:
                return await interaction.response.edit_message(content="⚠️ Trade canceled: No biological data was offered.", view=None)

            try:
                # 1. LOCK THE ECOSYSTEM (Start Transaction)
                async with aiosqlite.connect(DB_FILE) as db:
                    # Checked once more at the point of no return. The offer builder
                    # already refuses a starter, but the trade window is a live message
                    # and the guard that matters is the one nearest the write.
                    for offer, owner in ((self.p1_offer, user_a_id),
                                         (self.p2_offer, user_b_id)):
                        stopped = await first_blocked(db, [p['tag'] for p in offer], owner)
                        if stopped:
                            return await interaction.response.edit_message(
                                content=f"❌ **Trade Aborted:** {stopped[1]}",
                                view=None, embed=None)

                    # Snapshot both sides BEFORE anything moves, so the record survives
                    # the evolutions this trade is about to trigger.
                    snap_a = await snapshot(db, [p['tag'] for p in self.p1_offer])
                    snap_b = await snapshot(db, [p['tag'] for p in self.p2_offer])

                    await db.execute("BEGIN TRANSACTION")

                    try:
                        # 2. CREATE ONE MASTER CURSOR FOR THE WHOLE TRANSACTION
                        async with db.cursor() as cursor:
                            
                            # 2. TRANSFER P1's SPECIMENS TO P2
                            for p in self.p1_offer:
                                tag = p['tag']
                                
                                # Check for evolution
                                evo = await self.process_evolution(cursor, p, self.p2_offer)
                                
                                if evo["evolved"]:
                                    new_dex = evo["new_pokedex_id"]
                                    new_item = 'none' if evo["consume_item"] else p['held_item']
                                    
                                    await cursor.execute("""
                                        UPDATE caught_pokemon 
                                        SET user_id = ?, pokedex_id = ?, held_item = ? 
                                        WHERE instance_id = ? AND user_id = ?
                                    """, (user_b_id, new_dex, new_item, tag, user_a_id))
                                else:
                                    await cursor.execute("""
                                        UPDATE caught_pokemon 
                                        SET user_id = ? 
                                        WHERE instance_id = ? AND user_id = ?
                                    """, (user_b_id, tag, user_a_id))
                                    
                                if cursor.rowcount == 0:
                                    raise ValueError(f"Validation failed for Specimen `{tag[:8]}`.")

                                # The same renumbering a gift does: a traded specimen
                                # carries the rowid it was CAUGHT with, and box numbers
                                # are counted over rowid. Without this it lands wherever
                                # its original capture date puts it in its new owner's
                                # box - very often in front of their starter.
                                await bump_to_end_of_box(cursor, tag)

                            # 3. TRANSFER P2's SPECIMENS TO P1
                            for p in self.p2_offer:
                                tag = p['tag']
                                
                                # Check for evolution
                                evo = await self.process_evolution(cursor, p, self.p1_offer)
                                
                                if evo["evolved"]:
                                    new_dex = evo["new_pokedex_id"]
                                    new_item = 'none' if evo["consume_item"] else p['held_item']
                                    
                                    await cursor.execute("""
                                        UPDATE caught_pokemon 
                                        SET user_id = ?, pokedex_id = ?, held_item = ? 
                                        WHERE instance_id = ? AND user_id = ?
                                    """, (user_a_id, new_dex, new_item, tag, user_b_id))
                                else:
                                    await cursor.execute("""
                                        UPDATE caught_pokemon 
                                        SET user_id = ? 
                                        WHERE instance_id = ? AND user_id = ?
                                    """, (user_a_id, tag, user_b_id))
                                    
                                if cursor.rowcount == 0:
                                    raise ValueError(f"Validation failed for Specimen `{tag[:8]}`.")

                                # The same renumbering a gift does: a traded specimen
                                # carries the rowid it was CAUGHT with, and box numbers
                                # are counted over rowid. Without this it lands wherever
                                # its original capture date puts it in its new owner's
                                # box - very often in front of their starter.
                                await bump_to_end_of_box(cursor, tag)
                                
                            # 4. ACTIVE PARTNER SAFETY SWEEP
                            p1_tags = [p['tag'] for p in self.p1_offer]
                            p2_tags = [p['tag'] for p in self.p2_offer]
                            
                            # Re-use the existing master cursor, no 'async with' needed here!
                            await cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_a_id,))
                            a_partner = await cursor.fetchone()
                            if a_partner and a_partner[0] in p1_tags:
                                await cursor.execute("UPDATE users SET active_partner = NULL WHERE user_id = ?", (user_a_id,))
                            
                            await cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_b_id,))
                            b_partner = await cursor.fetchone()
                            if b_partner and b_partner[0] in p2_tags:
                                await cursor.execute("UPDATE users SET active_partner = NULL WHERE user_id = ?", (user_b_id,))
                            
                            # 5. RECORD IT, then COMMIT THE BATCH TRANSFER.
                            # Inside the transaction on purpose: a trade that rolls
                            # back must not leave a record of a transfer that never
                            # happened.
                            await log_trade(db, trade_type='trade',
                                            user_a=user_a_id, user_b=user_b_id,
                                            side_a=snap_a, side_b=snap_b,
                                            guild_id=getattr(interaction.guild, 'id', None))

                            await db.commit()

                    except ValueError as ve:
                        await db.rollback()
                        return await interaction.response.edit_message(content=f"❌ **Trade Aborted:** {ve}", view=None, embed=None)

                    except Exception as e:
                        await db.rollback()
                        print(f"Atomic Trade Error: {e}")
                        return await interaction.response.edit_message(content="❌ A critical database error occurred. No data was lost.", view=None, embed=None)
                    
                for child in self.children:
                    child.disabled = True
                    
                final_embed = self.generate_embed()
                final_embed.color = discord.Color.green()
                final_embed.title = "✅ Exchange Completed Successfully!"

                await interaction.response.edit_message(embed=final_embed, view=self)

                await announce_trade(interaction.client, trade_type='trade',
                                     user_a=self.player1, user_b=self.player2,
                                     side_a=snap_a, side_b=snap_b)
            finally:
                # UNLOCK NO MATTER WHAT HAPPENS
                self.active_trades.discard(self.player1.id)
                self.active_trades.discard(self.player2.id)

    def generate_embed(self):
        embed = discord.Embed(title="🤝 Active Specimen Exchange", color=discord.Color.blue())
        
        # Format Player 1's side
        p1_status = "✅ READY" if self.p1_ready else "⏳ Deciding..."
        p1_text = ""
        for p in self.p1_offer:
            # Display Box Number instead of the Tag
            p1_text += f"• **{p['name'].capitalize()}** (Lvl {p['level']}) | Box `#{p['box']}`\n"
        if not p1_text: p1_text = "*Nothing offered yet.*"
        
        # Format Player 2's side
        p2_status = "✅ READY" if self.p2_ready else "⏳ Deciding..."
        p2_text = ""
        for p in self.p2_offer:
            # Display Box Number instead of the Tag
            p2_text += f"• **{p['name'].capitalize()}** (Lvl {p['level']}) | Box `#{p['box']}`\n"
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

    @commands.group(name="gift", invoke_without_command=True)
    async def gift_group(self, ctx):
        """Base command for gifting. Use !gift pokemon or !gift tokens."""
        await ctx.send("🎁 Please specify what you want to gift: `!gift pokemon @user <BoxNum>` or `!gift tokens @user <Amount>`.")

    @gift_group.command(name="pokemon")
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat()
    async def gift_pokemon(self, ctx, target_user: discord.Member, box_num: int):
        if ctx.author == target_user:
            return await ctx.send("⚠️ You cannot gift a specimen to yourself!")
        if target_user.bot:
            return await ctx.send("🤖 Automated drones cannot accept biological specimens.")
        if box_num < 1:
            return await ctx.send("⚠️ Please provide a valid Box number greater than 0.")

        author_id = str(ctx.author.id)

        # Fetch the Pokémon using the exact same CTE logic as the trade system
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("""
                WITH NumberedPC AS (
                    SELECT 
                        cp.instance_id, 
                        cp.level, 
                        s.name,
                        ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ? 
                      AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                      AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                )
                SELECT name, level, instance_id
                FROM NumberedPC
                WHERE box_number = ?
            """, (author_id, box_num)) as cursor:
                pokemon = await cursor.fetchone()

            if not pokemon:
                return await ctx.send(f"⚠️ Could not find a valid specimen at Box `#{box_num}`. It may be deployed or doesn't exist.")

            # Refuse a locked starter HERE, not only at the confirm button. The button
            # still checks - the proposal is a message that keeps working, and the
            # count can cross the threshold while it sits there - but a confirmation
            # dialog for a transfer that cannot happen is a dialog that teaches people
            # the refusal is a glitch. `!trade add` already refuses at offer time; this
            # was the one route that did not.
            refusal = await blocked_from_trading(db, pokemon[2], author_id)
            if refusal:
                return await ctx.send(refusal)

        specimen_data = {
            "name": pokemon[0],
            "level": pokemon[1],
            "instance_id": pokemon[2]
        }

        # Setup Confirmation Embed
        embed = discord.Embed(
            title="🎁 Gift Confirmation",
            description=f"Are you sure you want to permanently transfer **{specimen_data['name'].capitalize()}** (Lvl {specimen_data['level']}) from Box `#{box_num}` to {target_user.mention}?",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Trade evolutions do NOT trigger during gifts.")

        view = GiftPokemonView(ctx.author, target_user, specimen_data, DB_FILE)
        view.message = await ctx.send(embed=embed, view=view)


    @gift_group.command(name="tokens", aliases=["credits", "eco"])
    @checks.has_started()
    @checks.is_authorized()
    async def gift_tokens(self, ctx, target_user: discord.Member, amount: int):
        if ctx.author == target_user:
            return await ctx.send("⚠️ You cannot gift funds to yourself!")
        if target_user.bot:
            return await ctx.send("🤖 Automated drones have no need for currency.")
        if amount <= 0:
            return await ctx.send("⚠️ You must gift an amount greater than 0.")

        author_id = str(ctx.author.id)

        # Check Author's balance
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (author_id,)) as cursor:
                balance_row = await cursor.fetchone()

        if not balance_row or balance_row[0] < amount:
            return await ctx.send(f"❌ You do not have enough Eco-Tokens. Your current balance is **{balance_row[0] if balance_row else 0:,}**.")

        # Setup Confirmation Embed
        embed = discord.Embed(
            title="💳 Transfer Confirmation",
            description=f"Are you sure you want to transfer **{amount:,} Eco-Tokens** to {target_user.mention}?",
            color=discord.Color.gold()
        )

        view = GiftTokensView(ctx.author, target_user, amount, DB_FILE)
        view.message = await ctx.send(embed=embed, view=view)

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
                    "`!pc`": "View all your caught pokemon.",
                    "`!view [ID]`": "Inspect a specimen's biometrics, statistics, and genetic footprint.",
                    "`!nickname`": "Assign your pokemon a custom name",
                    "`!settag`": "Give your pokemon a special tag to help sorting.",
                    "`!release`": "Re-Home a pokemon in exchange for Eco-Tokens. Takes several at once: `!release 4 7 12` or `!release 4-9`.",
                    "`!partner`": "Set a specific pokemon to be your partner.",
                    "`!equip`": "Assign an owned item to a specific pokemon.",
                    "`!unequip`": "Remove an owned item to a specific pokemon.",
                    "`!evolve`": "Manually evolve a pokemon with an item.",
                    "`!vitamins`": "Increase a specific pokemon's Effort Values (EVs) with vitamins.",
                    "`!candy`": "Increase a specific pokemon's level with rare candies."

                }
            },
            {
                "title": "Logistics & Commerce",
                "description": "Manage your inventory, economy, and trades.",
                "commands": {
                    "`!profile`": "View your Ecological Visas, Eco-Tokens, and active Field Energy.",
                    "`!inbox`": "View your notifications from the bot.",
                    "`!backpack`": "Open your paginated inventory of field equipment and materials.",
                    "`!techmoves`": "View all your available Technical Machines (TMs).",
                    "`!market`": "View the supply catalog for equipment.",
                    "`!tmshop`": "View the market for Technical Machines (TMs).",
                    "`!shop`": "Displays items from a rotating daily market.",
                    "`!gts`": "Access the Global Trade System to globally trade pokemon.",
                    "`!global market`": "Access the Global Market to globally sell pokemon.",
                    "`!buy [qty] [item]`": "Securely requisition items using Eco-Tokens.",
                    "`!sell [qty] [item]`": "Securely exchange items for Eco-Tokens.",
                    "`!trade @user`": "Initiate an atomic, multi-specimen transfer with another researcher.",
                    "`!gift [tokens/pokemon] @user [box number/token amount]`": "Gift a specified user a pokemon or tokens."
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
                    "`!deploy`": "Send out your pokemon to complete special jobs/missions.",
                    "`!jobs`": "View the 5 daily selected jobs/missions.",
                    "`!return`": "Call your pokemon back from their special jobs/missions for rewards.",
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
        
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # 1. Verify the subject actually exists in the database
                async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    if not await cursor.fetchone():
                        return await ctx.send(f"⚠️ **Target Not Found:** `{target_user.name}` is not registered in the ecological database.")
                    
                # ==========================================
                # 2. THE CASCADING DATA PURGE
                # ==========================================
                # One cascade, shared with !reset and !privacy delete. This command used
                # to carry its own copy of the list, and that copy had fallen four
                # tables behind - it left the target's TMs, alerts, deployed specimens
                # and GTS deposits sitting in the database, the last two pointing at
                # Pokemon it had just deleted.
                removed = await wipe_user(db, user_id, keep_account=False)

                # 3. Commit the eradication
                await db.commit()
                print(f"ADMIN WIPE {user_id}: {removed}")
            
            embed = discord.Embed(
                title="☣️ ECOLOGICAL PURGE AUTHORIZED",
                description=f"All biometric, financial, and tactical records belonging to **{target_user.name}** (`{user_id}`) have been completely eradicated from the system.",
                color=discord.Color.dark_red()
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Data Eradication Error: {e}")
            await ctx.send("❌ A critical failure occurred during the database purge. Check the terminal.")

    @commands.command(name="ban", aliases=["revoke_license"])
    @commands.is_owner()
    async def ban_user(self, ctx, target_user: discord.User, *, reason: str = "Violation of Ecological Directives."):
        """[ADMIN] Revokes a user's research license, locking them out of the ecosystem."""
        user_id = str(target_user.id)
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute("""
                    INSERT INTO banned_personnel (user_id, reason) 
                    VALUES (?, ?)
                """, (user_id, reason))
                await db.commit()
            
            embed = discord.Embed(
                title="⚖️ License Revoked", 
                description=f"**{target_user.name}** (`{user_id}`) has been permanently banned from the simulation.\n**Reason:** {reason}",
                color=discord.Color.dark_red()
            )
            await ctx.send(embed=embed)
            
        except aiosqlite.IntegrityError:
            await ctx.send(f"⚠️ **{target_user.name}** is already on the banned personnel list.")
        except Exception as e:
            print(f"Ban Error: {e}")
            await ctx.send("❌ A database error occurred while updating the security ledger.")

    @commands.command(name="unban", aliases=["restore_license"])
    @commands.is_owner()
    async def unban_user(self, ctx, target_user: discord.User):
        """[ADMIN] Restores a user's research license."""
        user_id = str(target_user.id)
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # We can capture the cursor directly from the execute command to check rowcount
                cursor = await db.execute("DELETE FROM banned_personnel WHERE user_id = ?", (user_id,))
                
                if cursor.rowcount > 0:
                    await db.commit()
                    await ctx.send(f"✅ **License Restored:** **{target_user.name}** (`{user_id}`) has been cleared for fieldwork.")
                else:
                    await ctx.send(f"⚠️ **{target_user.name}** is not currently on the banned list.")
                    
        except Exception as e:
            print(f"Unban Error: {e}")

    @commands.command(name="trade")
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat() # Can't trade while fighting!
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
        scope = scope.lower()
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                if scope in ["global", "world", "all"]:
                    # --- GLOBAL LEADERBOARD ---
                    async with db.execute("""
                        SELECT user_id, SUM(contribution_points) as total_cp 
                        FROM guild_members 
                        GROUP BY user_id 
                        ORDER BY total_cp DESC 
                        LIMIT 10
                    """) as cursor:
                        results = await cursor.fetchall()
                
                    embed = discord.Embed(title="🌍 Global Ecologist Rankings", color=discord.Color.blue())
                    embed.description = "The top 10 environmental researchers across all known habitats!"
                else:
                    # --- LOCAL LEADERBOARD ---
                    guild_id = str(ctx.guild.id)
                    async with db.execute("""
                    SELECT user_id, contribution_points 
                    FROM guild_members 
                    WHERE guild_id = ? 
                    ORDER BY contribution_points DESC 
                    LIMIT 10
                """, (guild_id,)) as cursor:
                        results = await cursor.fetchall()

                    # INSIDE the else. These two lines sat one indent to the left, so
                    # they ran after both branches and overwrote whatever the global
                    # branch had just built: `!leaderboard global` fetched the worldwide
                    # totals correctly and then titled them "Local Ecosystem Leaders",
                    # naming whichever server the command happened to be typed in.
                    embed = discord.Embed(title=f"📍 Local Ecosystem Leaders: {ctx.guild.name}", color=discord.Color.green())
                    embed.description = "The top 10 researchers maintaining this specific server's habitat."

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
                user_obj = await ctx.bot.fetch_user(int(user_id))
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

        except Exception as e:
            print(f"Leaderboard Error: {e}")
            await ctx.send("❌ Error calculating rankings.")

    @commands.command(name="inbox", aliases=["alerts", "notifications"])
    @checks.has_started()
    @checks.is_authorized()
    async def inbox(self, ctx):
        """Check your unread in-game notifications."""
        user_id = str(ctx.author.id)
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # 1. Fetch unread messages
                async with db.execute(
                    "SELECT id, alert_text, timestamp FROM user_alerts WHERE user_id = ? AND is_read = 0 ORDER BY timestamp ASC LIMIT 10", 
                    (user_id,)
                ) as cursor:
                    alerts = await cursor.fetchall()

                if not alerts:
                    return await ctx.send("📭 Your inbox is completely empty. You're all caught up!")

                # 2. Build the Embed
                embed = discord.Embed(
                    title="📬 System Inbox",
                    description="Here are your latest unread notifications:\n\n",
                    color=discord.Color.blue()
                )
                
                # Format each alert
                for alert_id, text, timestamp in alerts:
                    # Optional: Format the timestamp cleanly if desired
                    embed.description += f"• {text}\n\n"
                
                embed.set_footer(text="These alerts have now been marked as read.")
                await ctx.send(embed=embed)
                
                # 3. Mark them as read!
                alert_ids = [str(a[0]) for a in alerts]
                placeholders = ",".join("?" * len(alert_ids))
                await db.execute(
                    f"UPDATE user_alerts SET is_read = 1 WHERE id IN ({placeholders})", 
                    alert_ids
                )
                await db.commit()
                
        except Exception as e:
            print(f"Inbox Error: {e}")
            await ctx.send("❌ A database error occurred while accessing your inbox.")

    @commands.command(name="profile", aliases=["impact", "bal"])
    @checks.has_started()
    @checks.is_authorized()
    async def profile(self, ctx, member: discord.Member = None):
        """
        Your trainer card. `!settings card image|embed` chooses how it is drawn.

        THE DATA IS GATHERED ONCE and rendered two ways. The image card and the embed
        used to be two different sets of numbers waiting to happen - the whole reason
        the energy meter needed fixing last time was that two places computed it
        separately. `_gather_profile` is the only thing that reads the database, and
        both renderers are handed the same dictionary.
        """
        target = member or ctx.author
        user_id = str(target.id)
        guild_id = str(ctx.guild.id) if ctx.guild else None

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                data = await self._gather_profile(db, target, guild_id)
                style = await get_card_style(db, str(ctx.author.id))
        except Exception as e:
            print(f"Profile Database Error: {e}")
            return await ctx.send("❌ Error extracting biometric profile.")

        # Somebody else's card is never rendered from the viewer's preference alone if
        # the image path fails; both routes end in a send, and the embed is the one that
        # cannot fail for want of an asset.
        # Somebody still on a fallback clock is told once, on whichever route they use.
        # The card SHOWS their time; only this says the time might not be theirs.
        nudge = nudge_if_default(data['zone_source']) if target == ctx.author else None

        if style == CARD_IMAGE:
            try:
                # FETCHED HERE, not in `_gather_profile`, because it is the only thing
                # either rendering needs that is not in the database - and the embed
                # route would be paying a network round trip for a picture it never
                # draws. `_avatar_bytes` cannot raise, so a CDN failure costs the
                # picture and still leaves the card.
                data['avatar'], data['avatar_key'] = await _avatar_bytes(target)
                blob = await render_profile_card_async(build_profile_card(data))
                file = discord.File(io.BytesIO(blob), filename="profile.webp")
                return await ctx.send(content=nudge, file=file)
            except Exception as e:
                # A missing font, a missing background, a Pillow that is too old. The
                # card is a nicety; the profile is not. Fall through to the embed rather
                # than telling somebody their profile is broken.
                print(f"Profile card render failed, falling back to embed: {e}")

        await ctx.send(content=nudge, embed=self._profile_embed(ctx, target, data))

    async def _gather_profile(self, db, target, guild_id):
        """Every number both renderings need, read once."""
        user_id = str(target.id)

        async with db.execute(
                "SELECT COUNT(*) FROM user_alerts WHERE user_id = ? AND is_read = 0",
                (user_id,)) as cursor:
            unread = (await cursor.fetchone())[0]

        async with db.execute(
                "SELECT eco_tokens, unlocked_visas, current_energy, last_energy_tick "
                "FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()

        tokens = row[0] if row else 0
        visas_raw = (row[1] if row and row[1] else "canopy")
        db_energy = row[2] if row and len(row) > 2 else ENERGY_MAX
        last_tick = row[3] if row and len(row) > 3 else 0

        # LIFETIME, summed across guilds - not this server's slice. A level that changed
        # depending on where you typed the command would be the same defect the timezone
        # work took out of evolutions.
        level, title, lifetime = await trainer_level(db, user_id)

        # This server's own figure is still shown, because the local leaderboard ranks
        # on it and a profile that could not explain that ranking would be a puzzle.
        local_contribution = 0
        if guild_id:
            async with db.execute(
                    "SELECT contribution_points FROM guild_members "
                    "WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cursor:
                member_row = await cursor.fetchone()
            local_contribution = member_row[0] if member_row else 0

        async with db.execute(
                "SELECT COUNT(*), COALESCE(SUM(is_shiny), 0) FROM caught_pokemon "
                "WHERE user_id = ?", (user_id,)) as cursor:
            caught, shinies = await cursor.fetchone()

        # The party, in slot order, with what each specimen actually looks like.
        scope, scope_params = await party_filter(db, user_id)
        async with db.execute(f"""
            SELECT cp.pokedex_id, cp.is_shiny, cp.gender
            FROM user_party up
            JOIN caught_pokemon cp ON up.instance_id = cp.instance_id
            WHERE up.user_id = ? {scope}
            ORDER BY up.slot ASC
        """, (user_id, *scope_params)) as cursor:
            party = [(r[0], bool(r[1]), r[2]) for r in await cursor.fetchall()]

        zone, zone_source = await resolve_timezone(db, user_id, guild_id)
        when = now_in(zone)
        skies = current_skies(when)

        # THE BANK CAP IS THE TRAINER'S OWN, and it has to be worked out before the
        # regeneration is, because it is the ceiling that regeneration fills to.
        bank_cap = energy_bank_cap(level)
        energy, tick = regenerate_energy(db_energy, last_tick, int(time.time()), bank_cap)

        # ORDERED, because a comma-split is a set with an accidental order and "the
        # deepest sector" is a question only an ordered list can answer.
        visas = [v.strip().lower() for v in str(visas_raw).split(',') if v.strip()]
        visas = [b for b in BIOME_ORDER if b in visas]

        # The stored choice is carried through RAW and validated by `resolve_card_biome`
        # at each point of use. A wipe puts `unlocked_visas` back to 'canopy' without
        # knowing this column exists, so a choice made before one can name a sector that
        # is no longer held - which is why nothing downstream trusts it.
        stored_biome = await get_card_biome(db, user_id)

        # Stored if they have one, recovered from their starter if not - see
        # `utils/regions.py`. Every trainer who registered before the column existed
        # falls into the second case, and the nine starter trios are disjoint, so the
        # recovery is exact rather than a guess.
        region, region_stored = await trainer_region(db, user_id)

        return {
            'target': target,
            'card_biome': stored_biome,
            'biome': resolve_card_biome(stored_biome, visas),
            'region': region,
            'region_stored': region_stored,
            'unread': unread,
            'tokens': tokens,
            'visas': visas,
            'energy': energy,
            'energy_tick': tick,
            'bank_cap': bank_cap,
            'level': level,
            'title': title,
            'lifetime': lifetime,
            'local_contribution': local_contribution,
            'caught': caught,
            'shinies': shinies,
            'party': party,
            'zone': zone,
            'zone_source': zone_source,
            'clock': when.strftime('%H:%M'),
            'skies': tuple(sorted(skies)),
        }

    @staticmethod
    def _profile_embed(ctx, target, d):
        """
        The text rendering. Same numbers, no assets, no Pillow.

        LAID OUT AS AN AUTHOR LINE AND A ROW OF FIGURES rather than as a title and a
        column of them. The two headline meters - level and energy - stay full width
        because they carry a bar; the four totals go inline, which puts them on one
        line on a desktop and stops the embed running to two screens on a phone.

        The avatar goes in the thumbnail. It is the only free way for the embed to say
        whose profile this is: `display_avatar.url` is a string Discord already has, so
        unlike the image card there is nothing to download.
        """
        level, span = d['level'], max(1, contribution_for_level(d['level'] + 1)
                                      - contribution_for_level(d['level']))
        into = d['lifetime'] - contribution_for_level(level)

        embed = discord.Embed(colour=PROFILE_COLOUR,
                              timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.set_author(name=f"{target.display_name} · Ecological Profile",
                         icon_url=getattr(target.display_avatar, 'url', None))
        thumb = getattr(getattr(target, 'display_avatar', None), 'url', None)
        if thumb:
            embed.set_thumbnail(url=thumb)

        if d['unread'] and target == ctx.author:
            embed.description = (f"📬 **You have {d['unread']} unread "
                                 f"update{'s' if d['unread'] > 1 else ''}!** "
                                 f"Type `!inbox` to read them.")

        embed.add_field(
            name=f"🎖️ {d['title']} · Level {level}",
            value=(f"{_progress_bar(into, span)}  {into:,} / {span:,}\n"
                   f"*{d['lifetime']:,} lifetime contribution*"),
            inline=False)

        # `describe_energy` writes the banked and the running-on-reserves phrasing, and
        # the image card reads the same function. Spelling "100 over a full reserve" out
        # again here is how the two meters would start disagreeing about the same number.
        shown = max(0, d['energy'])
        note = describe_energy(d['energy'], d['bank_cap']) or ""
        embed.add_field(
            name="🔋 Field Energy",
            value=(f"{_progress_bar(shown, d['bank_cap'])}  "
                   f"**{shown} / {ENERGY_MAX}**"
                   + (f"\n*{note}*" if note else "")),
            inline=False)

        # THE ZONE IS NAMED, not just the hour. "1:22 · day" alone is unreadable to
        # anybody checking whether their own evening is what the game thinks it is -
        # which is the entire question a time-gated evolution makes them ask.
        sky_icon = "🌙" if 'night' in d['skies'] else "☀️"
        embed.add_field(
            name=f"{sky_icon} Your Clock",
            # The BARE zone name, not `describe_zone` - that renders the current time and
            # the offset too, and the current time is already the first thing on this
            # line. It is also the string somebody would type straight back into
            # `!settings timezone`, which a prettified one is not.
            value=f"**{d['clock']}** · {'/'.join(d['skies'])}\n"
                  f"*Time zone: {d['zone']}*",
            inline=False)

        # HOME REGION sits with the other totals rather than in a field of its own. It
        # is an identity, not a score, and the row is where somebody's eye already is.
        embed.add_field(name="Home Region",
                        value=region_label(d.get('region') or DEFAULT_REGION),
                        inline=True)
        embed.add_field(name="Global Eco-Tokens", value=f"🪙 {d['tokens']:,}",
                        inline=True)
        embed.add_field(name="Local Contribution",
                        value=f"⭐ {d['local_contribution']:,} points", inline=True)
        embed.add_field(name="Specimens Rescued", value=f"🐾 {d['caught']:,} total",
                        inline=True)
        embed.add_field(name="Shiny", value=f"✨ {d['shinies']:,}", inline=True)

        # `biome_label` rather than a local map. This was the fourth copy of the five
        # sector names in the codebase and the one most likely to fall behind, because
        # nothing that reads it would fail if it did - a stale entry here just quietly
        # renders `Apex` without its dragon.
        visas_display = " • ".join(biome_label(v) for v in d['visas']) or "—"
        # The chosen sector goes INSIDE the clearance field rather than in one of its
        # own. It is a footnote to the list above it - which sector of these you wear -
        # and a whole field for one word made it look like a separate achievement. Shown
        # only when it has been chosen: telling somebody on the default "Canopy, because
        # that is as far as you have got" reads as a rebuke.
        if d.get('card_biome'):
            visas_display += f"\n*Card dressed in {biome_label(d['biome'])}.*"
        embed.add_field(name="🛂 Sector Clearance (Visas)", value=visas_display,
                        inline=False)

        footer = ctx.guild.name if ctx.guild else ""
        if d['zone_source'] != SOURCE_USER:
            footer += ("  |  Set yours with `!settings timezone` so day/night matches "
                       "your own evening.")
        if footer:
            embed.set_footer(text=footer)
        return embed

def _progress_bar(current, total, width=12):
    """A bar drawn out of block characters, for the embed rendering."""
    total = max(1, int(total or 0))
    filled = max(0, min(width, round(width * (max(0, int(current or 0)) / total))))
    return "█" * filled + "░" * (width - filled)


async def setup(bot):
    await bot.add_cog(Social(bot))