import importlib.util
from pathlib import Path

_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "utils" / "notification_rendering.py"
)
_SPEC = importlib.util.spec_from_file_location("notification_rendering", _MODULE_PATH)
_NOTIFICATION_RENDERING = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_NOTIFICATION_RENDERING)
estimate_notification_clip = _NOTIFICATION_RENDERING.estimate_notification_clip


def test_text_card_clip_keeps_outer_margin_and_tracks_wrapped_content():
    short = estimate_notification_clip(
        {"card_type": "text", "heading": "消息提醒", "body": "正在搜索"}
    )
    long = estimate_notification_clip(
        {
            "card_type": "text",
            "heading": "消息提醒",
            "body": "搜索结果\n" + "很长的漫画标题" * 20,
        }
    )

    assert short["x"] == short["y"] == 0
    assert short["width"] == 672
    assert short["height"] > 300
    assert long["height"] > short["height"]


def test_clip_height_grows_with_subscription_rows_and_long_titles():
    empty = estimate_notification_clip(
        {"card_type": "subscription_list", "heading": "我的订阅", "rows": []}
    )
    populated = estimate_notification_clip(
        {
            "card_type": "subscription_list",
            "heading": "我的订阅",
            "rows": [
                {"title": "测试作品", "album_id": "123"},
                {"title": "超长作品标题" * 20, "album_id": "456"},
            ],
        }
    )

    assert populated["width"] == empty["width"]
    assert populated["height"] > empty["height"]


def test_heading_wrapping_increases_clip_height():
    short = estimate_notification_clip(
        {"card_type": "text", "heading": "提醒", "body": "完成"}
    )
    wrapped_heading = estimate_notification_clip(
        {"card_type": "text", "heading": "标题" * 30, "body": "完成"}
    )

    assert wrapped_heading["height"] > short["height"]


def test_update_card_sizes_from_displayed_title_not_unused_heading():
    short = estimate_notification_clip(
        {"card_type": "update", "heading": "订阅更新", "title": "作品"}
    )
    long = estimate_notification_clip(
        {
            "card_type": "update",
            "heading": "订阅更新",
            "title": "很长的作品标题" * 20,
        }
    )

    assert long["height"] > short["height"]
