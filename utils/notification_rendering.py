"""Sizing helpers for tightly cropped notification-card screenshots."""

import unicodedata
from math import ceil

_PAGE_PADDING = 26
_CARD_WIDTH = 620
_CLIP_WIDTH = _CARD_WIDTH + _PAGE_PADDING * 2
_CLIP_SAFETY = 1
_ROW_TITLE_LINE_HEIGHT = 18

# The template's fixed vertical structure, excluding the heading and the
# content inside its details/list section. Keep these values aligned with
# templates/notification_card.html.
_CARD_CHROME_HEIGHT = 231
_HEADING_LINE_HEIGHT = 38
_DETAILS_SHELL_HEIGHT = 62  # margin-top + vertical padding


def _char_width_units(char: str) -> float:
    """Approximate the rendered width in ems for the template's sans font."""
    if char in "\u200d\ufe0e\ufe0f":
        return 0.0
    if char.isspace():
        return 0.32
    if unicodedata.east_asian_width(char) in {"F", "W"}:
        return 1.0
    if char in "ilI.,:;'|!`()[]{}":
        return 0.34
    if char in "MW@#%&":
        return 0.82
    return 0.56


def _wrapped_lines(value, *, width_px: int, font_px: int) -> int:
    """Estimate CSS wrapped lines while honoring explicit newlines."""
    text = str(value or "")
    if not text:
        return 1

    max_units = max(1.0, width_px / font_px)
    lines = 0
    for paragraph in text.split("\n"):
        if not paragraph:
            lines += 1
            continue

        paragraph_lines = 1
        current_width = 0.0
        for char in paragraph:
            char_width = _char_width_units(char)
            if current_width and current_width + char_width > max_units:
                paragraph_lines += 1
                current_width = 0.0
            current_width += char_width
        lines += paragraph_lines

    return max(1, lines)


def _lines(value, *, width_px: int, font_px: int) -> int:
    return _wrapped_lines(value, width_px=width_px, font_px=font_px)


def estimate_notification_clip(data: dict) -> dict[str, int]:
    """Return a fixed-width clip whose height follows the card's content.

    AstrBot captures a full browser viewport by default. The clip keeps the
    card's 26px outer padding and removes unrelated viewport space. Height is
    derived from visible text/rows so wrapped messages are not cut off.
    """
    card_type = str(data.get("card_type") or "text")
    heading = data.get("heading") or data.get("title") or ""
    if card_type == "update":
        heading = data.get("title") or heading
    heading_lines = _lines(heading, width_px=550, font_px=27)
    height = (
        _PAGE_PADDING * 2
        + _CLIP_SAFETY
        + _CARD_CHROME_HEIGHT
        + _HEADING_LINE_HEIGHT * heading_lines
    )

    if card_type == "text":
        body_lines = _lines(data.get("body"), width_px=510, font_px=16)
        height += 28 * body_lines
    elif card_type == "progress":
        status_lines = _lines(data.get("status"), width_px=550, font_px=14)
        unit_lines = _lines(data.get("unit"), width_px=510, font_px=12)
        height += 20 * status_lines + 14 * unit_lines + 38 + 28 + 13
    elif card_type == "update":
        album_lines = _lines(
            f"漫画 ID {data.get('album_id', '')}", width_px=550, font_px=14
        )
        height += 20 * album_lines + 14 + 28 + 13
    elif card_type == "status":
        value_lines = _lines(data.get("title"), width_px=510, font_px=19)
        detail_lines = _lines(data.get("detail"), width_px=510, font_px=12)
        album_lines = _lines(
            f"漫画 ID {data.get('album_id', '')}", width_px=550, font_px=14
        )
        height += 20 * album_lines + 14 * detail_lines + 7 + 26 * value_lines + 8
    elif card_type == "subscription_list":
        height -= _DETAILS_SHELL_HEIGHT
        rows = data.get("rows") or []
        if rows:
            height += 20 + 20  # album count and list margin
            for index, row in enumerate(rows):
                title_lines = _lines(row.get("title"), width_px=470, font_px=16)
                id_lines = _lines(
                    f"ID {row.get('album_id', '')}", width_px=470, font_px=12
                )
                height += 28 + _ROW_TITLE_LINE_HEIGHT * title_lines + 5 + 14 * id_lines
                if index < len(rows) - 1:
                    height += 1
        else:
            height += 20 + 55  # album count and empty-state paragraph
    elif card_type == "search_results":
        height -= _DETAILS_SHELL_HEIGHT
        rows = data.get("rows") or []
        if rows:
            query_lines = _lines(
                f"{data.get('query', '')} {data.get('page', '')}",
                width_px=550,
                font_px=14,
            )
            height += 20 * query_lines + 18  # query/page line and list margin
            for index, row in enumerate(rows):
                title_lines = _lines(row.get("title"), width_px=550, font_px=17)
                id_lines = _lines(
                    f"ID {row.get('album_id', '')} {row.get('author', '')}",
                    width_px=550,
                    font_px=12,
                )
                row_height = 32 + ceil(25.5 * title_lines) + 5 + 14 * id_lines
                if row.get("tags"):
                    tag_lines = _lines(row["tags"], width_px=550, font_px=13)
                    row_height += 7 + ceil(20.8 * tag_lines)
                height += row_height
                if index < len(rows) - 1:
                    height += 1
            height += 10
        else:
            height += 20 + 55
    elif card_type == "download_result":
        title_lines = _lines(data.get("title"), width_px=510, font_px=19)
        height += 20 + 14 + 7 + 24 * title_lines
        stat_values = [
            data.get("author"),
            data.get("photo_count"),
            data.get("image_count"),
            data.get("format_label"),
        ]
        stat_lines = [_lines(value, width_px=217, font_px=17) for value in stat_values]
        height += (
            22
            + sum(
                30 + 14 + 7 + 24 * max(pair)
                for pair in (stat_lines[:2], stat_lines[2:])
            )
            + 12
        )
        if data.get("pack_status") or data.get("encrypted"):
            height += 14 + 28
        height += 12
    else:
        detail_lines = _lines(data.get("title"), width_px=510, font_px=19)
        height += 20 + 14 + 7 + 26 * detail_lines

    footer_lines = _lines(data.get("footer"), width_px=550, font_px=12)
    if footer_lines > 1:
        height += 14 * (footer_lines - 1)

    return {"x": 0, "y": 0, "width": _CLIP_WIDTH, "height": max(240, height)}
