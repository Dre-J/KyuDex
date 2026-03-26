from discord.ext import commands
import sqlite3
from utils.constants import DB_FILE

def is_not_in_combat():
    """A global firewall that prevents database manipulation while actively battling."""
    async def predicate(ctx):
        # We dynamically fetch your battle cog (assuming it's named 'BattleCog')
        battle_cog = ctx.bot.get_cog("Combat") 
        
        # Check if the cog exists and if the user is in its active_battles memory
        if battle_cog and hasattr(battle_cog, 'active_battles'):
            if str(ctx.author.id) in battle_cog.active_battles:
                await ctx.send("⚔️ **Combat Lock:** You cannot perform this action while engaged in a tactical skirmish!")
                return False
        return True # If they aren't in battle, let the command run!
        
    return commands.check(predicate)

def is_not_in_trade():
    """A global firewall preventing database manipulation during an active ecological exchange."""
    async def predicate(ctx):
        # We fetch your Social cog where the active_trades memory lives
        trading_cog = ctx.bot.get_cog("Social") 
        
        if trading_cog and hasattr(trading_cog, 'active_trades'):
            if ctx.author.id in trading_cog.active_trades:
                # 1. Send the warning to the user
                await ctx.send("🤝 **Exchange Lock:** You are currently negotiating a biological trade. Please complete or cancel it first.")
                # 2. ABORT THE COMMAND!
                return False 
                
        # If they are NOT in a trade, the code reaches here and opens the gate.
        return True
        
    return commands.check(predicate)

def is_authorized():
    """A custom decorator that blocks interactions from personnel with revoked licenses."""
    async def predicate(ctx):
        conn = sqlite3.connect(DB_FILE) # Ensure DB_FILE is accessible
        cursor = conn.cursor()
        
        cursor.execute("SELECT reason FROM banned_personnel WHERE user_id = ?", (str(ctx.author.id),))
        ban_data = cursor.fetchone()
        conn.close()
        
        if ban_data:
            reason = ban_data[0] if ban_data[0] else "Violation of Ecological Directives."
            await ctx.send(f"🚫 **Access Revoked:** Your research license has been permanently suspended by command.\n**Reason:** {reason}")
            return False # Command execution is aborted instantly!
            
        return True
        
    return commands.check(predicate)

def has_started():
    """A custom decorator to ensure the user is registered in the ecological database."""
    async def predicate(ctx):
        conn = sqlite3.connect(DB_FILE) # Make sure DB_FILE is accessible here!
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (str(ctx.author.id),))
        exists = cursor.fetchone()
        conn.close()
        
        if not exists:
            await ctx.send(f"🛑 **Unregistered Personnel:** You must obtain a research license and a starter specimen before exploring. Use `!start` to begin.")
            return False # This stops the command from running!
            
        return True # This allows the command to proceed!
        
    return commands.check(predicate)