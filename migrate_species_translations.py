"""
Rebuild `species_translations` so it can hold every language, and add three more.

**WHAT IS WRONG TODAY.** The table is keyed on `foreign_name` alone. A great many
species are spelled identically in several languages - Pikachu is Pikachu in French,
German, Spanish and Italian - so only the first insert of each spelling survived and the
rest were silently refused. Counted against the live database:

    JPN 1025    KOR 1025    FRE 1025
    GER  882    ESP  805    ITA   22

Italian has 22 rows and all 22 are Paradox species, because those are the ones whose
Italian names are unlike anybody else's. Pikachu has no German, Spanish or Italian row at
all. **1,366 names were imported and thrown away.**

That key is also what makes Rōmaji impossible: "Pikachu" in Rōmaji collides with
"Pikachu" in French, so the language the user asked for cannot be added until the key is
fixed. Rekeying on `(foreign_name, language_tag)` fixes both at once.

**WHAT THIS SCRIPT DOES.**

  1. rebuilds the table keyed on `(foreign_name, language_tag)`;
  2. adds a `folded` column - the name with its Latin accents removed - so a player
     typing `flabebe` catches Flabébé. 181 names are otherwise unreachable without a
     compose key;
  3. loads all nine languages from PokeAPI's own CSV, which recovers the 1,366 lost rows
     and adds Chinese Traditional, Chinese Simplified and Rōmaji.

Result: 9,225 rows across 1,025 species, up from 4,784.

**FOLDING IS LATIN-ONLY AND THAT IS NOT A TIDINESS DECISION.** Japanese dakuten are
Unicode combining marks. Fold kana blindly and カラカラ (Cubone) and ガラガラ (Marowak)
become the same string - along with 1,902 other kana and hangul names. Latin-only folding
changes 181 names and collides on none. `utils.translations.fold_name` is the one
implementation and this script imports it rather than keeping a copy.

**IT IS SAFE TO RUN WITH THE BOT UP.** `species_translations` is static reference data -
no row in it belongs to a player. The lookup asks `has_column` before reading `folded`,
so a bot running the new code against an unmigrated database behaves exactly as it does
today and picks up the new names on its next query. Running this against the OLD code is
equally safe: extra rows and an extra column are simply never read.

    python migrate_species_translations.py            # report only, writes nothing
    python migrate_species_translations.py --apply    # do it

Idempotent. Running it twice is a no-op the second time.

The names come from PokeAPI's CSV dump over the network. Pass `--names-csv <path>` to
use a local copy instead - the file is `pokemon_species_names.csv`.
"""

import argparse
import csv
import io
import os
import shutil
import sqlite3
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.translations import LANGUAGES, LANGUAGE_ORDER, fold_name, normalise_name

DB = 'ecosystem.db'
TABLE = 'species_translations'
NAMES_CSV = ('https://raw.githubusercontent.com/PokeAPI/pokeapi/master/'
             'data/v2/csv/pokemon_species_names.csv')

# PokeAPI's language ids, which its CSV uses as a foreign key. Derived from LANGUAGES so
# the two cannot drift: the module says which PokeAPI language each tag is, and this is
# the id that language has in `languages.csv`.
POKEAPI_LANGUAGE_IDS = {
    'ja-hrkt': 1, 'ja-roma': 2, 'ko': 3, 'zh-hant': 4, 'fr': 5,
    'de': 6, 'es': 7, 'it': 8, 'en': 9, 'ja': 11, 'zh-hans': 12,
}
WANTED = {POKEAPI_LANGUAGE_IDS[entry['pokeapi']]: tag
          for tag, entry in LANGUAGES.items()}

# Names live against the BASE species only. Everything above 1025 in our table is a form
# - `deoxys-attack`, `rotom-heat`, `giratina-origin` - and the games do not give those
# separate names in any language.
MAX_BASE_SPECIES = 1025


def fetch_names(source):
    """The PokeAPI name rows, from the network or from a local CSV."""
    if source:
        with open(source, encoding='utf-8') as handle:
            body = handle.read()
    else:
        request = urllib.request.Request(
            NAMES_CSV, headers={'User-Agent': 'KyuDex-migration/1.0'})
        body = urllib.request.urlopen(request, timeout=120).read().decode('utf-8')
    return list(csv.DictReader(io.StringIO(body)))


def build_rows(names, species, max_species=MAX_BASE_SPECIES):
    """
    The rows the table should hold, and anything wrong with them.

    `species` is {pokedex_id: our name for it}. The join is on the ID rather than on the
    name deliberately: we call species 386 `deoxys-normal` and PokeAPI calls it `deoxys`,
    and there are a dozen more like that. Matching on the id keeps every foreign name
    pointing at the name THIS database uses.

    The `max_species` cut happens HERE rather than in the SELECT that builds `species`,
    so that it is part of the rule this function expresses and can be driven by a test.
    Filtering in the query instead left it inert - PokeAPI's list stops at 1025 anyway,
    so removing the cap changed nothing that could be observed.
    """
    rows, problems = [], []
    seen = {}

    for record in names:
        try:
            species_id = int(record['pokemon_species_id'])
        except (KeyError, TypeError, ValueError):
            continue
        tag = WANTED.get(int(record.get('local_language_id') or 0))
        if not tag or species_id not in species or species_id > max_species:
            continue

        foreign = normalise_name(record.get('name'))
        if not foreign:
            continue
        english = species[species_id]

        key = (foreign, tag)
        if key in seen:
            # Two rows for the same name and language. If they disagree about the
            # species the source is broken and the migration stops; if they agree it is
            # a duplicate row and one of them is enough.
            #
            # This used to only `continue` on the disagreeing case, which let an exact
            # duplicate through into `rows` and needed a second uniqueness check further
            # down to catch it. Deduping here means the rows this returns are unique by
            # construction, and that second check is gone rather than sitting unreachable.
            if seen[key] != english:
                problems.append(
                    f"`{foreign}` is {tag} for both `{seen[key]}` and `{english}`")
            continue
        seen[key] = english
        rows.append((foreign, english, tag, fold_name(foreign)))

    covered = {tag: sum(1 for _f, _e, t, _d in rows if t == tag)
               for tag in LANGUAGE_ORDER}
    for tag, count in covered.items():
        if count == 0:
            problems.append(f"no {tag} names were found in the source at all")
    return rows, covered, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=DB, help="path to ecosystem.db")
    parser.add_argument('--apply', action='store_true',
                        help="actually write; without it this only reports")
    parser.add_argument('--names-csv', default=None,
                        help="local pokemon_species_names.csv instead of the network")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"  no database at {args.db}")
        return 1

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    species = {row[0]: row[1] for row in conn.execute(
        "SELECT pokedex_id, name FROM base_pokemon_species WHERE name IS NOT NULL")}
    print(f"\n  species in this database      : {len(species)} "
          f"({sum(1 for k in species if k <= MAX_BASE_SPECIES)} base, the rest forms)")

    before = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
    was = {row[0]: row[1] for row in conn.execute(
        f"SELECT language_tag, COUNT(*) FROM {TABLE} GROUP BY 1")}
    print(f"  rows in {TABLE} today : {before}")
    print("    " + "  ".join(f"{tag} {was.get(tag, 0)}" for tag in LANGUAGE_ORDER))

    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({TABLE})")]
    keyed = 'folded' in columns
    print(f"  already rebuilt              : {'yes' if keyed else 'no'}")

    try:
        names = fetch_names(args.names_csv)
    except Exception as e:
        print(f"\n  could not read the name list: {e}")
        print("  Pass --names-csv <path> to use a local pokemon_species_names.csv.")
        conn.close()
        return 1
    print(f"  name rows read from source   : {len(names)}")

    rows, covered, problems = build_rows(names, species)

    print(f"\n  rows that would be written   : {len(rows)}")
    for tag in LANGUAGE_ORDER:
        moved = covered[tag] - was.get(tag, 0)
        note = "unchanged" if moved == 0 else f"{moved:+d}"
        print(f"    {tag} {LANGUAGES[tag]['label']:<24} {covered[tag]:>5}   {note}")

    folds = sum(1 for _f, _e, _t, d in rows if d != _f)
    print(f"  names reachable only by folding: {folds}")

    # The claim worth refusing on: no name that is in the table today may be missing from
    # the table afterwards. Uniqueness is not checked here because `build_rows` dedupes,
    # so a check for it could not fail - it was there and a negative control walked
    # straight through it.
    existing = {(row[0], row[1]) for row in conn.execute(
        f"SELECT foreign_name, language_tag FROM {TABLE}")}
    dropped = existing - {(f, t) for f, _e, t, _d in rows}
    if dropped:
        problems.append(f"{len(dropped)} existing name(s) would be lost, e.g. "
                        f"{sorted(dropped)[:3]}")

    if problems:
        print("\n  PROBLEMS — nothing was changed:")
        for problem in problems:
            print(f"    • {problem}")
        conn.close()
        return 1

    if not args.apply:
        print("\n  Nothing was written. Re-run with --apply to make these changes.")
        conn.close()
        return 0

    backup = f"{args.db}.pre-translations.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written  : {backup}")

    try:
        conn.execute("BEGIN")
        conn.execute(f"DROP TABLE IF EXISTS {TABLE}_rebuild")
        conn.execute(f"""
            CREATE TABLE {TABLE}_rebuild (
                foreign_name  TEXT NOT NULL,
                english_name  TEXT NOT NULL,
                language_tag  TEXT NOT NULL,
                folded        TEXT,
                PRIMARY KEY (foreign_name, language_tag)
            )
        """)
        conn.executemany(
            f"INSERT INTO {TABLE}_rebuild "
            f"(foreign_name, english_name, language_tag, folded) VALUES (?, ?, ?, ?)",
            rows)
        conn.execute(f"DROP TABLE {TABLE}")
        conn.execute(f"ALTER TABLE {TABLE}_rebuild RENAME TO {TABLE}")
        # `!catch` looks a typed name up on every throw, and the dex reads every name for
        # one species. Both were table scans on a 9,225-row table.
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_folded "
                     f"ON {TABLE} (folded)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_english "
                     f"ON {TABLE} (english_name)")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"\n  FAILED, nothing changed: {e}")
        print(f"  the backup at {backup} is identical to the database as it stands.")
        conn.close()
        return 1

    after = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
    species_covered = conn.execute(
        f"SELECT COUNT(DISTINCT english_name) FROM {TABLE}").fetchone()[0]
    print(f"\n  done. {after} names across {species_covered} species "
          f"({after - before:+d}).")
    print("  The bot picks this up on its next lookup — no restart needed.")
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
