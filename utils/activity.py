"""
What counts as conversation.

Two listeners watch every message in a server and each has to answer the same question -
*is this a person talking, or a person operating the bot?* - before deciding whether the
message earns anything. `cogs/experience.py` answered it and `cogs/ecology.py` did not:

    experience.py     ignores command invocations, so passive XP rewards conversation
    ecology.py        counted EVERY message, so `!pc` and `!party` pushed spawns along

The comment in experience.py already spells out why that is wrong - "without this every
`!catch`, `!battle` and `!party` paid out as well" - and the spawn counter wanted exactly
the same sentence. A trainer paging through their box five times was, from the habitat's
point of view, a busy server.

So the rule lives here and both listeners ask it. That is the whole module: one question,
asked once, rather than two listeners drifting apart again the next time it is touched.

WHAT COUNTS AS A COMMAND. `ctx.valid` is true when the prefix matched AND the command
exists. A MISTYPED command - `!ctach pikachu` - is therefore still counted as
conversation. That is deliberate rather than overlooked: `get_context` is the only thing
that knows what the prefix is in this server, `ctx.valid` is the test experience.py has
been using in production, and widening the rule to "anything starting with the prefix"
would change what passive XP pays out as a side effect of a spawn fix. If typos should
stop counting too, this is the one line to change and both listeners follow.
"""


async def is_command(bot, message):
    """
    Whether this message is the bot being operated rather than a person talking.

    Async because working out the prefix is - `get_context` is what resolves a callable
    or per-guild prefix, and there is no synchronous way to ask.

    Never raises. A listener that cannot tell should let the message through and count
    it, because losing a spawn tick is a smaller wrong than an exception in an
    `on_message` that runs for every message in every server.
    """
    try:
        ctx = await bot.get_context(message)
        return bool(ctx.valid)
    except Exception:
        return False
