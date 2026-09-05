"""
Give the moves their descriptions.

**`base_moves` HAS NINE HUNDRED ROWS OF NUMBERS AND NOT ONE WORD OF PROSE.** Type, power,
accuracy, PP, priority, ailment, stat change - everything the engine needs to RESOLVE a
move, and nothing that says what it does. So `!movedex` could tell a trainer that Thousand
Arrows is Ground, 90 power, and not that it drags fliers out of the sky.

The same gap `migrate_ability_dex.py` filled for traits, filled the same way: one fetch
into a table of its own, and nothing at runtime ever calls out again.

**A TABLE RATHER THAN COLUMNS ON `base_moves`.** That table is the pristine import and is
read on every single turn by `fetch_move_payload`; a description belongs beside it, not
in it. It also keeps this migration independent of `migrate_nihil_light.py`, which writes
`base_moves` and enumerates its columns.

**TWO TEXTS, BECAUSE THEY ANSWER DIFFERENT QUESTIONS.** `short_effect` is one line and is
what a card shows; `effect` is the full rules text for the move whose one line is not
enough. Where PokeAPI has neither in English, the sentence a game printed is used and the
move is reported rather than left blank.

**IDEMPOTENT AND RESUMABLE.** It fetches only what the table lacks and commits as it goes,
so an interrupted run picks up where it stopped and a second complete run makes no
requests at all.

**A USER-AGENT IS NOT OPTIONAL** - PokeAPI answers python-urllib's default header with
`403 Forbidden`.

    python migrate_move_dex.py             # report only
    python migrate_move_dex.py --apply     # fetch and write
    python migrate_move_dex.py --apply --refresh
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
TABLE = 'base_move_text'
API = 'https://pokeapi.co/api/v2/move/{}'

USER_AGENT = 'KyuDex-migration/1.0 (+https://github.com/Dre-J/KyuDex)'
DELAY = 0.25
RETRIES = 3

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    name          TEXT PRIMARY KEY,
    display       TEXT,
    short_effect  TEXT,
    effect        TEXT,
    flavour       TEXT,
    generation    INTEGER,
    fetched_at    TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

GENERATIONS = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5,
               'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10}


def generation_number(slug):
    """`generation-iv` -> 4. PokeAPI numbers them in roman."""
    tail = str(slug or '').rsplit('-', 1)[-1].strip().lower()
    return GENERATIONS.get(tail)


def wanted_moves(conn):
    """Every move the engine can resolve, read from `base_moves` itself."""
    return sorted(row[0] for row in conn.execute(
        "SELECT name FROM base_moves WHERE name IS NOT NULL AND TRIM(name) != ''"))


def english(entries, *keys):
    """The first English text among `entries`, trying each key in turn."""
    for entry in entries or []:
        if (entry.get('language') or {}).get('name') != 'en':
            continue
        for key in keys:
            value = (entry.get(key) or '').strip()
            if value:
                # PokeAPI wraps its text at the width of a Game Boy screen.
                return ' '.join(value.split())
    return ''


# **WHAT POKEAPI DOES NOT HAVE, WRITTEN OUT HERE.** Forty-two of the 938 come back empty
# and they are not all the same kind of gap:
#
#   * 36 Z-Moves - PokeAPI has no Z-Move entries at all, under any spelling;
#   * 5 Starmobile torque moves - present, but with no English text of any kind;
#   * `nihil-light` - this world added it before PokeAPI did.
#
# Only the last is written out. The other 41 have real effects and I would be inventing
# the wording; `!movedex` shows them with their numbers and says the description is one
# nobody has, which is true and is better than a confident guess.
LOCAL_TEXT = {
    'nihil-light': {
        'display': 'Nihil Light',
        'short_effect': "Strikes even Fairy types, which cannot refuse it.",
        'effect': "Inflicts regular damage. Fairy types are hit for neutral damage "
                  "rather than being immune; on a dual type, the other half of the "
                  "typing still applies normally.",
        'flavour': "The user attacks by unleashing a powerful light that defies all "
                   "laws of nature.",
        'generation': 9,
    },
}


def api_name(name):
    """
    What PokeAPI calls this move.

    **THIRTY-SIX Z-MOVES ARE STORED TWICE**, once per damage class -
    `acid-downpour--physical` and `acid-downpour--special` - because a Z-Move takes the
    class of the move it upgrades and the engine needs both rows. PokeAPI has one entry
    under the bare name, so the suffix is dropped on the way out and both rows are filled
    from it.
    """
    return str(name or '').split('--', 1)[0]


def fetch(name):
    """`(row, complaint)` for one move. Never raises."""
    if name in LOCAL_TEXT:
        # Written here rather than asked for. No request, so a re-run costs nothing.
        return dict(LOCAL_TEXT[name], name=name), None

    request = urllib.request.Request(API.format(api_name(name)),
                                     headers={'User-Agent': USER_AGENT})
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.load(response)
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None, f"{name}: PokeAPI has no such move"
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
    flavour = english(payload.get('flavor_text_entries'), 'flavor_text')

    complaint = None
    if not short and not full:
        if not flavour:
            return None, f"{name}: no English text of any kind"
        complaint = f"{name}: no effect entry, using the game's flavour text"

    # `effect_chance` is written into the text as a literal `$effect_chance`. Substituted
    # here rather than left for the card, which would have to know PokeAPI's template
    # syntax to show a sentence.
    chance = payload.get('effect_chance')
    if chance is not None:
        short = short.replace('$effect_chance', str(chance))
        full = full.replace('$effect_chance', str(chance))

    return {
        'name': name,
        'display': english(payload.get('names'), 'name') or name.replace('-', ' ').title(),
        'short_effect': short or flavour,
        'effect': full or flavour,
        'flavour': flavour,
        'generation': generation_number((payload.get('generation') or {}).get('name')),
    }, complaint


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument('--db', default=DB, help="path to ecosystem.db")
    parser.add_argument('--apply', action='store_true',
                        help="actually fetch and write; without it this only reports")
    parser.add_argument('--refresh', action='store_true',
                        help="re-fetch moves already in the table")
    parser.add_argument('--limit', type=int, default=0,
                        help="stop after this many fetches (for a trial run)")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"  no database at {args.db}")
        return 1

    conn = sqlite3.connect(args.db)
    wanted = wanted_moves(conn)

    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (TABLE,)).fetchone() is not None
    have = set()
    if exists:
        have = {row[0] for row in conn.execute(
            f"SELECT name FROM {TABLE} WHERE TRIM(COALESCE(short_effect, '')) != ''")}

    todo = wanted if args.refresh else [n for n in wanted if n not in have]

    print(f"\n  table {TABLE:<15}: {'exists' if exists else 'to be created'}")
    print(f"  moves in base_moves: {len(wanted)}")
    print(f"  already described  : {len(have)}")
    print(f"  to fetch           : {len(todo)}")
    if todo[:6]:
        print(f"      {', '.join(todo[:6])}{' …' if len(todo) > 6 else ''}")
        print(f"      about {len(todo) * (DELAY + 0.15) / 60:.0f} minutes")

    if not args.apply:
        print("\n  Nothing was written. Re-run with --apply to fetch these.")
        return 0

    if not todo:
        print("\n  Nothing to do; every move already has a description.")
        return 0

    backup = f"{args.db}.pre-movetext.{int(time.time())}"
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
                f"  (name, display, short_effect, effect, flavour, generation) "
                f"VALUES (?, ?, ?, ?, ?, ?) "
                f"ON CONFLICT(name) DO UPDATE SET "
                f"  display = excluded.display, "
                f"  short_effect = excluded.short_effect, "
                f"  effect = excluded.effect, "
                f"  flavour = excluded.flavour, "
                f"  generation = excluded.generation, "
                f"  fetched_at = CURRENT_TIMESTAMP",
                (row['name'], row['display'], row['short_effect'], row['effect'],
                 row['flavour'], row['generation']))
            written += 1

        if index % 50 == 0:
            conn.commit()
            rate = index / max(0.001, time.time() - started)
            print(f"      {index:>4}/{len(todo)}  ~{(len(todo) - index) / rate:.0f}s left")
        time.sleep(DELAY)

    conn.commit()

    total = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
    print(f"\n  written            : {written}")
    print(f"  rows now           : {total} of {len(wanted)} moves")

    if complaints:
        print(f"  flavour text used  : {len(complaints)}")
        for line in complaints[:8]:
            print(f"      {line}")
    if failures:
        print(f"  could not describe : {len(failures)}")
        for line in failures[:12]:
            print(f"      {line}")
        print("      (`!movedex` shows these with their numbers and no prose, rather "
              "than refusing them)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
