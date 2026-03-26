import discord
from discord.ext import commands
import sqlite3
from utils.constants import DB_FILE
from utils import checks

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
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. Determine the Target Specimen
        if target.lower() in ["partner", "lead", "active", "latest"]:
            cursor.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,))
            partner_data = cursor.fetchone()
            if not partner_data or not partner_data[0]:
                await ctx.send("You don't have an Active Partner equipped! Specify a Tag ID instead.")
                conn.close()
                return
            actual_tag = partner_data[0]
        else:
            # If it's a normal tag, we'll search using LIKE
            actual_tag = f"{target}%"

        # 2. Fetch the Specimen's Current Data
        cursor.execute("""
            SELECT cp.instance_id, cp.pokedex_id, s.name 
            FROM caught_pokemon cp
            JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
            WHERE cp.instance_id LIKE ? AND cp.user_id = ?
        """, (actual_tag, user_id))
        
        pokemon_data = cursor.fetchone()
        
        if not pokemon_data:
            await ctx.send(f"Could not locate that specimen in your survey notebook.")
            conn.close()
            return
            
        db_tag_id, current_pokedex_id, current_name = pokemon_data
        
        # 3. Check the Metamorphosis Rulebook
        cursor.execute("""
            SELECT er.evolved_species_id, s.name 
            FROM evolution_rules er
            JOIN base_pokemon_species s ON er.evolved_species_id = s.pokedex_id
            WHERE er.base_species_id = ? 
            AND er.trigger_name = 'use-item' 
            AND er.item_name = ?
        """, (current_pokedex_id, formatted_item))
        
        evo_data = cursor.fetchone()
        
        if not evo_data:
            await ctx.send(f"⚠️ A **{formatted_item.replace('-', ' ').title()}** has no biological effect on a **{current_name.capitalize()}**.")
            conn.close()
            return
            
        new_pokedex_id, evolved_into_name = evo_data
        
        # 4. Check Inventory
        cursor.execute("SELECT quantity FROM user_inventory WHERE user_id = ? AND item_name = ?", (user_id, formatted_item))
        inv_data = cursor.fetchone()
        
        if not inv_data or inv_data[0] < 1:
            await ctx.send(f"🎒 You don't have a **{formatted_item.replace('-', ' ').title()}** in your field pack!")
            conn.close()
            return

        # 5. Execute the Metamorphosis safely
        try:
            # Deduct the item
            cursor.execute("UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = ? AND item_name = ?", (user_id, formatted_item))
            
            # Update the Specimen's Genetics
            cursor.execute("UPDATE caught_pokemon SET pokedex_id = ? WHERE instance_id = ?", (new_pokedex_id, db_tag_id))
            
            # ==========================================
            # DIRECTIVE TRACKER: KINETIC MATURATION (EVOLUTION)
            # ==========================================
            cursor.execute("""
                UPDATE field_directives
                SET current_progress = current_progress + 1
                WHERE user_id = ? AND objective_type = 'trigger_mutation' 
                AND (target_variable = 'any' OR target_variable = ?) AND is_completed = 0
            """, (user_id, current_name.lower()))

            cursor.execute("""
                SELECT required_amount, current_progress 
                FROM field_directives
                WHERE user_id = ? AND objective_type = 'trigger_mutation' 
                AND (target_variable = 'any' OR target_variable = ?) AND is_completed = 0
            """, (user_id, current_name.lower()))
            
            mut_row = cursor.fetchone()
            # ==========================================

            # Commit the item deduction, the evolution, and the quest progress together!
            conn.commit()
            
            embed = discord.Embed(title="🧬 Metamorphosis Complete!", color=discord.Color.gold())
            
            # Build the description dynamically so we can append the quest alert if needed
            base_desc = f"**{ctx.author.name}** exposed their **{current_name.capitalize()}** to a {formatted_item.replace('-', ' ').title()}...\n\nIt rapidly adapted and evolved into a **{evolved_into_name.capitalize()}**!"
            
            if mut_row and mut_row[1] == mut_row[0]:
                base_desc += "\n\n📡 **Directive Complete:** Kinetic Maturation Study concluded! Run `!claim` to receive your funding."
                
            embed.description = base_desc
            embed.set_footer(text=f"Tag ID: {db_tag_id[:8]} | 1x {formatted_item.replace('-', ' ').title()} Consumed")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            conn.rollback() # Ensure nothing saves if an error occurs!
            print(f"Evolution error: {e}")
            await ctx.send("A genetic sequencing error occurred during the evolution process.")
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(Evolution(bot))