"""
How often each command is run. Nothing about who ran it.

**THERE IS NO user_id COLUMN, AND THAT IS THE DESIGN.** The question this answers is
"which commands are worth maintaining" - which needs totals and nothing else. A per-user
breakdown would answer the same question no better while creating a behavioural profile
of every player: when they are online, what they do, how their habits change. The table
cannot leak that because the column to leak it from does not exist, which is a stronger
guarantee than a policy of not querying it.

It also means there is nothing here for `!privacy delete` to erase, and nothing for a
wipe to miss. `utils/accounts.py` works off two maps of table -> user column; a table
with no user column is invisible to both by construction rather than by being remembered.

**COMPLETIONS, NOT INVOCATIONS.** A command that failed a check - wrong channel, not
registered, on cooldown - was not usage, and counting those would make the busiest
command in the log whichever one people mistype most. Errors are counted separately so a
command that is being run and consistently failing is visible rather than hidden inside
one number.

**NOTHING HERE RUNS AT IMPORT OR AT COG LOAD**, and the schema is only ever created on a
connection the CALLER opened - the same rule `utils/limits.py` follows, and for the same
reason: a module that writes to whatever database happened to be configured at import
time is a mistake this codebase has already made once.
"""

import datetime

TABLE = 'command_usage'

# How many commands the digest names before it stops. A log post has a 4096-character
# description and a bot with a hundred commands would blow through it; the tail is
# summarised rather than truncated silently.
DIGEST_LIMIT = 25


async def ensure_schema(db):
    """Create the counter table. Idempotent, and safe to call on every write."""
    await db.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            command   TEXT NOT NULL,
            day       TEXT NOT NULL,
            uses      INTEGER NOT NULL DEFAULT 0,
            errors    INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (command, day)
        )
    """)


def today():
    """The current UTC date as `YYYY-MM-DD`.

    UTC deliberately, matching `utils/limits.py`: a local-time boundary moves with the
    host, so a server that changed timezone would split one day's counts across two rows.
    """
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')


async def record(db, command, *, failed=False, day=None):
    """
    Count one use of `command`. Does NOT commit.

    The caller owns the transaction, so a count cannot survive a rollback of the thing
    it was counting. `command` is the qualified name - `global market view`, not `view` -
    because the bare name of a subcommand is ambiguous across groups.
    """
    name = str(command or '').strip().lower()
    if not name:
        return
    await ensure_schema(db)
    await db.execute(
        f"INSERT INTO {TABLE} (command, day, uses, errors) VALUES (?, ?, ?, ?) "
        f"ON CONFLICT(command, day) DO UPDATE SET "
        f"uses = uses + excluded.uses, errors = errors + excluded.errors",
        (name, day or today(), 0 if failed else 1, 1 if failed else 0))


async def totals(db, *, since=None):
    """
    `[(command, uses, errors), ...]`, busiest first.

    `since` is an inclusive `YYYY-MM-DD`. Omitted, it is all of recorded history.
    """
    await ensure_schema(db)
    where, params = "", ()
    if since:
        where, params = "WHERE day >= ?", (since,)
    async with db.execute(
            f"SELECT command, SUM(uses), SUM(errors) FROM {TABLE} {where} "
            f"GROUP BY command ORDER BY SUM(uses) DESC, command ASC", params) as cursor:
        return [(r[0], int(r[1] or 0), int(r[2] or 0)) for r in await cursor.fetchall()]


def days_ago(days):
    """An inclusive `YYYY-MM-DD` bound `days` before today, for `totals(since=...)`."""
    when = (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=max(0, int(days))))
    return when.strftime('%Y-%m-%d')


def describe(rows, *, limit=DIGEST_LIMIT):
    """
    The counts as a code block, busiest first, with the tail summarised.

    Returns `(body, total_uses, total_errors, distinct)` so the caller can put the
    headline figures somewhere other than inside the block.
    """
    rows = list(rows or [])
    total_uses = sum(r[1] for r in rows)
    total_errors = sum(r[2] for r in rows)

    if not rows:
        return "*Nothing recorded yet.*", 0, 0, 0

    shown = rows[:limit]
    width = max(len(r[0]) for r in shown)
    lines = []
    for name, uses, errors in shown:
        share = (uses * 100.0 / total_uses) if total_uses else 0.0
        line = f"{name.ljust(width)}  {uses:>6,}  {share:>5.1f}%"
        if errors:
            # Only shown when there are any. A column of zeroes is a column of noise,
            # and a command that errors is the one thing here worth looking at twice.
            line += f"   {errors:,} err"
        lines.append(line)

    body = "```\n" + "\n".join(lines) + "\n```"
    remaining = len(rows) - len(shown)
    if remaining:
        tail = sum(r[1] for r in rows[len(shown):])
        body += f"\n*…and {remaining} more commands, {tail:,} uses between them.*"
    return body, total_uses, total_errors, len(rows)


async def sweep_old(db, keep_days=180):
    """Drop day-rows nobody will read again. Housekeeping, not correctness."""
    await ensure_schema(db)
    cutoff = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=max(1, int(keep_days)))).strftime('%Y-%m-%d')
    cursor = await db.execute(f"DELETE FROM {TABLE} WHERE day < ?", (cutoff,))
    return cursor.rowcount
