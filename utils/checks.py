from discord.ext import commands
import aiosqlite
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
        async with aiosqlite.connect(DB_FILE) as db:
        
            async with db.execute("SELECT reason FROM banned_personnel WHERE user_id = ?", (str(ctx.author.id),)) as cursor:
                ban_data = await cursor.fetchone()
        
        if ban_data:
            reason = ban_data[0] if ban_data[0] else "Violation of Ecological Directives."
            await ctx.send(f"🚫 **Access Revoked:** Your research license has been permanently suspended by command.\n**Reason:** {reason}")
            return False # Command execution is aborted instantly!
            
        return True
        
    return commands.check(predicate)

def partner_not_deployed():
    """Decorator to block commands if the user's active partner is out on a mission."""
    async def predicate(ctx):
        user_id = str(ctx.author.id)
        
        async with aiosqlite.connect(DB_FILE) as db:
            # 1. Get their active partner
            async with db.execute("SELECT active_partner FROM users WHERE user_id = ?", (user_id,)) as cursor:
                partner_data = await cursor.fetchone()
                
            if not partner_data or not partner_data[0]:
                return True # If they don't have a partner, let the command handle the error!
                
            active_partner = partner_data[0]
            
            # 2. Check if that specific tag ID is in the deployment table
            async with db.execute("SELECT start_time FROM active_deployments WHERE instance_id = ?", (active_partner,)) as cursor:
                is_deployed = await cursor.fetchone()
                
            if is_deployed:
                # This raises an error that your bot's global error handler will catch!
                await ctx.send("⚠️ Your Active Partner is currently deployed on a field mission! Recall them with `!return` first.")
                
        return True
    return commands.check(predicate)

def has_started():
    """A custom decorator to ensure the user is registered in the ecological database."""
    async def predicate(ctx):
        async with aiosqlite.connect(DB_FILE) as db:
        
            async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (str(ctx.author.id),)) as cursor:
                exists = await cursor.fetchone()
        
        if not exists:
            await ctx.send(f"🛑 **Unregistered Personnel:** You must obtain a research license and a starter specimen before exploring. Use `!start` to begin.")
            return False # This stops the command from running!
            
        return True # This allows the command to proceed!
        
    return commands.check(predicate)