import datetime
import os
import random
import discord
from discord.ext import commands
from utils.constants import (DB_FILE, EQUIPMENT_CATALOG, SHOP_CATALOG, TM_SHOP,
                             TM_CATALOG, TM_TIER_PRICES, CATEGORY_OPTIONS,
                             type_badges, species_badges, trait_badges)
from utils.species import (MAX_CHOICES, pretty_species, resolve_species,
                           suggest_species)
from utils.trading import (announce_trade, blocked_from_trading, log_trade,
                           snapshot)
from utils.sprites import resolve_sprite, sprite_attachment_name, HOME
from utils.roster import locate_specimen, looks_like_partner, bump_to_end_of_box
from utils.machines import (owns_tm, owned_tms, grant_tm, find_tm, search_tms,
                            filter_tms, species_tms)
from utils import checks
import math
import aiosqlite
import uuid

class GTSFulfillModal(discord.ui.Modal, title="Fulfill GTS Trade"):
    box_input = discord.ui.TextInput(
        label="Your Specimen's Box Number",
        placeholder="e.g., 15",
        min_length=1,
        max_length=5
    )

    def __init__(self, trade_data, db_file, parent_view):
        super().__init__()
        self.trade_data = trade_data
        self.db_file = db_file
        self.parent_view = parent_view 

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        gts_id, target_user_id, _, req_sp, req_min, req_max, req_gen = self.trade_data[:7]
        
        try:
            box_num = int(self.box_input.value.strip())
        except ValueError:
            return await interaction.response.send_message("⚠️ Please enter a valid Box Number.", ephemeral=True)

        await interaction.response.defer()

        try:
            async with aiosqlite.connect(self.db_file) as db:
                # 1. Fetch their offered Pokémon
                async with db.execute("""
                    WITH NumberedPC AS (
                        SELECT instance_id, level, gender, s.name, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ? AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments) AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                    )
                    SELECT instance_id, name, level, gender FROM NumberedPC WHERE box_number = ?
                """, (user_id, box_num)) as cursor:
                    offered_poke = await cursor.fetchone()

                if not offered_poke:
                    return await interaction.followup.send("⚠️ Could not find a valid specimen at that Box Number.")

                offered_id, offered_name, offered_lvl, offered_gen = offered_poke

                # 2. STRICT VALIDATION
                if offered_name.lower() != req_sp.lower():
                    return await interaction.followup.send(f"⚠️ Trade Failed: They requested a **{req_sp}**, but you offered a **{offered_name}**.")
                if not (req_min <= offered_lvl <= req_max):
                    return await interaction.followup.send(f"⚠️ Trade Failed: They requested Level **{req_min}-{req_max}**, but yours is Level **{offered_lvl}**.")
                if req_gen != "ANY" and offered_gen != req_gen:
                    return await interaction.followup.send(f"⚠️ Trade Failed: They requested Gender **{req_gen}**, but yours is **{offered_gen}**.")

                # 3. EXECUTE THE ATOMIC SWAP
                await db.execute("BEGIN TRANSACTION")
                try:
                    async with db.execute("SELECT instance_id FROM gts_deposits WHERE gts_id = ?", (gts_id,)) as cursor:
                        gts_instance_row = await cursor.fetchone()
                    
                    if not gts_instance_row:
                        await db.rollback()
                        return await interaction.followup.send("❌ Error: This GTS listing no longer exists. Someone may have beaten you to it!")
                    
                    gts_instance_id = gts_instance_row[0]

                    refusal = await blocked_from_trading(db, offered_id, user_id)
                    if refusal:
                        await db.rollback()
                        return await interaction.followup.send(refusal, ephemeral=True)

                    given = await snapshot(db, [offered_id])
                    received = await snapshot(db, [gts_instance_id])

                    # Swap the IDs!
                    await db.execute("UPDATE caught_pokemon SET user_id = ? WHERE instance_id = ?", (target_user_id, offered_id))
                    await db.execute("UPDATE caught_pokemon SET user_id = ? WHERE instance_id = ?", (user_id, gts_instance_id))
                    await bump_to_end_of_box(db, offered_id, gts_instance_id)

                    await db.execute("DELETE FROM gts_deposits WHERE gts_id = ?", (gts_id,))

                    # 🚨 INLINE ALERT DISPATCH!
                    alert_msg = f"🤝 **GTS Update:** Your deposited **{self.trade_data[7]}** was successfully traded for a **{offered_name}** by {interaction.user.name}!"
                    await db.execute("INSERT INTO user_alerts (user_id, alert_text) VALUES (?, ?)", (target_user_id, alert_msg))

                    await log_trade(db, trade_type='gts-swap', user_a=user_id,
                                    user_b=target_user_id, side_a=given, side_b=received,
                                    guild_id=getattr(interaction.guild, 'id', None),
                                    detail=f"One-click swap against listing {gts_id}")

                    await db.commit()

                    # Success UI Update
                    for child in self.parent_view.children: child.disabled = True
                    await interaction.message.edit(view=self.parent_view)

                    await interaction.followup.send(f"🎉 **Trade Successful!** The {self.trade_data[7]} has been transferred to your PC.")

                    await announce_trade(interaction.client, trade_type='gts-swap',
                                         user_a=interaction.user, user_b=target_user_id,
                                         side_a=given, side_b=received)

                except Exception as e:
                    await db.rollback()
                    print(f"GTS Swap Transaction Error: {e}")
                    await interaction.followup.send("❌ A database error occurred during the transfer.")

        except Exception as outer_e:
            print(f"GTS Modal Validation Error: {outer_e}")
            await interaction.followup.send("❌ A critical error occurred while validating your GTS trade.")
            
class GTSSearchPaginator(discord.ui.View):
    # 🚨 ADDED: preselected_instance=None
    def __init__(self, user, results, db_file, preselected_instance=None):
        super().__init__(timeout=180)
        self.user = user
        self.results = results
        self.db_file = db_file
        self.preselected_instance = preselected_instance # 🚨 Assigned here!
        self.current_page = 0
        self.max_pages = len(results)
        self.update_buttons()

    def update_buttons(self):
        self.children[0].disabled = self.current_page == 0 
        self.children[1].disabled = self.current_page >= self.max_pages - 1 

    def create_embed(self):
        row = self.results[self.current_page]
        (gts_id, dep_owner, msg, req_sp, req_min, req_max, req_gen, p_name, p_lvl,
         p_gen, p_shiny, p_abil, hp, atk, defn, spatk, spdef, spd) = row[:18]

        # Read off the END rather than widening the unpack above, so a row built to the
        # older eighteen-column shape still renders - it simply carries no trait badges.
        # A positional tuple that grows is the one thing every caller has to agree about
        # at once, and this view has two separate queries feeding it.
        p_gmax = row[18] if len(row) > 18 else 0
        p_h_mult = row[19] if len(row) > 19 else None
        
        iv_total = hp + atk + defn + spatk + spdef + spd
        iv_pct = int((iv_total / 186.0) * 100)
        shiny_icon = "✨" if p_shiny else ""
        gender_icon = "♂️" if p_gen == "M" else "♀️" if p_gen == "F" else "⚧️"
        
        req_lvl_str = f"{req_min}-{req_max}" if req_min != req_max else f"{req_min}"

        embed = discord.Embed(
            title=f"GTS Entry: {shiny_icon} {p_name} {gender_icon} (Lvl {p_lvl})",
            color=discord.Color.blue()
        )
        embed.add_field(name="🧬 Biological Data",
                        value=f"{species_badges(p_name)}"
                              f"{trait_badges(gmax=p_gmax, height_multiplier=p_h_mult)}"
                              f"\n**Ability:** {p_abil}\n"
                              f"**IV Potential:** {iv_pct}%", inline=True)
        embed.add_field(name="📝 Trainer Message", value=f"*{msg}*", inline=False)

        embed.add_field(
            name="⚠️ Requirements for Trade",
            value=f"**Species:** {req_sp}  {species_badges(req_sp)}\n"
                  f"**Level:** {req_lvl_str}\n**Gender:** {req_gen}",
            inline=False
        )
        
        embed.set_footer(text=f"Result {self.current_page + 1} of {self.max_pages} | GTS ID: {gts_id}")
        return embed

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.secondary, row=0)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: return
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.secondary, row=0)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: return
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="🤝 Fulfill Trade", style=discord.ButtonStyle.success, row=1)
    async def fulfill_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your search session!", ephemeral=True)
            
        current_trade = self.results[self.current_page]
        
        # PATH A: General Search (Needs Box Number via Modal)
        if not getattr(self, 'preselected_instance', None):
            return await interaction.response.send_modal(GTSFulfillModal(current_trade, self.db_file, self))
            
        # PATH B: Wanted Search (1-Click Execution!)
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        gts_id, target_user_id = current_trade[0], current_trade[1]
        
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("BEGIN TRANSACTION")
            try:
                async with db.execute("SELECT instance_id FROM gts_deposits WHERE gts_id = ?", (gts_id,)) as cursor:
                    gts_instance_row = await cursor.fetchone()
                
                if not gts_instance_row:
                    await db.rollback()
                    return await interaction.followup.send("❌ Error: This GTS listing no longer exists. Someone may have beaten you to it!")
                
                gts_instance_id = gts_instance_row[0]

                refusal = await blocked_from_trading(db, self.preselected_instance, user_id)
                if refusal:
                    await db.rollback()
                    return await interaction.followup.send(refusal, ephemeral=True)

                given = await snapshot(db, [self.preselected_instance])
                received = await snapshot(db, [gts_instance_id])

                # Atomic Swap!
                await db.execute("UPDATE caught_pokemon SET user_id = ? WHERE instance_id = ?", (target_user_id, self.preselected_instance))
                await db.execute("UPDATE caught_pokemon SET user_id = ? WHERE instance_id = ?", (user_id, gts_instance_id))
                await bump_to_end_of_box(db, self.preselected_instance, gts_instance_id)

                await db.execute("DELETE FROM gts_deposits WHERE gts_id = ?", (gts_id,))

                await log_trade(db, trade_type='gts-swap', user_a=user_id,
                                user_b=target_user_id, side_a=given, side_b=received,
                                guild_id=getattr(interaction.guild, 'id', None),
                                detail=f"One-click swap against listing {gts_id}")
                await db.commit()

                # UI Update
                for child in self.children: child.disabled = True
                await interaction.message.edit(view=self)
                await interaction.followup.send(f"🎉 **Trade Successful!** The {current_trade[7]} has been transferred to your PC.")

                await announce_trade(interaction.client, trade_type='gts-swap',
                                     user_a=interaction.user, user_b=target_user_id,
                                     side_a=given, side_b=received)
                
            except Exception as e:
                await db.rollback()
                print(f"GTS 1-Click Swap Error: {e}")
                await interaction.followup.send("❌ A database error occurred during the transfer.")

class SpeciesPicker(discord.ui.View):
    """
    A dropdown of species, for when a typed name did not resolve.

    There is no dropdown of ALL 1344 species anywhere, and there cannot be: Discord
    allows 25 options in a select menu. So the flow is to get the player to a list
    short enough to BE one - either the species actually on the GTS, or the closest
    matches to whatever they typed - and let them click instead of spell.
    """
    def __init__(self, owner, candidates, on_pick, *, placeholder="Pick a species..."):
        super().__init__(timeout=120)
        self.owner = owner
        self.on_pick = on_pick

        menu = discord.ui.Select(
            placeholder=placeholder,
            options=[discord.SelectOption(label=pretty_species(name), value=name)
                     for name in candidates[:MAX_CHOICES]])
        menu.callback = self._picked
        self.menu = menu
        self.add_item(menu)

    async def _picked(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner.id:
            return await interaction.response.send_message(
                "This isn't your search.", ephemeral=True)
        for child in self.children:
            child.disabled = True
        self.stop()
        await self.on_pick(interaction, self.menu.values[0])


async def offer_species_choices(interaction, typed, on_pick, *, candidates=None):
    """
    Turn an unrecognised species name into a dropdown, or explain why it cannot.

    Returns nothing useful - it either sends a picker or sends a refusal. The point is
    that it never accepts the name, because accepting an unrecognised name is exactly
    what left deposits sitting on the GTS that could never match anything.
    """
    choices = candidates if candidates is not None else suggest_species(typed)

    send = (interaction.followup.send if interaction.response.is_done()
            else interaction.response.send_message)

    if not choices:
        return await send(
            f"❓ No species matches **{typed}**. Check the spelling — the network "
            f"lists them the way the Pokédex does, so Mr. Mime and Nidoran♀ are "
            f"`mr-mime` and `nidoran-f`.",
            ephemeral=True)

    await send(
        f"❓ **{typed}** isn't a species the network recognises. "
        f"Did you mean one of these?",
        view=SpeciesPicker(interaction.user, choices, on_pick),
        ephemeral=True)


class GTSSearchModal(discord.ui.Modal, title="GTS Network Search"):
    wanted_species = discord.ui.TextInput(
        label="Specimen Wanted",
        placeholder="Leave blank to browse what's on the network",
        required=False,
        # 34 species names are longer than twenty characters, so the old cap made them
        # literally impossible to ask for. The longest is 27.
        max_length=30
    )
    wanted_gender = discord.ui.TextInput(
        label="Gender (M / F / Any)",
        default="Any",
        max_length=3
    )
    wanted_level = discord.ui.TextInput(
        label="Level Range (e.g., 1-100 or 50)",
        default="1-100",
        max_length=7
    )
    shiny_only = discord.ui.TextInput(
        label="Shiny Only? (Y/N)",
        default="N",
        max_length=1
    )

    def __init__(self, db_file):
        super().__init__()
        self.db_file = db_file

    async def on_submit(self, interaction: discord.Interaction):
        # 1. Parse the Inputs
        typed = self.wanted_species.value.strip()
        gender = self.wanted_gender.value.strip().upper()
        if gender not in ["M", "F"]: gender = "ANY"

        is_shiny = 1 if self.shiny_only.value.strip().upper() == "Y" else 0

        try:
            if "-" in self.wanted_level.value:
                min_lvl, max_lvl = map(int, self.wanted_level.value.split("-"))
            else:
                min_lvl = max_lvl = int(self.wanted_level.value)
        except ValueError:
            return await interaction.response.send_message("⚠️ Invalid level format.", ephemeral=True)

        criteria = (min_lvl, max_lvl, gender, is_shiny)

        async def run(picked_interaction, species):
            await self.run_search(picked_interaction, species, criteria)

        # Blank means "show me what is actually out there" - the one place a dropdown
        # of everything available really is possible, because what is ON the network
        # is a handful of species rather than all 1344.
        if not typed:
            async with aiosqlite.connect(self.db_file) as db:
                async with db.execute(
                        "SELECT DISTINCT dep_species FROM gts_deposits WHERE user_id != ?"
                        " ORDER BY dep_species", (str(interaction.user.id),)) as cursor:
                    stock = [row[0] for row in await cursor.fetchall()]

            listed = [resolve_species(name) or name for name in stock]
            if not listed:
                return await interaction.response.send_message(
                    "📭 Nothing is on the GTS network right now.", ephemeral=True)
            return await interaction.response.send_message(
                "🌐 Species currently on the network:",
                view=SpeciesPicker(interaction.user, listed, run,
                                   placeholder="Browse the network..."),
                ephemeral=True)

        species = resolve_species(typed)
        if not species:
            return await offer_species_choices(interaction, typed, run)

        await interaction.response.defer()
        await self.run_search(interaction, species, criteria)

    async def run_search(self, interaction, species, criteria):
        """The search itself, reachable from a typed name or from the dropdown."""
        min_lvl, max_lvl, gender, is_shiny = criteria
        if not interaction.response.is_done():
            await interaction.response.defer()

        # 2. Query the Database for Matches
        query = """
            SELECT 
                g.gts_id, g.user_id, g.message, g.req_species, g.req_min_level, g.req_max_level, g.req_gender,
                s.name, cp.level, cp.gender, cp.is_shiny, cp.ability, cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                cp.gmax_factor, cp.height_multiplier
            FROM gts_deposits g
            JOIN caught_pokemon cp ON g.instance_id = cp.instance_id
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            WHERE LOWER(g.dep_species) = LOWER(?) 
            AND cp.level BETWEEN ? AND ?
            AND (? = 'ANY' OR cp.gender = ?)
            AND (? = 0 OR cp.is_shiny = 1)
            AND g.user_id != ? -- Don't show the user their own deposits!
            ORDER BY g.deposit_time ASC
        """
        params = (species, min_lvl, max_lvl, gender, gender, is_shiny, str(interaction.user.id))

        async with aiosqlite.connect(self.db_file) as db:
            async with db.execute(query, params) as cursor:
                results = await cursor.fetchall()

        if not results:
            return await interaction.followup.send("📭 No specimens on the GTS match your exact search criteria right now.")

        # 3. Launch the Paginator
        view = GTSSearchPaginator(interaction.user, results, self.db_file)
        await interaction.followup.send(embed=view.create_embed(), view=view)

class GTSDepositModal(discord.ui.Modal, title="Global Trade Station Deposit"):
    req_species = discord.ui.TextInput(
        label="Species you want to receive",
        placeholder="e.g., Bulbasaur, Mr. Mime, Nidoran F",
        min_length=2,
        # 34 species names are longer than twenty characters; the longest is 27.
        max_length=30
    )
    req_level = discord.ui.TextInput(
        label="Desired Level Range",
        placeholder="e.g., 1-100 or 50",
        default="1-100",
        max_length=7
    )
    req_shiny = discord.ui.TextInput(
        label="Must be Shiny? (Y/N)",
        placeholder="Y or N",
        default="N",
        max_length=1
    )
    req_gender = discord.ui.TextInput(
        label="Desired Gender (M / F / Any)",
        placeholder="M, F, or Any",
        default="Any",
        max_length=3
    )
    message = discord.ui.TextInput(
        label="Trade Message",
        style=discord.TextStyle.paragraph,
        placeholder="Please trade with me. Thanks in advance!",
        default="Please trade with me. Thanks in advance!",
        required=False,
        max_length=100
    )

    def __init__(self, specimen_data, db_file):
        super().__init__()
        self.specimen = specimen_data # Dictionary containing name, level, gender, instance_id
        self.db_file = db_file

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        # 1. Parse Level Range
        try:
            if "-" in self.req_level.value:
                min_lvl, max_lvl = map(int, self.req_level.value.split("-"))
            else:
                min_lvl = max_lvl = int(self.req_level.value)
        except ValueError:
            return await interaction.response.send_message("⚠️ Invalid level format. Use `1-100` or a specific number.", ephemeral=True)

        # 2. Parse Gender
        req_gender_val = self.req_gender.value.strip().upper()
        if req_gender_val not in ["M", "F", "ANY"]:
            req_gender_val = "ANY"

        # 3. Parse Shiny Requirement (Y/N to 1/0)
        req_shiny_val = 1 if self.req_shiny.value.strip().upper() == "Y" else 0

        # 4. Resolve the requested species against the species table.
        # This is the whole bug: the name used to be `.capitalize()`d and stored as
        # typed. The matching engine compares two stored strings, so "Mr. Mime" against
        # a database that says `mr-mime` produced a deposit that was accepted, listed,
        # and could never match anything - with nothing anywhere to say why.
        typed = self.req_species.value.strip()
        species = resolve_species(typed)

        if not species:
            async def finish(picked_interaction, chosen):
                await self.finalise(picked_interaction, chosen, min_lvl, max_lvl,
                                    req_gender_val, req_shiny_val)
            return await offer_species_choices(interaction, typed, finish)

        await interaction.response.defer(ephemeral=True)
        await self.finalise(interaction, species, min_lvl, max_lvl,
                            req_gender_val, req_shiny_val)

    async def finalise(self, interaction, species, min_lvl, max_lvl,
                       req_gender_val, req_shiny_val):
        """Write the deposit. Reached from a resolved name or from the dropdown."""
        user_id = str(interaction.user.id)
        gts_id = str(uuid.uuid4())[:8]

        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)

        # Stored canonically on BOTH sides, so a future deposit typed any other way
        # still resolves to the same string these queries compare.
        req_species_val = species
        deposited = resolve_species(self.specimen['name']) or self.specimen['name']

        async with aiosqlite.connect(self.db_file) as db:
            # The GTS is a transfer route like any other, so the starter lock applies
            # here too - and it has to refuse at DEPOSIT, because once a deposit is
            # listed the match can fire without the owner being present.
            refusal = await blocked_from_trading(db, self.specimen['instance_id'], user_id)
            if refusal:
                return await interaction.followup.send(refusal, ephemeral=True)
            # CHECK LIMITS FIRST
            async with db.execute("SELECT COUNT(*) FROM gts_deposits WHERE user_id = ?", (user_id,)) as cursor:
                count = await cursor.fetchone()
                if count[0] >= 3:
                    return await interaction.followup.send("🛑 You have reached the maximum of 3 active GTS deposits.")

            # 5. Insert into GTS (Including req_is_shiny!)
            await db.execute("""
                INSERT INTO gts_deposits 
                (gts_id, user_id, instance_id, dep_species, dep_level, dep_gender, req_species, req_min_level, req_max_level, req_gender, req_is_shiny, message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (gts_id, user_id, self.specimen['instance_id'], deposited, self.specimen['level'], self.specimen['gender'],
                  req_species_val, min_lvl, max_lvl, req_gender_val, req_shiny_val, self.message.value))

            await db.commit()

        # 6. Trigger the Matching Engine in the background
        await interaction.followup.send(
            f"✅ **{pretty_species(deposited)}** uploaded to the GTS network in "
            f"exchange for a **{pretty_species(req_species_val)}**!\n"
            f"*Searching for compatible exchange partners...*")

        await process_gts_match(interaction.client, self.db_file, gts_id)

async def process_gts_match(bot, db_file, new_gts_id):
    """Checks a newly deposited GTS record against existing records to find a two-way match."""
    
    async with aiosqlite.connect(db_file) as db:
        # 1. Fetch exactly the columns we need to bypass any ALTER TABLE ordering issues
        query_fetch = """
            SELECT gts_id, user_id, instance_id, dep_species, dep_level, dep_gender, 
                   req_species, req_min_level, req_max_level, req_gender, req_is_shiny
            FROM gts_deposits WHERE gts_id = ?
        """
        async with db.execute(query_fetch, (new_gts_id,)) as cursor:
            new_dep = await cursor.fetchone()
            
        if not new_dep: return 
        
        # Safely unpack exactly 11 variables
        n_id, n_user, n_instance, n_dep_species, n_dep_lvl, n_dep_gen, n_req_species, n_req_min, n_req_max, n_req_gen, n_req_shiny = new_dep

        # We also need to know if the Pokémon WE just deposited is shiny to satisfy THEIR requests!
        async with db.execute("SELECT is_shiny FROM caught_pokemon WHERE instance_id = ?", (n_instance,)) as cursor:
            cp_row = await cursor.fetchone()
            n_dep_shiny = cp_row[0] if cp_row else 0

        # 2. Search for a Reverse Match!
        query_match = """
            SELECT g.gts_id, g.user_id, g.instance_id 
            FROM gts_deposits g
            JOIN caught_pokemon cp ON g.instance_id = cp.instance_id
            WHERE g.user_id != ? 
            
            AND LOWER(g.dep_species) = LOWER(?) 
            AND g.dep_level BETWEEN ? AND ? 
            AND (? = 'ANY' OR g.dep_gender = ?)
            AND (? = 0 OR cp.is_shiny = 1)
            
            AND LOWER(g.req_species) = LOWER(?)
            AND ? BETWEEN g.req_min_level AND g.req_max_level
            AND (g.req_gender = 'ANY' OR g.req_gender = ?)
            AND (COALESCE(g.req_is_shiny, 0) = 0 OR ? = 1)
            
            ORDER BY g.deposit_time ASC LIMIT 1
        """
        
        params = (
            n_user, 
            n_req_species, n_req_min, n_req_max, n_req_gen, n_req_gen, n_req_shiny, 
            n_dep_species, n_dep_lvl, n_dep_gen, n_dep_shiny 
        )
        
        async with db.execute(query_match, params) as cursor:
            match = await cursor.fetchone()
            
        if match:
            # WE FOUND A MATCH! EXECUTE THE TRADE.
            match_gts_id, match_user_id, match_instance = match
            
            await db.execute("BEGIN TRANSACTION")
            try:
                # Snapshot both specimens while they are still with their owners.
                snap_new = await snapshot(db, [n_instance])
                snap_match = await snapshot(db, [match_instance])

                # Swap Ownership
                await db.execute("UPDATE caught_pokemon SET user_id = ? WHERE instance_id = ?", (match_user_id, n_instance))
                await db.execute("UPDATE caught_pokemon SET user_id = ? WHERE instance_id = ?", (n_user, match_instance))
                await bump_to_end_of_box(db, n_instance, match_instance)
                
                # Remove both from the GTS
                await db.execute("DELETE FROM gts_deposits WHERE gts_id IN (?, ?)", (new_gts_id, match_gts_id))
                
                # Active Partner Safety Sweep
                await db.execute("""
                    UPDATE users SET active_partner = NULL 
                    WHERE (user_id = ? AND active_partner = ?) 
                       OR (user_id = ? AND active_partner = ?)
                """, (n_user, n_instance, match_user_id, match_instance))
                
                # 🚨 INLINE THE ALERTS DIRECTLY INTO THE TRANSACTION!
                # Prettified for the reader: species are stored canonically now, which
                # means 'mr-mime' rather than 'Mr. Mime'.
                dep_label, req_label = pretty_species(n_dep_species), pretty_species(n_req_species)
                alert_1 = f"🤝 **GTS Update:** Your deposited **{dep_label}** was successfully traded for a **{req_label}**! It is now in your PC."
                alert_2 = f"🤝 **GTS Update:** Your deposited **{req_label}** was successfully traded for a **{dep_label}**! It is now in your PC."
                
                await db.execute("INSERT INTO user_alerts (user_id, alert_text) VALUES (?, ?)", (n_user, alert_1))
                await db.execute("INSERT INTO user_alerts (user_id, alert_text) VALUES (?, ?)", (match_user_id, alert_2))

                await log_trade(db, trade_type='gts', user_a=n_user, user_b=match_user_id,
                                side_a=snap_new, side_b=snap_match,
                                detail=f"GTS auto-match {new_gts_id} ↔ {match_gts_id}")

                # Commit everything (Trades + Alerts) all at once!
                await db.commit()

            except Exception as e:
                await db.rollback()
                print(f"GTS Atomic Trade Error: {e}")
                return

            # Inside `if match:` - there is nothing to announce when no partner was
            # found - but outside the transaction, so a failed broadcast cannot undo a
            # trade that has already committed.
            await announce_trade(bot, trade_type='gts', user_a=n_user,
                                 user_b=match_user_id,
                                 side_a=snap_new, side_b=snap_match,
                                 detail="Matched automatically by the GTS")


class BackpackPaginator(discord.ui.View):
    def __init__(self, user, inventory_data, catalog):
        super().__init__(timeout=120)
        self.user = user
        self.raw_inventory = inventory_data
        self.catalog = catalog
        
        # State
        self.current_category = "all"
        self.filtered_inventory = self.raw_inventory
        self.items_per_page = 5
        self.current_page = 1
        self.total_pages = self._calculate_pages()
        
        # Add the dropdown UI
        self.select_menu = discord.ui.Select(
            placeholder="Filter field pack...",
            options=CATEGORY_OPTIONS,
            custom_id="bp_category_select",
            row=0 # Keep dropdown on top row
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)
        
        self.update_buttons()

    def _calculate_pages(self):
        return max(1, math.ceil(len(self.filtered_inventory) / self.items_per_page))

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ This is not your field pack!", ephemeral=True)
            
        self.current_category = self.select_menu.values[0]
        
        # Re-filter the inventory based on the selected category
        if self.current_category == "all":
            self.filtered_inventory = self.raw_inventory
        else:
            self.filtered_inventory = []
            for item_name, qty in self.raw_inventory:
                clean_key = item_name.lower().strip()
                cat_data = self.catalog.get(clean_key, {})
                if cat_data.get("category") == self.current_category:
                    self.filtered_inventory.append((item_name, qty))
                    
        # Reset to page 1 and recalculate pages
        self.current_page = 1
        self.total_pages = self._calculate_pages()
        self.update_buttons()
        
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    def update_buttons(self):
        """Disables navigation buttons if at the start or end of the catalog."""
        # Find the specific buttons by matching their custom_ids or checking type
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "bp_prev":
                    child.disabled = self.current_page <= 1
                elif child.custom_id == "bp_next":
                    child.disabled = self.current_page >= self.total_pages

    def generate_embed(self):
        """Slices the filtered list and builds the UI."""
        embed = discord.Embed(
            title=f"🎒 {self.user.name}'s Field Equipment", 
            color=discord.Color.orange(),
            description=f"**Page {self.current_page} of {self.total_pages}**"
        )
        
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.filtered_inventory[start_idx:end_idx]
        
        if not page_items:
            embed.description += "\n\n*No items found in this section of your pack.*"
            return embed
            
        for raw_item_name, quantity in page_items:
            clean_key = clean_key = raw_item_name.lower().strip()
            item_data = self.catalog.get(clean_key)
            
            if item_data:
                display_name = item_data.get('name', raw_item_name.title())
                emoji = item_data.get('emoji', '📦')
                desc = item_data.get('desc', '*No description available.*')
            else:
                display_name = raw_item_name.title().replace('-', ' ')
                emoji = "📦"
                desc = "*Archived/Unknown Anomaly*"
                
            embed.add_field(
                name=f"{emoji} {display_name}", 
                value=f"**Quantity:** {quantity}\n*{desc}*", 
                inline=False
            )
            
        return embed

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.primary, custom_id="bp_prev", row=1)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ This is not your field pack!", ephemeral=True)
            
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary, custom_id="bp_next", row=1)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ This is not your field pack!", ephemeral=True)
            
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

class TMShelfView(discord.ui.View):
    """
    A shelf of 340 TMs that a person can actually use.

    The market's own pager would need thirty-four pages to show them all, and nobody
    reaches page nineteen looking for Thunder Wave. So browsing is the FALLBACK here
    and searching is the front door - this view exists to render the result of a
    narrowing (one species, one type, one category), not to be scrolled from the top.

    Every row says whether it is already owned, because "what can I actually do right
    now" is the question a shop list is being asked.
    """

    PER_PAGE = 12

    def __init__(self, ctx, moves, owned, heading, note=""):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.moves = moves
        self.owned = owned
        self.heading = heading
        self.note = note
        self.page = 0
        self.update_buttons()

    @property
    def max_pages(self):
        return max(1, math.ceil(len(self.moves) / self.PER_PAGE))

    def update_buttons(self):
        self.prev_page.disabled = self.page <= 0
        self.next_page.disabled = self.page >= self.max_pages - 1

    def generate_embed(self):
        embed = discord.Embed(title=self.heading, color=discord.Color.teal())

        held = sum(1 for m in self.moves if m in self.owned)
        lines = [f"**{len(self.moves)}** machines · you own **{held}** of them."]
        if self.note:
            lines.append(self.note)
        lines.append("Buy with `!buy <move>` — one payment, yours forever.")
        embed.description = "\n".join(lines)

        start = self.page * self.PER_PAGE
        body = []
        for move in self.moves[start:start + self.PER_PAGE]:
            data = TM_CATALOG.get(move, {})
            # The type badge always leads, because it is what the eye scans a list of
            # forty moves for. Ownership is already said in the cost slot, so a tick
            # here was spending the one distinctive glyph on the less useful fact.
            mark = data.get('emoji', '💿')
            bits = [(data.get('type') or 'normal').title()]
            if data.get('power'):
                bits.append(f"{data['power']} power")
            elif data.get('class') == 'status':
                bits.append("status")
            cost = ("owned" if move in self.owned
                    else f"🪙 {data.get('price', 0):,}")
            body.append(f"{mark} **{move.replace('-', ' ').title()}** — "
                        f"{' · '.join(bits)} · {cost}")

        # One field, not one per move: 12 fields of two words each is a wall, and the
        # 25-field ceiling would be in sight the moment somebody wanted a longer page.
        embed.add_field(name="​", value="\n".join(body) or "*nothing*", inline=False)
        embed.set_footer(text=f"Page {self.page + 1} of {self.max_pages}")
        return embed

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "⚠️ This is not your shelf — run `!tmshop` yourself.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button):
        self.page = max(0, self.page - 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button):
        self.page = min(self.max_pages - 1, self.page + 1)
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)


class MarketView(discord.ui.View):
    # Discord refuses any embed carrying more than 25 fields, and one field is one
    # item, so the shelf has a hard ceiling no matter how the catalogue grows. Ten
    # to a page stays readable and leaves the ceiling a long way off.
    ITEMS_PER_PAGE = 10

    def __init__(self, catalog, category="all"):
        super().__init__(timeout=120)
        self.catalog = catalog
        # `!tmshop` opens this same view already on its own shelf, which is what makes
        # folding the TM shop in here a consolidation rather than a removal - one
        # implementation, one UI, and the command people already type still works.
        self.current_category = category
        self.current_page = 0

        # Add the dropdown dynamically
        self.select_menu = discord.ui.Select(
            placeholder="Select an equipment category...",
            options=CATEGORY_OPTIONS,
            custom_id="market_category_select",
            row=0
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)
        self.update_buttons()

    def visible_items(self):
        """Everything on sale in the chosen category, in catalogue order."""
        return [
            (item_key, data) for item_key, data in self.catalog.items()
            if data.get("purchasable") is not False
            and (self.current_category == "all"
                 or data.get("category") == self.current_category)
        ]

    @property
    def max_pages(self):
        return max(1, math.ceil(len(self.visible_items()) / self.ITEMS_PER_PAGE))

    def update_buttons(self):
        self.prev_button.disabled = self.current_page <= 0
        self.next_button.disabled = self.current_page >= self.max_pages - 1

    async def select_callback(self, interaction: discord.Interaction):
        # Update the state based on what they clicked
        self.current_category = self.select_menu.values[0]
        # A shorter category must not strand the reader past its last page.
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    def generate_embed(self):
        embed = discord.Embed(title="🛒 Ecological Supply Market", color=discord.Color.green())
        embed.description = "Use `!buy [quantity] [item_name]` to requisition supplies."
        if self.current_category == "tm":
            # Thirty-four pages of them. This shelf is here for completeness; the
            # command that actually finds one is the one to point at.
            embed.description += (
                "\n💿 All **340** TMs are stocked and every one is permanent. "
                "Searching beats scrolling: `!tmshop <move>`, or `!tmshop list "
                "<specimen>` for only what it can learn.")

        stock = self.visible_items()
        start = self.current_page * self.ITEMS_PER_PAGE
        for item_key, data in stock[start:start + self.ITEMS_PER_PAGE]:
            embed.add_field(
                name=f"{data['emoji']} {data['name']} (🪙 {data['price']})",
                value=data['desc'],
                inline=False
            )

        if not stock:
            embed.description += "\n\n*No items available in this category.*"
        else:
            embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} "
                                  f"| {len(stock)} items in stock")

        return embed

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.primary, row=1)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary, row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            embed.description = "The market is currently empty. Use `!global market sell` to list an asset!"
        else:
            for item in chunk:
                shiny_icon = "🌟" if item['is_shiny'] else "🌿"
                
                # Format the time remaining cleanly
                embed.add_field(
                    # The badges go on the VALUE, not the field name: an embed field
                    # name renders a custom emoji as its raw `<:alpha:154…>` text.
                    name=f"Listing #{item['list_id']} | {shiny_icon} {item['name'].capitalize()} (Lv. {item['level']})",
                    value=f"{species_badges(item['name'])}"
                          f"{trait_badges(gmax=item.get('gmax'), height_multiplier=item.get('h_mult'))}"
                          f"\n**Price:** 🪙 {item['price']:,} Tokens\n**Seller ID:** `{item['seller']}`\n**Listed Pokemon ID:** `{item['uuid'][:8]}`",
                    inline=False
                )

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} | Use !global market buy [Listing ID]")
        return embed

    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Please run your own `!global market view` command to browse.", ephemeral=True)
            
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("Please run your own `!global market view` command to browse.", ephemeral=True)
            
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

async def split_equip_request(db, user_id, request):
    """
    `!equip [target] <item>` split into (target, item).

    The target is optional, and unlike `!learn` the ambiguity cannot be settled by
    counting digits: `!equip air balloon` and `!equip 4 air balloon` differ only in
    whether the first word names a specimen, and item names are several words long.

    So the ITEM decides, by asking what the trainer is actually carrying. The whole
    phrase is tried first; only if that is not something they hold is the first word
    considered a target. A trainer with no Air Balloon therefore gets told they have no
    Air Balloon, rather than being told there is no specimen called `air`.
    """
    tokens = request.split()

    async with db.execute(
            "SELECT item_name FROM user_inventory WHERE user_id = ? AND quantity > 0",
            (user_id,)) as cursor:
        held = {row[0] for row in await cursor.fetchall()}
    # `none` is the documented way to clear a slot, and is not an inventory row.
    known = held | {'none', 'unequip'}

    whole = "-".join(tokens).lower()
    if whole in known:
        return None, whole

    if len(tokens) >= 2:
        rest = "-".join(tokens[1:]).lower()
        if rest in known:
            return tokens[0], rest

    # Neither reading names something they hold. Fall back to the shape the words have:
    # a leading box number or partner word is a target, anything else is all item - so
    # the complaint that follows is about the thing they actually got wrong.
    if len(tokens) >= 2 and (tokens[0].isdigit() or looks_like_partner(tokens[0])):
        return tokens[0], "-".join(tokens[1:]).lower()
    return None, whole

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
            ("greatball", 100), 
            ("potion", 100), 
            ("purifier", 50)
        ]
        
        exclusive_items = [
            ("ultraball", 200), 
            ("full-restore", 100), 
            ("rare-candy", 500)
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

        
    @commands.command(name="dshop", aliases=["daily"])
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
    
    @commands.group(name="gts", invoke_without_command=True)
    async def gts_base(self, ctx):
        """Base command for the Global Trade Station."""
        embed = discord.Embed(
            title="🌐 Global Trade Station (GTS)",
            description="Welcome to the biological exchange network. Here you can offer specimens in exchange for specific requests from other researchers globally.",
            color=discord.Color.blue()
        )
        embed.add_field(name="📥 Deposit", value="`!gts deposit <BoxNum>`\nUpload a specimen to the network.", inline=False)
        embed.add_field(name="📋 Active Listings", value="`!gts active`\nView your currently deposited specimens.", inline=False)
        embed.add_field(name="📤 Withdraw", value="`!gts remove <GTS_ID>`\nPull a specimen out of the network.", inline=False)
        embed.add_field(name="📤 Wanted", value="`!gts wanted <box number>`\nPulls all the criteria matching pokemon for the specific box number pokemon.", inline=False)
        await ctx.send(embed=embed)

    @gts_base.command(name="deposit", aliases=["add"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat()
    async def gts_deposit(self, ctx, box_num: int):
        """Deposits a specimen into the GTS."""
        if box_num < 1:
            return await ctx.send("⚠️ Please provide a valid Box number greater than 0.")

        user_id = str(ctx.author.id)

        # 1. Fetch the Pokémon using the CTE logic (Notice the new GTS lock check!)
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("""
                WITH NumberedPC AS (
                    SELECT 
                        cp.instance_id, 
                        cp.level, 
                        cp.gender,
                        s.name,
                        ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.user_id = ? 
                      AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                      AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits) -- 🚨 The GTS Lock!
                )
                SELECT name, level, gender, instance_id 
                FROM NumberedPC 
                WHERE box_number = ?
            """, (user_id, box_num)) as cursor:
                pokemon = await cursor.fetchone()

        if not pokemon:
            return await ctx.send(f"⚠️ Could not find a valid specimen at Box `#{box_num}`. It may be deployed, already in the GTS, or it doesn't exist.")

        specimen_data = {
            "name": pokemon[0],
            "level": pokemon[1],
            "gender": pokemon[2],
            "instance_id": pokemon[3]
        }

        # 2. Trigger the Modal!
        # Note: Modals MUST be sent in response to an interaction. 
        # Since this is a text command (!gts), we need to send a button first to open the modal, 
        # OR if you are migrating to hybrid/slash commands, use interaction.response.send_modal.
        
        # Here is the Button View approach for a standard text command:
        view = discord.ui.View(timeout=60)
        
        async def modal_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This isn't your deposit!", ephemeral=True)
            await interaction.response.send_modal(GTSDepositModal(specimen_data, DB_FILE))
            
        btn = discord.ui.Button(label="Open GTS Terminal", style=discord.ButtonStyle.success)
        btn.callback = modal_callback
        view.add_item(btn)
        
        await ctx.send(f"📡 Terminal ready for **{specimen_data['name'].capitalize()}** (Lvl {specimen_data['level']}). Click below to set your exchange requirements.", view=view)

    @gts_base.command(name="active", aliases=["status", "list"])
    @checks.has_started()
    @checks.is_authorized()
    async def gts_active(self, ctx):
        """Shows the user's active GTS deposits."""
        user_id = str(ctx.author.id)
        
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("""
                SELECT g.gts_id, g.dep_species, g.dep_level, g.req_species,
                       g.req_min_level, g.req_max_level, g.deposit_time,
                       cp.gmax_factor, cp.height_multiplier
                FROM gts_deposits g
                LEFT JOIN caught_pokemon cp ON cp.instance_id = g.instance_id
                WHERE g.user_id = ?
                ORDER BY g.deposit_time DESC
            """, (user_id,)) as cursor:
                deposits = await cursor.fetchall()
                
        if not deposits:
            return await ctx.send("📭 You currently have no specimens uploaded to the GTS network.")
            
        embed = discord.Embed(title="🌐 Your Active GTS Listings", color=discord.Color.blue())
        
        for d in deposits:
            (gts_id, dep_sp, dep_lvl, req_sp, req_min, req_max, dep_time,
             dep_gmax, dep_h_mult) = d
            lvl_req = f"Lvl {req_min}-{req_max}" if req_min != req_max else f"Lvl {req_min}"

            # Only the OFFERED specimen gets trait badges. What you are seeking is a
            # species and a level range, not a particular specimen, so there is no
            # G-Max factor or height to report on that half.
            embed.add_field(
                name=f"ID: `{gts_id}`",
                value=f"**Offered:** {pretty_species(dep_sp)} (Lvl {dep_lvl})\n"
                      f"{species_badges(dep_sp)}"
                      f"{trait_badges(gmax=dep_gmax, height_multiplier=dep_h_mult)}\n"
                      f"**Seeking:** {pretty_species(req_sp)} ({lvl_req})\n"
                      f"{species_badges(req_sp)}",
                inline=False
            )
            
        embed.set_footer(text=f"{len(deposits)}/3 Active Slots Used")
        await ctx.send(embed=embed)

    @gts_base.command(name="remove", aliases=["withdraw", "cancel"])
    @checks.has_started()
    @checks.is_authorized()
    async def gts_remove(self, ctx, gts_id: str):
        """Removes a specimen from the GTS and returns it to the user's PC."""
        user_id = str(ctx.author.id)
        clean_id = gts_id.strip()
        
        async with aiosqlite.connect(DB_FILE) as db:
            # Check if it exists and belongs to them
            async with db.execute("SELECT dep_species FROM gts_deposits WHERE gts_id = ? AND user_id = ?", (clean_id, user_id)) as cursor:
                record = await cursor.fetchone()
                
            if not record:
                return await ctx.send(f"⚠️ Could not find an active deposit with ID `{clean_id}`. It may have already been traded!")
                
            # Delete it
            await db.execute("DELETE FROM gts_deposits WHERE gts_id = ? AND user_id = ?", (clean_id, user_id))
            await db.commit()
            
        await ctx.send(f"✅ Successfully canceled the exchange. **{record[0]}** has been returned to your local PC.")

    @gts_base.command(name="wanted")
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat()
    async def gts_wanted(self, ctx, box_num: int):
        """Finds GTS listings looking for a specific specimen you own."""
        if box_num < 1:
            return await ctx.send("⚠️ Please provide a valid Box number.")

        user_id = str(ctx.author.id)
        
        try:
            # 1. Fetch your offered Pokémon
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute("""
                    WITH NumberedPC AS (
                        SELECT instance_id, level, gender, is_shiny, s.name, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.user_id = ? AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments) AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                    )
                    SELECT name, level, gender, is_shiny, instance_id FROM NumberedPC WHERE box_number = ?
                """, (user_id, box_num)) as cursor:
                    offered_poke = await cursor.fetchone()

            if not offered_poke:
                return await ctx.send(f"⚠️ Could not find a valid specimen at Box `#{box_num}`.")

            off_name, off_lvl, off_gen, off_shiny, off_instance = offered_poke

            # 2. The Reverse-Lookup Query
            query = """
            SELECT 
                g.gts_id, g.user_id, g.message, g.req_species, g.req_min_level, g.req_max_level, g.req_gender,
                s.name, cp.level, cp.gender, cp.is_shiny, cp.ability, cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                cp.gmax_factor, cp.height_multiplier
            FROM gts_deposits g
            JOIN caught_pokemon cp ON g.instance_id = cp.instance_id
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            WHERE LOWER(g.req_species) = LOWER(?)
            AND ? BETWEEN g.req_min_level AND g.req_max_level
            AND (g.req_gender = 'ANY' OR g.req_gender = ?)
            AND (COALESCE(g.req_is_shiny, 0) = 0 OR ? = 1)
            AND g.user_id != ?
            ORDER BY g.deposit_time ASC
            """
            params = (off_name, off_lvl, off_gen, off_shiny, user_id)

            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute(query, params) as cursor:
                    results = await cursor.fetchall()

            if not results:
                return await ctx.send(f"📭 Nobody on the GTS is currently looking for a Level {off_lvl} {off_name} right now.")

            # 3. Launch the Paginator
            view = GTSSearchPaginator(ctx.author, results, DB_FILE, preselected_instance=off_instance)
            await ctx.send(f"🔍 Found **{len(results)}** trainers looking for your {off_name}!", embed=view.create_embed(), view=view)

        except Exception as e:
            print(f"GTS Wanted Error: {e}")
            await ctx.send("❌ A critical database error occurred while searching the GTS.")

    @gts_base.command(name="search", aliases=["find"])
    @checks.has_started()
    @checks.is_authorized()
    async def gts_search(self, ctx):
        """Search the GTS network for specific Pokémon."""
        view = discord.ui.View(timeout=60)
        
        async def modal_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This isn't your terminal!", ephemeral=True)
            # Make sure your bot's DB_FILE variable is passed correctly here!
            await interaction.response.send_modal(GTSSearchModal(DB_FILE))
            
        btn = discord.ui.Button(label="Open Search Terminal", style=discord.ButtonStyle.primary)
        btn.callback = modal_callback
        view.add_item(btn)
        
        await ctx.send("📡 GTS Search Terminal ready. Click below to enter your search criteria.", view=view)

    @staticmethod
    def station_embed():
        """The station's front page, shown by `!global` and by `!global market`."""
        embed = discord.Embed(title="🌐 Global Transfer Station", color=discord.Color.blue())
        embed.description = (
            "`!global market sell [Tag ID] [Price]` - List a specimen on the market.\n"
            "`!global market view` - Browse available assets.\n"
            "`!global market inspect [Listing ID]` - Full genetic assay of a listing.\n"
            "`!global market buy [Listing ID]` - Procure a specimen.\n"
            "`!global market cancel [Listing ID]` - Recall your own listing."
        )
        return embed

    # ==========================================
    # THE GLOBAL TRANSFER STATION
    # ==========================================
    # This group was registered under the single name "global market" - one dictionary
    # key with a space in it. discord.py's prefix parser splits the message on
    # whitespace BEFORE it looks anything up, so `!global market view` made it search
    # `all_commands` for "global", found nothing, raised CommandNotFound, and the
    # default handler swallowed it. No reply, no error, nothing in the log.
    #
    # The whole station - sell, view, inspect, buy, cancel - had been unreachable that
    # way since the group was renamed. A real `global` group with `market` as a real
    # sub-group makes every documented invocation work exactly as written, rather than
    # renaming the feature out from under everyone who has already learned it.
    @commands.group(name="global", invoke_without_command=True)
    @checks.has_started()
    @checks.is_authorized()
    async def global_root(self, ctx):
        """The global marketplace. See `!global market`."""
        await ctx.send(embed=self.station_embed())

    @global_root.group(name="market", invoke_without_command=True)
    @checks.has_started()
    @checks.is_authorized()
    async def global_market(self, ctx):
        """The cross-server auction house. `!global market sell|view|inspect|buy|cancel`."""
        await ctx.send(embed=self.station_embed())

    @global_market.command(name="sell")
    @checks.has_started()
    @checks.is_authorized()
    async def global_market_sell(self, ctx, tag_id: str, price: int):
        """Lists a specimen on the global market for 48 hours."""
        user_id = str(ctx.author.id)
        
        if price <= 0:
            return await ctx.send("⚠️ You must request a conservation grant of at least 1 Eco-Token.")
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # 1. Verify Ownership & Retrieve Specimen Data (Box Number or UUID)
                if tag_id.isdigit() and len(tag_id) <= 6:
                    async with db.execute("""
                        WITH Roster AS (
                            SELECT cp.instance_id, s.name, cp.level, ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                            FROM caught_pokemon cp
                            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                            WHERE cp.user_id = ?
                            AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                            AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                        ) SELECT instance_id, name, level FROM Roster WHERE box_number = ?
                    """, (user_id, int(tag_id))) as cursor:
                        pokemon_data = await cursor.fetchone()
                else:
                    async with db.execute("""
                        SELECT cp.instance_id, s.name, cp.level 
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.instance_id LIKE ? AND cp.user_id = ?
                    """, (f"{tag_id}%", user_id)) as cursor:
                        pokemon_data = await cursor.fetchone()
                
                if not pokemon_data:
                    return await ctx.send("❌ Could not locate that specimen in your survey notebook.")
                    
                actual_tag, name, level = pokemon_data
                
                # 2. Security Check: Prevent selling active party members
                async with db.execute("SELECT slot FROM user_party WHERE instance_id = ?", (actual_tag,)) as cursor:
                    if await cursor.fetchone():
                        return await ctx.send("⚠️ You cannot transfer a specimen that is currently assigned to your active field roster! Remove it from your party first.")
                        
                # 3. Security Check: Prevent duplicate listings
                async with db.execute("SELECT listing_id FROM global_market WHERE instance_id = ?", (actual_tag,)) as cursor:
                    if await cursor.fetchone():
                        return await ctx.send("⚠️ This specimen is already listed on the open market!")
                    
                # The market is a transfer route too, so it refuses a starter at the
                # point of LISTING - a listing that could never legally complete is
                # worse than a refusal, because it wastes the buyer's time as well.
                refusal = await blocked_from_trading(db, actual_tag, user_id)
                if refusal:
                    return await ctx.send(refusal)

                # 4. Process the Listing (Generate a 48-hour expiration timestamp)
                expiration_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=48)

                await db.execute("""
                    INSERT INTO global_market (seller_id, instance_id, price, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, actual_tag, price, expiration_date.strftime('%Y-%m-%d %H:%M:%S')))
                
                await db.commit()
            
            # 5. Confirmation UI
            embed = discord.Embed(title="🌐 Global Transfer Authorized", color=discord.Color.gold())
            embed.description = f"**{ctx.author.name}** has listed a **Level {level} {name.capitalize()}** on the open market."
            embed.add_field(name="Requested Grant", value=f"🪙 {price:,} Eco-Tokens", inline=True)
            embed.add_field(name="Expiration", value="⏳ 48 Hours", inline=True)
            embed.set_footer(text=f"Tag ID: {actual_tag[:8]}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Global Market Sell Error: {e}")
            await ctx.send("❌ A database error occurred while processing the transfer.")

    @global_market.command(name="view", aliases=["browse", "market"])
    @checks.has_started()
    @checks.is_authorized()
    async def global_market_view(self, ctx):
        """Browses all active listings on the global market."""
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # 1. GARBAGE COLLECTION: Delete expired listings automatically!
                await db.execute("DELETE FROM global_market WHERE expires_at < CURRENT_TIMESTAMP")
                await db.commit()
                
                # 2. Fetch all active listings, joining the biological data AND fetching instance_id
                async with db.execute("""
                    SELECT gm.listing_id, gm.price, gm.seller_id,
                        s.name, cp.level, cp.is_shiny, gm.instance_id,
                        cp.gmax_factor, cp.height_multiplier
                    FROM global_market gm
                    JOIN caught_pokemon cp ON gm.instance_id = cp.instance_id
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    ORDER BY gm.listed_at DESC
                """) as cursor:
                    rows = await cursor.fetchall()

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
                    'uuid': row[6],
                    # Carried so the browse list can badge an Alpha or a G-Max specimen
                    # without opening every listing to find out.
                    'gmax': row[7],
                    'h_mult': row[8],
                })
                
            # 4. Boot up the Paginator
            view = MarketPaginator(ctx, market_data)
            await ctx.send(embed=view.create_embed(), view=view)
            
        except Exception as e:
            print(f"Global Market View Error: {e}")
            await ctx.send("❌ A database error occurred while accessing the market network.")

    @global_market.command(name="inspect", aliases=["info", "view_listing"])
    @checks.has_started()
    @checks.is_authorized()
    async def global_market_info(self, ctx, listing_id: int):
        """Runs a complete genetic and tactical assay on a specific market listing."""
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:

                # 1. The Deep Dive Query (Now pulling the gmax_factor)
                async with db.execute("""
                    SELECT gm.price, gm.seller_id, gm.expires_at,
                        cp.pokedex_id, s.name, cp.level, cp.nature, cp.is_shiny, cp.ability,
                        cp.iv_hp, cp.iv_attack, cp.iv_defense, cp.iv_sp_atk, cp.iv_sp_def, cp.iv_speed,
                        cp.gmax_factor, cp.gender, cp.height_multiplier
                    FROM global_market gm
                    JOIN caught_pokemon cp ON gm.instance_id = cp.instance_id
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE gm.listing_id = ?
                """, (listing_id,)) as cursor:
                    data = await cursor.fetchone()

            if not data:
                return await ctx.send(f"❌ Listing `#{listing_id}` does not exist or has already expired.")
                
            # Unpack the massive data payload, including the new marker
            (price, seller_id, expires_at, p_id, name, level, nature, is_shiny, ability,
             iv_hp, iv_atk, iv_def, iv_spa, iv_spd, iv_spe, gmax_factor, gender,
             h_mult) = data
            
            # 2. Calculate Genetic Potential (IVs)
            iv_total = iv_hp + iv_atk + iv_def + iv_spa + iv_spd + iv_spe
            iv_percentage = int((iv_total / 186.0) * 100)
            
            # 3. Handle the Expiration Timestamp for Discord's UI
            dt_obj = datetime.datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
            dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)
            unix_timestamp = int(dt_obj.timestamp())
            
            # ==========================================
            # 4. LOCAL ASSET LOADING
            # ==========================================
            # HOME art, falling through to the official artwork - the same chain the
            # battle scene, the box browser and the wild encounter use. This was the
            # last hand-built sprite path in the bot: it pinned official-artwork, so a
            # listing showed a different picture of the same specimen than the one the
            # seller had been looking at in `!view`, and it had never heard of a female
            # sprite either.
            safe_filename = sprite_attachment_name(p_id, is_shiny, gender)
            file_path = resolve_sprite(p_id, shiny=is_shiny, gender=gender, style=HOME)

            # Fallback Check: If the image is somehow missing from your folder, don't crash the bot!
            if not file_path:
                # Twelve species genuinely have no art anywhere. Say so rather than
                # attaching a broken image.
                print(f"⚠️ WARNING: no sprite anywhere for ID {p_id}")
                sprite_file = None
            else:
                # Package the image as a discord File object
                sprite_file = discord.File(file_path, filename=safe_filename)
                
            # ==========================================
            # 5. Build the UI
            shiny_icon = "🌟" if is_shiny else "🌿"
            # Was a lone 🌀 with no mention of size at all, so a listing could not tell
            # you it was an Alpha - the one trait a buyer most wants to know and cannot
            # infer from the stat block. Same badges the box browser draws.
            gmax_marker = trait_badges(gmax=gmax_factor, height_multiplier=h_mult)
            
            embed = discord.Embed(title=f"📋 Market Assay: Listing #{listing_id}", color=discord.Color.teal())
            
            # Seller & Price Info
            embed.add_field(name="Seller ID", value=f"`{seller_id}`", inline=True)
            embed.add_field(name="Procurement Cost", value=f"🪙 **{price:,}** Tokens", inline=True)
            embed.add_field(name="Time Remaining", value=f"<t:{unix_timestamp}:R>", inline=True)
            
            # Biological Specs
            embed.add_field(
                name=f"Biological Profile", 
                value=f"**Species:** {shiny_icon} {name.capitalize()}{gmax_marker}\n**Type:** {species_badges(name)}\n**Level:** {level}\n**Nature:** {nature.capitalize()}\n**Ability:** {ability.replace('-', ' ').title() if ability else 'Unknown'}",
                inline=False
            )
            
            # Genetic Assay (IVs formatted neatly in a code block)
            iv_block = f"""```text
HP:  {iv_hp:<2} | SpA: {iv_spa:<2}
Atk: {iv_atk:<2} | SpD: {iv_spd:<2}
Def: {iv_def:<2} | Spe: {iv_spe:<2}
```"""
            embed.add_field(name=f"🧬 Genetic Potential ({iv_percentage}%)", value=iv_block, inline=False)
            
            # Mount the local image to the embed
            if sprite_file:
                embed.set_image(url=f"attachment://{safe_filename}")
                
            embed.set_footer(text=f"Use !global market buy {listing_id} to authorize this transfer.")
            
            # Send the message, passing BOTH the embed and the file object!
            if sprite_file:
                await ctx.send(embed=embed, file=sprite_file)
            else:
                await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Global Market Inspect Error: {e}")
            await ctx.send("A database error occurred while running the genetic assay.")
    
    @global_market.command(name="buy", aliases=["procure", "purchase"])
    @checks.is_not_in_combat()
    @checks.has_started()
    @checks.is_not_in_trade()
    @checks.is_authorized()
    async def global_market_buy(self, ctx, listing_id: int):
        """Procures a specimen from the global market."""
        buyer_id = str(ctx.author.id)

        try:
            # 🚨 AIOSQLITE UPDATE: Open the connection
            async with aiosqlite.connect(DB_FILE) as db:
                
                # 1. Fetch and Verify the Listing
                async with db.execute("""
                    SELECT seller_id, instance_id, price 
                    FROM global_market 
                    WHERE listing_id = ? AND expires_at >= CURRENT_TIMESTAMP
                """, (listing_id,)) as cursor:
                    listing = await cursor.fetchone()
                
                if not listing:
                    return await ctx.send(f"❌ Listing `#{listing_id}` does not exist or has expired.")
                    
                seller_id, instance_id, price = listing
                
                if buyer_id == seller_id:
                    return await ctx.send("⚠️ You cannot procure your own asset!")
                    
                # 2. Check the Buyer's Funding
                async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (buyer_id,)) as cursor:
                    buyer_data = await cursor.fetchone()
                    
                buyer_balance = buyer_data[0] if buyer_data else 0
                
                if buyer_balance < price:
                    return await ctx.send(f"🪙 Grant denied. You need **{price:,}** Eco-Tokens to procure this asset (Current Balance: {buyer_balance:,}).")
                    
                # ==========================================
                # 3. EXECUTE THE ATOMIC TRANSACTION
                # ==========================================
                # Explicitly start the transaction!
                await db.execute("BEGIN TRANSACTION")
                
                try:
                    # A. Deduct funds from the buyer
                    await db.execute("UPDATE users SET eco_tokens = eco_tokens - ? WHERE user_id = ?", (price, buyer_id))
                    
                    # B. Transfer funds to the seller (Using UPSERT in case they don't have a wallet yet)
                    await db.execute("""
                        INSERT INTO users (user_id, eco_tokens) 
                        VALUES (?, ?) 
                        ON CONFLICT(user_id) DO UPDATE SET eco_tokens = eco_tokens + ?
                    """, (seller_id, price, price))
                    
                    # C. Reassign biological ownership, snapshotting it first.
                    sold = await snapshot(db, [instance_id])
                    await db.execute("UPDATE caught_pokemon SET user_id = ? WHERE instance_id = ?", (buyer_id, instance_id))
                    await bump_to_end_of_box(db, instance_id)

                    # D. Destroy the market listing
                    await db.execute("DELETE FROM global_market WHERE listing_id = ?", (listing_id,))

                    # The buyer's side is tokens rather than specimens, which is why
                    # the ledger records a `detail` as well as two lists.
                    await log_trade(db, trade_type='market', user_a=seller_id,
                                    user_b=buyer_id, side_a=sold, side_b=[],
                                    guild_id=getattr(ctx.guild, 'id', None),
                                    detail=f"Sold for {price:,} tokens (listing {listing_id})")
                    
                    # E. Fetch species name for the receipt
                    async with db.execute("""
                        SELECT s.name FROM caught_pokemon cp 
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id 
                        WHERE cp.instance_id = ?
                    """, (instance_id,)) as cursor:
                        species_name = (await cursor.fetchone())[0]
                    
                    # COMMIT locks in all 5 steps permanently!
                    await db.commit()
                    
                except Exception as inner_e:
                    # CRITICAL SAFETY NET: Undo the entire transaction if it crashed midway!
                    if db.in_transaction:
                        await db.rollback() 
                    # Raise the error up to the outer try/except block so it triggers the Discord failure message
                    raise inner_e 

            # 4. Generate the Transaction Receipt (Safely outside the DB block)
            embed = discord.Embed(title="🤝 Procurement Successful!", color=discord.Color.green())
            embed.description = f"**{ctx.author.name}** successfully secured the **{species_name.capitalize()}**!"
            embed.add_field(name="Conservation Grant Paid", value=f"🪙 {price:,} Tokens", inline=True)
            embed.add_field(name="Remaining Balance", value=f"🪙 {buyer_balance - price:,} Tokens", inline=True)
            embed.set_footer(text=f"Tag ID: {instance_id[:8]} | Seller ID: {seller_id}")

            await ctx.send(embed=embed)

            await announce_trade(self.bot, trade_type='market', user_a=seller_id,
                                 user_b=ctx.author, side_a=sold, side_b=[],
                                 detail=f"Sold for 🪙 {price:,} tokens")

        except Exception as e:
            print(f"Global Market Buy Error: {e}")
            await ctx.send("❌ A critical database error occurred. The transaction has been securely aborted and no tokens were lost.")
            

    @global_market.command(name="cancel", aliases=["remove", "delist", "retrieve"])
    async def global_market_cancel(self, ctx, listing_id: int):
        """Removes your own specimen from the global market."""
        user_id = str(ctx.author.id)
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:

                # 1. Security Check: Verify existence and ownership
                async with db.execute("""
                    SELECT seller_id, instance_id 
                    FROM global_market 
                    WHERE listing_id = ?
                """, (listing_id,)) as cursor:
                    listing = await cursor.fetchone()
                
                if not listing:
                    return await ctx.send(f"❌ Listing `#{listing_id}` does not exist. It may have already expired or been purchased.")
                    
                seller_id, instance_id = listing
                
                if seller_id != user_id:
                    return await ctx.send("⚠️ Security Alert: You can only delist your own ecological assets!")
                    
                # 2. Fetch the species name for the UI before we delete the record
                async with db.execute("""
                    SELECT s.name 
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                    WHERE cp.instance_id = ?
                """, (instance_id,)) as cursor:
                    species_data = await cursor.fetchone()
                species_name = species_data[0] if species_data else "Unknown Specimen"

                # 3. Destroy the Escrow Record
                await db.execute("DELETE FROM global_market WHERE listing_id = ?", (listing_id,))
                await db.commit()
            
            # 4. Confirmation UI
            embed = discord.Embed(title="📥 Asset Retrieved", color=discord.Color.dark_gray())
            embed.description = f"**{ctx.author.name}** has safely recalled their **{species_name.capitalize()}** from the open market."
            embed.set_footer(text="The specimen is now available for field deployment.")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Global Market Cancel Error: {e}")
            await ctx.send("A database error occurred while trying to retrieve your asset.")

    @commands.command(name="equip")
    @checks.has_started()
    @checks.is_not_in_combat()
    @checks.is_authorized()
    async def equip_item(self, ctx, *, request: str = None):
        """Attaches gear. `!equip leftovers` uses your selected partner."""
        user_id = str(ctx.author.id)

        if not request or not request.split():
            return await ctx.send(
                "⚠️ Usage: `!equip <item>` for your selected partner, or "
                "`!equip <box number|tag> <item>` for any specimen.")

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                target, formatted_item = await split_equip_request(db, user_id, request)

                # 1. START ATOMIC TRANSACTION
                await db.execute("BEGIN TRANSACTION")

                try:
                    # 2. Which specimen - the selected partner unless one is named.
                    specimen, problem = await locate_specimen(
                        db, user_id, target,
                        "cp.instance_id, s.name, cp.held_item")
                    if problem:
                        await db.rollback()
                        return await ctx.send(problem)

                    full_instance_id, raw_specimen_name, current_held_item = specimen
                    specimen_name = raw_specimen_name.capitalize()

                    # 3. UNEQUIP LOGIC (If they type "!equip [ID] none")
                    if formatted_item in ["none", "unequip"]:
                        if current_held_item == "none" or not current_held_item:
                            await db.rollback()
                            return await ctx.send(f"⚠️ **{specimen_name}** is not currently holding any equipment.")

                        await db.execute("""
                            INSERT INTO user_inventory (user_id, item_name, quantity)
                            VALUES (?, ?, 1)
                            ON CONFLICT(user_id, item_name)
                            DO UPDATE SET quantity = quantity + 1
                        """, (user_id, current_held_item))

                        await db.execute("UPDATE caught_pokemon SET held_item = 'none' WHERE instance_id = ?", (full_instance_id,))
                        await db.commit()

                        return await ctx.send(f"🎒 You detached the `{current_held_item.replace('-', ' ').title()}` from **{specimen_name}** and returned it to your pack.")

                    # 4. Verify Inventory Ownership for the New Item
                    async with db.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, formatted_item)) as cursor:
                        inv_data = await cursor.fetchone()

                    if not inv_data or inv_data[0] < 1:
                        await db.rollback()
                        return await ctx.send(f"⚠️ **Logistics Error:** You do not have any `{formatted_item.replace('-', ' ').title()}` in your field backpack.")

                    # 5. EXECUTE THE ATOMIC SWAP
                    await db.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, formatted_item))

                    if current_held_item and current_held_item != 'none':
                        await db.execute("""
                            INSERT INTO user_inventory (user_id, item_name, quantity)
                            VALUES (?, ?, 1)
                            ON CONFLICT(user_id, item_name)
                            DO UPDATE SET quantity = quantity + 1
                        """, (user_id, current_held_item))
                        swap_msg = f"\n*The previously held `{current_held_item.replace('-', ' ').title()}` was returned to your pack.*"
                    else:
                        swap_msg = ""

                    await db.execute("UPDATE caught_pokemon SET held_item = ? WHERE instance_id = ?", (formatted_item, full_instance_id))
                    await db.commit()

                except Exception as inner_e:
                    # 🚨 CRITICAL RECOVERY: Catch inner transaction failures
                    if db.in_transaction:
                        await db.rollback()
                    raise inner_e # Push the error to the outer block to send the Discord message

            # 6. RENDER THE UI
            embed = discord.Embed(title="🎒 Tactical Equipment Assigned", color=discord.Color.green())
            embed.description = f"**{ctx.author.name}** equipped `{formatted_item.replace('-', ' ').title()}` to **{specimen_name}**!{swap_msg}"
            embed.set_footer(text=f"Tag ID: {full_instance_id[:8]}")

            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Equip Error: {e}")
            await ctx.send("❌ A database error occurred while assigning the equipment. No items were lost.")

    @commands.command(name="unequip", aliases=["remove_item", "detach"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_combat()
    @checks.is_not_in_trade()
    async def unequip_item(self, ctx, instance_id: str = None):
        """Takes gear back. With no target it uses your selected partner."""
        user_id = str(ctx.author.id)

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # 1. Which specimen - the selected partner unless one is named.
                specimen, problem = await locate_specimen(
                    db, user_id, instance_id,
                    "cp.instance_id, s.name, cp.held_item")
                if problem:
                    return await ctx.send(problem)

                full_instance_id, raw_name, held_item = specimen
                specimen_name = raw_name.capitalize()

                # 2. CHECK IF IT ACTUALLY HAS AN ITEM
                if not held_item or held_item == 'none':
                    return await ctx.send(f"⚠️ **{specimen_name}** is not currently equipped with any tactical gear.")

                # 3. ATOMIC TRANSACTION
                await db.execute("BEGIN TRANSACTION")
                try:
                    # A. Push the item safely back into the user's inventory
                    await db.execute("""
                        INSERT INTO user_inventory (user_id, item_name, quantity)
                        VALUES (?, ?, 1)
                        ON CONFLICT(user_id, item_name)
                        DO UPDATE SET quantity = quantity + 1
                    """, (user_id, held_item))

                    # B. Wipe the held item slot on the specimen
                    await db.execute("UPDATE caught_pokemon SET held_item = 'none' WHERE instance_id = ?", (full_instance_id,))

                    await db.commit()

                except Exception as inner_e:
                    # 🚨 CRITICAL RECOVERY
                    if db.in_transaction:
                        await db.rollback()
                    raise inner_e

            # 4. UI OUTPUT
            embed = discord.Embed(title="🎒 Equipment Recovered", color=discord.Color.green())
            embed.description = f"**{ctx.author.name}** safely detached the `{held_item.replace('-', ' ').title()}` from **{specimen_name}** and stowed it in the field backpack."
            embed.set_footer(text=f"Tag ID: {full_instance_id[:8]}")

            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Unequip Error: {e}")
            await ctx.send("❌ A critical database error occurred while recovering the equipment. No items were lost.")

    @commands.command(name="market", aliases=["shop"])
    @checks.has_started()
    @checks.is_authorized()
    async def view_market(self, ctx):
        """Displays available field equipment for purchase."""
        view = MarketView(SHOP_CATALOG)
        embed = view.generate_embed()
        await ctx.send(embed=embed, view=view)

    @commands.command(name="tmshop", aliases=["tms"])
    @checks.has_started()
    @checks.is_authorized()
    async def tm_shop(self, ctx, *, request: str = None):
        """
        The TM shelf. `!tmshop <move>`, `!tmshop list <specimen>`, `!tmshop type:water`.

        A 340-item catalogue cannot be browsed and should not pretend otherwise, so
        every spelling of this command is a way of NARROWING it. The single most useful
        one is `!tmshop list <specimen>`: nobody knows off the top of their head that
        Rotom-Wash learns Will-O-Wisp, and forty options is a decision where 340 is a
        wall.
        """
        user_id = str(ctx.author.id)
        tokens = (request or "").split()

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                owned = await owned_tms(db, user_id)

                # ---------------------------------------------- nothing typed
                if not tokens:
                    embed = discord.Embed(
                        title="💿 Technical Machine Archive",
                        description=(
                            f"**{len(TM_CATALOG)}** machines are in stock, and every one "
                            f"of them is permanent — bought once, usable forever, on "
                            f"every specimen that can learn it.\n\n"
                            f"You own **{len(owned)}**."),
                        color=discord.Color.teal())
                    embed.add_field(
                        name="Finding one",
                        value=("`!tmshop stealth rock` — look up a single machine\n"
                               "`!tmshop list` — your partner's learnable TMs\n"
                               "`!tmshop list 4` — box #4's, or name a tag\n"
                               "`!tmshop type:water` · `!tmshop class:status`"),
                        inline=False)
                    embed.add_field(
                        name="What they cost",
                        value=(f"🪙 **{TM_TIER_PRICES['basic']:,}** utility · "
                               f"🪙 **{TM_TIER_PRICES['standard']:,}** coverage · "
                               f"🪙 **{TM_TIER_PRICES['premium']:,}** premium\n"
                               f"Buy with `!buy <move>`. Teach with `!learn <move>`."),
                        inline=False)
                    return await ctx.send(embed=embed)

                # ---------------------------------------------- type:/class: filters
                element = damage_class = None
                leftover = []
                for token in tokens:
                    key, _, value = token.partition(':')
                    if value and key.lower() in ('type', 'element'):
                        element = value
                    elif value and key.lower() in ('class', 'category', 'kind'):
                        damage_class = value
                    else:
                        leftover.append(token)

                if element or damage_class:
                    hits = filter_tms(element, damage_class)
                    if not hits:
                        return await ctx.send(
                            f"❌ No TMs match that filter. Types are the eighteen "
                            f"elemental ones; categories are `physical`, `special` and "
                            f"`status`.")
                    described = " ".join(filter(None, [
                        (element or '').title(), (damage_class or '').lower()]))
                    view = TMShelfView(ctx, hits, owned,
                                       f"💿 TM Archive — {described}")
                    return await ctx.send(embed=view.generate_embed(), view=view)

                # ---------------------------------------------- list [specimen]
                if leftover and leftover[0].lower() in ('list', 'all', 'learnable'):
                    target = " ".join(leftover[1:]) or None

                    if target and target.lower() in ('all', 'everything'):
                        view = TMShelfView(ctx, sorted(TM_CATALOG), owned,
                                           "💿 TM Archive — everything in stock")
                        return await ctx.send(embed=view.generate_embed(), view=view)

                    pokemon, problem = await locate_specimen(
                        db, user_id, target, "cp.pokedex_id, s.name, cp.level")
                    if problem:
                        return await ctx.send(problem)

                    poke_id, species, level = pokemon
                    hits = await species_tms(db, poke_id)
                    if not hits:
                        return await ctx.send(
                            f"📭 **{species.capitalize()}** cannot learn anything from a "
                            f"TM. Try `!moveset` for what it grows into instead.")

                    view = TMShelfView(
                        ctx, hits, owned,
                        f"💿 TMs for {species.capitalize()}",
                        note=f"Everything a Lv. {level} {species.capitalize()} can be "
                             f"taught from a machine.")
                    return await ctx.send(embed=view.generate_embed(), view=view)

                # ---------------------------------------------- one machine
                typed = " ".join(leftover)
                move = find_tm(typed)
                if not move:
                    near = search_tms(typed)[:8]
                    if near:
                        listed = ", ".join(f"`{m.replace('-', ' ').title()}`"
                                           for m in near)
                        return await ctx.send(
                            f"🔎 No single match for `{typed}`. Did you mean: {listed}?")
                    return await ctx.send(
                        f"❌ No TM called `{typed}`. Machines only exist for moves some "
                        f"species learns by machine — `!moveset` shows which those are "
                        f"for a given specimen.")

                data = TM_CATALOG[move]
                pretty = move.replace('-', ' ').title()
                has = move in owned

                embed = discord.Embed(
                    title=f"{data['emoji']} TM {pretty}",
                    description=data['desc'].replace(" Apply it with `!tm`.", ""),
                    color=discord.Color.green() if has else discord.Color.teal())
                embed.add_field(name="Price",
                                value=("✅ Already owned" if has
                                       else f"🪙 {data['price']:,}"), inline=True)
                embed.add_field(name="Category",
                                value=(data.get('class') or 'status').title(),
                                inline=True)
                embed.add_field(name="Type",
                                value=type_badges([data.get('type') or 'normal']),
                                inline=True)

                # Which of THEIR specimens can take it. A price is not the useful half
                # of a shop listing when the question is "is this any use to me".
                async with db.execute("""
                    SELECT DISTINCT s.name
                    FROM caught_pokemon cp
                    JOIN base_pokemon_species s ON s.pokedex_id = cp.pokedex_id
                    JOIN species_movepool sm ON sm.pokedex_id = cp.pokedex_id
                    WHERE cp.user_id = ? AND sm.move_name = ?
                      AND sm.learn_method = 'machine'
                    ORDER BY s.name
                """, (user_id, move)) as cursor:
                    eligible = [row[0] for row in await cursor.fetchall()]

                if eligible:
                    shown = ", ".join(n.replace('-', ' ').title()
                                      for n in eligible[:20])
                    more = f" *(+{len(eligible) - 20} more)*" if len(eligible) > 20 else ""
                    embed.add_field(name=f"Your specimens that can learn it ({len(eligible)})",
                                    value=f"{shown}{more}"[:1024], inline=False)
                else:
                    embed.add_field(
                        name="Your specimens that can learn it",
                        value="*None of them, yet.*", inline=False)

                embed.set_footer(
                    text=(f"Teach it with !learn {move}" if has
                          else f"Buy it with !buy {move}"))
                return await ctx.send(embed=embed)

        except Exception as e:
            print(f"TM shop error: {e}")
            await ctx.send("❌ A database error occurred while reading the TM archive.")

    @commands.command(name="sell")
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_trade()
    async def exchange_item(self, ctx, quantity: int, *, item_name: str):
        """Exchange valuable materials or surplus items for Eco-Tokens."""
        if quantity < 1:
            return await ctx.send("⚠️ You must exchange at least one item.")

        user_id = str(ctx.author.id)
        
        # 1. Strip all non-alphanumeric characters for a foolproof search
        search_term = ''.join(e for e in item_name.lower() if e.isalnum())

        db_item_name = None
        exchange_value = 0
        item_display_name = None
        emoji = '📦'

        # 2. Identify the item in the catalog
        for cat_key, cat_data in EQUIPMENT_CATALOG.items():
            if ''.join(e for e in cat_key.lower() if e.isalnum()) == search_term:
                db_item_name = cat_key
                
                # Check for a specific 'sell_price', otherwise default to 50% of the buy price
                exchange_value = cat_data.get('sell_price', cat_data.get('price', 0) // 2)
                item_display_name = cat_data['name']
                emoji = cat_data.get('emoji', '📦')
                break

        if not db_item_name:
            return await ctx.send("❌ That item does not exist in the database.")

        if exchange_value <= 0:
            return await ctx.send(f"⚠️ **{item_display_name}** has no exchange value on the market.")

        total_payout = exchange_value * quantity

        try:
            # 🚨 AIOSQLITE UPDATE: Safely handle the connection
            async with aiosqlite.connect(DB_FILE) as db:
                await db.execute("BEGIN TRANSACTION")

                try:
                    # 3. Check User Inventory
                    async with db.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, db_item_name)) as cursor:
                        inv_data = await cursor.fetchone()

                    current_qty = inv_data[0] if inv_data else 0

                    if current_qty < quantity:
                        await db.rollback()
                        return await ctx.send(f"⚠️ Insufficient materials! You only have **{current_qty}x {item_display_name}**.")

                    # 4. Deduct the item(s) from inventory
                    await db.execute("""
                        UPDATE user_inventory SET quantity = quantity - ? 
                        WHERE user_id = ? AND item_name = ?
                    """, (quantity, user_id, db_item_name))
                    
                    # Keep the database clean by wiping zero-quantity rows
                    await db.execute("DELETE FROM user_inventory WHERE quantity <= 0")

                    # 5. Add the Eco-Tokens
                    await db.execute("""
                        UPDATE users SET eco_tokens = eco_tokens + ? 
                        WHERE user_id = ?
                    """, (total_payout, user_id))

                    # Fetch the newly updated balance for the receipt
                    async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (user_id,)) as cursor:
                        new_balance_data = await cursor.fetchone()
                    new_balance = new_balance_data[0]

                    # 6. Lock the transaction
                    await db.commit()

                except Exception as inner_e:
                    if db.in_transaction:
                        await db.rollback()
                    raise inner_e 

            # 7. Render UI Output
            embed = discord.Embed(title="♻️ Material Exchange Successful", color=discord.Color.green())
            embed.description = f"Exchanged **{quantity}x {item_display_name}** {emoji} for **{total_payout:,}** Eco-Tokens.\nNew Balance: **{new_balance:,}**"
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Transaction Error in !exchange: {e}")
            await ctx.send("❌ A critical database error occurred. The exchange has been aborted and your inventory is safe.")

    @commands.command(name="buy", aliases=["purchase"])
    @checks.has_started()
    @checks.is_authorized()
    @checks.is_not_in_trade()
    @checks.is_not_in_combat()
    async def buy_item(self, ctx, *, request: str = None):
        """Securely purchases items using an atomic database transaction."""
        user_id = str(ctx.author.id)

        # The quantity used to be a required first argument, which made `!buy protect`
        # a parse error rather than a purchase. It reads as optional now - a leading
        # number is a count, anything else is the start of the name - because the shop
        # is mostly TMs, and you never want more than one of those.
        tokens = (request or "").split()
        if not tokens:
            return await ctx.send("⚠️ Usage: `!buy <item>` or `!buy <quantity> <item>`.")

        if len(tokens) > 1 and tokens[0].isdigit():
            quantity, item_name = int(tokens[0]), " ".join(tokens[1:])
        else:
            quantity, item_name = 1, " ".join(tokens)

        if quantity < 1:
            return await ctx.send("⚠️ You must purchase at least one item.")

        # Strip all non-alphanumeric characters for a foolproof search (e.g. "Rare Candy" -> "rarecandy")
        search_term = ''.join(e for e in item_name.lower() if e.isalnum())
        
        is_tm = False
        db_item_name = None
        unit_cost = None
        item_display_name = None
        emoji = '📦'

        # ==========================================
        # THE SMART ROUTER
        # ==========================================
        
        # 1. PRIORITY: Check the Daily Shop for discounts or exclusive items
        daily_shop = self.get_daily_shop()
        for daily_item in daily_shop:
            if ''.join(e for e in daily_item['name'].lower() if e.isalnum()) == search_term:
                db_item_name = daily_item['name']
                unit_cost = daily_item['price']
                
                # Grab the rich metadata from the catalog if it exists
                cat_data = EQUIPMENT_CATALOG.get(db_item_name, {})
                item_display_name = cat_data.get('name', db_item_name.replace('-', ' ').title())
                emoji = cat_data.get('emoji', '📦')
                break

        # 2. Check the General Catalog if it wasn't in today's supply drop
        if not db_item_name:
            for cat_key, cat_data in EQUIPMENT_CATALOG.items():
                if ''.join(e for e in cat_key.lower() if e.isalnum()) == search_term:
                    # Enforce the 'purchasable: False' rule for Key Items/Berries
                    if cat_data.get('purchasable', True) is False:
                        return await ctx.send("❌ That item cannot be purchased directly from the standard market.")
                    
                    db_item_name = cat_key
                    unit_cost = cat_data['price']
                    item_display_name = cat_data['name']
                    emoji = cat_data.get('emoji', '📦')
                    break

        # 3. Check the TM Shop. `find_tm` rather than an exact key, so `!buy stealth
        #    rock`, `!buy stealthrock` and `!buy TM Stealth Rock` all land - a shelf of
        #    340 is not a shelf anybody spells perfectly.
        if not db_item_name:
            formatted_tm = find_tm(item_name)
            if formatted_tm:
                db_item_name = formatted_tm
                unit_cost = TM_SHOP[formatted_tm]
                item_display_name = f"TM {formatted_tm.replace('-', ' ').title()}"
                emoji = '💿'
                is_tm = True
                # A TM is permanent, so a second one is a purchase that buys nothing.
                # Silently charging for it would be the worst of the three options.
                quantity = 1

        if not db_item_name:
            near = search_tms(item_name)[:5]
            if near:
                suggestions = ", ".join(f"`{m.replace('-', ' ').title()}`" for m in near)
                return await ctx.send(
                    f"❌ No item or TM by that name. Did you mean: {suggestions}?")
            return await ctx.send("❌ That item or TM is not available in the supply market.")
            
        # ==========================================

        total_cost = unit_cost * quantity

        try:
            # 🚨 AIOSQLITE UPDATE: Safely handle the connection
            async with aiosqlite.connect(DB_FILE) as db:
                # 1. START ATOMIC TRANSACTION
                await db.execute("BEGIN TRANSACTION")

                # Nested try-block so we can catch mid-transaction errors and rollback!
                try:
                    # A TM already owned is not sold again. Checked INSIDE the
                    # transaction, before the tokens move, so two `!buy`s racing each
                    # other cannot both pay for the same permanent item.
                    if is_tm and await owns_tm(db, user_id, db_item_name):
                        await db.rollback()
                        return await ctx.send(
                            f"💿 You already own **{item_display_name}** — TMs are "
                            f"permanent and never run out. Teach it with "
                            f"`!learn {db_item_name}`.")

                    # 2. Check User Funds
                    async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?", (user_id,)) as cursor:
                        user_data = await cursor.fetchone()

                    # If the user doesn't exist in the DB yet, treat their balance as 0
                    current_balance = user_data[0] if user_data else 0

                    if current_balance < total_cost:
                        # We must rollback before returning!
                        await db.rollback()
                        return await ctx.send(f"⚠️ Insufficient funds! You need **{total_cost:,}** Eco-Tokens, but you only have **{current_balance:,}**.")

                    # 3. Deduct Funds
                    await db.execute("UPDATE users SET eco_tokens = eco_tokens - ? WHERE user_id = ?", (total_cost, user_id))

                    # ==========================================
                    # 4. DYNAMIC INVENTORY ROUTING
                    # ==========================================
                    if is_tm:
                        # Route to the TM Ledger. One row, not a running total - the
                        # count stopped meaning anything the moment TMs became
                        # permanent, and a growing number would only invite somebody to
                        # read it as a balance again.
                        await grant_tm(db, user_id, db_item_name)
                    else:
                        # Route to the Standard Backpack Ledger!
                        await db.execute("""
                            INSERT INTO user_inventory (user_id, item_name, quantity) 
                            VALUES (?, ?, ?) 
                            ON CONFLICT(user_id, item_name) 
                            DO UPDATE SET quantity = quantity + ?
                        """, (user_id, db_item_name, quantity, quantity))
                        print("DEBUG: Item Purchase executed successfully.")
                    # ==========================================

                    # 5. COMMIT TRANSACTION (Lock the changes in permanently)
                    await db.commit()

                except Exception as inner_e:
                    # 6. ROLLBACK ON ERROR (If the database crashes, refund the money automatically)
                    if db.in_transaction:
                        await db.rollback()
                    raise inner_e # Push the error out to the main handler

            # 7. Render UI (safely outside the DB block)
            embed = discord.Embed(title="✅ Requisition Successful!", color=discord.Color.blue())
            embed.description = f"Purchased **{quantity}x {item_display_name}** {emoji} for **{total_cost:,}** Eco-Tokens.\nNew Balance: **{current_balance - total_cost:,}**"
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Transaction Error in !buy: {e}")
            await ctx.send("❌ A critical database error occurred. The transaction has been aborted and no funds were deducted.")

    @commands.command(name="backpack", aliases=["gear", "items", "bag"])
    @checks.has_started()
    @checks.is_authorized()
    async def backpack(self, ctx):
        user_id = str(ctx.author.id)
        
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute("SELECT item_name, quantity FROM user_inventory WHERE user_id = ? AND quantity > 0", (user_id,)) as cursor:
                    inventory = await cursor.fetchall()

            if not inventory:
                return await ctx.send("🎒 Your field backpack is completely empty! Visit the `!market` to stock up on gear.")
                
            view = BackpackPaginator(ctx.author, inventory, EQUIPMENT_CATALOG)
            initial_embed = view.generate_embed()
            await ctx.send(embed=initial_embed, view=view)
            
        except Exception as e:
            print(f"Backpack Query Error: {e}")
            await ctx.send("❌ An error occurred while retrieving your inventory data.")
            
async def setup(bot):
    await bot.add_cog(Economy(bot))