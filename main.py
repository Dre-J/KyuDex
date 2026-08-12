import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

# Basic Setup
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

bot.remove_command('help')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}!')
    print('Environmental monitoring systems online.')

async def load_extensions():
    """Iterates through the 'cogs' folder and loads every Python file."""
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f"Loaded module: {filename}")
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

# 3. The Developer Commands (Strictly protected!)
@bot.command(name="reload", hidden=True)
@commands.is_owner() # SECURITY: Only you (the bot owner) can run this!
async def reload_cog(ctx, extension: str):
    """Reloads a specific module without taking the bot offline."""
    try:
        await bot.reload_extension(f"cogs.{extension}")
        await ctx.send(f"🔄 Module `cogs/{extension}.py` successfully reloaded.")
    except Exception as e:
        await ctx.send(f"⚠️ Error reloading `{extension}`: ```py\n{e}\n```")

@bot.command(name="load", hidden=True)
@commands.is_owner()
async def load_cog(ctx, extension: str):
    """Loads a brand new module."""
    try:
        await bot.load_extension(f"cogs.{extension}")
        await ctx.send(f"📥 Module `cogs/{extension}.py` loaded.")
    except Exception as e:
        await ctx.send(f"⚠️ Error loading `{extension}`: ```py\n{e}\n```")

load_dotenv() #Loads Hidden variables from .env file
TOKEN = os.getenv('DISC_TOKEN')
def tune_database():
    """
    Put the database into WAL before anything touches it.

    The default rollback journal takes an exclusive lock for every write, so a battle
    turn writing state blocks every other read across every server until it finishes.
    WAL lets readers carry on through a write, which is the shape of nearly all the
    contention here. Paired with synchronous=NORMAL, the usual companion: a hard power
    cut can cost the last transaction but cannot corrupt the file.

    Both settings persist in the database itself, so this is a one-time change that is
    re-asserted at each boot rather than a per-connection cost. Reported rather than
    assumed - PRAGMA journal_mode returns the mode actually in force.
    """
    import sqlite3
    from utils.constants import DB_FILE
    try:
        with sqlite3.connect(DB_FILE) as conn:
            mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            conn.execute("PRAGMA synchronous=NORMAL")
        print(f"🗄️ Database journal mode: {mode}")
    except Exception as e:
        print(f"⚠️ WARNING: Could not tune the database ({e}). Falling back to defaults.")


# Boot Execution
async def main():
    tune_database()
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())