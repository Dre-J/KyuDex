"""
Components V2 cards: one container, a strip of buttons, one panel open at a time.

**WHY A CARD RATHER THAN AN EMBED.** An embed is a fixed shape - a description, then up
to twenty-five fields, all of it on screen at once. `!dex` had grown to eleven fields and
`!view` to a description of eight lines plus a stat block, and both had reached the point
where the thing the reader came for was somewhere in the middle of everything else. A
container can be SHORT: the portrait and the identity line, and then only whichever panel
was asked for.

**THE SAME BUTTON OPENS AND CLOSES.** Pressing the open tab collapses the card back to
its header, so no panel needs a ✕ of its own and a card can be parked small while the
roster is walked. `COLLAPSED` is that state.

**THE VIEW IS REBUILT, NEVER PATCHED.** `rebuild()` throws the whole container away and
draws it again from the card's own state. Editing components in place is how a card ends
up with a Stats button that says it is open beside a Moves panel; there is one code path
that decides what is on screen, and it runs every time anything changes.

Two mockups drove the layout - `info_mockup.py` and `dex_mockup.py` - and both spoke to
Discord over raw HTTP because the library of the day had no Components V2 support. This
one is on discord.py 2.7.1, which does, so the payloads are built by the library and the
owner check, the timeout and the interaction plumbing come with it.
"""
import discord
from discord import ui

# No panel open. Pressing the open tab again lands here.
COLLAPSED = 'none'

# Discord counts a whole container's text against one budget, so a panel that borrows a
# flavour entry or a field log is trimmed rather than allowed to bounce the message.
TEXT_LIMIT = 3000


def trim(text, limit=TEXT_LIMIT):
    """`text`, shortened at a word boundary if it has to be."""
    text = str(text or '')
    if len(text) <= limit:
        return text
    cut = text[:limit - 1]
    return cut[:cut.rfind(' ')].rstrip() + '…' if ' ' in cut else cut + '…'


def card_button(label, *, emoji=None, style=discord.ButtonStyle.secondary,
                disabled=False, callback=None):
    """One button, with its callback attached rather than declared by a decorator.

    The decorator form fixes the buttons at class-definition time, which is the one thing
    a card that redraws itself cannot have: how many buttons there are, and what they say,
    depends on what is on screen.
    """
    button = ui.Button(label=label, emoji=emoji, style=style, disabled=disabled)
    if callback is not None:
        button.callback = callback
    return button


def text(content):
    return ui.TextDisplay(trim(content))


def divider(visible=True):
    return ui.Separator(visible=visible, spacing=discord.SeparatorSpacing.small)


def row(*items):
    line = ui.ActionRow()
    for item in items:
        line.add_item(item)
    return line


class TabbedCard(ui.LayoutView):
    """
    A container whose panels are opened one at a time by a row of buttons.

    Subclasses supply the content and keep the state:

        TABS      key -> (label, emoji), in the order the strip draws them
        header()  the items shown above every panel
        panel()   the items for one tab
        controls() any further rows below the tab strip
        accent()  the container's colour
    """

    TABS = {}
    ACCENT = None
    NOT_YOURS = "This card belongs to somebody else."

    def __init__(self, owner_id, *, tab=COLLAPSED, timeout=180):
        super().__init__(timeout=timeout)
        self.owner_id = int(owner_id)
        self.tab = tab if tab in self.TABS else COLLAPSED

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(self.NOT_YOURS, ephemeral=True)
            return False
        return True

    # --- what a subclass fills in ------------------------------------
    def accent(self):
        return self.ACCENT

    def header(self):
        return []

    def panel(self, tab):
        return []

    def controls(self):
        return []

    # --- assembly ----------------------------------------------------
    def rebuild(self):
        """Draw the whole card again from current state. Returns self, to chain."""
        self.clear_items()
        container = ui.Container(accent_colour=self.accent())
        for item in self.header():
            container.add_item(item)

        body = self.panel(self.tab) if self.tab in self.TABS else []
        if body:
            container.add_item(divider())
            for item in body:
                container.add_item(item)

        container.add_item(divider())
        container.add_item(self.tab_row())
        for line in self.controls():
            container.add_item(line)

        self.add_item(container)
        return self

    def tab_row(self):
        """The strip. The open tab is highlighted and aims at COLLAPSED."""
        return row(*[
            card_button(
                label, emoji=emoji, callback=self.tab_press(key),
                style=(discord.ButtonStyle.primary if key == self.tab
                       else discord.ButtonStyle.secondary))
            for key, (label, emoji) in self.TABS.items()
        ])

    def tab_press(self, key):
        async def press(interaction):
            self.tab = COLLAPSED if key == self.tab else key
            await self.redraw(interaction)
        return press

    async def redraw(self, interaction, *, attachments=None):
        """
        Send the rebuilt card back.

        `attachments` is left alone unless the caller passes one. A card whose picture has
        not changed must NOT re-send an empty attachment list: the media block still points
        at `attachment://…`, and clearing the attachments would leave it pointing at
        nothing. Only the presses that change the sprite hand one over.
        """
        self.rebuild()
        if attachments is None:
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.edit_message(view=self, attachments=attachments)
