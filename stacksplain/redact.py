import re

MASK = "[REDACTED]"

# Secrets with a recognizable shape: masked wherever they appear.
_KNOWN_FORMATS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{10,}"),                    # Anthropic
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),                        # OpenAI and similar
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),                  # AWS access key ID
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),                 # GitHub token
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),               # GitHub fine-grained token
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),                 # Slack token
    re.compile(r"\beyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}"),        # JWT
]

# Keep the prefix, mask the secret part.
_BEARER = re.compile(r"(?i)\b(Bearer\s+)[A-Za-z0-9._~+/=-]{8,}")
_URL_PASSWORD = re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://[^\s:/@]+:)[^\s@/]+(@)")

# A secret-sounding name assigned a value, e.g. `api_key = "..."` or `PASSWORD: ...`.
# The value must be a whole token, not code: no calls, indexing, or attribute access
# (`get_password()`, `os.environ["X"]`), and not a number, boolean, or type name.
_VALUE_CHARS = r"""[^\s"',;()\[\]{}]"""
_ASSIGNMENT = re.compile(
    r"(?i)"
    r"(\b[\w.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key)[\w.-]*"
    r"""["']?\s*[:=]\s*["']?)"""
    r"(?![\d.]+\b)"
    r"(?!(?:true|false|none|null|str|string|int|bool|bytes|number)\b)"
    rf"({_VALUE_CHARS}{{4,}})"
    rf"(?!{_VALUE_CHARS}|[(\[.])"
)


def redact(text: str) -> str:
    """Mask likely secrets so they are never sent to the API."""
    for pattern in _KNOWN_FORMATS:
        text = pattern.sub(MASK, text)
    text = _BEARER.sub(rf"\g<1>{MASK}", text)
    text = _URL_PASSWORD.sub(rf"\g<1>{MASK}\g<2>", text)
    text = _ASSIGNMENT.sub(rf"\g<1>{MASK}", text)
    return text
