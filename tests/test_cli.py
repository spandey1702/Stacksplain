import os
import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from stacksplain.cli import main

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

MOCK_EXPLANATION = "WHAT:\nThe object is null.\n\nWHY:\nNot initialized.\n\nFIX:\nAdd null check.\n\nAVOID:\nUse constructor injection."


@pytest.fixture
def mock_explainer():
    with patch("stacksplain.cli.Explainer") as mock:
        instance = mock.return_value
        instance.explain.return_value = MOCK_EXPLANATION
        yield instance


class TestCLI:
    def test_explain_from_argument(self, mock_explainer):
        runner = CliRunner()
        result = runner.invoke(main, ["NullPointerException at line 42"])
        assert result.exit_code == 0
        assert "WHAT:" in result.output

    def test_explain_from_file(self, mock_explainer, tmp_path):
        error_file = tmp_path / "error.log"
        error_file.write_text("SegmentationFault at core.c:99")
        runner = CliRunner()
        result = runner.invoke(main, ["--file", str(error_file)])
        assert result.exit_code == 0
        assert "WHAT:" in result.output

    def test_explain_from_stdin(self, mock_explainer):
        runner = CliRunner()
        result = runner.invoke(main, input="TypeError: cannot unpack non-sequence int")
        assert result.exit_code == 0
        assert "WHAT:" in result.output

    def test_no_input_exits_with_error(self):
        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code == 1

    def test_empty_input_exits_with_error(self, mock_explainer):
        runner = CliRunner()
        result = runner.invoke(main, ["   "])
        assert result.exit_code == 1


class TestDryRun:
    def test_shows_masked_text_and_sends_nothing(self):
        with patch("stacksplain.cli.Explainer") as explainer:
            result = CliRunner().invoke(
                main, ["--dry-run", "cannot connect to postgres://admin:hunter2@db/app"]
            )
        assert result.exit_code == 0
        assert "nothing was sent" in result.output
        assert "postgres://admin:[REDACTED]@db/app" in result.output
        assert "hunter2" not in result.output
        explainer.assert_not_called()

    def test_scan_lists_files_never_opened(self, tmp_path):
        (tmp_path / "app.py").write_text("print('hi')\n")
        (tmp_path / ".env").write_text("SECRET=1\n")
        (tmp_path / ".stacksplainignore").write_text("private/\n")
        (tmp_path / "private").mkdir()
        (tmp_path / "private" / "data.txt").write_text("x\n")
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            result = CliRunner().invoke(
                main, ["--dry-run", "--scan", "--path", str(tmp_path), "KeyError: 'x'"]
            )
        assert result.exit_code == 0
        assert ".env  (may contain secrets)" in result.output
        assert "private/  (listed in .stacksplainignore)" in result.output
        assert "app.py" not in result.output
