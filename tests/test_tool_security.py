import sys
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.app.config import settings
from backend.tools.registry import registry
from backend.tools.apps import launch_application, open_website
from backend.tools.media import control_media_player, set_system_volume, play_youtube_video
from backend.tools.notes import save_quick_note, remember_user_preference
from backend.tools.search import web_search


def test_system_action_authorization_disabled(monkeypatch):
    async def _test():
        monkeypatch.setattr(settings, "ENABLE_SYSTEM_ACTIONS", False)

        res = await registry.execute("launch_application", {"app_name": "Spotify"})
        assert "disabled by policy" in res
        assert "ENABLE_SYSTEM_ACTIONS=true" in res

        res_url = await registry.execute("open_website", {"url": "https://example.com"})
        assert "disabled by policy" in res_url

    asyncio.run(_test())


def test_launch_application_input_validation():
    async def _test():
        # Shell metacharacter injection attempt
        res = await launch_application("Safari; rm -rf /")
        assert "Invalid application name" in res

        # Path traversal attempt
        res2 = await launch_application("../../bin/bash")
        assert "Invalid application name" in res2

        # Flag injection attempt
        res3 = await launch_application("-v")
        assert "Invalid application name" in res3

    asyncio.run(_test())


def test_launch_application_whitelist_enforcement(monkeypatch):
    async def _test():
        monkeypatch.setattr(sys, "platform", "darwin")
        res = await launch_application("UnauthorizedMaliciousApp")
        assert "not in the authorized applications whitelist" in res

    asyncio.run(_test())


def test_launch_application_success_on_darwin(monkeypatch):
    async def _test():
        monkeypatch.setattr(sys, "platform", "darwin")

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            res = await launch_application("Spotify")
            assert "Successfully opened Spotify" in res
            mock_exec.assert_called_once_with(
                "open", "-a", "Spotify",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

    asyncio.run(_test())


def test_launch_application_unsupported_on_non_darwin(monkeypatch):
    async def _test():
        monkeypatch.setattr(sys, "platform", "linux")
        res = await launch_application("Spotify")
        assert "only supported on macOS" in res

    asyncio.run(_test())


def test_open_website_scheme_validation():
    async def _test():
        # Reject dangerous URL schemes
        res_file = await open_website("file:///etc/passwd")
        assert "Unsupported URL scheme 'file'" in res_file

        res_js = await open_website("javascript:alert(1)")
        assert "Unsupported URL scheme 'javascript'" in res_js

        res_data = await open_website("data:text/html,<html>hello</html>")
        assert "Unsupported URL scheme 'data'" in res_data

        # Reject URLs with no netloc
        res_empty = await open_website("https://")
        assert "Missing valid host domain" in res_empty

    asyncio.run(_test())


def test_open_website_valid_url(monkeypatch):
    async def _test():
        monkeypatch.setattr(sys, "platform", "darwin")

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            res = await open_website("https://github.com/google")
            assert "Opened https://github.com/google in your browser!" in res

    asyncio.run(_test())


def test_control_media_player_security():
    async def _test():
        # Attempt AppleScript command injection
        res_inject = await control_media_player('play" \n do shell script "touch /tmp/pwned')
        assert "Unsupported media action" in res_inject

        # Valid action
        with patch("backend.tools.media.run_applescript_async", new_callable=AsyncMock) as mock_as:
            mock_as.return_value = "ok"
            res_valid = await control_media_player("play")
            assert "Spotify: executed play!" in res_valid

    asyncio.run(_test())


def test_set_system_volume_validation():
    async def _test():
        # Non-integer
        res_invalid = await set_system_volume("not_a_number")
        assert "must be an integer" in res_invalid

        # Clamping behavior
        with patch("backend.tools.media.run_applescript_async", new_callable=AsyncMock) as mock_as:
            mock_as.return_value = ""
            res_high = await set_system_volume(150)
            assert "Master volume set to 100%." in res_high

            res_low = await set_system_volume(-50)
            assert "Master volume set to 0%." in res_low

    asyncio.run(_test())


def test_play_youtube_video_sanitization():
    async def _test():
        # Empty query
        res = await play_youtube_video("")
        assert "must be a non-empty string" in res

        # Mock successful yt-dlp resolution
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"Best Song Ever\ndQw4w9WgXcQ\n", b"")

        mock_open_proc = AsyncMock()
        mock_open_proc.wait.return_value = 0

        with patch("asyncio.create_subprocess_exec", side_effect=[mock_proc, mock_open_proc]):
            res = await play_youtube_video("Rick Astley")
            assert "Playing Best Song Ever on YouTube" in res

    asyncio.run(_test())


def test_notes_and_preferences_sanitization():
    # Quick note length and category sanitization
    res_note = save_quick_note("Remember to buy milk", category="groceries; drop table")
    assert "I saved your note: 'Remember to buy milk'" in res_note

    # Invalid preference key
    res_bad_key = remember_user_preference("invalid key with spaces!", "some value")
    assert "Invalid preference key" in res_bad_key

    # Valid preference
    res_ok = remember_user_preference("favorite_ide", "VS Code")
    assert "favorite ide is 'VS Code'" in res_ok


def test_web_search_with_mock():
    async def _test():
        # Empty query
        res_empty = await web_search("")
        assert "must be a non-empty string" in res_empty

        # Mock DDGS text
        with patch("backend.tools.search.DDGS") as mock_ddgs_cls:
            mock_inst = MagicMock()
            mock_inst.text.return_value = [
                {"title": "FastAPI Docs", "body": "FastAPI is a modern web framework"}
            ]
            mock_ddgs_cls.return_value = mock_inst

            res = await web_search("FastAPI", max_results=3)
            assert "FastAPI Docs" in res
            assert "FastAPI is a modern web framework" in res

    asyncio.run(_test())
