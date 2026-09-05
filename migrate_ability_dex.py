"""
Give the abilities their descriptions.

**THE DATABASE KNOWS WHICH SPECIMEN HAS WHICH ABILITY AND NOTHING ELSE ABOUT IT.**
`base_pokemon_species` carries `standard_abilities` and `hidden_ability` for all 1,344
species - 313 distinct abilities - so "who can have Levitate" has always been answerable
locally. What is missing is the other half: what Levitate actually does. There is no
table, no column and no file anywhere in the repo that says.

**SO THIS IS THE ONLY PART THAT NEEDS THE NETWORK.** It fetches PokeAPI once, writes
`base_abilities`, and nothing at runtime ever calls out again - `!abilitydex` reads this
table and the species table and talks to nobody.

**WHAT IT ASKS FOR.** Two texts per ability, because they answer different questions:

    short_effect   one line, which is what a card shows
    effect         the full rules text, for the ability whose one line is not enough

Both come from `effect_entries`, in English. A handful of abilities have no English
effect entry at all; those fall back to the `flavor_text_entries` a game printed, and are
reported rather than silently left blank.

**IDEMPOTENT, AND RESUMABLE, WHICH IS THE SAME THING HERE.** It only fetches what the
table does not already have, so a run interrupted at ability 200 picks up at 201 rather
than starting again - and a second complete run makes no requests at all. `--refresh`
re-fetches everything, for when PokeAPI has corrected something.

**A USER-AGENT IS NOT OPTIONAL.** PokeAPI answers python-urllib's default header with
`403 Forbidden`. That took a while to find, and it is the whole difference between this
script working and appearing to be offline.

    python migrate_ability_dex.py             # report only: what is missing
    python migrate_ability_dex.py --apply     # fetch and write
    python migrate_ability_dex.py --apply --refresh   # re-fetch everything
"""
import argparse
import json
import os
import shutil
import sqlite3
import time
import urllib.error
import urllib.request

DB = 'ecosystem.db'
TABLE = 'base_abilities'
API = 'https://pokeapi.co/api/v2/ability/{}'

# PokeAPI refuses the default urllib header outright. Named after the project so a rate
# limit lands on us rather than on "python".
USER_AGENT = 'KyuDex-migration/1.0 (+https://github.com/Dre-J/KyuDex)'

# Polite rather than fast. Three hundred requests at this spacing is about two minutes,
# and this runs once.
DELAY = 0.25
RETRIES = 3

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    name          TEXT PRIMARY KEY,
    display       TEXT,
    short_effect  TEXT,
    effect        TEXT,
    generation    INTEGER,
    fetched_at    TEXT DEFAULT CURRENT_TIMESTAMP
)
"""


def wanted_abilities(conn):
    """
    Every ability any species in this world can have, as a sorted list.

    Read from the species table rather than from a list in the repo, so an ability added
    by a later import is covered by being there. The literal string 'None' is what the
    import wrote for a species with no hidden ability, and is not an ability.
    """
    names = set()
    for standard, hidden in conn.execute(
            "SELECT standard_abilities, hidden_ability FROM base_pokemon_species"):
        for raw in (standard or '').split(','):
            name = raw.strip().lower()
            if name and name != 'none':
                names.add(name)
        name = (hidden or '').strip().lower()
        if name and name != 'none':
            names.add(name)
    return sorted(names)


def english(entries, *keys):
    """The first English text among `entries`, trying each key in turn."""
    for entry in entries or []:
        if (entry.get('language') or {}).get('name') != 'en':
            continue
        for key in keys:
            value = (entry.get(key) or '').strip()
            if value:
                # PokeAPI wraps flavour text at the width of a Game Boy screen.
                return ' '.join(value.split())
    return ''


# PokeAPI numbers generations in ROMAN, as `generation-iv`. Stripping the digits out of
# that finds none at all, which is how the first run wrote NULL for all of them.
GENERATIONS = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5,
               'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10}


def generation_number(slug):
    """`generation-iv` -> 4, and None for anything this does not recognise."""
    tail = str(slug or '').rsplit('-', 1)[-1].strip().lower()
    return GENERATIONS.get(tail)


def fetch(name):
    """`(row, complaint)` for one ability. Never raises."""
    request = urllib.request.Request(API.format(name),
                                     headers={'User-Agent': USER_AGENT})
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.load(response)
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, f"{name}: PokeAPI has no such ability"
            if attempt == RETRIES - 1:
                return None, f"{name}: HTTP {e.code}"
        except Exception as e:
            if attempt == RETRIES - 1:
                return None, f"{name}: {type(e).__name__} {e}"
        time.sleep(1.5 * (attempt + 1))
    else:                                                      # pragma: no cover
        return None, f"{name}: gave up"

    short = english(payload.get('effect_entries'), 'short_effect')
    full = english(payload.get('effect_entries'), 'effect')
    # SOME ABILITIES HAVE NO EFFECT ENTRY IN ENGLISH, only the sentence a game printed.
    # Better than an empty card, and the caller is told which ones these were.
    flavour = english(payload.get('flavor_text_entries'), 'flavor_text')
    complaint = None
    if not short and not full:
        if not flavour:
            return None, f"{name}: no English text of any kind"
        complaint = f"{name}: no effect entry, using the game's flavour text"

    display = english(payload.get('names'), 'name') or name.replace('-', ' ').title()

    return {
        'name': name,
        'display': display,
        'short_effect': short or flavour,
        'effect': full or flavour,
        'generation': generation_number((payload.get('generation') or {}).get('name')),
    }, complaint


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument('--db', default=DB, help="path to ecosystem.db")
    parser.add_argument('--apply', action='store_true',
                        help="actually fetch and write; without it this only reports")
    parser.add_argument('--refresh', action='store_true',
                        help="re-fetch abilities already in the table")
    parser.add_argument('--limit', type=int, default=0,
                        help="stop after this many fetches (for a trial run)")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"  no database at {args.db}")
        return 1

    conn = sqlite3.connect(args.db)
    wanted = wanted_abilities(conn)

    have = set()
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (TABLE,)).fetchone() is not None
    if exists:
        have = {row[0] for row in conn.execute(
            f"SELECT name FROM {TABLE} WHERE short_effect IS NOT NULL "
            f"AND TRIM(short_effect) != ''")}

    todo = wanted if args.refresh else [n for n in wanted if n not in have]

    print(f"\n  table {TABLE:<15}: {'exists' if exists else 'to be created'}")
    print(f"  abilities in world : {len(wanted)}")
    print(f"  already described  : {len(have)}")
    print(f"  to fetch           : {len(todo)}")
    if todo[:6]:
        print(f"      {', '.join(todo[:6])}{' …' if len(todo) > 6 else ''}")

    if not args.apply:
        print("\n  Nothing was written. Re-run with --apply to fetch these.")
        return 0

    if not todo:
        print("\n  Nothing to do; every ability already has a description.")
        return 0

    backup = f"{args.db}.pre-abilities.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written     : {backup}")

    conn.execute(SCHEMA)
    conn.commit()

    if args.limit:
        todo = todo[:args.limit]

    written, complaints, failures = 0, [], []
    started = time.time()
    for index, name in enumerate(todo, 1):
        row, complaint = fetch(name)
        if complaint and row is None:
            failures.append(complaint)
        elif complaint:
            complaints.append(complaint)

        if row is not None:
            conn.execute(
                f"INSERT INTO {TABLE} "
                f"  (name, display, short_effect, effect, generation) "
                f"VALUES (?, ?, ?, ?, ?) "
                f"ON CONFLICT(name) DO UPDATE SET "
                f"  display = excluded.display, "
                f"  short_effect = excluded.short_effect, "
                f"  effect = excluded.effect, "
                f"  generation = excluded.generation, "
                f"  fetched_at = CURRENT_TIMESTAMP",
                (row['name'], row['display'], row['short_effect'], row['effect'],
                 row['generation']))
            written += 1

        # COMMITTED AS IT GOES, which is what makes an interrupted run resumable rather
        # than merely re-runnable: everything fetched before the interruption is kept.
        if index % 20 == 0:
            conn.commit()
            rate = index / max(0.001, time.time() - started)
            print(f"      {index:>4}/{len(todo)}  ~{(len(todo) - index) / rate:.0f}s left")
        time.sleep(DELAY)

    conn.commit()

    total = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
    print(f"\n  written            : {written}")
    print(f"  rows now           : {total} of {len(wanted)} abilities")

    if complaints:
        print(f"  flavour text used  : {len(complaints)}")
        for line in complaints[:8]:
            print(f"      {line}")
    if failures:
        print(f"  could not describe : {len(failures)}")
        for line in failures[:12]:
            print(f"      {line}")
        print("      (`!abilitydex` shows these without a description rather than "
              "refusing them)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
