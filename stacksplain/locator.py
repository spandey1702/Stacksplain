import os
import time
import logging
from pathlib import Path
import anthropic
from anthropic import beta_tool
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
_RETRY_DELAYS = [1, 2, 4]

load_dotenv()

_IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", "target", ".idea", ".vscode", ".pytest_cache",
    "egg-info", ".terraform",
}
_MAX_RESULTS = 40
_MAX_LINE_LEN = 200
_MAX_READ_LINES = 200

_SYSTEM_PROMPT = """You are an expert software engineer debugging a real codebase.
A developer has pasted an error or stack trace. You have tools to search and
read the actual project files on disk — use them before answering. Do not
guess at code you haven't read.

Process:
1. Pull out identifiers from the error (class/function/file names, symbols).
2. Use search_codebase to find where they're defined or referenced.
3. Use read_file_lines to read the surrounding code at the most likely
   location(s) before concluding anything.
4. If the first search doesn't clearly explain the error, search again with
   a different term rather than guessing.

Respond in exactly this format — no extra text before or after:

LOCATION:
[The specific file(s) and line(s) you found via the tools. If you genuinely
can't locate it in this codebase after searching, say so plainly here.]

WHAT:
[2-3 sentences explaining what this error means in plain English]

WHY:
[The root cause, grounded in the actual code you read — cite specifics]

FIX:
[Concrete steps to fix it, referencing the real file/line and current code]

AVOID:
[One tip on how to prevent this class of error in future]

Rules:
- Be concise. Developers are busy.
- Never state a file/line you didn't actually confirm via read_file_lines.
- If multiple locations are plausible, investigate the most likely one first;
  mention the others briefly only if the top candidate doesn't pan out."""


class Locator:
    def __init__(self, root: str = "."):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Add it to your .env file or export it in your shell."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = os.getenv("ANTHROPIC_API_MODEL", "claude-sonnet-5")
        self.root = Path(root).resolve()

    def _iter_files(self):
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS and not d.endswith(".egg-info")]
            for name in filenames:
                yield Path(dirpath) / name

    def _search_codebase(self, pattern: str) -> str:
        """Search the codebase for a filename, symbol, or text pattern.

        Args:
            pattern: A substring to search for in file names and file contents
                (case-insensitive). Use identifiers from the error — class
                names, function names, file names.
        """
        pattern_lower = pattern.lower()
        results: list[str] = []

        for path in self._iter_files():
            if len(results) >= _MAX_RESULTS:
                break
            rel = path.relative_to(self.root)
            if pattern_lower in path.name.lower():
                results.append(f"{rel}  (filename match)")
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if pattern_lower in line.lower():
                    snippet = line.strip()[:_MAX_LINE_LEN]
                    results.append(f"{rel}:{i}: {snippet}")
                    if len(results) >= _MAX_RESULTS:
                        break

        if not results:
            return f"No matches for '{pattern}' in {self.root}."
        return "\n".join(results)

    def _read_file_lines(self, path: str, start_line: int, end_line: int) -> str:
        """Read a range of lines from a file in the codebase.

        Args:
            path: File path relative to the project root (as returned by search_codebase).
            start_line: First line to read (1-indexed).
            end_line: Last line to read (inclusive). Capped to 200 lines per call.
        """
        target = (self.root / path).resolve()
        if self.root not in target.parents and target != self.root:
            return f"Error: '{path}' resolves outside the project root."
        if not target.is_file():
            return f"Error: '{path}' is not a file."

        try:
            lines = target.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            return f"Error reading '{path}': {e}"

        start = max(1, start_line)
        end = min(len(lines), start_line + _MAX_READ_LINES - 1, end_line)
        if start > len(lines):
            return f"Error: '{path}' only has {len(lines)} lines."

        numbered = "\n".join(f"{i}: {lines[i - 1]}" for i in range(start, end + 1))
        return f"{path} (lines {start}-{end} of {len(lines)}):\n{numbered}"

    def locate(self, error_text: str) -> str:
        search_codebase = beta_tool(self._search_codebase)
        read_file_lines = beta_tool(self._read_file_lines)

        last_exc: Exception | None = None
        for attempt, delay in enumerate([0] + _RETRY_DELAYS, start=1):
            if delay:
                logger.warning(f"Retrying in {delay}s (attempt {attempt}/{len(_RETRY_DELAYS) + 1})...")
                time.sleep(delay)
            try:
                runner = self._client.beta.messages.tool_runner(
                    model=self._model,
                    max_tokens=4096,
                    system=_SYSTEM_PROMPT,
                    tools=[search_codebase, read_file_lines],
                    messages=[{"role": "user", "content": error_text}],
                )
                final = None
                for message in runner:
                    final = message
                if final is None:
                    raise RuntimeError("No response from model.")
                return next(block.text for block in final.content if block.type == "text")
            except Exception as e:
                logger.error(f"API error (attempt {attempt}): {e}")
                last_exc = e

        raise last_exc  # type: ignore[misc]
