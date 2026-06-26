import os
import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from wtferror.cli import main

os.environ.setdefault("GOOGLE_API_KEY", "test-key")

MOCK_EXPLANATION = "WHAT:\nThe object is null.\n\nWHY:\nNot initialized.\n\nFIX:\nAdd null check.\n\nAVOID:\nUse constructor injection."


@pytest.fixture
def mock_explainer():
    with patch("wtferror.cli.Explainer") as mock:
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
