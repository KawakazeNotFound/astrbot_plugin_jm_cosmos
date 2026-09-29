"""Helpers for replacing plain-message runs with rendered image cards."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Iterable
from typing import Any

_LEADING_EMOJI_MARKERS = re.compile(
    r"(?m)^[ \t]*(?:(?:[\U0001F000-\U0001FAFF\u2600-\u27BF]\ufe0f?)"
    r"(?:\u200d[\U0001F000-\U0001FAFF\u2600-\u27BF]\ufe0f?)*[ \t]*)+"
)


def strip_leading_emoji_markers(text: str) -> str:
    """Remove decorative emoji prefixes while retaining emoji inside user text."""
    return _LEADING_EMOJI_MARKERS.sub("", text)


async def render_plain_segments(
    components: Iterable[Any],
    render_card: Callable[[str], Awaitable[str | None]],
    is_plain: Callable[[Any], bool],
    image_factory: Callable[[str], Any],
) -> list[Any]:
    """Render each contiguous plain-text run and preserve all other components.

    If rendering fails, the original plain components are restored in their
    original positions. Images, replies, mentions, files, and other segments
    pass through untouched.
    """
    output: list[Any] = []
    pending: list[Any] = []
    pending_text: list[str] = []

    async def flush() -> None:
        if not pending:
            return

        text = "".join(pending_text)
        try:
            image_url = await render_card(text)
        except Exception:
            image_url = None

        if image_url:
            output.append(image_factory(image_url))
        else:
            output.extend(pending)

        pending.clear()
        pending_text.clear()

    for component in components:
        if is_plain(component):
            value = (
                component.get("text", "")
                if isinstance(component, dict)
                else getattr(component, "text", "")
            )
            pending.append(component)
            pending_text.append(str(value or ""))
        else:
            await flush()
            output.append(component)

    await flush()
    return output
