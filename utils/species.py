"""Turning what a player typed into a species the database actually has.

The GTS took a species name as free text, ran `.capitalize()` on it and stored it. The
matching engine then compared that string to another stored string. Both halves work
perfectly - and the whole thing fails silently the moment the two players spell a name
differently from each other or from the database.

The database spells things its own way: `mr-mime`, `nidoran-f`, `farfetchd`, `ho-oh`,
`type-null`, `jangmo-o`. **393 of the 1344 species names contain a hyphen.** A player
typing "Mr. Mime" or "Nidoran F" got a deposit that was accepted, listed, and could
never match anything, with nothing anywhere to say why.

Normalising both sides to letters-and-digits fixes almost all of it: "Mr. Mime",
"mr mime", "MR-MIME" and "mr-mime" all become `mrmime`. There are **zero collisions**
across the whole species table under that rule, so it cannot make two species
indistinguishable - which is the only thing that would make it a bad idea.
"""
import re
import sqlite3
from difflib import SequenceMatcher

from utils.constants import DB_FILE

# Discord allows at most 25 options in a select menu, which is why there is no dropdown
# of all 1344 species anywhere in this file. Everything here works towards getting a
# player to a list SHORT enough to be one.
MAX_CHOICES = 25

SPECIES_NAMES = []      # canonical, exactly as base_pokemon_species stores them
_BY_NORMAL = {}         # normalised -> canonical


def normalise(text):
    """Letters and digits only. 'Mr. Mime', 'mr mime' and 'mr-mime' all agree here."""
    return re.sub(r'[^a-z0-9]', '', str(text or '').lower())


try:
    with sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True) as _conn:
        SPECIES_NAMES = sorted(
            row[0] for row in _conn.execute(
                "SELECT name FROM base_pokemon_species WHERE name IS NOT NULL"))
    _BY_NORMAL = {normalise(name): name for name in SPECIES_NAMES}
    print(f"🔤 Indexed {len(SPECIES_NAMES)} species names for trade lookups.")
except Exception as e:                                          # pragma: no cover
    print(f"⚠️ WARNING: Could not index species names ({e}). "
          f"Trade species will not be validated.")


def resolve_species(text):
    """
    The canonical species name for what the player typed, or None.

    Deliberately forgiving about punctuation, spacing and case, and deliberately NOT
    forgiving about anything else - a near miss returns None and gets suggestions
    rather than being silently accepted, which is the behaviour that broke the GTS.
    """
    return _BY_NORMAL.get(normalise(text))


def suggest_species(text, limit=MAX_CHOICES):
    """
    Species this might have meant, best first, at most `limit` of them.

    Three passes, because they answer different mistakes: a prefix match catches a
    half-typed name, a substring match catches a forgotten prefix like "galar", and
    a similarity ratio catches an ordinary typo.
    """
    needle = normalise(text)
    if not needle:
        return []

    prefix, contains, close = [], [], []
    for name in SPECIES_NAMES:
        flat = normalise(name)
        if flat.startswith(needle):
            prefix.append(name)
        elif needle in flat:
            contains.append(name)
        elif len(needle) >= 3:
            score = SequenceMatcher(None, needle, flat).ratio()
            if score >= 0.72:
                close.append((score, name))

    close.sort(key=lambda pair: (-pair[0], pair[1]))
    ordered = prefix + contains + [name for _, name in close]

    seen, out = set(), []
    for name in ordered:
        if name not in seen:
            seen.add(name)
            out.append(name)
        if len(out) >= limit:
            break
    return out


def pretty_species(name):
    """A stored name as a player should see it: 'mr-mime' -> 'Mr Mime'."""
    return str(name or '').replace('-', ' ').title()
