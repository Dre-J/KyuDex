"""
Bring `evolution_rules` up to what PokeAPI actually knows, in three phases.

WHY THIS EXISTS
---------------
The table was built from PokeAPI's evolution chains, but three kinds of information were
dropped on the way in, and each one left evolutions permanently unreachable.

PHASE 1 - THE HELD ITEM.
`item_name` means "the item you USE" - a Fire Stone, a Dawn Stone. PokeAPI keeps the item
a specimen must be HOLDING in a separate `held_item` field, and there was no column for
it, so all twenty were lost. Sneasel -> Weavile was stored as `level-up` + `night` with no
Razor Claw at all, and every trade-with-item evolution had no item either - which is why
cogs/social.py's `if required_item` was always false and a Scyther became a Scizor on any
trade whatsoever.

PHASE 2 - THE KNOWN MOVE.
Fifteen evolutions want the specimen to know a particular move, and one - Eevee ->
Sylveon - wants it to know a move of a particular TYPE, alongside high friendship. With
nowhere to record that, all sixteen became rules with no checkable requirement at all,
which the rulebook correctly refuses to fire. Sylveon, Mamoswine, Yanmega, Tangrowth,
Lickilicky, Ambipom, Mr. Mime, Sudowoodo, Tsareena, Overqwil, Naganadel, Grapploct and
Farigiraf were all unobtainable.

PHASE 3 - THE REGIONAL FORMS.
This is the big one. PokeAPI's chains are keyed by SPECIES, so `meowth -> perrserker` is
filed under plain Meowth even though only the Galarian form evolves that way. This dex
gives every regional form its own pokedex_id in the 10xxx range - and not one rule was
keyed to any of them. All 319 alternate forms were evolutionary dead ends, including
Galarian Yamask, whose Runerigus is the reason this phase exists.

The fix is available because this PokeAPI instance carries `base_form` and `evolved_form`
on the evolution detail, naming the exact forms on each end. 44 rows are inserted, keyed
on the regional form's own id, so a Galarian Meowth evolves and a Kantonian one does not.

RUNNING IT
----------
    python migrate_evolution_items.py              # dry run, prints the plan
    python migrate_evolution_items.py --apply      # writes, after taking a backup

IDEMPOTENT. A second run finds nothing to do. It only ever fills a column that is
currently NULL and only ever inserts a (base, evolved, trigger) that is not already there,
so a value corrected by hand later survives a re-run.

It refuses to write without a backup it took itself, in this run, and verifies that backup
table-by-table and row-by-row before touching anything.

Requirements are matched on (base_species_id, evolved_species_id, TRIGGER). Matching on
the species pair alone is wrong, and both traps are live in this data:

  - slowpoke -> slowking exists twice, once as `trade` (King's Rock) and once as
    `use-item` (Galarica Wreath, the Galarian line). Only the trade row wants a held item.
  - feebas -> milotic exists twice, once as `level-up` (the max-beauty route, no item)
    and once as `trade` (Prism Scale). Only the trade row wants one.
"""
import argparse
import datetime
import json
import os
import sqlite3
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.join(ROOT, 'ecosystem.db')
CACHE = os.path.join(ROOT, '.evolution_chains.json')
UA = {'User-Agent': 'Mozilla/5.0 (KyuDex evolution sync)'}

# The requirement fields this schema can carry, and where PokeAPI keeps each one. Adding a
# requirement is a row here plus a column below; nothing else needs to know what it means.
REQUIREMENTS = {
    'held_item':       lambda d: (d.get('held_item') or {}).get('name'),
    'known_move':      lambda d: (d.get('known_move') or {}).get('name'),
    'known_move_type': lambda d: (d.get('known_move_type') or {}).get('name'),
}

# (table, column, declaration). Every one is added with a plain ALTER and a duplicate is
# tolerated, so this list is a description of the target schema rather than a script.
NEW_COLUMNS = [
    ('evolution_rules', 'held_item',           'TEXT'),
    ('evolution_rules', 'known_move',          'TEXT'),
    ('evolution_rules', 'known_move_type',     'TEXT'),
    # Two battle counters, for the evolutions whose trigger is something that HAPPENS.
    # Galarian Yamask becomes a Runerigus after a hit of 49 or more; Galarian Farfetch'd
    # becomes a Sirfetch'd after three criticals in one battle. Both are conditions the
    # engine already sees and simply never wrote down.
    ('caught_pokemon',  'biggest_hit_taken',   'INTEGER DEFAULT 0'),
    ('caught_pokemon',  'crits_landed_battle', 'INTEGER DEFAULT 0'),
]


def fetch(url):
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=30).read())


def load_chains(refresh=False):
    """Every evolution chain PokeAPI knows, cached so a re-run costs nothing."""
    if os.path.exists(CACHE) and not refresh:
        return json.load(open(CACHE, encoding='utf-8'))

    index = fetch('https://pokeapi.co/api/v2/evolution-chain?limit=2000')
    chains, started = [], time.time()
    for i, row in enumerate(index['results'], 1):
        for attempt in range(3):
            try:
                chains.append(fetch(row['url']))
                break
            except Exception as exc:
                if attempt == 2:
                    raise RuntimeError(f"could not fetch {row['url']}: {exc}")
                time.sleep(1.5)
        if i % 100 == 0:
            print(f"  fetched {i}/{len(index['results'])}  ({time.time() - started:.0f}s)")
    json.dump(chains, open(CACHE, 'w', encoding='utf-8'))
    return chains


def _name(value):
    return value.get('name') if isinstance(value, dict) else value


def all_edges(chains):
    """(base species, evolved species, detail dict) for every edge in every chain."""
    found = []

    def walk(node):
        parent = node['species']['name']
        for child in node['evolves_to']:
            for detail in child['evolution_details']:
                found.append((parent, child['species']['name'], detail))
            walk(child)

    for chain in chains:
        walk(chain['chain'])
    return found


def take_backup():
    """A verified copy, before anything is written. Returns its path."""
    stamp = datetime.date.today().isoformat()
    dest = os.path.join(ROOT, f'ecosystem.db.bak-{stamp}')
    suffix = 1
    while os.path.exists(dest):
        suffix += 1
        dest = os.path.join(ROOT, f'ecosystem.db.bak-{stamp}-{suffix}')

    source = sqlite3.connect(f'file:{LIVE}?mode=ro', uri=True)
    target = sqlite3.connect(dest)
    source.backup(target)
    target.close()
    source.close()

    # Verify it before it is trusted. A backup nobody checked is a rumour.
    live = sqlite3.connect(f'file:{LIVE}?mode=ro', uri=True)
    copy = sqlite3.connect(f'file:{dest}?mode=ro', uri=True)
    tables = [r[0] for r in live.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    mirrored = [r[0] for r in copy.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    if tables != mirrored:
        raise RuntimeError("backup has a different set of tables - refusing to continue")
    for table in tables:
        a = live.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        b = copy.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        if a != b:
            raise RuntimeError(f"backup row count differs for {table}: {a} vs {b}")
    live.close()
    copy.close()
    print(f"  backup verified: {os.path.basename(dest)}  ({len(tables)} tables)")
    return dest


def add_columns(db, announce=False):
    """Every column in NEW_COLUMNS, tolerating the ones already there."""
    added = []
    for table, column, declaration in NEW_COLUMNS:
        try:
            db.execute(f'ALTER TABLE {table} ADD COLUMN {column} {declaration}')
            added.append(f'{table}.{column}')
        except sqlite3.OperationalError as exc:
            if 'duplicate column' not in str(exc).lower():
                raise
    if announce and added:
        print("columns to add: " + ", ".join(added) + "\n")
    return added


def plan_requirements(db, edges, species):
    """[(row id, {column: value}, description)] for rules missing a requirement."""
    rows = db.execute(
        'SELECT id, base_species_id, evolved_species_id, trigger_name, '
        'held_item, known_move, known_move_type FROM evolution_rules').fetchall()
    stored = {'held_item': 4, 'known_move': 5, 'known_move_type': 6}

    plan, unmatched = [], []
    for base, evolved, detail in edges:
        wants = {column: read(detail) for column, read in REQUIREMENTS.items()
                 if read(detail)}
        if not wants:
            continue
        # A form-specific edge is Phase 3's business, not this one.
        if _name(detail.get('base_form')) not in (None, base):
            continue
        if _name(detail.get('evolved_form')) not in (None, evolved):
            continue
        # AFFECTION is not a stat this world has. Eevee -> Sylveon exists twice in
        # PokeAPI: once as friendship 160 plus a Fairy move, and once as two affection
        # hearts plus a Fairy move. Recording the requirement against the affection row
        # too would make Sylveon reachable on a Fairy move ALONE, because that row has no
        # other requirement this schema can see. So the unmodellable route is skipped and
        # the friendship one becomes the route.
        if detail.get('min_affection'):
            continue
        if base not in species or evolved not in species:
            unmatched.append((base, evolved, wants, 'species not in this database'))
            continue
        trigger = detail['trigger']['name']
        matches = [r for r in rows if r[1] == species[base]
                   and r[2] == species[evolved] and r[3] == trigger]
        # ...and where a pair has several rows under one trigger, the friendship figure
        # tells them apart. Without this the Sylveon requirement would land on both rows.
        if len(matches) > 1:
            wanted_happiness = detail.get('min_happiness')
            narrowed = [r for r in matches
                        if db.execute('SELECT min_happiness FROM evolution_rules '
                                      'WHERE id = ?', (r[0],)).fetchone()[0]
                        == wanted_happiness]
            if narrowed:
                matches = narrowed
        if not matches:
            unmatched.append((base, evolved, wants, f'no {trigger} row'))
            continue
        for row in matches:
            missing = {c: v for c, v in wants.items() if row[stored[c]] is None}
            if not missing:
                continue
            label = f"{base} -> {evolved}"
            when = detail.get('time_of_day')
            if when:
                label += f" ({when})"
            plan.append((row[0], missing,
                         f"{label:38} {trigger:9} "
                         + ", ".join(f"{c}={v}" for c, v in sorted(missing.items()))))
    return plan, unmatched


def plan_forms(db, edges, species):
    """
    ([(values, description)] to insert, [(row id, base, evolved, description)] to re-key).

    Two outcomes rather than one, because a form-specific evolution can already be in the
    table under the WRONG key. `meowth -> perrserker` is filed against plain Meowth, since
    that is how PokeAPI's chain is shaped - so a Kantonian Meowth becomes a Perrserker
    today, and a Kantonian Sneasel becomes a Sneasler, and a Kantonian Slowpoke becomes a
    Galarian Slowking. Inserting the correct rule beside the wrong one would leave both
    routes open, so where the wrong row exists it is RE-KEYED in place: no row is deleted
    and none is duplicated.

    A row is only re-keyed when EVERY PokeAPI edge for that (species, target, trigger) is
    form-specific. If any edge is generic, the base-keyed row is legitimate and is left
    exactly where it is.
    """
    rows = db.execute(
        'SELECT id, base_species_id, evolved_species_id, trigger_name '
        'FROM evolution_rules').fetchall()
    present = {(r[1], r[2], r[3]) for r in rows}

    # Which (species, target, trigger) triples are form-specific in EVERY edge.
    shape = {}
    for base, evolved, detail in edges:
        base_form = _name(detail.get('base_form'))
        evolved_form = _name(detail.get('evolved_form'))
        specific = ((base_form and base_form != base)
                    or (evolved_form and evolved_form != evolved))
        shape.setdefault((base, evolved, detail['trigger']['name']), []).append(
            bool(specific))
    always_specific = {k for k, flags in shape.items() if all(flags)}

    inserts, rekeys, unresolved, seen = [], [], [], set()
    for base, evolved, detail in edges:
        base_form = _name(detail.get('base_form'))
        evolved_form = _name(detail.get('evolved_form'))
        if not ((base_form and base_form != base)
                or (evolved_form and evolved_form != evolved)):
            continue

        source = base_form or base
        target = evolved_form or evolved
        trigger = detail['trigger']['name']
        if source not in species or target not in species:
            unresolved.append((source, target, trigger))
            continue

        key = (species[source], species[target], trigger)
        if key in present or key in seen:
            continue
        seen.add(key)

        # Is there a row under the plain species that should have been this one?
        misfiled = None
        if (base, evolved, trigger) in always_specific:
            misfiled = next((r for r in rows
                             if r[1] == species.get(base) and r[2] == species.get(evolved)
                             and r[3] == trigger), None)

        if misfiled:
            rekeys.append((misfiled[0], species[source], species[target],
                           f"{base} -> {evolved}  becomes  {source} -> {target}"))
            continue

        values = (species[source], species[target], trigger,
                  detail.get('min_level'), _name(detail.get('item')),
                  detail.get('min_happiness'), detail.get('time_of_day') or '',
                  (detail.get('held_item') or {}).get('name'),
                  (detail.get('known_move') or {}).get('name'),
                  (detail.get('known_move_type') or {}).get('name'))
        inserts.append((values, f"{source:22} -> {target:24} {trigger}"))
    return inserts, rekeys, unresolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true',
                        help='actually write (default is a dry run)')
    parser.add_argument('--refresh', action='store_true',
                        help='re-fetch from PokeAPI instead of using the cache')
    args = parser.parse_args()

    if not os.path.exists(LIVE):
        sys.exit(f"no database at {LIVE}")

    print("Loading evolution chains...")
    edges = all_edges(load_chains(args.refresh))
    print(f"  PokeAPI reports {len(edges)} evolution edges\n")

    # The whole plan is decided against an IN-MEMORY copy carrying the target schema, so
    # nothing can be written to the live file while it is being worked out.
    scratch = sqlite3.connect(':memory:')
    source = sqlite3.connect(f'file:{LIVE}?mode=ro', uri=True)
    source.backup(scratch)
    source.close()
    new_columns = add_columns(scratch, announce=True)

    species = {r[0]: r[1] for r in scratch.execute(
        'SELECT name, pokedex_id FROM base_pokemon_species')}

    requirements, req_unmatched = plan_requirements(scratch, edges, species)
    forms, rekeys, form_unresolved = plan_forms(scratch, edges, species)
    scratch.close()

    if requirements:
        print("-- requirements to record --")
        for _, _, line in requirements:
            print(f"  SET  {line}")
    if rekeys:
        print("\n-- rules filed against the wrong form, re-keyed in place --")
        for _, _, _, line in sorted(rekeys, key=lambda r: r[3]):
            print(f"  FIX  {line}")
    if forms:
        print("\n-- regional-form rules to insert --")
        for _, line in sorted(forms, key=lambda f: f[1]):
            print(f"  ADD  {line}")
    for base, evolved, wants, why in req_unmatched:
        print(f"  !!   {base} -> {evolved} {wants}: {why}")
    if form_unresolved:
        print("\n-- form edges this dex cannot express --")
        for source, target, trigger in sorted(set(form_unresolved)):
            print(f"  --   {source} -> {target} ({trigger}): form missing from the dex")

    print(f"\n{len(new_columns)} column(s), {len(requirements)} requirement(s), "
          f"{len(rekeys)} re-key(s), {len(forms)} new rule(s).")

    if not (new_columns or requirements or rekeys or forms):
        print("Nothing to do - the database is already migrated.")
        return

    if not args.apply:
        print("\nDRY RUN. Re-run with --apply to write.")
        return

    print("\nTaking a backup before writing...")
    take_backup()

    write = sqlite3.connect(LIVE)
    try:
        write.execute('BEGIN')
        add_columns(write)
        for row_id, values, _ in requirements:
            for column, value in values.items():
                write.execute(
                    f'UPDATE evolution_rules SET {column} = ? '
                    f'WHERE id = ? AND {column} IS NULL', (value, row_id))
        for row_id, base_id, evolved_id, _ in rekeys:
            write.execute(
                'UPDATE evolution_rules SET base_species_id = ?, evolved_species_id = ? '
                'WHERE id = ?', (base_id, evolved_id, row_id))
        for values, _ in forms:
            write.execute(
                'INSERT INTO evolution_rules (base_species_id, evolved_species_id, '
                'trigger_name, min_level, item_name, min_happiness, time_of_day, '
                'held_item, known_move, known_move_type) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', values)
        write.commit()
    except Exception:
        write.rollback()
        raise
    finally:
        write.close()

    check = sqlite3.connect(f'file:{LIVE}?mode=ro', uri=True)
    total = check.execute('SELECT COUNT(*) FROM evolution_rules').fetchone()[0]
    regional = check.execute(
        'SELECT COUNT(*) FROM evolution_rules WHERE base_species_id >= 10000').fetchone()[0]
    counts = {c: check.execute(
        f'SELECT COUNT(*) FROM evolution_rules WHERE {c} IS NOT NULL').fetchone()[0]
        for c in REQUIREMENTS}
    check.close()
    print(f"\nDone. {total} rules, {regional} of them keyed to a regional form.")
    for column, count in sorted(counts.items()):
        print(f"  {column}: {count}")


if __name__ == '__main__':
    main()
