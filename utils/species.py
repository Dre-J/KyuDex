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

**TWO MORE INDEXES SIT BEHIND THAT ONE**, both added because `!dex` had no spawn to
prefix-match against and so refused names that plainly exist: the stem index, for the
thirty-odd species with no bare row of their own (`oinkologne` is not in the table;
`oinkologne-male` is), and the word index, for a form name typed in the order English
puts it in (`mega charizard x`). Each is built by REFUSING anything ambiguous, and each
is consulted only after an exact miss - so both can add spellings and neither can ever
take one away. The section comments below carry the rules.
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
_BY_STEM = {}           # normalised bare species name -> the form that carries its number
_BY_WORDS = {}          # sorted word tuple -> canonical, for names typed in any order


def normalise(text):
    """Letters and digits only. 'Mr. Mime', 'mr mime' and 'mr-mime' all agree here."""
    return re.sub(r'[^a-z0-9]', '', str(text or '').lower())


# ==========================================
# 🔀 SPECIES THAT HAVE NO BARE NAME
# ==========================================
# **Oinkologne is not in the table.** `oinkologne-male` is, at #916, and
# `oinkologne-female` is, at #10254 - and there is no row spelt just `oinkologne` for
# anybody to find. The same is true of Indeedee, Deoxys, Urshifu, Toxtricity, Basculin,
# Lycanroc and twenty-five others: the species has a national dex number, and the only
# names it answers to are the ones with a form on the end.
#
# `!catch` never noticed, because it prefix-matches what the player typed against the
# spawn already standing in the channel. `!dex` did notice, because it has nothing to
# match against but the table - so `!dex oinkologne` came back "no specimen on file"
# about a species with a picture and a number, and the way through was to already know
# that it wanted `oinkologne-male`.
#
# So a stem index. For every group of forms, the part of the name they all share becomes
# a spelling of the DEFAULT form - the one holding the national dex number - under three
# rules that keep it from guessing:
#
#   1. only groups with more than one form, so nothing invents a stem for `ho-oh`,
#      `great-tusk` or `jangmo-o` out of the half of the name before the hyphen;
#   2. never a stem that is already a species name, so an exact match always wins - a
#      `pikachu` typed at the dex is #25 and not a Rock Star Pikachu;
#   3. never a stem two groups could both mean, and never one that would shadow a
#      species outside its own group.
#
# It yields 35 spellings for 32 species on the current table, with nothing ambiguous -
# three of them are the deeper cuts of Maushold, whose forms share `maushold-family-of`
# and whose bare name would otherwise still have been missing. Worth re-counting if the
# species table is ever reloaded, since rule 3 drops collisions silently.
def _stem_index(rows, canonical, all_names):
    """`{normalised stem: canonical name}` from `(base, pokedex_id, is_default, name)`."""
    groups = {}
    for base, pokedex_id, is_default, name in rows:
        groups.setdefault(base, []).append((pokedex_id, is_default, name))

    claims = {}
    for members in groups.values():
        if len(members) < 2:
            continue                                            # rule 1
        parts = [name.split('-') for _id, _default, name in members]
        shared = 0
        while (shared < min(len(p) for p in parts)
               and len({p[shared] for p in parts}) == 1):
            shared += 1
        if not shared:
            continue

        # The form the national dex numbers, which is what somebody typing the bare
        # name is asking for. `is_default` first, then the lower number - Meowstic is
        # #678 male and #10025 female, and the male is the one with the entry.
        owner = min(members, key=lambda m: (0 if m[1] else 1, m[0]))[2]
        held = {name for _id, _default, name in members}

        # Every depth of the shared part, so both `maushold` and the full
        # `maushold-family-of` reach the same place.
        for cut in range(1, shared + 1):
            stem = "-".join(parts[0][:cut])
            flat = normalise(stem)
            if not flat or flat in canonical:                   # rule 2
                continue
            # rule 3, second half: a stem must not reach past its own group.
            if any(other.startswith(f"{stem}-") and other not in held
                   for other in all_names):
                continue
            claims.setdefault(flat, set()).add(owner)

    # rule 3, first half.
    return {flat: next(iter(owners)) for flat, owners in claims.items()
            if len(owners) == 1}


# ==========================================
# 🔤 THE OTHER ORDER PEOPLE TYPE A FORM IN
# ==========================================
# The table spells a form's name subject-first - `charizard-mega-x`, `zigzagoon-galar`,
# `raichu-alola` - and English does not. Nobody says "Charizard Mega X" out loud; they
# say "Mega Charizard X", and `!dex mega charizard x` came back as nothing on file.
#
# Matching on the SET of words rather than their order fixes all of it at once, and the
# adjectives below fix the rest: a player says "Alolan Raichu", never "Alola Raichu".
#
# Ambiguity is handled the same way the stem index handles it - by refusing. Two species
# whose names are anagrams of each other at the word level would name nothing in
# particular, so neither gets an entry. There are currently none.
NAME_WORD_ALIASES = {
    'alolan': 'alola', 'galarian': 'galar', 'hisuian': 'hisui', 'paldean': 'paldea',
    'gigantamax': 'gmax',
}


def _words_of(text):
    """A name as its parts, normalised, aliased and sorted. Order stops mattering here."""
    parts = [p for p in re.split(r'[^a-z0-9]+', str(text or '').lower()) if p]
    return tuple(sorted(NAME_WORD_ALIASES.get(p, p) for p in parts))


try:
    with sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True) as _conn:
        SPECIES_NAMES = sorted(
            row[0] for row in _conn.execute(
                "SELECT name FROM base_pokemon_species WHERE name IS NOT NULL"))
        _BY_NORMAL = {normalise(name): name for name in SPECIES_NAMES}

        _claims = {}
        for _name in SPECIES_NAMES:
            _claims.setdefault(_words_of(_name), set()).add(_name)
        _BY_WORDS = {words: next(iter(owners)) for words, owners in _claims.items()
                     if len(owners) == 1 and len(words) > 1}
        try:
            _forms = _conn.execute("""
                SELECT f.base_pokedex_id, f.pokedex_id, f.is_default, s.name
                FROM species_forms f
                JOIN base_pokemon_species s ON s.pokedex_id = f.pokedex_id
                WHERE s.name IS NOT NULL
            """).fetchall()
            _BY_STEM = _stem_index(_forms, set(_BY_NORMAL), set(SPECIES_NAMES))
        except Exception as _form_error:                        # pragma: no cover
            # A database without species_forms is a thinner lookup, not a broken one:
            # every full name still resolves exactly as it did before.
            print(f"⚠️ Could not index form stems ({_form_error}). "
                  f"Bare species names will not resolve.")
    print(f"🔤 Indexed {len(SPECIES_NAMES)} species names "
          f"({len(_BY_STEM)} bare form names) for trade and dex lookups.")
except Exception as e:                                          # pragma: no cover
    print(f"⚠️ WARNING: Could not index species names ({e}). "
          f"Trade species will not be validated.")


def resolve_species(text):
    """
    The canonical species name for what the player typed, or None.

    Deliberately forgiving about punctuation, spacing and case, and deliberately NOT
    forgiving about anything else - a near miss returns None and gets suggestions
    rather than being silently accepted, which is the behaviour that broke the GTS.

    Two additions, tried strictly in this order and only ever after an exact miss, so
    neither can take a spelling away from the species it already reached:

      1. the stem index - a species whose every row carries a form suffix also answers
         to its bare name, so `oinkologne` finds #916;
      2. the word index - a form name typed in the order English puts it in, so
         `mega charizard x` finds `charizard-mega-x`.
    """
    flat = normalise(text)
    return (_BY_NORMAL.get(flat) or _BY_STEM.get(flat)
            or _BY_WORDS.get(_words_of(text)))


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
