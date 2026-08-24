"""Editing a message without losing the picture attached to it.

Discord binds an image to an embed in one of two ways: by URL, or by the name of a file
attached to the same message (`attachment://battle.png`). The bot always sends the second
kind - the sprite and the battle scene are uploaded with the message.

The trap is what happens when you FETCH that message back. `message.embeds[0].image.url`
does not come back as `attachment://battle.png`; it comes back as a signed CDN link with
an expiry stamped into it. Edit the message with that embed and Discord re-issues the
attachment under a NEW signed URL, while the embed you just sent still points at the old
one. The picture then either renders from a dying link or falls out of the embed entirely
and shows up as a bare file underneath it.

The caught-spawn card hits this: it is rewritten when somebody catches the spawn, which
means fetching, editing and re-attaching. PvE battles never did, only because they
regenerate and re-upload the scene on every single turn, which rebinds the name by
accident rather than on purpose.

The PvP dashboard used to hit it too, and was the reason this helper was written - the
scene vanished the moment the first player locked in a move. It no longer fetches at
all: updating who a duel is waiting on now edits the message CONTENT and nothing else,
so the embed and its attachment are never in the payload to be re-issued. That is the
better fix wherever it is available, because it cannot go wrong rather than going right
carefully. This helper is for the cases that genuinely must rewrite an embed they only
have a fetched copy of.

Re-point the embed at the file by NAME before editing, and hand the existing attachments
straight back.
"""


def rebind_image(embed, message):
    """
    Point `embed`'s image back at the message's own attachment, by name.

    Returns the attachments to pass to `edit`, so a caller reads as:

        keep = rebind_image(embed, message)
        await message.edit(embed=embed, attachments=keep)

    A message with no attachments returns an empty list, which is exactly what `edit`
    wants for "there were none and there still are none".
    """
    if message is None or embed is None:
        return []

    attachments = list(getattr(message, 'attachments', None) or [])
    if not attachments:
        return []

    # The first attachment is the picture in every case this bot produces - a spawn card
    # carries one sprite and a battle message carries one scene. Anything else is left
    # alone rather than guessed at.
    filename = getattr(attachments[0], 'filename', None)
    if filename:
        try:
            embed.set_image(url=f"attachment://{filename}")
        except Exception as e:                                   # pragma: no cover
            print(f"⚠️ Could not rebind embed image: {e}")

    return attachments
