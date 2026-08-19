import discord
from discord.ext import commands
import os
import asyncio
import traceback
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
    await warm_battle_scenes()


async def warm_battle_scenes():
    """
    Draw every battle backdrop and weather overlay before anyone asks for one.

    They are cached on first use, so otherwise the first battle in each biome pays ~240ms
    to draw a 1600x900 backdrop before it can send anything - a slow opening turn for a
    real player, once per biome per restart.

    Deliberately after login rather than before it: the bot comes online immediately and
    warms in the background, so this costs nobody a delayed startup. Handed to a worker
    thread because it is a couple of seconds of solid PIL work and the event loop still
    has a gateway heartbeat to keep.

    Set KYU_NO_PREWARM=1 to skip it. Peak memory is unchanged either way - normal play
    fills these same caches - but on a very small host you may prefer to pay for a biome
    only if it is actually visited.
    """
    if os.getenv("KYU_NO_PREWARM"):
        print("🎨 Scene pre-warm skipped (KYU_NO_PREWARM).")
        return

    try:
        from cogs import battle_render
        built, seconds, megabytes = await asyncio.to_thread(battle_render.prewarm_scene_caches)
        print(f"🎨 Battle scenes warmed: {built} surfaces in {seconds:.1f}s "
              f"({megabytes:.0f}MB held)")
    except Exception as e:
        # A cold cache is slower, never broken, so this must not stop the bot booting.
        print(f"⚠️ WARNING: Could not pre-warm battle scenes ({e}). They will build on demand.")

@bot.event
async def on_command_error(ctx, error):
    """
    Keep the console for things that are actually broken.

    The default handler prints a full traceback for every mistyped command and every
    refused check - and the channel restriction in `cogs/config.py` refuses by design,
    so a server that switched it on would otherwise fill its log with tracebacks for
    working correctly. Those two are swallowed; everything else still prints exactly as
    it did, because a swallowed real error is far worse than a noisy one.
    """
    if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        # Best effort: an error handler that itself raises - because the bot cannot
        # speak in that channel - loses the original error as well as its own.
        try:
            return await ctx.send(f"⚠️ Missing `{error.param.name}`. "
                                  f"Usage: `!{ctx.command.qualified_name} "
                                  f"{ctx.command.signature}`")
        except Exception:
            return

    print(f"Command error in {ctx.command}: {error!r}")
    traceback.print_exception(type(error), error, error.__traceback__)


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