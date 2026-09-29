import asyncio
import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def _load_main_module(monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    package_name = "_jmcosmos_info_command_test"

    package = types.ModuleType(package_name)
    package.__path__ = [str(repo_root)]
    package.__package__ = package_name
    monkeypatch.setitem(sys.modules, package_name, package)

    core = types.ModuleType(f"{package_name}.core")
    core.__path__ = []
    for name in (
        "DownloadQuotaManager",
        "JMAuthManager",
        "JMBrowser",
        "JMConfigManager",
        "JMDownloadManager",
        "JMPacker",
        "SubscriptionManager",
    ):
        setattr(core, name, type(name, (), {}))
    core.classify_exception = lambda exc: ("network", str(exc) or "timeout")
    monkeypatch.setitem(sys.modules, f"{package_name}.core", core)

    download_queue = types.ModuleType(f"{package_name}.core.download_queue")
    download_queue.DownloadJobQueue = type("DownloadJobQueue", (), {})
    monkeypatch.setitem(
        sys.modules, f"{package_name}.core.download_queue", download_queue
    )

    utils = types.ModuleType(f"{package_name}.utils")
    utils.__path__ = []
    utils.MessageFormatter = SimpleNamespace(
        format_error=lambda error_type, detail="": f"error:{error_type}:{detail}",
        format_album_info=lambda detail: f"album:{detail['title']}",
    )
    utils.generate_album_filename = lambda **kwargs: ""
    utils.send_with_recall = Mock()
    monkeypatch.setitem(sys.modules, f"{package_name}.utils", utils)

    message_rendering = types.ModuleType(f"{package_name}.utils.message_rendering")
    message_rendering.render_plain_segments = Mock()
    message_rendering.strip_leading_emoji_markers = lambda text: text
    monkeypatch.setitem(
        sys.modules, f"{package_name}.utils.message_rendering", message_rendering
    )
    notification_rendering = types.ModuleType(
        f"{package_name}.utils.notification_rendering"
    )
    notification_rendering.estimate_notification_clip = lambda data: {}
    monkeypatch.setitem(
        sys.modules,
        f"{package_name}.utils.notification_rendering",
        notification_rendering,
    )

    astrbot = types.ModuleType("astrbot")
    astrbot.__path__ = []
    api = types.ModuleType("astrbot.api")
    api.__path__ = []
    api.AstrBotConfig = object
    api.logger = Mock()
    astrbot.api = api
    monkeypatch.setitem(sys.modules, "astrbot", astrbot)
    monkeypatch.setitem(sys.modules, "astrbot.api", api)

    components = types.ModuleType("astrbot.api.message_components")
    components.Image = type("Image", (), {})
    components.Plain = type("Plain", (), {})
    components.File = type("File", (), {})
    monkeypatch.setitem(sys.modules, "astrbot.api.message_components", components)

    event_api = types.ModuleType("astrbot.api.event")
    event_api.AstrMessageEvent = object
    event_api.filter = SimpleNamespace(command=lambda *_args, **_kwargs: lambda fn: fn)
    monkeypatch.setitem(sys.modules, "astrbot.api.event", event_api)

    star_api = types.ModuleType("astrbot.api.star")
    star_api.Context = object
    star_api.Star = object
    star_api.StarTools = object
    star_api.register = lambda *_args, **_kwargs: lambda cls: cls
    monkeypatch.setitem(sys.modules, "astrbot.api.star", star_api)

    module_name = f"{package_name}.main"
    spec = importlib.util.spec_from_file_location(module_name, repo_root / "main.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def _make_plugin(module, browser, *, cover_preview=False, download_dir=None):
    plugin = object.__new__(module.JMCosmosPlugin)
    plugin.browser = browser
    plugin.config_manager = SimpleNamespace(
        send_cover_preview=cover_preview,
        download_dir=download_dir or Path("."),
        cover_recall_enabled=False,
    )
    plugin._check_permission = lambda _event: (True, "")

    async def text_result(_event, text):
        return text

    plugin._text_result = text_result
    return plugin


@pytest.mark.asyncio
async def test_jmi_returns_network_feedback_when_detail_lookup_times_out(monkeypatch):
    module = _load_main_module(monkeypatch)
    monkeypatch.setattr(module, "_INFO_DETAIL_TIMEOUT_SECONDS", 0.01, raising=False)

    class Browser:
        async def get_album_detail(self, _album_id):
            await asyncio.Event().wait()

    plugin = _make_plugin(module, Browser())
    results = module.JMCosmosPlugin.info_command(plugin, object(), "123456")

    assert "正在获取本子" in await anext(results)
    error_message = await asyncio.wait_for(anext(results), timeout=0.2)

    assert error_message.startswith("error:network:")


@pytest.mark.asyncio
async def test_jmi_sends_album_details_when_cover_lookup_times_out(
    monkeypatch, tmp_path
):
    module = _load_main_module(monkeypatch)
    monkeypatch.setattr(module, "_INFO_COVER_TIMEOUT_SECONDS", 0.01, raising=False)

    class Browser:
        async def get_album_detail(self, _album_id):
            return {"title": "示例作品"}

        async def get_album_cover(self, _album_id, _cover_dir):
            await asyncio.Event().wait()

    plugin = _make_plugin(module, Browser(), cover_preview=True, download_dir=tmp_path)
    results = module.JMCosmosPlugin.info_command(plugin, object(), "123456")

    assert "正在获取本子" in await anext(results)
    details_message = await asyncio.wait_for(anext(results), timeout=0.2)

    assert details_message == "album:示例作品"
