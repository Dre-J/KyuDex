import discord
from discord.ext import commands
import os
import asyncio


# Basic Setup
intents = discord.Intents.default()
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

# --- Token Setup ---
# Read the token securely from the text file
def get_token():
    if not os.path.exists("token.txt"):
        print("Error: token.txt file not found!")
        exit()
    with open("token.txt", "r") as file:
        return file.read().strip()
# Boot Execution
async def main():
    async with bot:
        await load_extensions()
        await bot.start(get_token())

if __name__ == "__main__":
    asyncio.run(main())