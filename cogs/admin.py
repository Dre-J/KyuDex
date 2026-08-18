"""Owner-only tools for putting things right.

Three jobs that previously needed a SQL client: handing somebody an item or some tokens,
and correcting a specimen whose species is wrong.

Everything here is `@commands.is_owner()`, which is stricter than server administrator -
it is the account that owns the bot application, and nobody else, in any server. That
matters because these commands mint currency and rewrite other people's Pokemon; a
server admin having them would make every server the bot joins a place where somebody
can conjure Master Balls.

**Every change is announced in the channel and printed to the log**, with the target's
id and what actually changed. An admin tool whose effects cannot be reconstructed later
is how a duplication bug becomes unprovable - the same argument as the trade ledger.
"""
import aiosqlite
import discord
from discord.ext import commands

from utils.constants import DB_FILE, EQUIPMENT_CATALOG, TM_SHOP

# The two ledgers a grant can land in. A TM is not a backpack item - it lives in
# `user_tms`, and `!buy` already routes on that distinction. Giving one out has to make
# the same choice, or an admin-granted TM lands somewhere `!tm` will never look for it.
BACKPACK, TM_LEDGER = 'inventory', 'tms'


def normalise(text):
    """`Great Ball`, `great-ball` and `greatball` are the same request."""
    return ''.join(ch for ch in str(text or '').lower() if ch.isalnum())


def resolve_item(typed):
    """
    What the admin meant, as (ledger, key, display name), or None.

    Checks the item catalogue first and the TM shelf second, which is the order `!buy`
    uses. Nothing here is gated on `purchasable` - refusing to hand out a Master Ball
    because the shop does not sell one would defeat the point of the command.
    """
    wanted = normalise(typed)
    if not wanted:
        return None

    for key, data in EQUIPMENT_CATALOG.items():
        if normalise(key) == wanted or normalise(data.get('name')) == wanted:
            return BACKPACK, key, data.get('name', key.replace('-', ' ').title())

    for move in TM_SHOP:
        if normalise(move) == wanted or normalise(f"tm{move}") == wanted:
            return TM_LEDGER, move, f"TM {move.replace('-', ' ').title()}"

    return None


async def resolve_specimen(db, tag):
    """
    One specimen from a tag or a tag prefix, as (row, error).

    Refuses an AMBIGUOUS prefix rather than picking one. Every other lookup in this
    codebase takes the first match, which is tolerable when it is scoped to your own
    roster and is not when the command rewrites any specimen in the database - six
    characters of a UUID collide sooner than people expect, and the wrong Pokemon
    quietly becoming a different species is not a mistake anybody would trace.
    """
    async with db.execute("""
        SELECT cp.instance_id, cp.user_id, cp.pokedex_id, cp.ability, cp.level,
               cp.nickname, s.name, s.standard_abilities, s.hidden_ability
        FROM caught_pokemon cp
        JOIN base_pokemon_species s ON cp.pokedex_id = s.pokedex_id
        WHERE cp.instance_id LIKE ?
        LIMIT 5
    """, (f"{tag}%",)) as cursor:
        rows = await cursor.fetchall()

    if not rows:
        return None, f"❌ No specimen has a tag starting with `{tag}`."
    if len(rows) > 1:
        found = ", ".join(f"`{r[0][:8]}`" for r in rows)
        return None, (f"⚠️ `{tag}` matches {len(rows)} specimens ({found}). "
                      f"Give me more of the tag.")
    return rows[0], None


def inherited_ability(current, old_standards, old_hidden, new_standards, new_hidden):
    """
    The ability the specimen keeps when its species changes.

    Slot is preserved, not the name: a Pokemon in ability slot 2 stays in slot 2, and a
    hidden ability stays hidden. This is the same mapping the evolution path uses, and
    it is here rather than imported because that copy is welded into a level-up handler
    that also writes to the database.
    """
    if current and old_hidden and current == old_hidden and new_hidden:
        return new_hidden

    slot = 0
    if old_standards and current:
        old_list = [a.strip() for a in old_standards.split(',') if a.strip()]
        if current in old_list:
            slot = old_list.index(current)

    new_list = [a.strip() for a in (new_standards or '').split(',') if a.strip()]
    if not new_list:
        return new_hidden or current or 'unknown'
    return new_list[slot] if slot < len(new_list) else new_list[0]


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================================
    # GIVE
    # ==========================================
    @commands.group(name="give", invoke_without_command=True)
    @commands.is_owner()
    async def give(self, ctx):
        """[ADMIN] Hands out items or tokens."""
        await ctx.send("Usage: `!give item @user <quantity> <item>` or "
                       "`!give tokens @user <amount>`.")

    @give.command(name="item", aliases=["items", "tm"])
    @commands.is_owner()
    async def give_item(self, ctx, target: discord.User, quantity: int, *, item: str):
        """[ADMIN] Adds an item (or a TM) to somebody's pack. `!give item @user 5 ultra ball`"""
        if quantity == 0:
            return await ctx.send("⚠️ Give them something, or take something away — not zero.")

        resolved = resolve_item(item)
        if not resolved:
            return await ctx.send(
                f"❌ `{item}` is not an item or a TM I know about. Names come from the "
                f"market catalogue — try `!market`.")

        ledger, key, display = resolved
        user_id = str(target.id)

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute("SELECT 1 FROM users WHERE user_id = ?",
                                      (user_id,)) as cursor:
                    if not await cursor.fetchone():
                        return await ctx.send(
                            f"⚠️ **{target.name}** is not registered. They need `!start` first.")

                table, column = (('user_inventory', 'item_name') if ledger == BACKPACK
                                 else ('user_tms', 'tm_name'))

                await db.execute(f"""
                    INSERT INTO {table} (user_id, {column}, quantity)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, {column}) DO UPDATE SET
                        quantity = quantity + excluded.quantity
                """, (user_id, key, quantity))

                # A negative grant is a correction, and it must not leave somebody
                # holding minus two Potions - a quantity below zero reads as a huge
                # number in some places and as a broken row in others.
                await db.execute(
                    f"UPDATE {table} SET quantity = 0 "
                    f"WHERE user_id = ? AND {column} = ? AND quantity < 0",
                    (user_id, key))

                async with db.execute(
                        f"SELECT quantity FROM {table} WHERE user_id = ? AND {column} = ?",
                        (user_id, key)) as cursor:
                    held = (await cursor.fetchone())[0]

                await db.commit()
        except Exception as e:
            print(f"Admin give item error: {e}")
            return await ctx.send("❌ A database error occurred. Nothing was granted.")

        print(f"ADMIN GRANT {ctx.author.id} -> {user_id}: {quantity:+} {key} ({ledger})")

        verb = "Granted" if quantity > 0 else "Removed"
        embed = discord.Embed(
            title="📦 Requisition Override",
            description=f"{verb} **{abs(quantity)}x {display}** "
                        f"{'to' if quantity > 0 else 'from'} **{target.name}**.",
            colour=discord.Colour.blurple())
        embed.add_field(name="They now hold", value=f"**{held}**", inline=True)
        embed.add_field(name="Ledger",
                        value="TM case" if ledger == TM_LEDGER else "Field pack",
                        inline=True)
        embed.set_footer(text=f"Authorised by {ctx.author.name} · target {user_id}")
        await ctx.send(embed=embed)

    @give.command(name="tokens", aliases=["token", "credits", "eco"])
    @commands.is_owner()
    async def give_tokens(self, ctx, target: discord.User, amount: int):
        """[ADMIN] Adds (or removes) Eco Tokens. `!give tokens @user 5000`"""
        if amount == 0:
            return await ctx.send("⚠️ Give them something, or take something away — not zero.")

        user_id = str(target.id)

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                async with db.execute("SELECT eco_tokens FROM users WHERE user_id = ?",
                                      (user_id,)) as cursor:
                    row = await cursor.fetchone()

                if not row:
                    return await ctx.send(
                        f"⚠️ **{target.name}** is not registered. They need `!start` first.")

                # Clamped at zero rather than allowed to go negative: a debt nobody can
                # see is a debt that silently blocks every purchase they try to make.
                before = row[0] or 0
                after = max(0, before + amount)

                await db.execute("UPDATE users SET eco_tokens = ? WHERE user_id = ?",
                                 (after, user_id))
                await db.commit()
        except Exception as e:
            print(f"Admin give tokens error: {e}")
            return await ctx.send("❌ A database error occurred. No funds were moved.")

        print(f"ADMIN FUNDS {ctx.author.id} -> {user_id}: {before:,} -> {after:,}")

        embed = discord.Embed(
            title="🪙 Conservation Grant Authorised" if amount > 0 else "🪙 Funds Recovered",
            description=f"**{target.name}**'s balance moved by **{after - before:+,}** "
                        f"Eco Tokens.",
            colour=discord.Colour.gold())
        embed.add_field(name="Before", value=f"🪙 {before:,}", inline=True)
        embed.add_field(name="After", value=f"🪙 {after:,}", inline=True)
        if after - before != amount:
            embed.add_field(
                name="Note",
                value=f"Clamped at zero — the full **{amount:+,}** would have gone negative.",
                inline=False)
        embed.set_footer(text=f"Authorised by {ctx.author.name} · target {user_id}")
        await ctx.send(embed=embed)

    # ==========================================
    # REWRITE
    # ==========================================
    @commands.group(name="rewrite", invoke_without_command=True)
    @commands.is_owner()
    async def rewrite(self, ctx):
        """[ADMIN] Corrects a specimen's records."""
        await ctx.send("Usage: `!rewrite id <tag> <new pokedex id> [ability]`.")

    @rewrite.command(name="id", aliases=["species", "dex"])
    @commands.is_owner()
    async def rewrite_id(self, ctx, tag: str, new_id: int, *, ability: str = None):
        """[ADMIN] Changes a specimen's species, and its ability with it. `!rewrite id a1b2c3 26`"""
        try:
            async with aiosqlite.connect(DB_FILE) as db:
                specimen, problem = await resolve_specimen(db, tag)
                if problem:
                    return await ctx.send(problem)

                (instance_id, owner_id, old_id, old_ability, level, nickname,
                 old_name, old_standards, old_hidden) = specimen

                async with db.execute(
                        "SELECT name, standard_abilities, hidden_ability, form_type "
                        "FROM base_pokemon_species WHERE pokedex_id = ?",
                        (new_id,)) as cursor:
                    target_species = await cursor.fetchone()

                if not target_species:
                    return await ctx.send(
                        f"❌ There is no species with pokedex id `{new_id}`.")

                new_name, new_standards, new_hidden, form_type = target_species

                if new_id == old_id:
                    return await ctx.send(
                        f"⚠️ `{instance_id[:8]}` is already **{new_name.title()}**.")

                # An explicit ability is checked against the NEW species. Writing an
                # ability the species cannot have produces a specimen whose ability the
                # battle engine will look up and not find, which is a far more annoying
                # bug than a rejected command.
                if ability:
                    allowed = [a.strip() for a in (new_standards or '').split(',') if a.strip()]
                    if new_hidden and new_hidden != 'None':
                        allowed.append(new_hidden)
                    wanted = ability.strip().lower().replace(' ', '-')
                    if wanted not in allowed:
                        return await ctx.send(
                            f"❌ **{new_name.title()}** cannot have `{wanted}`. "
                            f"It may have: {', '.join(f'`{a}`' for a in allowed) or '*nothing recorded*'}.")
                    new_ability = wanted
                    how = "set by hand"
                else:
                    new_ability = inherited_ability(old_ability, old_standards, old_hidden,
                                                    new_standards, new_hidden)
                    how = "carried over by slot"

                await db.execute(
                    "UPDATE caught_pokemon SET pokedex_id = ?, ability = ? "
                    "WHERE instance_id = ?", (new_id, new_ability, instance_id))
                await db.commit()
        except Exception as e:
            print(f"Admin rewrite id error: {e}")
            return await ctx.send("❌ A database error occurred. Nothing was rewritten.")

        print(f"ADMIN REWRITE {ctx.author.id}: {instance_id} "
              f"{old_id}({old_name})/{old_ability} -> {new_id}({new_name})/{new_ability}")

        embed = discord.Embed(
            title="🧬 Genetic Record Rewritten",
            description=f"Tag `{instance_id[:8]}`"
                        + (f" — *{nickname}*" if nickname else "")
                        + f", owned by `{owner_id}`.",
            colour=discord.Colour.dark_teal())
        embed.add_field(name="Species",
                        value=f"{old_name.replace('-', ' ').title()} → "
                              f"**{new_name.replace('-', ' ').title()}**", inline=False)
        embed.add_field(name="Ability",
                        value=f"{(old_ability or 'unknown').replace('-', ' ').title()} → "
                              f"**{new_ability.replace('-', ' ').title()}** *({how})*",
                        inline=False)
        embed.add_field(name="Unchanged", value=f"Level {level}, IVs, nature, held item",
                        inline=False)

        # Said rather than fixed, because "fixing" it means deleting moves somebody may
        # have spent a TM on, and that is the admin's call rather than mine.
        if form_type and form_type not in ('base', 'alolan', 'galarian', 'hisuian',
                                           'paldean'):
            embed.add_field(
                name="⚠️ Note",
                value=f"`{form_type}` is a battle-only form. It will not appear in the "
                      f"wild and may behave oddly outside combat.",
                inline=False)

        embed.set_footer(text=f"Authorised by {ctx.author.name}")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Admin(bot))
