import os
import time
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
_RETRY_DELAYS = [1, 2, 4]

load_dotenv()

_SYSTEM_PROMPT = """You are an expert software engineer and debugging assistant.
A developer has pasted an error message or stack trace. Your job is to explain it clearly and help them fix it fast.

Respond in exactly this format — no extra text before or after:

WHAT:
[2-3 sentences explaining what this error means in plain English]

WHY:
[The most likely root cause(s) — be specific, not generic]

FIX:
[Concrete steps to fix it. Include a short code example if it helps.]

AVOID:
[One tip on how to prevent this class of error in future]

Rules:
- Be concise. Developers are busy.
- Be specific. "Check your code" is useless.
- If the language/framework is identifiable from the stack trace, tailor your answer to it.
- If multiple root causes are equally likely, list them in order of probability."""


class Explainer:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not set. Add it to your .env file or export it in your shell."
            )
        self._client = genai.Client(api_key=api_key)
        self._model = os.getenv("GOOGLE_API_MODEL", "gemini-2.0-flash")

    def explain(self, error_text: str) -> str:
        last_exc: Exception | None = None
        for attempt, delay in enumerate([0] + _RETRY_DELAYS, start=1):
            if delay:
                logger.warning(f"Retrying in {delay}s (attempt {attempt}/{len(_RETRY_DELAYS) + 1})...")
                time.sleep(delay)
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=error_text,
                    config=types.GenerateContentConfig(
                        system_instruction=_SYSTEM_PROMPT,
                        temperature=0.2,
                    ),
                )
                return response.text
            except Exception as e:
                logger.exception(f"API error (attempt {attempt}): {e}")
                last_exc = e
        raise last_exc  # type: ignore[misc]
