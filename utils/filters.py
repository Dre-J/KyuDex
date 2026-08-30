"""
The `!pc` filter language: dotted flags that stack.

    !pc .shiny .ivs d
    !pc .spatkiv 31 .nature adamant
    !pc .level 50-100 .gmax .ot 1234567890
    !pc charizard .iv >=90 .tag competitive

WHY A PARSER AND NOT MORE `elif`s. The old filter was a chain of `arg.startswith("x:")`
tests written inline in the command, and it could do four things: a tag, a type, shiny,
and one of four sorts. Every new filter was another branch in the middle of a Discord
handler, which meant none of them could be tested without a Discord context, and the
column names were being pasted into an f-string next to the values.

Everything here is a lookup in `FIELDS`. **A column name can only ever come out of that
map** - never out of the player's typing - and every value is a bound parameter. That is
the whole reason the SQL is assembled here rather than in the cog: it is the one place
where getting it wrong would matter, so it is the one place with no user-controlled
identifiers in it.

THE GRAMMAR is deliberately small:

    .flag              a switch          .shiny  .gmax
    .flag value        a filter          .level 50   .nature adamant
    .flag=value        the same thing    .level=50
    .flag a|d          a sort            .ivs d  .level a
    bare word          a name search     charizard

A value may be a plain number, a comparison, or a range: `31`, `>=25`, `<10`, `20-31`.
Anything a field does not understand is refused BY NAME rather than ignored, because a
filter that silently does nothing is worse than one that says it cannot.
"""

import re

from utils.constants import IV_PERFECT_TOTAL

# The sort words. `a`/`d` because that is what the request asked for; the longer forms
# because people type them.
ASCENDING = ('a', 'asc', 'ascending', 'up', 'low', 'lowest')
DESCENDING = ('d', 'desc', 'descending', 'down', 'high', 'highest', 'best')

IV_TOTAL_SQL = ("(cp.iv_hp + cp.iv_attack + cp.iv_defense + cp.iv_sp_atk "
                "+ cp.iv_sp_def + cp.iv_speed)")
# The percentage the PC list prints. `.iv 90` means the 90% a player can see on the
# line, not a raw total of 90 - matching what is displayed is what makes the filter
# guessable. `.ivtotal` is there for anybody who wants the raw 0-186 sum.
#
# 186 comes from IV_PERFECT_TOTAL rather than being typed here. It was written inline in
# this string and again in `cogs/ecology.py`'s PC line, which is two copies of a number
# that has to agree with IV_MAX - and if they ever disagreed, the filter would quietly
# stop selecting what the list displays.
IV_PERCENT_SQL = f"({IV_TOTAL_SQL} * 100 / {IV_PERFECT_TOTAL})"


class Field:
    """
    One filterable column.

    `kind` decides how a value is read:
      'number'  - a figure, a comparison or a range
      'text'    - matched case-insensitively, exactly
      'like'    - matched case-insensitively, anywhere in the value
      'switch'  - takes no value at all
    """

    def __init__(self, sql, kind, label, sortable=True, aliases=(), note=None):
        self.sql = sql
        self.kind = kind
        self.label = label
        self.sortable = sortable
        self.aliases = aliases
        self.note = note


FIELDS = {
    # --- individual IVs, the thing the request named ---
    'hpiv':      Field('cp.iv_hp', 'number', 'HP IV', aliases=('ivhp',)),
    'atkiv':     Field('cp.iv_attack', 'number', 'Attack IV',
                       aliases=('ivatk', 'attackiv', 'ivattack')),
    'defiv':     Field('cp.iv_defense', 'number', 'Defence IV',
                       aliases=('ivdef', 'defenceiv', 'defenseiv')),
    'spatkiv':   Field('cp.iv_sp_atk', 'number', 'Sp. Attack IV',
                       aliases=('ivspatk', 'spaiv', 'ivspa')),
    'spdefiv':   Field('cp.iv_sp_def', 'number', 'Sp. Defence IV',
                       aliases=('ivspdef', 'spdiv', 'ivspd')),
    'speiv':     Field('cp.iv_speed', 'number', 'Speed IV',
                       aliases=('ivspe', 'speediv', 'ivspeed', 'spdeiv')),

    # --- the aggregates ---
    'iv':        Field(IV_PERCENT_SQL, 'number', 'IV %', aliases=('ivs', 'ivpercent')),
    'ivtotal':   Field(IV_TOTAL_SQL, 'number', 'IV total', aliases=('ivsum',)),

    # --- the rest of the sheet ---
    'level':     Field('cp.level', 'number', 'Level', aliases=('lvl',)),
    'happiness': Field('cp.happiness', 'number', 'Happiness',
                       aliases=('friendship', 'happy')),
    'nature':    Field('cp.nature', 'text', 'Nature'),
    'ability':   Field('cp.ability', 'like', 'Ability', aliases=('abil',)),
    'gender':    Field('cp.gender', 'text', 'Gender', aliases=('sex',)),
    'tag':       Field('cp.custom_tag', 'like', 'Tag', aliases=('label',)),
    'ot':        Field('cp.original_user_id', 'text', 'Original Trainer',
                       aliases=('og', 'ogtrainer', 'originaltrainer')),
    'name':      Field('cp.name', 'like', 'Species', aliases=('species', 'dex')),
    'nickname':  Field('cp.nickname', 'like', 'Nickname', aliases=('nick',)),
    'box':       Field('cp.box_number', 'number', 'Box number', aliases=('slot',)),
    'lang':      Field('cp.origin_language', 'text', 'Language',
                       aliases=('language', 'origin')),
    'size':      Field('cp.height_multiplier', 'number', 'Size'),

    # --- switches ---
    'shiny':     Field('cp.is_shiny', 'switch', 'Shiny'),
    'gmax':      Field('cp.gmax_factor', 'switch', 'Gigantamax',
                       aliases=('gigantamax', 'gmaxfactor')),
    'starter':   Field('cp.is_starter', 'switch', 'Starter'),
}

# Flat lookup, aliases folded in. Built once, and asserted to have no collisions -
# an alias that silently shadowed a real field would make a filter mean something
# other than its name.
LOOKUP = {}
for _key, _field in FIELDS.items():
    for _name in (_key,) + tuple(_field.aliases):
        assert _name not in LOOKUP, f"duplicate filter name: {_name}"
        LOOKUP[_name] = _key

# `type` is not a caught_pokemon column - it lives in base_pokemon_types - so it gets its
# own clause rather than a Field. Kept in the language because the old parser had it and
# removing a filter people use is not an upgrade.
TYPE_SQL = ("EXISTS (SELECT 1 FROM base_pokemon_types t "
            "WHERE t.pokedex_id = cp.pokedex_id AND LOWER(t.type_name) = ?)")

GENDER_WORDS = {'m': 'M', 'male': 'M', 'boy': 'M',
                'f': 'F', 'female': 'F', 'girl': 'F',
                'n': 'None', 'none': 'None', 'genderless': 'None',
                'unknown': 'None', 'x': 'None'}

SWITCH_NEGATIONS = ('not', 'no', 'false', 'off', '0')

_RANGE = re.compile(r'^(\d+)\s*-\s*(\d+)$')
_COMPARISON = re.compile(r'^(>=|<=|>|<|=|!=)?\s*(\d+)$')


def _number_clause(sql, raw):
    """A numeric value as `(clause, params, complaint)`."""
    text = str(raw).strip().replace(' ', '')

    ranged = _RANGE.match(text)
    if ranged:
        low, high = int(ranged.group(1)), int(ranged.group(2))
        if low > high:
            return None, None, f"⚠️ `{raw}` runs backwards. Try `{high}-{low}`."
        return f"{sql} BETWEEN ? AND ?", [low, high], None

    compared = _COMPARISON.match(text)
    if compared:
        operator = compared.group(1) or '='
        return f"{sql} {operator} ?", [int(compared.group(2))], None

    return None, None, (f"⚠️ `{raw}` is not a number, a comparison or a range. "
                        f"Try `31`, `>=25`, `<10` or `20-31`.")


def _sort_direction(value):
    """'ASC', 'DESC', or None if this word is not a direction at all."""
    word = str(value or '').strip().lower()
    if word in ASCENDING:
        return 'ASC'
    if word in DESCENDING:
        return 'DESC'
    return None


def _tokenise(query):
    """
    The raw query split into `(flag, value)` pairs and bare words.

    A flag's value is the next token when that token is not itself a flag. `.shiny .ivs d`
    therefore reads as a switch and a sort rather than as `.shiny` taking `.ivs`.

    The third element is whether the value was ATTACHED with `=` or `:`. That is the
    escape hatch for the one real collision in this grammar: `a` and `d` mean ascending
    and descending, so `.tag d` sorts by tag - which is not what the player whose tag is
    actually the letter `d` meant. An attached value is always a filter and never a
    sort, so `.tag=d` says the other thing.
    """
    tokens = str(query or '').split()
    out = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith('.') and len(token) > 1:
            body = token[1:]
            value, explicit = None, False
            for separator in ('=', ':'):
                if separator in body:
                    body, _, value = body.partition(separator)
                    explicit = True
                    break
            if value is None and index + 1 < len(tokens):
                nxt = tokens[index + 1]
                if not nxt.startswith('.'):
                    value = nxt
                    index += 1
            out.append((body.lower(), value, explicit))
        else:
            out.append((None, token, False))
        index += 1
    return out


EVO_FLAGS = ('evo', 'evos', 'family', 'line', 'evolution', 'evolutions')


def evo_targets(query):
    """
    The species named by any `.evo` flag, so a caller can resolve them before parsing.

    `.evo` is the one filter that cannot be answered without the database - an
    evolutionary family is a graph walk, not a column - and this module is deliberately
    a pure parser with no connection of its own. So resolution is split in two: the cog
    asks what needs looking up, looks it up, and hands the answer back to `parse_filters`.
    The alternative was to give the parser a database handle, which would have made
    every test of every OTHER filter need one too.
    """
    return [value for flag, value, _explicit in _tokenise(str(query or ''))
            if flag in EVO_FLAGS and value]


def parse_filters(query, family_ids=None, extra_flags=()):
    """
    A `!pc` query as `(where_clauses, params, order_by, applied, complaint)`.

    `where_clauses` is a list of SQL fragments to AND together; `params` are their bound
    values in order. `order_by` is a full ORDER BY clause. `applied` is a list of short
    human-readable descriptions, for showing the player what actually took effect.

    A complaint stops everything: a query with one bad filter in it runs NOTHING, rather
    than quietly running the rest. Showing a filtered list that ignored half the request
    is how somebody releases the wrong specimen.
    """
    clauses, params, applied = [], [], []
    order_by = "ORDER BY cp.box_number ASC"
    sorted_by = None

    # The legacy `key:value` spellings the old parser understood. Kept working because
    # people have them in their muscle memory, and because a filter language that breaks
    # what it replaces is a downgrade wearing a new name.
    legacy = {'tag:': 'tag', 'label:': 'tag', 'type:': 'type', 'sort:': 'sort'}
    normalised = []
    for word in str(query or '').split():
        lowered = word.lower()
        matched = next((p for p in legacy if lowered.startswith(p)), None)
        if matched:
            normalised.append('.' + legacy[matched] + '=' + word[len(matched):])
        elif lowered in ('shiny', 'is:shiny'):
            normalised.append('.shiny')
        else:
            normalised.append(word)

    for flag, value, explicit in _tokenise(' '.join(normalised)):
        # --- a bare word is a name search ---
        if flag is None:
            clauses.append("(LOWER(cp.name) LIKE ? OR LOWER(COALESCE(cp.nickname, '')) LIKE ?)")
            params.extend([f"%{value.lower()}%", f"%{value.lower()}%"])
            applied.append(f"name ~ {value}")
            continue

        # --- `.sort iv` and `.sort name`, the old spelling ---
        if flag == 'sort':
            target = LOOKUP.get(str(value or '').lower())
            if target is None:
                aliases = {'stats': 'iv', 'az': 'name', 'new': 'box', 'newest': 'box'}
                target = aliases.get(str(value or '').lower())
            if target is None:
                return None, None, None, None, (
                    f"⚠️ `{value}` is not something I can sort by. Try `.ivs d`, "
                    f"`.level d` or `.name a`.")
            direction = 'DESC' if target in ('iv', 'ivtotal', 'box') else 'ASC'
            sorted_by = (target, direction)
            continue

        # --- flags this caller handles itself ---
        # The market sorts by `.price`, which is a property of the LISTING and has no
        # column on caught_pokemon. Rather than teach this parser about a table `!pc`
        # never touches, a caller declares the flags it will deal with and they pass
        # through here untouched. Without this the shared parser refused `.price` as
        # unknown before the market's own handler ever saw it.
        if flag in extra_flags:
            continue

        # --- `.evo charizard`, resolved by the caller before we got here ---
        if flag in EVO_FLAGS:
            if not value:
                return None, None, None, None, (
                    "⚠️ `.evo` needs a species, e.g. `.evo charizard` - it shows every "
                    "member of that evolutionary line.")
            resolved = (family_ids or {}).get(str(value).strip().lower())
            if not resolved:
                return None, None, None, None, (
                    f"⚠️ `{value}` is not a species I know, so I cannot work out its "
                    f"evolutionary line.")
            ids, pretty = resolved
            clauses.append(
                f"cp.pokedex_id IN ({','.join('?' for _ in ids)})")
            params.extend(ids)
            applied.append(f"{pretty.capitalize()} line ({len(ids)})")
            continue

        # --- `.type water`, which is not a column on this table ---
        if flag in ('type', 'types', 'element'):
            if not value:
                return None, None, None, None, "⚠️ `.type` needs a type, e.g. `.type water`."
            clauses.append(TYPE_SQL)
            params.append(value.lower())
            applied.append(f"type = {value.lower()}")
            continue

        key = LOOKUP.get(flag)
        if key is None:
            close = sorted(n for n in LOOKUP if n.startswith(flag[:3]))[:4]
            hint = (" Did you mean " + " · ".join(f"`.{n}`" for n in close) + "?") if close else ""
            return None, None, None, None, (
                f"⚠️ `.{flag}` is not a filter I know.{hint}\n"
                f"Run `!pc .help` for the list.")

        field = FIELDS[key]

        # A direction turns any field into a sort. `.ivs d` is the spelling the request
        # asked for and it falls straight out of this rather than being special-cased.
        direction = None if explicit else _sort_direction(value)
        if direction and field.sortable and field.kind != 'switch':
            sorted_by = (key, direction)
            continue

        # --- switches ---
        if field.kind == 'switch':
            wanted = 1
            if value is not None and str(value).strip().lower() in SWITCH_NEGATIONS:
                wanted = 0
            clauses.append(f"{field.sql} = ?")
            params.append(wanted)
            applied.append(field.label if wanted else f"not {field.label.lower()}")
            continue

        if value is None or value == '':
            return None, None, None, None, (
                f"⚠️ `.{flag}` needs a value, e.g. "
                f"`.{flag} {'31' if field.kind == 'number' else 'something'}`.")

        # --- numbers, comparisons and ranges ---
        if field.kind == 'number':
            clause, bound, complaint = _number_clause(field.sql, value)
            if complaint:
                return None, None, None, None, f"{complaint} (in `.{flag}`)"
            clauses.append(clause)
            params.extend(bound)
            applied.append(f"{field.label} {value}")
            continue

        # --- text and substring matches ---
        text = str(value).strip()
        if key == 'gender':
            resolved = GENDER_WORDS.get(text.lower())
            if resolved is None:
                return None, None, None, None, (
                    f"⚠️ `{text}` is not a gender. Try `.gender m`, `.gender f` or "
                    f"`.gender none`.")
            text = resolved
        if key == 'ot':
            # A mention pastes as <@1234>, and somebody copying an ID out of Discord
            # gets the mention far more often than the bare number.
            digits = ''.join(ch for ch in text if ch.isdigit())
            if digits:
                text = digits

        if field.kind == 'text':
            clauses.append(f"LOWER(COALESCE({field.sql}, '')) = ?")
            params.append(text.lower())
        else:
            clauses.append(f"LOWER(COALESCE({field.sql}, '')) LIKE ?")
            params.append(f"%{text.lower()}%")
        applied.append(f"{field.label} = {text}")

    if sorted_by:
        key, direction = sorted_by
        # The column comes out of FIELDS. Nothing a player typed reaches this string.
        order_by = f"ORDER BY {FIELDS[key].sql} {direction}, cp.box_number ASC"
        applied.append(f"sorted by {FIELDS[key].label} "
                       f"{'ascending' if direction == 'ASC' else 'descending'}")

    return clauses, params, order_by, applied, None


async def resolve_query(db, query, extra_flags=()):
    """
    Parse a filter query, resolving any `.evo` against the database first.

    THE ONE DOOR both `!pc` and the market go through. The two-step dance - ask what
    needs looking up, look it up, parse - is easy to get subtly wrong and there is no
    reason for two commands to each get it wrong differently.

    Returns exactly what `parse_filters` returns.
    """
    families = {}
    for target in evo_targets(query):
        from utils.db_manager import evolution_family
        ids, pretty = await evolution_family(db, target)
        if ids:
            families[str(target).strip().lower()] = (ids, pretty)
    return parse_filters(query, families, extra_flags)


def filter_help():
    """The list, for `!pc .help`. Generated from FIELDS so it cannot fall behind."""
    lines = ["**Filters stack.** `!pc .shiny .ivs d`, `!pc .spatkiv 31 .nature adamant`",
             "",
             "**Numbers** take `31`, `>=25`, `<10` or `20-31`.",
             "**Any filter** can sort instead: `.ivs d` (descending), `.level a`.",
             ""]
    switches = [f"`.{k}`" for k, f in FIELDS.items() if f.kind == 'switch']
    lines.append("**Switches:** " + " ".join(sorted(switches))
                 + " — prefix a value of `no` to invert, e.g. `.shiny no`.")
    lines.append("")
    numbers = [f"`.{k}`" for k, f in FIELDS.items() if f.kind == 'number']
    lines.append("**Numbers:** " + " ".join(sorted(numbers)))
    lines.append("")
    words = [f"`.{k}`" for k, f in FIELDS.items() if f.kind in ('text', 'like')]
    lines.append("**Words:** " + " ".join(sorted(words)) + " `.type`")
    lines.append("")
    lines.append("**`.evo <species>`** shows the whole evolutionary line — "
                 "`.evo charizard` finds your Charmander too.")
    lines.append("")
    lines.append("A bare word searches species and nicknames: `!pc charizard .shiny`")
    return "\n".join(lines)
