import discord
from discord.ext import commands
from utils.constants import DB_FILE
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
                async with db.execute("""
                    SELECT er.evolved_species_id, s.name, s.standard_abilities, s.hidden_ability
                    FROM evolution_rules er
                    JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
                    WHERE er.base_species_id = ? 
                    AND er.trigger_name = 'use-item' 
                    AND er.item_name = ?
                """, (current_pokedex_id, formatted_item)) as cursor:
                    evo_data = await cursor.fetchone()
                
                if not evo_data:
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
                
                # 4. Check Inventory
                async with db.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, formatted_item)) as cursor:
                    inv_data = await cursor.fetchone()
                
                if not inv_data or inv_data[0] < 1:
                    return await ctx.send(f"🎒 You don't have a **{formatted_item.replace('-', ' ').title()}** in your field pack!")

                # 5. Execute the Metamorphosis safely
                await db.execute("BEGIN TRANSACTION")
                try:
                    # Deduct the item
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
            
            base_desc = f"**{ctx.author.name}** exposed their **{current_name.capitalize()}** to a {formatted_item.replace('-', ' ').title()}...\n\nIt rapidly adapted and evolved into a **{evolved_into_name.capitalize()}**!"
            
            # Add a note if their ability changed!
            if current_ability != new_ability:
                base_desc += f"\n\n✨ Through mutation, its ability changed from **{current_ability.replace('-', ' ').title()}** to **{new_ability.replace('-', ' ').title()}**!"
            
            if mutation_finished:
                base_desc += "\n\n📡 **Directive Complete:** Kinetic Maturation Study concluded! Run `!claim` to receive your funding."
                
            embed.description = base_desc
            embed.set_footer(text=f"Tag ID: {db_tag_id[:8]} | 1x {formatted_item.replace('-', ' ').title()} Consumed")
            
            await ctx.send(embed=embed)

        except Exception as master_err:
            print(f"Critical command error in manual_evolve: {master_err}")
            import traceback
            traceback.print_exc()
            await ctx.send("⚠️ A critical system failure occurred while parsing biological data.")
            
async def setup(bot):
    await bot.add_cog(Evolution(bot))