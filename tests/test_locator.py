import os
import pytest
from unittest.mock import MagicMock, patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from stacksplain.locator import Locator


@pytest.fixture
def project(tmp_path):
    (tmp_path / "app.py").write_text(
        "def divide(a, b):\n"
        "    return a / b\n"
        "\n"
        "def main():\n"
        "    divide(1, 0)\n"
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.py").write_text("divide(1, 0)\n")
    return tmp_path


class TestSearchCodebase:
    def test_finds_matching_line(self, project):
        locator = Locator(root=str(project))
        result = locator._search_codebase("def divide")
        assert "app.py:1:" in result
        assert "def divide" in result

    def test_ignores_common_directories(self, project):
        locator = Locator(root=str(project))
        result = locator._search_codebase("divide(1, 0)")
        assert "node_modules" not in result

    def test_no_matches(self, project):
        locator = Locator(root=str(project))
        result = locator._search_codebase("totally_absent_symbol_xyz")
        assert "No matches" in result

    def test_filename_match(self, project):
        locator = Locator(root=str(project))
        result = locator._search_codebase("app.py")
        assert "filename match" in result


class TestReadFileLines:
    def test_reads_requested_range(self, project):
        locator = Locator(root=str(project))
        result = locator._read_file_lines("app.py", 1, 2)
        assert "1: def divide(a, b):" in result
        assert "2:     return a / b" in result

    def test_rejects_path_outside_root(self, project):
        locator = Locator(root=str(project))
        result = locator._read_file_lines("../../etc/passwd", 1, 5)
        assert "outside the project root" in result

    def test_missing_file(self, project):
        locator = Locator(root=str(project))
        result = locator._read_file_lines("does_not_exist.py", 1, 5)
        assert "not a file" in result

    def test_start_beyond_file_length(self, project):
        locator = Locator(root=str(project))
        result = locator._read_file_lines("app.py", 999, 1005)
        assert "only has" in result


class TestScanSafety:
    def test_search_skips_env_file(self, project):
        (project / ".env").write_text("ANTHROPIC_API_KEY=sk-secret\n")
        result = Locator(root=str(project))._search_codebase("ANTHROPIC_API_KEY")
        assert "sk-secret" not in result

    def test_read_refuses_env_file(self, project):
        (project / ".env").write_text("SECRET=1\n")
        result = Locator(root=str(project))._read_file_lines(".env", 1, 5)
        assert "secrets" in result

    def test_read_refuses_symlink_to_secret(self, project):
        (project / ".env").write_text("SECRET=1\n")
        (project / "notes.txt").symlink_to(project / ".env")
        result = Locator(root=str(project))._read_file_lines("notes.txt", 1, 5)
        assert "secrets" in result

    def test_search_skips_symlink_outside_root(self, project, tmp_path_factory):
        outside = tmp_path_factory.mktemp("outside") / "private.txt"
        outside.write_text("top secret\n")
        (project / "link.txt").symlink_to(outside)
        result = Locator(root=str(project))._search_codebase("top secret")
        assert "link.txt" not in result

    def test_search_redacts_secret_in_code(self, project):
        (project / "config.py").write_text('API_KEY = "sk-ant-api03-abcdefghijklmnop"\n')
        result = Locator(root=str(project))._search_codebase("API_KEY")
        assert "config.py:1:" in result
        assert "sk-ant-api03" not in result

    def test_read_redacts_secret_in_code(self, project):
        (project / "config.py").write_text('DATABASE_URL = "postgres://admin:hunter2@db/app"\n')
        result = Locator(root=str(project))._read_file_lines("config.py", 1, 1)
        assert "hunter2" not in result
        assert "[REDACTED]" in result

    def test_search_skips_large_files(self, project):
        (project / "big.log").write_text("needle\n" + "x" * 1_100_000)
        result = Locator(root=str(project))._search_codebase("needle")
        assert "No matches" in result


class TestLocatorInit:
    def test_raises_without_api_key(self, tmp_path):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not set"):
                Locator(root=str(tmp_path))


class TestLocate:
    def test_locate_returns_final_text(self, project):
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "LOCATION:\napp.py:2\n\nWHAT:\nTest\n\nWHY:\nTest\n\nFIX:\nTest\n\nAVOID:\nTest"
        mock_message = MagicMock()
        mock_message.content = [mock_block]

        with patch("stacksplain.locator.anthropic.Anthropic"):
            with patch("stacksplain.locator.beta_tool", side_effect=lambda f: f):
                locator = Locator(root=str(project))
                with patch.object(locator._client.beta.messages, "tool_runner", return_value=[mock_message]):
                    result = locator.locate("ZeroDivisionError in app.py")
                    assert "LOCATION:" in result
                    assert "app.py:2" in result

    def test_locate_stops_after_max_turns(self, project):
        looping = [MagicMock(stop_reason="tool_use", content=[]) for _ in range(20)]
        with patch("stacksplain.locator.anthropic.Anthropic"):
            with patch("stacksplain.locator.beta_tool", side_effect=lambda f: f):
                locator = Locator(root=str(project))
                with patch.object(locator._client.beta.messages, "tool_runner", return_value=looping):
                    result = locator.locate("ZeroDivisionError in app.py")
        assert "Couldn't pin down" in result
