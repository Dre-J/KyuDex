"""
`!dex` - everything this world knows about a species, on one screen.

**IT READS, IT NEVER WRITES.** Nothing in this cog touches caught_pokemon, the inventory
or a trainer's row. That is what makes the buttons safe to leave live: the worst a stale
dashboard can do is show somebody a Charizard.

**THE ENTRY IS PAGED, NOT PICKED.** A species averages fourteen flavour entries across
thirty-five games and most are word-for-word repeats, so `utils.dex.flavour_entries`
groups them and the ⏮/⏭ pair walks the groups. Bulbasaur has 22 entries and 12 pages.

**THE FORM BUTTON WALKS species_forms, NOT THE NAME.** Splitting a species name on its
first hyphen works for `rotom-heat` and destroys `mr-mime`, `ho-oh`, `type-null` and
`jangmo-o`; the mapping is imported by migrate_dex_data.py instead.

**A THINNER DEX IS BETTER THAN A CRASH.** Every dex table is optional. On a database
that has not had migrate_dex_data.py applied, the flavour text, egg groups, hatch
counter and genus simply do not appear and everything else still works.
"""
import discord
from discord.ext import commands

import aiosqlite

from utils.constants import DB_FILE, type_badges, SPAWNABLE_FORM_TYPES
from utils.db_manager import evolution_family
from utils.regions import region_label, region_of_generation
from utils.species import MAX_CHOICES, pretty_species, resolve_species, suggest_species
from utils.sprites import HOME, resolve_sprite, sprite_attachment_name
from utils.translations import LANGUAGES, names_for_species
from utils import checks
from utils import dex as D

DEX_COLOUR = discord.Colour(0x41F097)

# The national dex stops at 1025; everything above that id in base_pokemon_species is a
# form and has no number of its own.
LAST_NATIONAL = 1025

# Discord allows 1024 characters in a field and 4096 in a description. The flavour entry
# is the description, and the longest in the database is 235 characters, so the room is
# for the version list underneath it.
DESCRIPTION_LIMIT = 4096


def trim(text, limit):
    """`text`, shortened at a word boundary if it has to be."""
    text = str(text or '')
    if len(text) <= limit:
        return text
    cut = text[:limit - 1]
    return cut[:cut.rfind(' ')].rstrip() + '…' if ' ' in cut else cut + '…'


class DexView(discord.ui.View):
    """
    The dashboard. Holds only what it needs to re-render: an id, and three toggles.

    State is deliberately NOT a cached embed. Every press rebuilds from the database, so
    a dex left open while a migration is applied starts showing the new data rather than
    a snapshot from before it.
    """

    def __init__(self, cog, owner_id, pokedex_id, *, shiny=False, female=False, page=0):
        super().__init__(timeout=180)
        self.cog = cog
        self.owner_id = owner_id
        self.pokedex_id = pokedex_id
        self.shiny = shiny
        self.female = female
        self.page = page
        self.forms = []
        self.pages = 1

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "🔬 That is somebody else's dex. Run `!dex` for your own.",
                ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

    # ------------------------------------------------------------------
    async def refresh(self, interaction=None):
        embed, attachment, self.forms, self.pages = await self.cog.render(
            self.pokedex_id, shiny=self.shiny, female=self.female, page=self.page)
        self.arrange()
        if interaction is None:
            return embed, attachment
        # attachments= rather than a bare edit: the sprite is a file attachment, and
        # editing without replacing it leaves the previous species' picture in place.
        await interaction.response.edit_message(
            embed=embed, view=self,
            attachments=[attachment] if attachment else [])
        return embed, attachment

    def arrange(self):
        """Label and enable the controls for whatever is on screen now."""
        self.previous_species.disabled = self.pokedex_id <= 1
        self.next_species.disabled = self.pokedex_id >= LAST_NATIONAL
        self.previous_species.label = f"◀ #{max(1, self.pokedex_id - 1):04d}"
        self.next_species.label = f"#{min(LAST_NATIONAL, self.pokedex_id + 1):04d} ▶"

        self.shiny_toggle.style = (discord.ButtonStyle.success if self.shiny
                                   else discord.ButtonStyle.secondary)
        self.gender_toggle.label = "♀ Female" if self.female else "♂ Male"
        self.form_cycle.disabled = len(self.forms) < 2
        self.form_cycle.label = (f"🔀 Form 1/1" if len(self.forms) < 2
                                 else f"🔀 Form {self.form_index() + 1}/{len(self.forms)}")

        self.previous_entry.disabled = self.pages < 2
        self.next_entry.disabled = self.pages < 2
        self.entry_count.label = f"Entry {self.page + 1}/{max(1, self.pages)}"

    def form_index(self):
        for index, (pokedex_id, _name) in enumerate(self.forms):
            if pokedex_id == self.pokedex_id:
                return index
        return 0

    # --- species navigation -------------------------------------------
    @discord.ui.button(label="◀", style=discord.ButtonStyle.primary, row=0)
    async def previous_species(self, interaction, _button):
        await self.jump(interaction, self.pokedex_id - 1)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.primary, row=0)
    async def next_species(self, interaction, _button):
        await self.jump(interaction, self.pokedex_id + 1)

    async def jump(self, interaction, pokedex_id):
        """Move to another species, resetting everything that belonged to the last one."""
        self.pokedex_id = max(1, min(LAST_NATIONAL, pokedex_id))
        # The page and the form belong to the species that was on screen. Carrying them
        # over would open Ivysaur on "entry 9 of 12" when it has four, and on a form
        # index that means nothing.
        self.page = 0
        await self.refresh(interaction)

    # --- appearance ---------------------------------------------------
    @discord.ui.button(label="✨ Shiny", style=discord.ButtonStyle.secondary, row=1)
    async def shiny_toggle(self, interaction, _button):
        self.shiny = not self.shiny
        await self.refresh(interaction)

    @discord.ui.button(label="♂ Male", style=discord.ButtonStyle.secondary, row=1)
    async def gender_toggle(self, interaction, _button):
        self.female = not self.female
        await self.refresh(interaction)

    @discord.ui.button(label="🔀 Form", style=discord.ButtonStyle.secondary, row=1)
    async def form_cycle(self, interaction, _button):
        if len(self.forms) > 1:
            following = self.forms[(self.form_index() + 1) % len(self.forms)]
            self.pokedex_id = following[0]
            # A form is a different species row with its own entries, so the page resets
            # for the same reason it does when walking the national dex.
            self.page = 0
        await self.refresh(interaction)

    # --- flavour paging -----------------------------------------------
    @discord.ui.button(label="⏮", style=discord.ButtonStyle.secondary, row=2)
    async def previous_entry(self, interaction, _button):
        self.page = (self.page - 1) % max(1, self.pages)
        await self.refresh(interaction)

    @discord.ui.button(label="Entry 1/1", style=discord.ButtonStyle.secondary, row=2,
                       disabled=True)
    async def entry_count(self, interaction, _button):
        await interaction.response.defer()

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.secondary, row=2)
    async def next_entry(self, interaction, _button):
        self.page = (self.page + 1) % max(1, self.pages)
        await self.refresh(interaction)


class Dex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def render(self, pokedex_id, *, shiny=False, female=False, page=0):
        """
        Build the embed for one species. Returns (embed, file, forms, page count).

        Everything is read here in one connection rather than by the View, so a button
        press is one open-and-close and the View holds no database state at all.
        """
        async with aiosqlite.connect(f"file:{DB_FILE}?mode=ro", uri=True) as db:
            async with db.execute(
                    "SELECT name, form_type, height, weight, gender_rate, "
                    "is_legendary, is_mythical, standard_abilities, hidden_ability "
                    "FROM base_pokemon_species WHERE pokedex_id = ?",
                    (pokedex_id,)) as cursor:
                row = await cursor.fetchone()
            if not row:
                return None, None, [], 1
            (name, form_type, height, weight, gender_rate,
             legendary, mythical, standards, hidden) = row

            forms = await D.form_siblings(db, pokedex_id)
            base = await D.base_species(db, pokedex_id)
            stats, total = await D.base_stats(db, pokedex_id)
            types = await D.species_types(db, pokedex_id)

            # A FORM BORROWS ITS SPECIES' FACTS. Dex data is keyed on the base species,
            # and the form rows in base_pokemon_species carry defaults rather than real
            # values for anything that belongs to the species rather than the shape -
            # Wormadam Sandy's row says gender_rate 4 when every Wormadam is female.
            base_name = name
            if base != pokedex_id:
                async with db.execute(
                        "SELECT name, gender_rate FROM base_pokemon_species "
                        "WHERE pokedex_id = ?", (base,)) as cursor:
                    parent = await cursor.fetchone()
                if parent:
                    base_name, gender_rate = parent[0], parent[1]

            facts = await D.dex_facts(db, base)
            entries = await D.flavour_entries(db, base)
            names = await names_for_species(db, base_name)
            # evolution_family returns (ids, the name it resolved) - the second half is
            # for callers that had to normalise a typed name, and is not wanted here.
            family, _resolved = await evolution_family(db, base_name)
            stages = await D.evolution_stages(db, family)

        pages = max(1, len(entries))
        page = page % pages if entries else 0
        self_id = pokedex_id

        embed = discord.Embed(colour=DEX_COLOUR)
        number = base if base <= LAST_NATIONAL else pokedex_id
        embed.title = f"#{number:04d}  ·  {pretty_species(name)}"
        if facts.get('genus'):
            embed.set_author(name=facts['genus'])

        if entries:
            text, versions = entries[page]
            embed.description = trim(
                f"*{text}*\n​\n— **{D.describe_versions(versions)}**",
                DESCRIPTION_LIMIT)
        else:
            embed.description = ("*No field notes have been filed for this specimen.*"
                                 "\n​\nRun `migrate_dex_data.py` to load them.")

        attachment = None
        path = resolve_sprite(pokedex_id, shiny=shiny,
                              gender='F' if female else 'M', style=HOME)
        if path:
            filename = sprite_attachment_name(
                pokedex_id, shiny=shiny, gender='F' if female else 'M')
            attachment = discord.File(path, filename=filename)
            embed.set_image(url=f"attachment://{filename}")

        embed.add_field(name="Typing", value=type_badges(types) or "—", inline=True)
        region = region_of_generation(facts.get('generation'))
        embed.add_field(name="Region",
                        value=region_label(region) if region else "—", inline=True)
        embed.add_field(
            name="Spawnable",
            value="✅ Yes" if form_type in SPAWNABLE_FORM_TYPES else "🚫 No",
            inline=True)

        embed.add_field(name="Height", value=D.describe_height(height), inline=True)
        embed.add_field(name="Weight", value=D.describe_weight(weight), inline=True)
        embed.add_field(name="Gender Ratio",
                        value=D.describe_gender_ratio(gender_rate), inline=True)

        embed.add_field(name="Egg Groups",
                        value=D.describe_egg_groups(facts.get('egg_groups')),
                        inline=True)
        embed.add_field(name="Hatch Time",
                        value=D.describe_hatch(facts.get('hatch_counter')), inline=True)
        rarity = ("💫 Mythical" if mythical else "👑 Legendary" if legendary
                  else "🍼 Baby" if facts.get('is_baby') else "—")
        embed.add_field(name="Standing", value=rarity, inline=True)

        embed.add_field(
            name=f"Base Stats  ·  {total} total",
            value="\n".join(f"`{label:<3} {value:>3}` {D.stat_bar(value)}"
                            for label, value in stats) or "—",
            inline=False)

        if stages:
            # Siblings on one rung are joined with a slash - Eevee's nine, or a species
            # and its regional twin - and the rungs with arrows.
            line = "  →  ".join(
                " / ".join(
                    f"**{pretty_species(species)}**"
                    if pokedex_id in (self_id, base) else pretty_species(species)
                    for pokedex_id, species in rung)
                for rung in stages)
            embed.add_field(name="Evolution Line", value=trim(line, 1024), inline=False)

        if names:
            # Stored lowercase, because that is how `!catch` normalises what a player
            # types. Title-cased only here, where it is read rather than matched - kana
            # and hangul are unaffected by .title(), and the Latin ones need it.
            embed.add_field(
                name="Also Known As",
                value=trim(" • ".join(
                    f"{LANGUAGES[tag]['emoji']} {value.title()}"
                    for tag, value in names.items()), 1024),
                inline=False)

        abilities = [a.strip() for a in str(standards or '').split(',') if a.strip()]
        real_hidden = str(hidden or '').strip()
        shown = [a.replace('-', ' ').title() for a in abilities]
        if real_hidden and real_hidden.lower() != 'none':
            shown.append(f"{real_hidden.replace('-', ' ').title()} *(hidden)*")
        if shown:
            embed.add_field(name="Abilities", value=" • ".join(shown), inline=False)

        footer = []
        if len(forms) > 1:
            footer.append(f"{len(forms)} forms")
        if facts.get('has_gender_differences'):
            footer.append("the sexes look different")
        if shiny:
            footer.append("shiny")
        embed.set_footer(text="  ·  ".join(footer) if footer
                         else "KyuDex field archive")
        return embed, attachment, forms, pages

    @commands.command(name="dex", aliases=["pokedex", "entry"])
    @checks.has_started()
    @checks.is_authorized()
    async def dex(self, ctx, *, species: str = None):
        """
        Look a species up. `!dex bulbasaur`, or `!dex 25`.

        The buttons walk the national dex, cycle a species' forms, and page through its
        field notes from every game that recorded one.
        """
        if not species:
            return await ctx.send(
                "🔬 Which specimen? `!dex bulbasaur`, or `!dex 25`.")

        typed = species.strip()
        pokedex_id = None
        if typed.isdigit():
            pokedex_id = int(typed)
            if not 1 <= pokedex_id <= LAST_NATIONAL:
                return await ctx.send(
                    f"🔬 The national dex runs from #0001 to #{LAST_NATIONAL:04d}.")
        else:
            canonical = resolve_species(typed)
            if not canonical:
                suggestions = suggest_species(typed)[:MAX_CHOICES]
                hint = ("  Did you mean: "
                        + ", ".join(f"`{s}`" for s in suggestions[:5])
                        if suggestions else "")
                return await ctx.send(
                    f"🔬 No specimen called `{typed}` is on file.{hint}")
            async with aiosqlite.connect(f"file:{DB_FILE}?mode=ro", uri=True) as db:
                async with db.execute(
                        "SELECT pokedex_id FROM base_pokemon_species WHERE name = ?",
                        (canonical,)) as cursor:
                    found = await cursor.fetchone()
            pokedex_id = found[0] if found else None

        if not pokedex_id:
            return await ctx.send(f"🔬 No specimen called `{typed}` is on file.")

        view = DexView(self, ctx.author.id, pokedex_id)
        embed, attachment = await view.refresh()
        if embed is None:
            return await ctx.send("🔬 That specimen has no record in the archive.")
        await ctx.send(embed=embed, view=view,
                       file=attachment if attachment else discord.utils.MISSING)


async def setup(bot):
    await bot.add_cog(Dex(bot))
