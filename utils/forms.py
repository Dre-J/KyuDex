"""
The thirteen form-change items, and the one place that knows what they do.

Three of them are HELD items and are not really this module's business: the Adamant
Crystal, Lustrous Globe and Griseous Core reshape their holder on entry and lift two of
its elements, which is the Griseous Orb's machinery exactly. They are rows in
SPECIES_FORM_ITEMS and SPECIES_TYPE_BOOST_ITEMS in utils/constants.py, and the battle
engine already reads both tables.

The other ten are used from the bag, out of battle, and come in three shapes:

  RING    - a closed loop of forms the specimen moves between. Deoxys' four, Rotom's
            six, and the simple two-state pairs (Gracidea, Reveal Glass, Prison Bottle).
  GRID    - Zygarde, which is two independent axes: 10%/50% and Aura Break/Power
            Construct. Four species names for four combinations, so a ring cannot
            express it - switching ability must not also change size.
  FUSION  - two specimens become one. Kyurem, Necrozma and Calyrex.

**FUSION HAS TO GIVE THE OTHER SPECIMEN BACK.** Kyurem-White is a Kyurem that ate a
Reshiram, and that Reshiram had its own IVs, EVs, nickname, ribbons and moves. Deleting
it would be the easy implementation and an unforgivable one. It is moved OUT of
caught_pokemon into `fused_specimens`, verbatim, and moved back on separation.

Moving it out rather than flagging it in place is deliberate. There are 66 places in
this repo that SELECT from caught_pokemon, and a "hidden" specimen would have to be
excluded from every one of them - a filter missed in any single place means a fused
Reshiram that can still be traded, released or sent into battle. A row that is not in
the table cannot be any of those things, and no existing query changed.

**THE FUSION RECORD FOLLOWS THE HOST, NOT THE OWNER.** `fused_specimens` records no
user_id; the owner is whoever owns the host right now. So a fused Kyurem can be traded
like anything else and the new owner separates it to get the Reshiram - and none of the
nine ownership-transfer sites in the repo needed a line changed. The one path that DOES
need a guard is release, because deleting the host would orphan what is inside it.
"""
import json

RING = 'ring'
GRID = 'grid'
FUSION = 'fusion'

# The column `fused_specimens` parks an absorbed specimen in.
FUSION_TABLE = 'fused_specimens'

# Columns never copied back out of a stored payload: the id is the row's identity and the
# owner is taken from the host, so that a traded fusion separates to the right trainer.
NOT_RESTORED = ('user_id',)


FORM_ITEMS = {
    # ==========================================
    # RINGS
    # ==========================================
    'meteorite': {
        'kind': RING,
        'label': 'Meteorite',
        'emoji': '☄️',
        'desc': "Shifts Deoxys between its Normal, Attack, Defense and Speed Formes.",
        'rings': (('deoxys-normal', 'deoxys-attack', 'deoxys-defense', 'deoxys-speed'),),
        'flavour': "the meteorite pulses, and {name} rearranges itself",
    },
    'rotom-catalog': {
        'kind': RING,
        'label': 'Rotom Catalog',
        'emoji': '📖',
        'desc': "Lets Rotom possess a Heat, Wash, Frost, Fan or Mow appliance.",
        'rings': (('rotom', 'rotom-heat', 'rotom-wash', 'rotom-frost', 'rotom-fan',
                   'rotom-mow'),),
        'flavour': "{name} leaps into a new appliance",
        # EACH APPLIANCE OWNS ONE MOVE. Overheat belongs to the oven, Leaf Storm to the
        # mower, Blizzard to the fridge, Air Slash to the fan, Hydro Pump to the washer -
        # and the move is the appliance, not the ghost. Without pruning, a player could
        # tour the catalogue collecting all five and end up with a Rotom-Heat holding
        # Leaf Storm, which no form of Rotom can learn.
        #
        # Measured against species_movepool, switching appliance drops exactly one move,
        # and moving from base Rotom into any appliance drops none - base Rotom's 66
        # moves are a subset of every appliance's 67.
        'prunes_moves': True,
    },
    'gracidea': {
        'kind': RING,
        'label': 'Gracidea',
        'emoji': '💐',
        'desc': "Turns Shaymin between its Land and Sky Formes.",
        'rings': (('shaymin-land', 'shaymin-sky'),),
        'flavour': "the flowers open, and {name} answers",
    },
    'reveal-glass': {
        'kind': RING,
        'label': 'Reveal Glass',
        'emoji': '🪞',
        'desc': "Turns Tornadus, Thundurus, Landorus or Enamorus between their "
                "Incarnate and Therian Formes.",
        'rings': (('tornadus-incarnate', 'tornadus-therian'),
                  ('thundurus-incarnate', 'thundurus-therian'),
                  ('landorus-incarnate', 'landorus-therian'),
                  ('enamorus-incarnate', 'enamorus-therian')),
        'flavour': "the glass shows {name} its true shape",
    },
    'prison-bottle': {
        'kind': RING,
        'label': 'Prison Bottle',
        'emoji': '🏺',
        'desc': "Releases Hoopa's true power - and seals it away again.",
        # A ring rather than the one-way trip the games make it, because the games undo
        # it after three days and KyuDex has nothing that ticks. A door that only opens
        # is a worse deal than the one Hoopa actually gets.
        'rings': (('hoopa', 'hoopa-unbound'),),
        'flavour': "the seal on the bottle gives way",
    },

    # ==========================================
    # THE GRID
    # ==========================================
    'zygarde-cube': {
        'kind': GRID,
        'label': 'Zygarde Cube',
        'emoji': '🟩',
        'desc': "Reassembles Zygarde between 10% and 50%, switches it between Aura "
                "Break and Power Construct, and teaches it the three moves only the "
                "Cube can.",
        # (size, ability) -> species. Written out because the four names are not
        # derivable from each other: `zygarde-50` carries no suffix while
        # `zygarde-50-power-construct` does, and `zygarde-10` is id 10181 while
        # `zygarde-10-power-construct` is 10118.
        'axes': ('size', 'ability'),
        'grid': {
            ('10', 'aura-break'): 'zygarde-10',
            ('50', 'aura-break'): 'zygarde-50',
            ('10', 'power-construct'): 'zygarde-10-power-construct',
            ('50', 'power-construct'): 'zygarde-50-power-construct',
        },
        # The movepool already records these three against `learn_method = 'zygarde-cube'`
        # - the data has been sitting there unreachable, exactly like the Technical
        # Records were. This is the door.
        'teaches': 'zygarde-cube',
        'flavour': "the Cube's cells rearrange",
    },

    # ==========================================
    # FUSIONS
    # ==========================================
    'dna-splicers': {
        'kind': FUSION,
        'label': 'DNA Splicers',
        'emoji': '🧬',
        'desc': "Fuses Kyurem with Reshiram or Zekrom, and separates them again.",
        'host': 'kyurem',
        'fusions': {'reshiram': 'kyurem-white', 'zekrom': 'kyurem-black'},
        'flavour': "{host} and {partner} are spliced together",
    },
    'n-lunarizer': {
        'kind': FUSION,
        'label': 'N-Lunarizer',
        'emoji': '🌙',
        'desc': "Fuses Necrozma with Lunala into Dawn Wings, and separates them again.",
        'host': 'necrozma',
        'fusions': {'lunala': 'necrozma-dawn'},
        'flavour': "{host} draws {partner} into itself",
    },
    'n-solarizer': {
        'kind': FUSION,
        'label': 'N-Solarizer',
        'emoji': '☀️',
        'desc': "Fuses Necrozma with Solgaleo into Dusk Mane, and separates them again.",
        'host': 'necrozma',
        'fusions': {'solgaleo': 'necrozma-dusk'},
        'flavour': "{host} draws {partner} into itself",
    },
    'reins-of-unity': {
        'kind': FUSION,
        'label': 'Reins of Unity',
        'emoji': '🎠',
        'desc': "Lets Calyrex ride Glastrier or Spectrier, and dismount again.",
        'host': 'calyrex',
        'fusions': {'glastrier': 'calyrex-ice', 'spectrier': 'calyrex-shadow'},
        # THE ONE THAT PRUNES. A mounted Calyrex learns its steed's moves - Glacial
        # Lance, Chilling Neigh's whole repertoire - and on dismounting it cannot keep
        # them. 37 of Ice Rider's 104 moves are not in base Calyrex's 69.
        'prunes_moves': True,
        'flavour': "{host} takes up the reins, and {partner} answers",
    },
}

# The three that are HELD rather than used. Listed so that `!form` can say so instead of
# claiming no such item, and so the suite can assert the thirteen are all accounted for.
HELD_FORM_ITEMS = {
    'adamant-crystal': ('dialga', "Dialga takes its Origin Forme while holding this."),
    'lustrous-globe': ('palkia', "Palkia takes its Origin Forme while holding this."),
    'griseous-core': ('giratina-altered',
                      "Giratina takes its Origin Forme while holding this."),
}

MOVE_SLOTS = ('move_1', 'move_2', 'move_3', 'move_4')


def form_item(name):
    """The spec for a bag form item, or None."""
    return FORM_ITEMS.get(str(name or '').strip().lower())


def is_held_form_item(name):
    return str(name or '').strip().lower() in HELD_FORM_ITEMS


def ring_for(spec, species):
    """The ring this species belongs to under this item, or None."""
    species = str(species or '').strip().lower()
    for ring in spec.get('rings', ()):
        if species in ring:
            return ring
    return None


def ring_targets(spec, species):
    """Every OTHER form in the ring, in ring order. Empty if the item does not apply."""
    ring = ring_for(spec, species)
    if not ring:
        return []
    return [form for form in ring if form != str(species).strip().lower()]


def next_in_ring(spec, species):
    """The next form round the loop - what the item does when given no target."""
    ring = ring_for(spec, species)
    if not ring:
        return None
    return ring[(ring.index(str(species).strip().lower()) + 1) % len(ring)]


def grid_position(spec, species):
    """Where this species sits on the grid, as (size, ability), or None."""
    species = str(species or '').strip().lower()
    for position, name in spec.get('grid', {}).items():
        if name == species:
            return position
    return None


def grid_move(spec, species, axis, value):
    """
    The species one axis of the grid away, or None.

    Moving along `size` must leave `ability` alone and vice versa, which is the whole
    reason this is a grid and not two rings: a Zygarde told to change its ability must
    not also be resized.
    """
    position = grid_position(spec, species)
    if not position:
        return None
    axes = spec.get('axes', ())
    if axis not in axes:
        return None
    updated = list(position)
    updated[axes.index(axis)] = value
    return spec.get('grid', {}).get(tuple(updated))


def grid_options(spec, axis):
    """Every value one axis of the grid accepts, in the order it was written."""
    axes = spec.get('axes', ())
    if axis not in axes:
        return []
    index = axes.index(axis)
    seen = []
    for position in spec.get('grid', {}):
        if position[index] not in seen:
            seen.append(position[index])
    return seen


def fusion_targets(spec):
    """{partner species: what the pair becomes}."""
    return dict(spec.get('fusions', {}))


def fused_species(spec):
    """Every species that IS a fusion under this item."""
    return set(spec.get('fusions', {}).values())


def item_for_species(species):
    """
    Every bag item that could do something to this species, as a list of item keys.

    Used by `!form` when the player names a specimen and no item, so the refusal can say
    what WOULD work rather than only that this did not.
    """
    species = str(species or '').strip().lower()
    found = []
    for key, spec in FORM_ITEMS.items():
        if spec['kind'] == RING and ring_for(spec, species):
            found.append(key)
        elif spec['kind'] == GRID and grid_position(spec, species):
            found.append(key)
        elif spec['kind'] == FUSION and (species == spec['host']
                                         or species in fused_species(spec)
                                         or species in spec['fusions']):
            found.append(key)
    return found


# ==========================================
# THE DATABASE HALF
# ==========================================
async def species_row(db, name):
    """(pokedex_id, standard_abilities, hidden_ability) for a species name, or None."""
    async with db.execute(
            "SELECT pokedex_id, standard_abilities, hidden_ability "
            "FROM base_pokemon_species WHERE name = ?",
            (str(name or '').strip().lower(),)) as cursor:
        return await cursor.fetchone()


def ability_after_change(current, standards, hidden):
    """
    Which ability a specimen keeps when it changes form.

    A form change is not an ability change, so a legal ability is left alone - a
    Thundurus-Incarnate with Defiant keeps it. But most of these forms do not HAVE the
    ability the old one did: Therian Thundurus is Volt Absorb and nothing else, and
    leaving Defiant on it would be an ability that species cannot have. Anything not on
    the new form's list falls back to its first standard ability.
    """
    legal = [a.strip().lower() for a in str(standards or '').split(',') if a.strip()]
    real_hidden = str(hidden or '').strip().lower()
    if real_hidden and real_hidden != 'none':
        legal.append(real_hidden)
    current = str(current or '').strip().lower()
    if current and current in legal:
        return current
    return legal[0] if legal else current


async def apply_form(db, instance_id, species, current_ability=None):
    """
    Move one specimen to another form. Returns the new (pokedex_id, ability), or None.

    Does NOT commit - every caller here is part of a larger transaction, and a form
    change that half-happened is worse than one that did not.
    """
    row = await species_row(db, species)
    if not row:
        return None
    pokedex_id, standards, hidden = row
    ability = ability_after_change(current_ability, standards, hidden)
    await db.execute(
        "UPDATE caught_pokemon SET pokedex_id = ?, ability = ? WHERE instance_id = ?",
        (pokedex_id, ability, instance_id))
    return pokedex_id, ability


async def learnable_moves(db, pokedex_id):
    """Every move this species can learn by any route, as a set."""
    async with db.execute(
            "SELECT DISTINCT move_name FROM species_movepool WHERE pokedex_id = ?",
            (pokedex_id,)) as cursor:
        return {row[0] for row in await cursor.fetchall()}


async def moves_by_method(db, pokedex_id, method):
    """The moves this species learns by one named route, in name order."""
    async with db.execute(
            "SELECT DISTINCT move_name FROM species_movepool "
            "WHERE pokedex_id = ? AND learn_method = ? ORDER BY move_name",
            (pokedex_id, method)) as cursor:
        return [row[0] for row in await cursor.fetchall()]


async def prune_moves(db, instance_id, pokedex_id, fallback='tackle'):
    """
    Strip moves the specimen's NEW form cannot learn. Returns what was forgotten.

    Dismounting Calyrex is the only thing that needs this, and it needs it badly: a
    Glacial Lance on a base Calyrex is a move that species has no route to at all. The
    moves are read from species_movepool rather than from a hand-written list, so the
    answer changes when the movepool does.

    A specimen stripped down to nothing keeps `fallback` rather than four empty slots,
    because every engine here assumes move_1 is a move.
    """
    allowed = await learnable_moves(db, pokedex_id)
    async with db.execute(
            f"SELECT {', '.join(MOVE_SLOTS)} FROM caught_pokemon WHERE instance_id = ?",
            (instance_id,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        return []

    kept, forgotten = [], []
    for move in row:
        name = str(move or '').strip().lower()
        if not name or name == 'none':
            continue
        (kept if name in allowed else forgotten).append(name)

    if not forgotten:
        return []
    if not kept:
        kept = [fallback]
    slots = (kept + [None] * len(MOVE_SLOTS))[:len(MOVE_SLOTS)]
    await db.execute(
        f"UPDATE caught_pokemon SET "
        f"{', '.join(f'{slot} = ?' for slot in MOVE_SLOTS)} WHERE instance_id = ?",
        (*slots, instance_id))
    return forgotten


SEPARATE_WORDS = ('separate', 'split', 'unfuse', 'defuse', 'dismount', 'release',
                  'undo', 'off')
MOVES_WORDS = ('moves', 'move', 'teach', 'signature')


def wants_separation(argument):
    return str(argument or '').strip().lower() in SEPARATE_WORDS


def wants_moves(argument):
    return str(argument or '').strip().lower() in MOVES_WORDS


def match_form(spec, species, argument):
    """
    Which form the player meant, given a ring and a word. None if the word means nothing.

    Deliberately forgiving about the prefix: inside Deoxys' ring, `attack` and
    `deoxys-attack` are the same request, and nobody types the second one.
    """
    ring = ring_for(spec, species)
    if not ring:
        return None
    wanted = str(argument or '').strip().lower().replace(' ', '-')
    if not wanted:
        return next_in_ring(spec, species)
    for form in ring:
        if form == wanted:
            return form
        # `rotom-heat` answers to `heat`, `shaymin-sky` to `sky`. The base form of a ring
        # has no suffix, so it answers to its own bare name and to `base`.
        head, _, tail = form.partition('-')
        if tail and tail == wanted:
            return form
        if not tail and wanted in ('base', 'normal', head):
            return form
    return None


def form_label(species):
    """'Rotom (Heat)' - the name a player reads."""
    head, _, tail = str(species or '').partition('-')
    if not tail:
        return head.title()
    return f"{head.title()} ({tail.replace('-', ' ').title()})"


async def fusion_record(db, host_instance_id):
    """The fusion this specimen is carrying, as a row, or None."""
    try:
        async with db.execute(
                f"SELECT host_instance_id, item_name, base_pokedex_id, payload "
                f"FROM {FUSION_TABLE} WHERE host_instance_id = ?",
                (host_instance_id,)) as cursor:
            return await cursor.fetchone()
    except Exception:
        # The table only exists after the migration. A bot running this code against an
        # unmigrated database has no fusions, which is the correct answer rather than a
        # crash on every release.
        return None


async def is_fused(db, host_instance_id):
    return await fusion_record(db, host_instance_id) is not None


async def fuse(db, host_instance_id, partner_instance_id, item_name, result_species):
    """
    Absorb one specimen into another. Returns the host's new (pokedex_id, ability).

    The partner's row is copied out VERBATIM before it is deleted, so everything about
    it - IVs, EVs, nickname, moves, shininess, who caught it - comes back untouched.
    Does not commit.
    """
    async with db.execute(
            "SELECT * FROM caught_pokemon WHERE instance_id = ?",
            (partner_instance_id,)) as cursor:
        partner = await cursor.fetchone()
        columns = [description[0] for description in cursor.description]
    if not partner:
        return None

    async with db.execute(
            "SELECT pokedex_id, ability FROM caught_pokemon WHERE instance_id = ?",
            (host_instance_id,)) as cursor:
        host = await cursor.fetchone()
    if not host:
        return None

    payload = json.dumps(dict(zip(columns, partner)))
    await db.execute(
        f"INSERT INTO {FUSION_TABLE} "
        f"(host_instance_id, item_name, base_pokedex_id, payload) VALUES (?, ?, ?, ?)",
        (host_instance_id, item_name, host[0], payload))
    await db.execute("DELETE FROM caught_pokemon WHERE instance_id = ?",
                     (partner_instance_id,))
    return await apply_form(db, host_instance_id, result_species, host[1])


async def separate(db, host_instance_id):
    """
    Give back what a fused specimen is carrying.

    Returns (restored instance_id, restored pokedex_id, base pokedex_id) or None. Does
    not commit.
    """
    record = await fusion_record(db, host_instance_id)
    if not record:
        return None
    _host, _item, base_pokedex_id, payload = record

    async with db.execute(
            "SELECT user_id, ability FROM caught_pokemon WHERE instance_id = ?",
            (host_instance_id,)) as cursor:
        host = await cursor.fetchone()
    if not host:
        return None
    owner, ability = host

    stored = json.loads(payload)
    async with db.execute("PRAGMA table_info(caught_pokemon)") as cursor:
        live_columns = [row[1] for row in await cursor.fetchall()]

    # Only columns that BOTH the payload and the table still have. A specimen fused
    # before a schema change comes back with whatever it had, and the rest defaults -
    # which beats refusing to give it back at all.
    restore = {name: value for name, value in stored.items()
               if name in live_columns and name not in NOT_RESTORED}
    restore['user_id'] = owner          # the host's owner NOW, not the one who fused it

    await db.execute(
        f"INSERT INTO caught_pokemon ({', '.join(restore)}) "
        f"VALUES ({', '.join('?' for _ in restore)})",
        tuple(restore.values()))
    await db.execute(f"DELETE FROM {FUSION_TABLE} WHERE host_instance_id = ?",
                     (host_instance_id,))

    async with db.execute(
            "SELECT name FROM base_pokemon_species WHERE pokedex_id = ?",
            (base_pokedex_id,)) as cursor:
        base = await cursor.fetchone()
    if base:
        await apply_form(db, host_instance_id, base[0], ability)
    return (stored.get('instance_id'), stored.get('pokedex_id'), base_pokedex_id)


# ==========================================
# THE COMMAND'S RULEBOOK
# ==========================================
# Everything `!form` decides lives here rather than in the cog, so that all of it can be
# driven by a test with a database and no Discord. The cog is left holding the specimen
# lookup, the inventory check and ctx.send.

async def describe_options(db, species, shown, instance_id):
    """What this specimen's form items could do for it - the answer to a bare `!form`."""
    keys = item_for_species(species)
    record = await fusion_record(db, instance_id)
    if record:
        spec = form_item(record[1]) or {}
        label = spec.get('label', record[1])
        return (f"🧬 **{shown}** is fused. `!form <box> {record[1]} separate` takes it "
                f"apart again with the **{label}**.")
    if not keys:
        return (f"🧬 Nothing on the form shelf does anything for **{shown}**. Those "
                f"items are for Deoxys, Rotom, Shaymin, Hoopa, Zygarde, the weather "
                f"quartet, Kyurem, Necrozma and Calyrex.")

    lines = []
    for key in keys:
        spec = FORM_ITEMS[key]
        if spec['kind'] == FUSION:
            partners = ", ".join(sorted(spec['fusions']))
            lines.append(f"{spec['emoji']} **{spec['label']}** — `!form <box> {key} "
                         f"<box of {partners}>`")
        elif spec['kind'] == GRID:
            sizes = "/".join(grid_options(spec, 'size'))
            lines.append(f"{spec['emoji']} **{spec['label']}** — `{sizes}`, "
                         f"`aura-break`/`power-construct`, or `moves`")
        else:
            options = ", ".join(form_label(f) for f in ring_targets(spec, species))
            lines.append(f"{spec['emoji']} **{spec['label']}** — {options}")
    return f"🧬 **{shown}** answers to:\n" + "\n".join(lines)


async def perform(db, owner_id, item, instance_id, species, shown, ability, argument,
                  locate=None):
    """
    Do what the item does. Returns the line to print.

    Every refusal is a RETURNED STRING rather than an exception, because a refusal a
    player can read is worth more than a traceback in the console. Does not commit; the
    caller owns the transaction, so a fusion is all-or-nothing.

    `locate` is injected so that this module does not have to import a cog's idea of what
    a box number is, and so a test can drive fusions without one.
    """
    spec = form_item(item)
    if not spec:
        return f"⚠️ `{item}` is not a form item."
    if spec['kind'] == FUSION:
        return await _perform_fusion(db, owner_id, item, spec, instance_id, species,
                                     shown, argument, locate)
    if spec['kind'] == GRID:
        return await _perform_grid(db, spec, instance_id, species, shown, ability,
                                   argument)
    return await _perform_ring(db, spec, instance_id, species, shown, ability, argument)


def _ring_families(spec):
    """'Deoxys', or 'Tornadus, Thundurus, Landorus and Enamorus' - for a refusal."""
    heads = []
    for ring in spec.get('rings', ()):
        head = ring[0].partition('-')[0].title()
        if head not in heads:
            heads.append(head)
    if len(heads) == 1:
        return heads[0]
    return ", ".join(heads[:-1]) + f" and {heads[-1]}"


async def _perform_ring(db, spec, instance_id, species, shown, ability, argument):
    if not ring_for(spec, species):
        return (f"⚠️ A **{spec['label']}** does nothing for **{shown}**. It is for "
                f"{_ring_families(spec)}.")
    target = match_form(spec, species, argument)
    if not target:
        options = ", ".join(f"`{f.partition('-')[2] or f}`"
                            for f in ring_targets(spec, species))
        return (f"⚠️ **{shown}** has no forme called `{argument}`. "
                f"Try one of: {options}.")
    if target == species:
        return f"🧬 **{shown}** is already in that forme."

    changed = await apply_form(db, instance_id, target, ability)
    if not changed:
        return f"⚠️ `{target}` is not a species this database has."

    # PRUNED AFTER THE FORM CHANGES, not before: what the specimen may keep is decided
    # against the movepool of the form it is BECOMING, and `apply_form` is what makes it
    # that form. Same ordering the fusion path uses, for the same reason.
    forgotten = []
    if spec.get('prunes_moves'):
        forgotten = await prune_moves(db, instance_id, changed[0])

    flavour = spec.get('flavour', "{name} changes shape").format(name=shown)
    line = (f"{spec['emoji']} {flavour[0].upper()}{flavour[1:]} — **{shown}** is now "
            f"**{form_label(target)}**.")
    if forgotten:
        listed = ", ".join(m.replace('-', ' ').title() for m in forgotten)
        line += (f"\n📝 It forgot {listed} — that belonged to the appliance it left, "
                 f"not to Rotom.")
    return line


async def _perform_grid(db, spec, instance_id, species, shown, ability, argument):
    position = grid_position(spec, species)
    if not position:
        return f"⚠️ A **{spec['label']}** is for Zygarde, and **{shown}** is not one."

    if wants_moves(argument):
        row = await species_row(db, species)
        moves = await moves_by_method(db, row[0], spec['teaches']) if row else []
        if not moves:
            return (f"⚠️ The movepool records nothing against `{spec['teaches']}` for "
                    f"**{shown}**.")
        listed = ", ".join(f"`{m.replace('-', ' ').title()}`" for m in moves)
        return (f"{spec['emoji']} The **{spec['label']}** can teach **{shown}**: "
                f"{listed}.\nUse `!teach` to put one in a slot.")

    wanted = str(argument or '').strip().lower().replace(' ', '-').rstrip('%')
    if not wanted:
        sizes = "/".join(f"`{s}`" for s in grid_options(spec, 'size'))
        abilities = "/".join(f"`{a}`" for a in grid_options(spec, 'ability'))
        return (f"{spec['emoji']} **{shown}** is at **{position[0]}%** with "
                f"**{position[1].replace('-', ' ').title()}**.\n"
                f"Say {sizes} to resize, {abilities} to switch cells, or `moves`.")

    for axis in spec['axes']:
        if wanted in grid_options(spec, axis):
            target = grid_move(spec, species, axis, wanted)
            if target == species:
                return f"🧬 **{shown}** is already there."
            if not await apply_form(db, instance_id, target, ability):
                return f"⚠️ `{target}` is not a species this database has."
            after = grid_position(spec, target)
            return (f"{spec['emoji']} The Cube's cells rearrange — **{shown}** is now "
                    f"**{after[0]}%** with **{after[1].replace('-', ' ').title()}**.")

    every = ", ".join(f"`{v}`" for axis in spec['axes']
                      for v in grid_options(spec, axis))
    return f"⚠️ `{argument}` is not something the Cube does. Try {every}, or `moves`."


async def _perform_fusion(db, owner_id, item, spec, instance_id, species, shown,
                          argument, locate):
    record = await fusion_record(db, instance_id)

    if wants_separation(argument) or (record and not argument):
        if not record:
            return f"⚠️ **{shown}** is not fused, so there is nothing to separate."
        if record[1] != item:
            other = FORM_ITEMS.get(record[1], {}).get('label', record[1])
            return (f"⚠️ **{shown}** was fused with a **{other}**, and that is what "
                    f"takes it apart.")
        outcome = await separate(db, instance_id)
        if not outcome:
            return f"⚠️ **{shown}** could not be separated. Nothing was changed."
        _restored, restored_dex, base_dex = outcome

        # PRUNED AFTER THE FORM REVERTS, not before: the moves a dismounted Calyrex may
        # keep are decided against its BASE movepool, and `separate` is what puts it back.
        forgotten = []
        if spec.get('prunes_moves'):
            forgotten = await prune_moves(db, instance_id, base_dex)

        async with db.execute(
                "SELECT name FROM base_pokemon_species WHERE pokedex_id = ?",
                (restored_dex,)) as cursor:
            partner = await cursor.fetchone()
        line = (f"{spec['emoji']} **{shown}** separates. "
                f"**{form_label(partner[0] if partner else 'its partner')}** is back in "
                f"your roster.")
        if forgotten:
            listed = ", ".join(m.replace('-', ' ').title() for m in forgotten)
            line += (f"\n📝 It could no longer hold {listed} — those were its steed's "
                     f"moves, not its own.")
        return line

    if record:
        return (f"⚠️ **{shown}** is already fused. `!form <box> {item} separate` takes "
                f"it apart first.")

    if species != spec['host']:
        if species in fused_species(spec):
            return (f"⚠️ **{shown}** is already a fusion. `!form <box> {item} separate` "
                    f"takes it apart.")
        return (f"⚠️ A **{spec['label']}** is for {spec['host'].title()}, and "
                f"**{shown}** is not one.")

    if not argument:
        partners = ", ".join(p.title() for p in sorted(spec['fusions']))
        return f"⚠️ Which one? `!form <box> {item} <box of {partners}>`."

    if locate is None:
        return "⚠️ That fusion cannot be resolved here."
    partner_row, complaint = await locate(db, owner_id, argument)
    if complaint:
        return complaint
    partner_instance, _partner_dex, partner_species, partner_nick = partner_row

    if partner_instance == instance_id:
        return "⚠️ A specimen cannot be fused with itself."
    result_species = spec['fusions'].get(partner_species)
    if not result_species:
        partners = ", ".join(p.title() for p in sorted(spec['fusions']))
        return (f"⚠️ **{shown}** cannot fuse with **{form_label(partner_species)}**. "
                f"A **{spec['label']}** joins it to {partners}.")
    if await fusion_record(db, partner_instance):
        return (f"⚠️ **{partner_nick or form_label(partner_species)}** is itself fused, "
                f"and has to be separated first.")

    if not await fuse(db, instance_id, partner_instance, item, result_species):
        return "⚠️ That fusion could not be completed. Nothing was changed."
    flavour = spec.get('flavour', "{host} and {partner} are joined").format(
        host=shown, partner=partner_nick or form_label(partner_species))
    return (f"{spec['emoji']} {flavour[0].upper()}{flavour[1:]} — "
            f"**{form_label(result_species)}**.\n"
            f"📦 {partner_nick or form_label(partner_species)} is held inside it, and "
            f"comes back when you separate them.")
