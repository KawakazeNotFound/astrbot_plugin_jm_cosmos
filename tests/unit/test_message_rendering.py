import importlib.util
from dataclasses import dataclass
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[2] / "utils" / "message_rendering.py"
_SPEC = importlib.util.spec_from_file_location("message_rendering", _MODULE_PATH)
_MESSAGE_RENDERING = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MESSAGE_RENDERING)
render_plain_segments = _MESSAGE_RENDERING.render_plain_segments
strip_leading_emoji_markers = _MESSAGE_RENDERING.strip_leading_emoji_markers


@dataclass
class Plain:
    text: str


@dataclass
class Image:
    url: str


@dataclass
class Reply:
    message_id: str


@pytest.mark.asyncio
async def test_render_plain_runs_preserves_images_and_replies_in_order():
    cover = Image("cover.jpg")
    reply = Reply("quoted-message")
    components = [cover, Plain("标题\n"), Plain("详情"), reply, Plain("尾注")]
    rendered_text = []

    async def render_card(text):
        rendered_text.append(text)
        return f"card:{len(rendered_text)}.png"

    result = await render_plain_segments(
        components,
        render_card,
        lambda component: isinstance(component, Plain),
        Image,
    )

    assert rendered_text == ["标题\n详情", "尾注"]
    assert result == [cover, Image("card:1.png"), reply, Image("card:2.png")]
    assert result[0] is cover
    assert result[2] is reply


@pytest.mark.asyncio
async def test_render_failure_keeps_original_plain_components():
    components = [Plain("第一段"), Image("inline.png"), Plain("第二段")]

    async def render_card(_text):
        return None

    result = await render_plain_segments(
        components,
        render_card,
        lambda component: isinstance(component, Plain),
        Image,
    )

    assert result == components
    assert all(actual is expected for actual, expected in zip(result, components))


def test_strip_leading_emoji_markers_preserves_body_content():
    assert strip_leading_emoji_markers("📖 标题\n✅ 完成😀") == "标题\n完成😀"
