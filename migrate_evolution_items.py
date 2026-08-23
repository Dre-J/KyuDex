"""
Add `held_item` to evolution_rules and populate it from PokeAPI.

WHY THIS EXISTS
---------------
`evolution_rules` has an `item_name` column that means "the item you USE" - a Fire Stone,
a Dawn Stone. It has never had a column for the item the specimen must be HOLDING, and
PokeAPI keeps those in a different field (`held_item`), so all twenty of them were dropped
when the table was first built. Zero of its 513 rows carried a held-item requirement.

The visible consequences:

  - Sneasel -> Weavile was stored as `level-up` + `night` with no Razor Claw at all
  - every trade-with-item evolution had no item: Scyther became Scizor on ANY trade,
    because cogs/social.py checks `item_name` and `item_name` was NULL

RUNNING IT
----------
    python migrate_evolution_items.py              # dry run, prints the plan
    python migrate_evolution_items.py --apply      # writes, after taking a backup

It is IDEMPOTENT: a second run finds nothing to do and says so. It only ever writes rows
whose `held_item` is currently NULL, so a value corrected by hand later is never
overwritten by a re-run.

It refuses to write without a backup it took itself, in this run, and verifies that backup
row-for-row before touching anything.

The twenty rows are matched on (base_species_id, evolved_species_id, TRIGGER). Matching on
the species pair alone is wrong twice over, and both traps are live in this data:

  - slowpoke -> slowking exists twice, once as `trade` (King's Rock) and once as
    `use-item` (Galarica Wreath, the Galarian line). Only the trade row wants a held item.
  - feebas -> milotic exists twice, once as `level-up` (the max-beauty route, no item)
    and once as `trade` (Prism Scale). Only the trade row wants one.
"""
import argparse
import datetime
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.join(ROOT, 'ecosystem.db')
CACHE = os.path.join(ROOT, '.evolution_chains.json')
UA = {'User-Agent': 'Mozilla/5.0 (KyuDex evolution sync)'}


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


def held_item_edges(chains):
    """(base species name, evolved species name, trigger, held item, time of day)."""
    found = []

    def walk(node):
        parent = node['species']['name']
        for child in node['evolves_to']:
            for detail in child['evolution_details']:
                if detail.get('held_item'):
                    found.append((parent, child['species']['name'],
                                  detail['trigger']['name'],
                                  detail['held_item']['name'],
                                  detail.get('time_of_day') or ''))
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

    # Verify it row for row before it is trusted. A backup nobody checked is a rumour.
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


def build_plan(db, edges):
    """[(row id, held item, description)], plus the edges that matched nothing."""
    names = {r[0]: r[1] for r in db.execute(
        'SELECT name, pokedex_id FROM base_pokemon_species')}
    rows = db.execute(
        'SELECT id, base_species_id, evolved_species_id, trigger_name, held_item '
        'FROM evolution_rules').fetchall()

    plan, unmatched, already = [], [], []
    for base, evolved, trigger, item, when in sorted(edges):
        if base not in names or evolved not in names:
            unmatched.append((base, evolved, item, 'species not in this database'))
            continue
        matches = [r for r in rows
                   if r[1] == names[base] and r[2] == names[evolved] and r[3] == trigger]
        if not matches:
            unmatched.append((base, evolved, item, f'no {trigger} row'))
            continue
        for row in matches:
            if row[4] is not None:
                already.append((row[0], base, evolved, row[4]))
                continue
            label = f"{base} -> {evolved}"
            if when:
                label += f" ({when})"
            plan.append((row[0], item, f"{label:38} {trigger:9} {item}"))
    return plan, unmatched, already


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
    edges = held_item_edges(load_chains(args.refresh))
    print(f"  PokeAPI reports {len(edges)} held-item evolutions\n")

    # The plan is built against a READ-ONLY handle. Nothing can be written while it is
    # being decided, which is the point.
    db = sqlite3.connect(f'file:{LIVE}?mode=ro', uri=True)
    columns = [r[1] for r in db.execute('PRAGMA table_info(evolution_rules)')]
    needs_column = 'held_item' not in columns
    if needs_column:
        print("evolution_rules has no `held_item` column - it will be added.\n")
        # Build the plan against a schema that has it, without touching the live file.
        db.close()
        db = sqlite3.connect(':memory:')
        source = sqlite3.connect(f'file:{LIVE}?mode=ro', uri=True)
        source.backup(db)
        source.close()
        db.execute('ALTER TABLE evolution_rules ADD COLUMN held_item TEXT')

    plan, unmatched, already = build_plan(db, edges)
    db.close()

    for _, _, line in plan:
        print(f"  SET  {line}")
    for row_id, base, evolved, item in already:
        print(f"  --   id={row_id} {base} -> {evolved} already holds {item!r}")
    for base, evolved, item, why in unmatched:
        print(f"  !!   {base} -> {evolved} ({item}): {why}")

    print(f"\n{len(plan)} row(s) to update, {len(already)} already set, "
          f"{len(unmatched)} unmatched.")

    if not plan and not needs_column:
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
        if needs_column:
            write.execute('ALTER TABLE evolution_rules ADD COLUMN held_item TEXT')
        for row_id, item, _ in plan:
            write.execute(
                'UPDATE evolution_rules SET held_item = ? WHERE id = ? AND held_item IS NULL',
                (item, row_id))
        write.commit()
    except Exception:
        write.rollback()
        raise
    finally:
        write.close()

    check = sqlite3.connect(f'file:{LIVE}?mode=ro', uri=True)
    total = check.execute(
        'SELECT COUNT(*) FROM evolution_rules WHERE held_item IS NOT NULL').fetchone()[0]
    rows = check.execute('SELECT COUNT(*) FROM evolution_rules').fetchone()[0]
    check.close()
    print(f"\nDone. {total} of {rows} rules now carry a held-item requirement.")


if __name__ == '__main__':
    main()
