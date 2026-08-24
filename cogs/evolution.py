import discord
from discord.ext import commands
from utils.prefs import trainer_skies
from utils.db_manager import stone_evolution, ritual_routes
from utils.regions import current_region
from utils.constants import (DB_FILE, current_skies, RITUAL_TRIGGERS,
                             RITUAL_MIN_LEVEL, RITUAL_KEYWORD,
                             choose_ritual, describe_ritual_choices,
                             requested_ritual, ritual_word)
from utils import checks
from utils.directives import credit_evolution
import aiosqlite

class Evolution(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="evolve", aliases=["mutate", "adapt"])
    @checks.is_authorized()
    @checks.has_started()
    async def manual_evolve(self, ctx, target: str, *, item_name: str):
        user_id = str(ctx.author.id)
        
        # Format the item name to match PokeAPI standards (e.g., "Water Stone" -> "water-stone")
        formatted_item = item_name.lower().replace(" ", "-")

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                # 1. Determine the Target Specimen (Partner, Box Number, or Tag)
                if target.lower() in ["partner", "lead", "active", "latest"]:
                    async with db.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,)) as cursor:
                        partner_data = await cursor.fetchone()
                    
                    if not partner_data or not partner_data[0]:
                        return await ctx.send("⚠️ You don't have an Active Partner equipped! Specify a Box Number or Tag ID instead.")
                    
                    actual_tag = partner_data[0]
                    
                    # Fetch directly by the partner's UUID
                    # 🚨 ADDED: cp.ability, s.standard_abilities, s.hidden_ability
                    async with db.execute("""
                        SELECT cp.instance_id, cp.pokedex_id, s.name, cp.ability, s.standard_abilities, s.hidden_ability
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.instance_id = ? AND cp.user_id = ?
                    """, (actual_tag, user_id)) as cursor:
                        pokemon_data = await cursor.fetchone()

                elif target.isdigit() and len(target) <= 6:
                    async with db.execute("""
                        WITH Roster AS (
                            SELECT cp.instance_id, cp.pokedex_id, s.name, cp.ability, s.standard_abilities, s.hidden_ability,
                                ROW_NUMBER() OVER(ORDER BY cp.rowid ASC) as box_number
                            FROM caught_pokemon cp
                            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                            WHERE cp.user_id = ?
                            AND cp.instance_id NOT IN (SELECT instance_id FROM active_deployments)
                            AND cp.instance_id NOT IN (SELECT instance_id FROM gts_deposits)
                        )
                        SELECT instance_id, pokedex_id, name, ability, standard_abilities, hidden_ability
                        FROM Roster WHERE box_number = ?
                    """, (user_id, int(target))) as cursor:
                        pokemon_data = await cursor.fetchone()
                        
                else:
                    actual_tag = f"{target}%"
                    async with db.execute("""
                        SELECT cp.instance_id, cp.pokedex_id, s.name, cp.ability, s.standard_abilities, s.hidden_ability
                        FROM caught_pokemon cp
                        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
                        WHERE cp.instance_id LIKE ? AND cp.user_id = ?
                    """, (actual_tag, user_id)) as cursor:
                        pokemon_data = await cursor.fetchone()
                
                if not pokemon_data:
                    return await ctx.send("❌ Could not locate that specimen in your survey notebook. Check your Box Number or Tag ID.")
                    
                db_tag_id, current_pokedex_id, current_name, current_ability, pre_std_abs_raw, pre_hidden_ab = pokemon_data
                
                # 3. Check the Metamorphosis Rulebook
                # 🚨 ADDED: s.standard_abilities, s.hidden_ability to the evolution target!
                # THE REGION DECIDES WHICH FORM A STONE PRODUCES, and until now nothing
                # decided it at all - this was a bare `fetchone()` with no ORDER BY, so
                # Alolan Raichu, Alolan Exeggutor and Hisuian Lilligant were unreachable
                # by whatever order SQLite happened to return rows in.
                #
                # `stone_evolution` lives in utils/db_manager.py beside the level-up
                # rulebook, so both halves of "what does this evolve into" are asked in
                # one place and a test can drive the real query rather than a copy.
                evo_data = await stone_evolution(
                    db, current_pokedex_id, formatted_item,
                    region=await current_region(db, user_id))

                # THE HELD-ITEM ROUTE. A Razor Claw is not a stone: in the games the
                # specimen levels up while HOLDING it, and the item survives. So this
                # branch asks a different question from the one above - not "do you own
                # one" but "is this specimen wearing one" - and spends nothing.
                #
                # Only reached when there is no use-item rule, so a stone keeps its own
                # behaviour untouched and the two routes can never both fire.
                held_route = None
                if not evo_data:
                    async with db.execute("""
                        SELECT er.evolved_species_id, s.name, s.standard_abilities,
                               s.hidden_ability, er.time_of_day
                        FROM evolution_rules er
                        JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
                        WHERE er.base_species_id = ?
                        AND er.trigger_name = 'level-up'
                        AND er.held_item = ?
                    """, (current_pokedex_id, formatted_item)) as cursor:
                        held_rules = await cursor.fetchall()

                    if held_rules:
                        async with db.execute(
                                "SELECT held_item FROM caught_pokemon WHERE instance_id = ?",
                                (db_tag_id,)) as cursor:
                            worn = await cursor.fetchone()
                        worn_item = (worn[0] if worn else '' or '').lower().replace(' ', '-')

                        if worn_item != formatted_item:
                            pretty = formatted_item.replace('-', ' ').title()
                            return await ctx.send(
                                f"🧬 **{current_name.capitalize()}** has to be HOLDING the "
                                f"{pretty} for this to work - owning one is not enough. "
                                f"Give it the {pretty} with `!give`, then try again.")

                        skies = await trainer_skies(
                            db, ctx.author.id,
                            ctx.guild.id if ctx.guild else None)
                        for rule in held_rules:
                            if not rule[4] or rule[4] in skies:
                                held_route = rule
                                break

                        if held_route is None:
                            wanted = sorted({r[4] for r in held_rules if r[4]})
                            return await ctx.send(
                                f"🌙 **{current_name.capitalize()}** will only change while "
                                f"holding that during the **{' or '.join(wanted)}**, and it "
                                f"is currently **{'/'.join(sorted(skies))}**. Come back later.")

                        evo_data = held_route[:4]

                # THE RITUAL ROUTE. A handful of evolutions are triggered by things this
                # world has no equivalent of at all - Legends Arceus' Strong Style, the
                # Isle of Armor's two Towers, Basculin's recoil swim upriver. Rather than
                # pretend to model them, a specimen whose only route is one of those can
                # be pushed through it by hand once it is experienced enough.
                #
                # The level is an admitted stand-in and is named in constants rather than
                # buried here, so it reads as the substitution it is.
                # `!evolve <specimen> ritual` may carry a word saying WHICH rite, which is
                # what Kubfu needs - the Tower of Darkness and the Tower of Waters make
                # two different Urshifu, and this used to take row zero of an unordered
                # query, so only Single Strike was ever reachable.
                ritual = None
                asked_for_ritual = requested_ritual(formatted_item)
                if not evo_data and asked_for_ritual:
                    ritual_rules = await ritual_routes(db, current_pokedex_id)

                    if ritual_rules:
                        async with db.execute(
                                "SELECT level FROM caught_pokemon WHERE instance_id = ?",
                                (db_tag_id,)) as cursor:
                            lvl = await cursor.fetchone()
                        if (lvl[0] if lvl else 0) < RITUAL_MIN_LEVEL:
                            return await ctx.send(
                                f"🕯️ **{current_name.capitalize()}** is not seasoned "
                                f"enough for that. The rite asks for level "
                                f"**{RITUAL_MIN_LEVEL}**; it is level **{lvl[0] if lvl else 0}**.")

                        ritual, complaint = choose_ritual(ritual_rules,
                                                          ritual_word(formatted_item))
                        if ritual is None:
                            offered = "\n".join(
                                f"• {line}" for line in
                                describe_ritual_choices(ritual_rules))
                            preamble = (
                                f"🕯️ There is no rite called `{complaint}` for a "
                                f"**{current_name.capitalize()}**."
                                if complaint else
                                f"🕯️ **{current_name.capitalize()}** has more than one "
                                f"rite, and they do not lead to the same place.")
                            return await ctx.send(
                                f"{preamble}\n{offered}\n"
                                f"Say `!evolve {target} ritual <word>`.")
                        evo_data = ritual[:4]

                if not evo_data:
                    if asked_for_ritual:
                        return await ctx.send(
                            f"🕯️ There is no rite for a **{current_name.capitalize()}**. "
                            f"`!evolve <specimen> ritual` is only for the few whose real "
                            f"trigger this world cannot stage.")
                    return await ctx.send(f"⚠️ A **{formatted_item.replace('-', ' ').title()}** has no biological effect on a **{current_name.capitalize()}**.")

                new_pokedex_id, evolved_into_name, post_std_abs_raw, post_hidden_ab = evo_data
                
                # ==========================================
                # 🚨 ABILITY INHERITANCE ENGINE
                # ==========================================
                pre_std_abs = [a.strip() for a in (pre_std_abs_raw or "").split(',')]
                post_std_abs = [a.strip() for a in (post_std_abs_raw or "").split(',')]
                
                # Step 1: Determine the genetic slot of the current ability
                ability_slot = 0 # Default to Standard Slot 1
                if current_ability == pre_hidden_ab:
                    ability_slot = 'hidden'
                elif len(pre_std_abs) > 1 and current_ability == pre_std_abs[1]:
                    ability_slot = 1 # Standard Slot 2
                    
                # Step 2: Map the slot to the evolved form's genetics
                new_ability = 'pressure' # Failsafe fallback
                
                if ability_slot == 'hidden' and post_hidden_ab:
                    new_ability = post_hidden_ab
                elif ability_slot == 1 and len(post_std_abs) > 1:
                    new_ability = post_std_abs[1]
                elif post_std_abs:
                    new_ability = post_std_abs[0]
                # ==========================================
                
                # 4. Check Inventory - the STONE route only. A held item was already proved
                #    to be on the specimen a few lines up, and it is not in the pack to be
                #    found: a Razor Claw a Sneasel is wearing left the bag when it was given.
                if held_route is None and ritual is None:
                    async with db.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, formatted_item)) as cursor:
                        inv_data = await cursor.fetchone()

                    if not inv_data or inv_data[0] < 1:
                        return await ctx.send(f"🎒 You don't have a **{formatted_item.replace('-', ' ').title()}** in your field pack!")

                # 5. Execute the Metamorphosis safely
                await db.execute("BEGIN TRANSACTION")
                try:
                    # Deduct the item - the stone is used up, the held item is not. A Razor
                    # Claw stays on the Weavile that grew around it, which is both what the
                    # games do and the only answer that leaves the specimen's held_item
                    # column pointing at something it is still wearing.
                    if held_route is None and ritual is None:
                        await db.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, formatted_item))
                    
                    # 🚨 UPDATE THE SPECIMEN'S GENETICS AND ABILITY
                    await db.execute("UPDATE caught_pokemon SET pokedex_id = ?, ability = ? WHERE instance_id = ?", (new_pokedex_id, new_ability, db_tag_id))
                    
                    # DIRECTIVE TRACKER: KINETIC MATURATION (EVOLUTION)
                    # Shared with the two confirmation buttons, which are the other
                    # doors an evolution comes through - one of them used to have no
                    # tracker at all.
                    _, mutation_finished = await credit_evolution(
                        db, user_id, current_name)

                    await db.commit()
                except Exception as e:
                    await db.rollback() 
                    print(f"Evolution atomic error: {e}")
                    return await ctx.send("❌ A genetic sequencing error occurred during the evolution process. No items were lost.")
                
            # Outside the DB Context Manager: Build the UI
            embed = discord.Embed(title="🧬 Metamorphosis Complete!", color=discord.Color.gold())
            
            if ritual is not None:
                base_desc = f"**{ctx.author.name}** walked their **{current_name.capitalize()}** through the old rite...\n\nWhatever it met out there, it came back a **{evolved_into_name.capitalize()}**!"
            elif held_route is None:
                base_desc = f"**{ctx.author.name}** exposed their **{current_name.capitalize()}** to a {formatted_item.replace('-', ' ').title()}...\n\nIt rapidly adapted and evolved into a **{evolved_into_name.capitalize()}**!"
            else:
                base_desc = f"**{ctx.author.name}**'s **{current_name.capitalize()}**, still holding its {formatted_item.replace('-', ' ').title()}, shuddered and grew...\n\nIt evolved into a **{evolved_into_name.capitalize()}**!"
            
            # Add a note if their ability changed!
            if current_ability != new_ability:
                base_desc += f"\n\n✨ Through mutation, its ability changed from **{current_ability.replace('-', ' ').title()}** to **{new_ability.replace('-', ' ').title()}**!"
            
            if mutation_finished:
                base_desc += "\n\n📡 **Directive Complete:** Kinetic Maturation Study concluded! Run `!claim` to receive your funding."
                
            embed.description = base_desc
            # The stone is used up; a held item is retained; a rite costs nothing at all.
            if ritual is not None:
                spent = f"Rite of {ritual[4].replace('-', ' ').title()}"
            elif held_route is None:
                spent = "1x " + formatted_item.replace('-', ' ').title() + " Consumed"
            else:
                spent = formatted_item.replace('-', ' ').title() + " Retained"
            embed.set_footer(text=f"Tag ID: {db_tag_id[:8]} | {spent}")
            
            await ctx.send(embed=embed)

        except Exception as master_err:
            print(f"Critical command error in manual_evolve: {master_err}")
            import traceback
            traceback.print_exc()
            await ctx.send("⚠️ A critical system failure occurred while parsing biological data.")
            
async def setup(bot):
    await bot.add_cog(Evolution(bot))