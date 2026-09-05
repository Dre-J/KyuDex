"""
Import what Pokemon Showdown's players actually run.

**SMOGON PUBLISHES ITS USAGE STATS AS FLAT TEXT**, one file per format per month, at
`smogon.com/stats/YYYY-MM/moveset/`. Each is about 800KB and carries, per species: the
abilities, items, EV spreads, moves, Tera types and teammates people used, with the
percentage of sets each appeared in. One request per format, and nothing at runtime ever
calls out again.

**THE PERCENTAGES ARE SMOGON'S AND THE LEGALITY IS OURS.** A Smogon set is advice from a
different game: level 100, team preview, its own banlist, and a movepool frozen to one
generation. This world has level caps, its own rules, and a movepool spanning every
generation. So the numbers are stored EXACTLY as published and the filtering happens on
the way out, in `utils/showdown.py` - which means the card can always say how much of a
set it had to drop, rather than quietly presenting a filtered percentage as if it were
the real one.

**TERA TYPES ARE IMPORTED AND WILL NEVER BE SHOWN.** Nothing in this engine terastallises
- `tera_type` is read by exactly one move and set by nothing - so a Tera panel would be
advice a player cannot take. Stored anyway, because the day the mechanic lands the data
is already here and the change is a display one.

**IDEMPOTENT.** A format+month already imported is skipped; `--refresh` re-fetches. The
rows are keyed by format and species WITHOUT the month, so importing a newer month
replaces the old figures rather than accumulating two sets of them.

    python migrate_showdown_spreads.py                    # report only
    python migrate_showdown_spreads.py --apply            # fetch and write
    python migrate_showdown_spreads.py --apply --format gen9uu
"""
import argparse
import os
import re
import shutil
import sqlite3
import time
import urllib.error
import urllib.request

DB = 'ecosystem.db'
USAGE_TABLE = 'showdown_usage'
SPECIES_TABLE = 'showdown_species'

INDEX = 'https://www.smogon.com/stats/'
MOVESET = 'https://www.smogon.com/stats/{month}/moveset/{format}-{rating}.txt'

USER_AGENT = 'KyuDex-migration/1.0 (+https://github.com/Dre-J/KyuDex)'

# The rating cutoff. 1695 is the one Smogon itself treats as "good players" for OU-level
# formats; 0 would include every ladder game ever played, which is a different question.
DEFAULT_RATING = 1695
DEFAULT_FORMATS = ('gen9ou',)

# The section headings inside a moveset file, and what each becomes in the table. Anything
# not named here is skipped - "Checks and Counters" is a matchup table rather than a set,
# and its lines are shaped differently.
SECTIONS = {
    'Abilities': 'ability',
    'Items': 'item',
    'Spreads': 'spread',
    'Moves': 'move',
    'Tera Types': 'tera',
    'Teammates': 'teammate',
}

# `| Rocky Helmet 26.353% |` - the value may contain spaces, hyphens and colons.
ENTRY = re.compile(r'^\|\s+(.+?)\s+([\d.]+)%\s*\|$')
RAW_COUNT = re.compile(r'^\|\s+Raw count:\s+(\d+)\s*\|$')
VIABILITY = re.compile(r'^\|\s+Viability Ceiling:\s+(\d+)\s*\|$')
BORDER = re.compile(r'^\+-+\+$')

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {USAGE_TABLE} (
    format   TEXT NOT NULL,
    species  TEXT NOT NULL,
    kind     TEXT NOT NULL,
    value    TEXT NOT NULL,
    usage    REAL,
    month    TEXT,
    PRIMARY KEY (format, species, kind, value)
);
CREATE INDEX IF NOT EXISTS idx_{USAGE_TABLE}_lookup
    ON {USAGE_TABLE} (species, format, kind);
CREATE TABLE IF NOT EXISTS {SPECIES_TABLE} (
    format    TEXT NOT NULL,
    species   TEXT NOT NULL,
    raw_count INTEGER,
    viability INTEGER,
    month     TEXT,
    PRIMARY KEY (format, species)
);
"""


def fetch_text(url):
    """The body at `url`, or None. A User-Agent is not optional on smogon.com."""
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.read().decode('utf-8', 'replace')
    except Exception as e:
        print(f"  could not fetch {url}: {type(e).__name__} {e}")
        return None


def latest_month():
    """The newest `YYYY-MM` Smogon has published, or None."""
    body = fetch_text(INDEX)
    if not body:
        return None
    months = sorted(set(re.findall(r'href="(20\d\d-\d\d)/"', body)))
    return months[-1] if months else None


def parse_moveset(text):
    """
    `{species: {'raw_count', 'viability', 'entries': [(kind, value, usage)]}}`.

    The format is a run of ASCII-art blocks: a species name, its counts, then one block
    per section. Parsed on the section HEADING rather than on position, because the
    sections a species has depend on the format - a Little Cup file has no Tera Types.
    """
    found = {}
    species = None
    section = None

    lines = [raw.rstrip() for raw in text.splitlines()]

    for index, line in enumerate(lines):
        # **A SPECIES HEADER IS RECOGNISED BY WHAT FOLLOWS IT, NOT BY WHAT PRECEDES IT.**
        # The first attempt took "the line after a border with nothing open" and read the
        # Checks and Counters entries as species - `Sinistcha 75.754 (81.54±1.45)` became
        # a Pokemon - and found 105 of the six hundred. The header is the only block
        # anywhere in the file shaped border / name / border / `Raw count:`, so that is
        # what is matched.
        if (BORDER.match(line)
                and index + 3 < len(lines)
                and lines[index + 1].startswith('|')
                and BORDER.match(lines[index + 2])
                and RAW_COUNT.match(lines[index + 3])):
            species = lines[index + 1].strip('|').strip()
            found.setdefault(species, {'raw_count': None, 'viability': None,
                                       'entries': []})
            section = None
            continue

        if BORDER.match(line):
            section = None
            continue
        if not line.startswith('|') or species is None:
            continue

        inner = line.strip('|').strip()

        count = RAW_COUNT.match(line)
        if count:
            found[species]['raw_count'] = int(count.group(1))
            continue
        ceiling = VIABILITY.match(line)
        if ceiling:
            found[species]['viability'] = int(ceiling.group(1))
            continue

        if inner in SECTIONS:
            section = SECTIONS[inner]
            continue
        if inner.startswith('Checks and Counters'):
            # A matchup table rather than a set. Its lines carry no trailing percentage
            # so they would not match ENTRY anyway, but closing the section says so.
            section = None
            continue

        if section is None:
            continue

        entry = ENTRY.match(line)
        if entry:
            value, usage = entry.group(1), float(entry.group(2))
            # "Other" is the tail Smogon groups together. It is a real percentage and a
            # useless one - it names no set - so it is dropped rather than stored as a
            # value nobody can act on.
            if value != 'Other':
                found[species]['entries'].append((section, value, usage))

    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument('--db', default=DB, help="path to ecosystem.db")
    parser.add_argument('--apply', action='store_true',
                        help="actually fetch and write; without it this only reports")
    parser.add_argument('--refresh', action='store_true',
                        help="re-fetch formats already imported")
    parser.add_argument('--format', action='append', dest='formats',
                        help="a Showdown format id; repeatable (default: gen9ou)")
    parser.add_argument('--month', help="YYYY-MM (default: the newest published)")
    parser.add_argument('--rating', type=int, default=DEFAULT_RATING,
                        help=f"ladder rating cutoff (default: {DEFAULT_RATING})")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"  no database at {args.db}")
        return 1

    formats = tuple(args.formats or DEFAULT_FORMATS)
    month = args.month or latest_month()
    if not month:
        print("  could not work out which month to import, and none was given")
        return 1

    conn = sqlite3.connect(args.db)
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (USAGE_TABLE,)).fetchone() is not None

    already = {}
    if exists:
        already = {row[0]: (row[1], row[2]) for row in conn.execute(
            f"SELECT format, month, COUNT(*) FROM {USAGE_TABLE} GROUP BY format")}

    todo = [f for f in formats if args.refresh or already.get(f, ('',))[0] != month]

    print(f"\n  month              : {month}")
    print(f"  rating cutoff      : {args.rating}")
    print(f"  table {USAGE_TABLE:<14}: {'exists' if exists else 'to be created'}")
    for name in formats:
        held = already.get(name)
        state = f"{held[1]} rows from {held[0]}" if held else "not imported"
        print(f"      {name:<14} {state}")
    print(f"  to fetch           : {len(todo)}")

    if not args.apply:
        print("\n  Nothing was written. Re-run with --apply to fetch these.")
        return 0
    if not todo:
        print("\n  Nothing to do; every format is already at this month.")
        return 0

    backup = f"{args.db}.pre-showdown.{int(time.time())}"
    shutil.copy2(args.db, backup)
    print(f"\n  backup written     : {backup}")

    conn.executescript(SCHEMA)
    conn.commit()

    for name in todo:
        url = MOVESET.format(month=month, format=name, rating=args.rating)
        print(f"\n  fetching {name} …")
        body = fetch_text(url)
        if not body:
            print(f"      skipped: nothing at {url}")
            continue

        parsed = parse_moveset(body)
        if not parsed:
            print("      skipped: nothing parsed - the file's shape may have changed")
            continue

        # REPLACED, NOT MERGED. A species that fell out of the format between two months
        # would otherwise keep its old rows for ever, and the card would present figures
        # from a metagame that no longer exists.
        conn.execute(f"DELETE FROM {USAGE_TABLE} WHERE format = ?", (name,))
        conn.execute(f"DELETE FROM {SPECIES_TABLE} WHERE format = ?", (name,))

        rows = 0
        for species, block in parsed.items():
            conn.execute(
                f"INSERT OR REPLACE INTO {SPECIES_TABLE} "
                f"  (format, species, raw_count, viability, month) VALUES (?, ?, ?, ?, ?)",
                (name, species, block['raw_count'], block['viability'], month))
            for kind, value, usage in block['entries']:
                conn.execute(
                    f"INSERT OR REPLACE INTO {USAGE_TABLE} "
                    f"  (format, species, kind, value, usage, month) "
                    f"VALUES (?, ?, ?, ?, ?, ?)",
                    (name, species, kind, value, usage, month))
                rows += 1
        conn.commit()
        print(f"      {len(parsed)} species, {rows} rows")

    total = conn.execute(f"SELECT COUNT(*) FROM {USAGE_TABLE}").fetchone()[0]
    species = conn.execute(
        f"SELECT COUNT(DISTINCT species) FROM {USAGE_TABLE}").fetchone()[0]
    print(f"\n  rows now           : {total} across {species} species")
    print("\n  Nothing is filtered here. `utils/showdown.py` drops what this world "
          "cannot field, on the way out, so the card can say how much it dropped.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
