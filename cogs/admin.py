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

from utils import audit
from utils.constants import DB_FILE, EQUIPMENT_CATALOG
from utils.formulas import get_xp_requirement
from utils.machines import grant_tm, find_tm

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

    # The same lookup `!buy` uses, so an admin and a shopper cannot disagree about
    # which of 340 TMs `stealth rock` means.
    move = find_tm(typed)
    if move:
        return TM_LEDGER, move, f"TM {move.replace('-', ' ').title()}"

    return None


def pretty_moves(moves):
    """A move list as a reader sees it, with empty slots left visible rather than hidden."""
    named = [m.replace('-', ' ').title() for m in moves if m and m != 'none']
    return ", ".join(named) if named else "*nothing*"


async def natural_moveset(db, pokedex_id, level):
    """
    The four moves a specimen of this species and level would naturally know.

    The most recent four level-up moves at or below its level - the same rule the NPC
    roster builder uses, and the level-aware version of what a capture does. Padded to
    four with 'none', which is what an empty slot looks like everywhere else; a species
    with a thin early movepool genuinely has fewer than four.
    """
    async with db.execute("""
        SELECT move_name FROM species_movepool
        WHERE pokedex_id = ? AND learn_method = 'level-up'
          AND level_learned <= ? AND level_learned > 0
        GROUP BY move_name ORDER BY MIN(level_learned) DESC LIMIT 4
    """, (pokedex_id, level)) as cursor:
        moves = [row[0] for row in await cursor.fetchall()]

    # A species whose whole level-up pool starts above this level - or one recorded with
    # level_learned 0 throughout - would otherwise come out of here with four empty
    # slots and no way to act in a battle. Fall back to the earliest thing it can learn.
    if not moves:
        async with db.execute("""
            SELECT move_name FROM species_movepool
            WHERE pokedex_id = ? AND learn_method = 'level-up'
            GROUP BY move_name ORDER BY MIN(level_learned) ASC LIMIT 4
        """, (pokedex_id,)) as cursor:
            moves = [row[0] for row in await cursor.fetchall()]

    return (moves + ['none'] * 4)[:4]


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

                if ledger == TM_LEDGER:
                    # A TM is owned or it is not - there is no quantity to add to. The
                    # count-based branch below would have clamped a negative grant to
                    # zero and LEFT THE ROW, so taking a TM away would have looked like
                    # it worked while the trainer kept it. Revoking has to delete.
                    if quantity > 0:
                        await grant_tm(db, user_id, key)
                    else:
                        await db.execute(
                            "DELETE FROM user_tms WHERE user_id = ? AND tm_name = ?",
                            (user_id, key))
                    held = "the TM" if quantity > 0 else "nothing"
                else:
                    await db.execute("""
                        INSERT INTO user_inventory (user_id, item_name, quantity)
                        VALUES (?, ?, ?)
                        ON CONFLICT(user_id, item_name) DO UPDATE SET
                            quantity = quantity + excluded.quantity
                    """, (user_id, key, quantity))

                    # A negative grant is a correction, and it must not leave somebody
                    # holding minus two Potions - a quantity below zero reads as a huge
                    # number in some places and as a broken row in others.
                    await db.execute(
                        "UPDATE user_inventory SET quantity = 0 "
                        "WHERE user_id = ? AND item_name = ? AND quantity < 0",
                        (user_id, key))

                    async with db.execute(
                            "SELECT quantity FROM user_inventory "
                            "WHERE user_id = ? AND item_name = ?",
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

        await audit.post_admin_action(
            self.bot, action="Item grant", actor=ctx.author, target=target,
            colour=discord.Colour.blurple(),
            fields=[("Item", f"{display} (`{key}`)"),
                    ("Change", f"**{quantity:+}** → they now hold **{held}**"),
                    ("Ledger", "TM case" if ledger == TM_LEDGER else "Field pack")])

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

        await audit.post_admin_action(
            self.bot, action="Token grant", actor=ctx.author, target=target,
            colour=discord.Colour.gold(),
            fields=[("Change", f"**{after - before:+,}** Eco Tokens"),
                    ("Balance", f"🪙 {before:,} → 🪙 {after:,}")],
            detail=(f"Requested {amount:+,}, clamped at zero."
                    if after - before != amount else None))

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
        """[ADMIN] Changes a specimen's species, ability and moves. `!rewrite id a1b2c3 26`"""
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

                # The moves go with the species. A Pidgey rewritten into a Gengar kept
                # Gust and Sand Attack, which the new body cannot learn and `!moves`
                # will not list - a specimen holding moves outside its own movepool is
                # exactly the state every other command assumes cannot happen.
                async with db.execute(
                        "SELECT move_1, move_2, move_3, move_4 FROM caught_pokemon "
                        "WHERE instance_id = ?", (instance_id,)) as cursor:
                    old_moves = list(await cursor.fetchone())

                new_moves = await natural_moveset(db, new_id, level)

                await db.execute(
                    "UPDATE caught_pokemon SET pokedex_id = ?, ability = ?, "
                    "move_1 = ?, move_2 = ?, move_3 = ?, move_4 = ? "
                    "WHERE instance_id = ?",
                    (new_id, new_ability, *new_moves, instance_id))
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
        embed.add_field(name="Moves",
                        value=f"{pretty_moves(old_moves)}\n→ **{pretty_moves(new_moves)}**",
                        inline=False)
        embed.add_field(name="Unchanged", value=f"Level {level}, IVs, nature, held item",
                        inline=False)

        if form_type and form_type not in ('base', 'alolan', 'galarian', 'hisuian',
                                           'paldean'):
            embed.add_field(
                name="⚠️ Note",
                value=f"`{form_type}` is a battle-only form. It will not appear in the "
                      f"wild and may behave oddly outside combat.",
                inline=False)

        embed.set_footer(text=f"Authorised by {ctx.author.name}")
        await ctx.send(embed=embed)

        # The owner of the specimen is named as the target even though they did not do
        # this - because the question this record answers is "why did my Pokemon change
        # species", and their id is what somebody will search for.
        await audit.post_admin_action(
            self.bot, action="Species rewrite", actor=ctx.author,
            colour=discord.Colour.dark_teal(),
            fields=[("Specimen", f"`{instance_id}`"
                                 + (f" — *{nickname}*" if nickname else "")),
                    ("Owner", f"`{owner_id}`"),
                    ("Species", f"{old_name} (`{old_id}`) → {new_name} (`{new_id}`)"),
                    ("Ability", f"{old_ability} → {new_ability} ({how})"),
                    # The moves it USED to have, in full. This is where a TM somebody
                    # paid for goes, so the record has to be enough to put them back by
                    # hand - an admin who rewrote the wrong tag has no other copy.
                    ("Moves", f"{pretty_moves(old_moves)} → {pretty_moves(new_moves)}")])

    @rewrite.command(name="level", aliases=["lvl"])
    @commands.is_owner()
    async def rewrite_level(self, ctx, tag: str, new_level: int):
        """[ADMIN] Sets a specimen's level. `!rewrite level a1b2c3 50`"""
        if not 1 <= new_level <= 100:
            return await ctx.send("⚠️ A level is between 1 and 100.")

        try:
            async with aiosqlite.connect(DB_FILE) as db:
                specimen, problem = await resolve_specimen(db, tag)
                if problem:
                    return await ctx.send(problem)

                (instance_id, owner_id, pokedex_id, _ability, old_level, nickname,
                 species_name, _standards, _hidden) = specimen

                async with db.execute(
                        "SELECT growth_rate FROM base_pokemon_species "
                        "WHERE pokedex_id = ?", (pokedex_id,)) as cursor:
                    row = await cursor.fetchone()
                growth_rate = (row[0] if row else None) or 'medium-fast'

                # The XP has to move with the level or the change undoes itself. A
                # specimen dropped to 5 while still carrying level-70 experience levels
                # straight back up the moment it wins a battle, because the levelling
                # loop reads the TOTAL and climbs until it stops qualifying. So this
                # writes the exact threshold the new level sits on: the XP required to
                # have REACHED it, which is the requirement for the level below.
                new_xp = 0 if new_level <= 1 else get_xp_requirement(new_level - 1,
                                                                    growth_rate)

                await db.execute(
                    "UPDATE caught_pokemon SET level = ?, experience = ? "
                    "WHERE instance_id = ?", (new_level, new_xp, instance_id))
                await db.commit()
        except Exception as e:
            print(f"Admin rewrite level error: {e}")
            return await ctx.send("❌ A database error occurred. Nothing was rewritten.")

        print(f"ADMIN REWRITE LEVEL {ctx.author.id}: {instance_id} "
              f"{old_level} -> {new_level}")

        embed = discord.Embed(
            title="📈 Growth Record Rewritten",
            description=f"Tag `{instance_id[:8]}`"
                        + (f" — *{nickname}*" if nickname else "")
                        + f", owned by `{owner_id}`.",
            colour=discord.Colour.dark_teal())
        embed.add_field(name="Species",
                        value=species_name.replace('-', ' ').title(), inline=False)
        embed.add_field(name="Level", value=f"{old_level} → **{new_level}**",
                        inline=False)
        embed.add_field(name="Experience",
                        value=f"Reset to **{new_xp:,}**, the {growth_rate} threshold for "
                              f"level {new_level}.", inline=False)
        embed.add_field(name="Unchanged",
                        value="Species, ability, moves, IVs, EVs, nature, held item",
                        inline=False)
        embed.set_footer(text=f"Authorised by {ctx.author.name}")
        await ctx.send(embed=embed)

        await audit.post_admin_action(
            self.bot, action="Level rewrite", actor=ctx.author,
            colour=discord.Colour.dark_teal(),
            fields=[("Specimen", f"`{instance_id}`"
                                 + (f" — *{nickname}*" if nickname else "")),
                    ("Owner", f"`{owner_id}`"),
                    ("Species", species_name),
                    ("Level", f"{old_level} → {new_level}"),
                    ("Experience", f"reset to {new_xp} ({growth_rate})")])


async def setup(bot):
    await bot.add_cog(Admin(bot))
