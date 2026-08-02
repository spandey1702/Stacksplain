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
