"""
`!dex` - everything this world knows about a species, on one card.

**IT NEVER WRITES.** It reads caught_pokemon now, to say how many of the species on
screen the trainer actually holds, but nothing in this cog writes anything anywhere. That
is what makes the buttons safe to leave live: the worst a stale card can do is show
somebody a Charizard, or a catch tally from ninety seconds ago.

**IT IS A CONTAINER, NOT AN EMBED.** The embed carried eleven fields and showed all of
them at once, so the base stats, the evolution line and the international names were
always on screen whether or not anybody wanted them. The five panels here open one at a
time, and pressing the open one closes it - see utils/cards.py, which owns that machinery
and shares it with `!view`.

**THE ENTRY IS PAGED, NOT PICKED.** A species averages fourteen flavour entries across
thirty-five games and most are word-for-word repeats, so `utils.dex.flavour_entries`
groups them and the ⏮/⏭ pair walks the groups. Bulbasaur has 22 entries and 12 pages.

**THE FORM BUTTON WALKS species_forms, NOT THE NAME.** Splitting a species name on its
first hyphen works for `rotom-heat` and destroys `mr-mime`, `ho-oh`, `type-null` and
`jangmo-o`; the mapping is imported by migrate_dex_data.py instead.

**A THINNER DEX IS BETTER THAN A CRASH.** Every dex table is optional. On a database that
has not had migrate_dex_data.py applied, the flavour text, egg groups, hatch counter and
genus simply do not appear and everything else still works.
"""
import discord
from discord import ui
from discord.ext import commands

import aiosqlite

from utils.cards import TabbedCard, card_button, divider, row, text, trim
from utils.constants import DB_FILE, type_badges, SPAWNABLE_FORM_TYPES
from utils.db_manager import evolution_family
from utils.regions import region_label, region_of_generation
from utils.species import MAX_CHOICES, pretty_species, resolve_species, suggest_species
from utils.sprites import HOME, resolve_sprite, sprite_attachment_name
from utils.translations import LANGUAGES, names_for_species
from utils import checks
from utils import abilities as A
from utils import dex as D
from utils import items as I

DEX_COLOUR = discord.Colour(0x41F097)
SHINY_GOLD = discord.Colour(0xF1C40F)

# The national dex stops at 1025; everything above that id in base_pokemon_species is a
# form and has no number of its own.
LAST_NATIONAL = 1025


class DexCard(TabbedCard):
    """
    The card. Holds an id, three toggles and which panel is open - and no cached data.

    Every press re-reads the database, so a dex left open while a migration is applied
    starts showing the new data rather than a snapshot from before it.
    """

    TABS = {
        'notes':     ("Notes", "📖"),
        'stats':     ("Stats", "📊"),
        'biology':   ("Biology", "🧬"),
        'evolution': ("Evolution", "🌳"),
        'names':     ("Names", "🌐"),
    }
    NOT_YOURS = "🔬 That is somebody else's dex. Run `!dex` for your own."

    def __init__(self, cog, owner_id, pokedex_id, *, shiny=False, female=False, page=0):
        super().__init__(owner_id, tab='notes')
        self.cog = cog
        self.pokedex_id = pokedex_id
        self.shiny = shiny
        self.female = female
        self.page = page
        self.data = None
        self.sprite_path = None

    # ------------------------------------------------------------------
    async def load(self):
        """Re-read everything for the current id. Returns the sprite file, or None."""
        self.data = await self.cog.read(self.pokedex_id, str(self.owner_id))
        if self.data is None:
            return None
        self.page = self.page % max(1, len(self.data['entries'])) if self.data['entries'] else 0
        return self.sprite_file()

    def sprite_file(self):
        """Resolve the picture ONCE and remember the path.

        The header has to know whether there is one - twelve species have no art in any
        style, and a media block pointing at an attachment that was never sent renders as
        a broken image - and asking the resolver again to find that out would walk the
        whole fallback chain twice for an answer already in hand.
        """
        self.sprite_path = resolve_sprite(self.pokedex_id, shiny=self.shiny,
                                          gender='F' if self.female else 'M', style=HOME)
        if not self.sprite_path:
            return None
        return discord.File(self.sprite_path, filename=self.sprite_name())

    def sprite_name(self):
        return sprite_attachment_name(self.pokedex_id, shiny=self.shiny,
                                      gender='F' if self.female else 'M')

    async def reload(self, interaction):
        """Re-read and redraw, replacing the picture - for every press that changes it."""
        was = self.data
        attachment = await self.load()
        if self.data is None:
            # Only reachable if a species row went missing between two presses. Saying so
            # beats redrawing a header off nothing, which fails silently inside a
            # callback and looks to the reader like a dead button.
            self.data = was
            return await interaction.response.send_message(
                "🔬 That specimen has no record in the archive.", ephemeral=True)
        await self.redraw(interaction, attachments=[attachment] if attachment else [])

    def accent(self):
        return SHINY_GOLD if self.shiny else DEX_COLOUR

    def pages(self):
        return max(1, len(self.data['entries'])) if self.data else 1

    def form_index(self):
        for index, (pokedex_id, _name) in enumerate(self.data['forms']):
            if pokedex_id == self.pokedex_id:
                return index
        return 0

    def walk_from(self):
        """Which number the ◀ ▶ arrows step from.

        A form sits above 1025 and has no number of its own, so the arrows walk from the
        BASE species - otherwise ▶ off Rotom Heat asks for #10009 and finds nothing.
        """
        base = self.data['base'] if self.data else self.pokedex_id
        return base if base <= LAST_NATIONAL else LAST_NATIONAL

    # --- the card -----------------------------------------------------
    def header(self):
        """Number, name, portrait, standing - and what the reader already owns."""
        data = self.data
        facts = data['facts']
        number = data['base'] if data['base'] <= LAST_NATIONAL else data['pokedex_id']
        region = region_of_generation(facts.get('generation'))

        standing = ("💫 Mythical" if data['mythical'] else
                    "👑 Legendary" if data['legendary'] else
                    "🍼 Baby" if facts.get('is_baby') else None)
        strip = [type_badges(data['types']) or "—"]
        if region:
            strip.append(region_label(region))
        if standing:
            strip.append(standing)
        strip.append("✅ Spawnable" if data['form_type'] in SPAWNABLE_FORM_TYPES
                     else "🚫 Not spawnable")

        marks = []
        if self.shiny:
            marks.append("✨ shiny")
        if facts.get('has_gender_differences'):
            marks.append("♀ female art" if self.female else "♂ male art")
        if len(data['forms']) > 1:
            marks.append(f"{len(data['forms'])} forms")
        if data['entries']:
            # Which entry, but only while the notes are open - a counter for a panel that
            # is closed points at something the reader cannot see. Closed, it says how
            # many are in there, which is the reason to open it.
            marks.append(f"entry {self.page + 1} of {len(data['entries'])}"
                         if self.tab == 'notes'
                         else f"{len(data['entries'])} field notes")

        blocks = [text(f"# #{number:04d}  ·  {pretty_species(data['name'])}")]
        if facts.get('genus'):
            blocks.append(text(f"-# {facts['genus']}"))
        blocks.append(divider(visible=False))

        if self.sprite_path:
            blocks.append(discord.ui.MediaGallery(discord.MediaGalleryItem(
                f"attachment://{self.sprite_name()}",
                # Alt text, so the card is not a blank rectangle to a screen reader.
                description=self.sprite_name())))
        else:
            # Twelve species have no art in any style. Saying so beats a broken image.
            blocks.append(text("-# *No archive imagery for this form.*"))

        blocks.append(text("  ·  ".join(strip)
                           + (f"\n-# {'  ·  '.join(marks)}" if marks else "")))
        blocks.append(text(
            f"🎒 **Your records:** {D.describe_ownership(data['owned'], self.pokedex_id, data['forms'])}"))
        return blocks

    def panel(self, tab):
        return {
            'notes': self.notes_panel,
            'stats': self.stats_panel,
            'biology': self.biology_panel,
            'evolution': self.evolution_panel,
            'names': self.names_panel,
        }[tab]()

    def notes_panel(self):
        entries = self.data['entries']
        if not entries:
            return [text("### 📖 Field Notes\n"
                         "*No field notes have been filed for this specimen.*\n"
                         "-# Run `migrate_dex_data.py` to load them.")]
        body, versions = entries[self.page % len(entries)]
        return [text(f"### 📖 Field Notes\n> *{body}*\n"
                     f"-# — **{D.describe_versions(versions)}**")]

    def stats_panel(self):
        stats, total = self.data['stats'], self.data['total']
        best = max(stats, key=lambda pair: pair[1]) if stats else None
        table = "\n".join(f"{label:<4}{value:>4}  {D.stat_bar(value)}"
                          for label, value in stats)
        tail = (f"-# Bars scale to {D.STAT_BAR_MAX} · strongest: **{best[0]} {best[1]}**"
                if best else "")
        return [text(f"### 📊 Base Stats  ·  {total} total\n```\n{table}\n```\n{tail}")]

    def biology_panel(self):
        data, facts = self.data, self.data['facts']
        abilities = [a.strip() for a in str(data['standards'] or '').split(',') if a.strip()]
        shown = [f"`{a.replace('-', ' ').title()}`" for a in abilities]
        hidden = str(data['hidden'] or '').strip()
        if hidden and hidden.lower() != 'none':
            shown.append(f"`{hidden.replace('-', ' ').title()}` *(hidden)*")
        happiness = facts.get('base_happiness')
        return [text(
            "### 🧬 Biology\n"
            f"📏 **Height:** {D.describe_height(data['height'])}\n"
            f"⚖️ **Weight:** {D.describe_weight(data['weight'])}\n"
            f"⚧ **Gender Ratio:** {D.describe_gender_ratio(data['gender_rate'])}\n"
            f"🥚 **Egg Groups:** {D.describe_egg_groups(facts.get('egg_groups'))}\n"
            f"⏳ **Hatch Time:** {D.describe_hatch(facts.get('hatch_counter'))}\n"
            f"🤝 **Base Happiness:** {happiness if happiness is not None else '—'}\n"
            f"🧠 **Abilities:** {' • '.join(shown) if shown else '—'}")]

    def evolution_panel(self):
        """The line, and - the point of the panel - how each arrow is actually walked."""
        data = self.data
        lines = []
        if data['stages']:
            # Siblings on one rung joined with a slash - Eevee's nine, or a species and
            # its regional twin - and the rungs with arrows. The one on screen is bolded.
            shape = "  →  ".join(
                " / ".join(f"**{pretty_species(species)}**"
                           if pokedex_id in (data['pokedex_id'], data['base'])
                           else pretty_species(species)
                           for pokedex_id, species in rung)
                for rung in data['stages'])
            lines.append(shape)

        routes = D.evolution_route_lines(
            data['routes'], data['family_names'],
            highlight=(data['pokedex_id'], data['base']),
            order=D.stage_index(data['stages']))
        if routes:
            lines.append("\n".join(f"• {route}" for route in routes))
        elif not lines:
            return [text("### 🌳 Evolution\n*This species neither evolves nor is "
                         "evolved into.*")]

        if any(D.NO_ROUTE in route for route in routes):
            lines.append("-# A route with no way to fire is one the games settle with "
                         "something this world has no equivalent of.")
        return [text(trim("### 🌳 Evolution\n" + "\n\n".join(lines)))]

    def names_panel(self):
        data = self.data
        lines = []
        if len(data['forms']) > 1:
            forms = " • ".join(
                f"**{pretty_species(name)}**" if pokedex_id == data['pokedex_id']
                else pretty_species(name)
                for pokedex_id, name in data['forms'])
            lines.append(f"🔀 **Forms** ({len(data['forms'])})\n{forms}")
        if data['names']:
            # Stored lowercase, because that is how `!catch` normalises what a player
            # types. Title-cased only here, where it is read rather than matched - kana
            # and hangul are unaffected by .title(), and the Latin ones need it.
            abroad = " • ".join(f"{LANGUAGES[tag]['emoji']} {value.title()}"
                                for tag, value in data['names'].items())
            lines.append(f"🌐 **Also Known As**\n{abroad}")
        return [text(trim("### 🌐 Names and Forms\n"
                          + ("\n\n".join(lines) if lines
                             else "*Nothing else on file for this species.*")))]

    def controls(self):
        data = self.data
        forms = data['forms']
        genderless = data['gender_rate'] is None or data['gender_rate'] < 0
        walk = self.walk_from()

        rows = [
            row(
                card_button("Shiny", emoji="✨", callback=self.toggle_shiny,
                            style=(discord.ButtonStyle.success if self.shiny
                                   else discord.ButtonStyle.secondary)),
                card_button("♀ Female" if self.female else "♂ Male",
                            # Toggling sex on a genderless species would ask for art that
                            # cannot exist, and the label would be a lie either way round.
                            callback=self.toggle_female, disabled=genderless),
                card_button(f"Form {self.form_index() + 1}/{max(1, len(forms))}",
                            emoji="🔀", callback=self.cycle_form,
                            disabled=len(forms) < 2),
            ),
            row(
                card_button(f"◀ #{max(1, walk - 1):04d}", callback=self.previous_species,
                            style=discord.ButtonStyle.primary, disabled=walk <= 1),
                card_button(f"#{min(LAST_NATIONAL, walk + 1):04d} ▶",
                            callback=self.next_species,
                            style=discord.ButtonStyle.primary,
                            disabled=walk >= LAST_NATIONAL),
            ),
        ]

        # Flavour paging, and only while the notes are on screen: the entry counter names
        # something the reader cannot see once the panel is shut.
        if self.tab == 'notes' and self.pages() > 1:
            rows.append(row(
                card_button("⏮", callback=self.previous_entry),
                card_button(f"Entry {self.page + 1}/{self.pages()}", disabled=True),
                card_button("⏭", callback=self.next_entry),
            ))
        return rows

    # --- presses ------------------------------------------------------
    async def toggle_shiny(self, interaction):
        self.shiny = not self.shiny
        await self.reload(interaction)

    async def toggle_female(self, interaction):
        self.female = not self.female
        await self.reload(interaction)

    async def cycle_form(self, interaction):
        forms = self.data['forms']
        if len(forms) > 1:
            self.pokedex_id = forms[(self.form_index() + 1) % len(forms)][0]
            # A form is a different species row with its own entries, so the page resets
            # for the same reason it does when walking the national dex.
            self.page = 0
        await self.reload(interaction)

    async def previous_species(self, interaction):
        await self.jump(interaction, self.walk_from() - 1)

    async def next_species(self, interaction):
        await self.jump(interaction, self.walk_from() + 1)

    async def jump(self, interaction, pokedex_id):
        """Move to another species, resetting everything that belonged to the last one."""
        self.pokedex_id = max(1, min(LAST_NATIONAL, pokedex_id))
        # The page and the form belong to the species that was on screen. Carrying them
        # over would open Ivysaur on "entry 9 of 12" when it has four.
        self.page = 0
        await self.reload(interaction)

    async def previous_entry(self, interaction):
        self.page = (self.page - 1) % self.pages()
        await self.redraw(interaction)

    async def next_entry(self, interaction):
        self.page = (self.page + 1) % self.pages()
        await self.redraw(interaction)


class AbilityCard(TabbedCard):
    """
    One trait: what it does, and every specimen that can have it.

    **NO CACHED DATA**, the same rule `DexCard` follows: every press re-reads, so a card
    left open while `migrate_ability_dex.py` runs starts showing the descriptions rather
    than a snapshot from before them.

    The roster half comes from `base_pokemon_species`, which has always had it. The
    description comes from `base_abilities`, which the migration writes - and if that
    table is not there, the card says so and still lists the bearers.
    """

    TABS = {
        'effect':  ("Full rules", "📜"),
        'bearers': ("Who has it", "🧬"),
    }
    ACCENT = DEX_COLOUR

    def __init__(self, owner_id, name, **kwargs):
        super().__init__(owner_id, **kwargs)
        self.name = name
        self.described = None
        self.standard = []
        self.hidden = []

    async def load(self):
        async with aiosqlite.connect(f"file:{DB_FILE}?mode=ro", uri=True) as db:
            self.described = await A.describe(db, self.name)
            self.standard, self.hidden = await A.bearers(db, self.name)
        return self

    def display(self):
        return (self.described or {}).get('display') or A.pretty_ability(self.name)

    def header(self):
        title = f"### 🧬 {self.display()}"
        generation = (self.described or {}).get('generation')
        if generation:
            title += f"  ·  *Gen {generation}*"

        lines = [title]
        short = (self.described or {}).get('short_effect')
        if short:
            lines.append(short)
        else:
            # NOT AN ERROR, and not a reason to refuse the lookup. The species table
            # knows this trait exists; only the description is missing.
            lines.append("*No description on file — run `migrate_ability_dex.py`.*")

        lines.append(f"-# {len(self.standard)} species carry it, "
                     f"{len(self.hidden)} as a hidden trait.")
        return [text("\n".join(lines))]

    def panel(self, tab):
        if tab == 'effect':
            full = (self.described or {}).get('effect')
            if not full:
                return [text("### 📜 Full rules\n*Nothing on file for this trait.*")]
            return [text(f"### 📜 Full rules\n{full}")]

        if tab == 'bearers':
            return [text(self.bearer_list())]
        return []

    def bearer_list(self):
        """Both rosters, or a line saying there is nothing to show."""
        blocks = ["### 🧬 Who has it"]
        for label, names in (("Standard", self.standard), ("Hidden", self.hidden)):
            if not names:
                continue
            blocks.append(f"**{label}** ({len(names)})\n"
                          + ", ".join(pretty_species(n) for n in names))
        if len(blocks) == 1:
            # Reachable: an ability described by PokeAPI that nothing in this world has.
            blocks.append("*Nothing in this world carries it.*")
        return "\n\n".join(blocks)


class ItemCard(TabbedCard):
    """
    One item: what it does, what it costs, and what else sits on its shelf.

    **NO MIGRATION BEHIND THIS ONE.** Every one of the 460 catalogue entries already
    carries a description, and 311 already have a sprite on disk - so the PokeAPI table
    the trait dex needed would have bought nothing here but a second, competing
    description of the games rather than of this world. See `utils/items.py`.
    """

    TABS = {
        'shop':  ("Availability", "🪙"),
        'shelf': ("Same kind", "🗂️"),
    }
    ACCENT = DEX_COLOUR
    NOT_YOURS = "🎒 That is somebody else's catalogue. Run `!itemdex` for your own."

    def __init__(self, owner_id, key, **kwargs):
        super().__init__(owner_id, **kwargs)
        self.key = key
        self.entry = I.entry(key)
        self.picture = I.sprite_path(key)

    def attachment(self):
        """The item's picture, or None - 149 of them are this world's own inventions."""
        if not self.picture:
            return None
        return discord.File(self.picture, filename=self.sprite_name())

    def sprite_name(self):
        return f"item_{self.key.replace('-', '_')}.png"

    def header(self):
        label, emoji = I.category_of(self.key)
        items = []
        if self.picture:
            items.append(ui.MediaGallery(discord.MediaGalleryItem(
                f"attachment://{self.sprite_name()}",
                description=f"{I.pretty_item(self.key)}.")))
        items.append(text(
            f"### {self.entry.get('emoji') or emoji} {I.pretty_item(self.key)}\n"
            f"{self.entry.get('desc') or '*Nothing on file.*'}\n"
            f"-# {emoji} {label} · `{self.key}`"))
        return items

    def panel(self, tab):
        if tab == 'shop':
            return [text("### 🪙 Availability\n" + "\n".join(I.availability(self.key)))]
        if tab == 'shelf':
            neighbours = I.shelf(self.key)
            if not neighbours:
                return [text("### 🗂️ Same kind\n*Nothing else on this shelf.*")]
            label, _emoji = I.category_of(self.key)
            return [text(f"### 🗂️ Same kind\n**{label}** ({len(neighbours)} shown)\n"
                         + ", ".join(f"`{k}`" for k in neighbours))]
        return []


class Dex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def read(self, pokedex_id, user_id):
        """
        Everything the card can show about one species, in one connection.

        Read here rather than panel by panel for the reason the card gives: a button press
        should be one open-and-close, and a panel that opened its own connection would
        read the database five times to draw one message.
        """
        async with aiosqlite.connect(f"file:{DB_FILE}?mode=ro", uri=True) as db:
            async with db.execute(
                    "SELECT name, form_type, height, weight, gender_rate, "
                    "is_legendary, is_mythical, standard_abilities, hidden_ability "
                    "FROM base_pokemon_species WHERE pokedex_id = ?",
                    (pokedex_id,)) as cursor:
                found = await cursor.fetchone()
            if not found:
                return None
            (name, form_type, height, weight, gender_rate,
             legendary, mythical, standards, hidden) = found

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
            routes = await D.evolution_routes(db, family)

            # Every species the routes might name, including the ones a rule points AT
            # that the family walk never reached - a Kubfu's two Urshifu are forms, and
            # `evolution_family` walks species.
            wanted = set(family) | {route['evolved'] for route in routes} | {route['base']
                                                                             for route in routes}
            family_names = await self.names_of(db, wanted)

            # WHAT THE READER OWNS, counted across every shape of the species rather than
            # only the one on screen: a Rotom stored under rotom-heat's own id would
            # otherwise read as a species they had never caught.
            owned = await D.owned_counts(
                db, user_id, {pokedex_id, base} | {form for form, _n in forms})

        return {
            'pokedex_id': pokedex_id, 'name': name, 'base': base, 'form_type': form_type,
            'height': height, 'weight': weight, 'gender_rate': gender_rate,
            'legendary': legendary, 'mythical': mythical,
            'standards': standards, 'hidden': hidden,
            'forms': forms, 'stats': stats, 'total': total, 'types': types,
            'facts': facts, 'entries': entries, 'names': names, 'stages': stages,
            'routes': routes, 'family_names': family_names, 'owned': owned,
        }

    async def names_of(self, db, ids):
        """{pokedex_id: printable name} for whatever ids the routes mention."""
        ids = [int(i) for i in ids if i is not None]
        if not ids:
            return {}
        placeholders = ','.join('?' * len(ids))
        async with db.execute(
                f"SELECT pokedex_id, name FROM base_pokemon_species "
                f"WHERE pokedex_id IN ({placeholders})", tuple(ids)) as cursor:
            return {row[0]: pretty_species(row[1]) for row in await cursor.fetchall()}

    async def resolve(self, typed):
        """A typed species or number as (pokedex_id, complaint)."""
        typed = (typed or '').strip()
        if not typed:
            return None, "🔬 Which specimen? `!dex bulbasaur`, or `!dex 25`."

        if typed.isdigit():
            pokedex_id = int(typed)
            if not 1 <= pokedex_id <= LAST_NATIONAL:
                return None, (f"🔬 The national dex runs from #0001 to "
                              f"#{LAST_NATIONAL:04d}.")
            return pokedex_id, None

        canonical = resolve_species(typed)
        if not canonical:
            suggestions = suggest_species(typed)[:MAX_CHOICES]
            hint = ("  Did you mean: " + ", ".join(f"`{s}`" for s in suggestions[:5])
                    if suggestions else "")
            return None, f"🔬 No specimen called `{typed}` is on file.{hint}"

        async with aiosqlite.connect(f"file:{DB_FILE}?mode=ro", uri=True) as db:
            async with db.execute(
                    "SELECT pokedex_id FROM base_pokemon_species WHERE name = ?",
                    (canonical,)) as cursor:
                found = await cursor.fetchone()
        if not found:
            return None, f"🔬 No specimen called `{typed}` is on file."
        return found[0], None

    @commands.command(name="dex", aliases=["pokedex", "entry"])
    @checks.has_started()
    @checks.is_authorized()
    async def dex(self, ctx, *, species: str = None):
        """
        Look a species up. `!dex bulbasaur`, or `!dex 25`.

        The buttons open the five panels, walk the national dex, cycle a species' forms,
        swap the artwork, and page through the field notes from every game that recorded
        one.
        """
        pokedex_id, complaint = await self.resolve(species)
        if complaint:
            return await ctx.send(complaint)

        card = DexCard(self, ctx.author.id, pokedex_id)
        attachment = await card.load()
        if card.data is None:
            return await ctx.send("🔬 That specimen has no record in the archive.")

        await ctx.send(view=card.rebuild(),
                       file=attachment if attachment else discord.utils.MISSING)

    @commands.command(name="abilitydex", aliases=["ability", "abilities", "trait"])
    @checks.has_started()
    @checks.is_authorized()
    async def abilitydex(self, ctx, *, ability: str = None):
        """
        Look a trait up. `!abilitydex levitate`.

        The buttons open its full rules and the list of every specimen that can have it -
        which the database has always known and nothing could ask until now.
        """
        name, complaint = await A.lookup(ability)
        if complaint:
            return await ctx.send(complaint)

        card = await AbilityCard(ctx.author.id, name).load()
        await ctx.send(view=card.rebuild())

    # NOT `gear`: `!backpack` in cogs/economy.py already answers to it, and discord.py
    # refuses the whole extension rather than the one clash - the cog stops loading.
    @commands.command(name="itemdex", aliases=["iteminfo"])
    @checks.has_started()
    @checks.is_authorized()
    async def itemdex(self, ctx, *, item: str = None):
        """
        Look an item up. `!itemdex leftovers`.

        The buttons say how it is come by - bought, or earned from a directive - and what
        else sits on the same shelf, which is the only sane way to browse four hundred.
        """
        key, complaint = I.resolve(item)
        if complaint:
            return await ctx.send(complaint)

        card = ItemCard(ctx.author.id, key)
        attachment = card.attachment()
        await ctx.send(view=card.rebuild(),
                       file=attachment if attachment else discord.utils.MISSING)


async def setup(bot):
    await bot.add_cog(Dex(bot))
