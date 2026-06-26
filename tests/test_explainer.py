import os
import pytest
from unittest.mock import MagicMock, patch

os.environ.setdefault("GOOGLE_API_KEY", "test-key")

from stacksplain.explainer import Explainer


class TestExplainer:
    def test_raises_without_api_key(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="GOOGLE_API_KEY not set"):
                Explainer()

    def test_explain_returns_text(self):
        mock_response = MagicMock()
        mock_response.text = "WHAT:\nTest\n\nWHY:\nTest\n\nFIX:\nTest\n\nAVOID:\nTest"

        with patch("stacksplain.explainer.genai.Client") as mock_client:
            instance = mock_client.return_value
            instance.models.generate_content.return_value = mock_response

            explainer = Explainer()
            result = explainer.explain("NullPointerException at line 42")

            assert "WHAT:" in result
            assert "WHY:" in result
            assert "FIX:" in result
            assert "AVOID:" in result

    def test_explain_passes_error_text_to_api(self):
        mock_response = MagicMock()
        mock_response.text = "WHAT:\nfoo"

        with patch("stacksplain.explainer.genai.Client") as mock_client:
            instance = mock_client.return_value
            instance.models.generate_content.return_value = mock_response

            explainer = Explainer()
            explainer.explain("SegmentationFault at core.c:99")

            call_args = instance.models.generate_content.call_args
            assert "SegmentationFault at core.c:99" in str(call_args)
