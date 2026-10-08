import pytest
from stacksplain.redact import redact, MASK


class TestKnownFormats:
    @pytest.mark.parametrize("secret", [
        "sk-ant-api03-abcdefghijklmnop",
        "sk-proj-abcdefghijklmnopqrstuvwx",
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_abcdefghijklmnopqrstuvwxyz0123",
        "github_pat_abcdefghijklmnopqrstuvwxyz",
        "xoxb-1234567890-abcdefghij",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N",
    ])
    def test_masks_known_secret(self, secret):
        result = redact(f"Request failed using {secret} at client.py:12")
        assert secret not in result
        assert MASK in result
        assert "client.py:12" in result

    def test_masks_private_key_block(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\nIBAAKC\n-----END RSA PRIVATE KEY-----"
        assert redact(text) == MASK

    def test_masks_bearer_token_keeps_prefix(self):
        result = redact("Authorization: Bearer abc123def456ghi789")
        assert result == f"Authorization: Bearer {MASK}"

    def test_masks_password_in_url(self):
        result = redact("could not connect to postgres://admin:hunter2@db:5432/app")
        assert result == f"could not connect to postgres://admin:{MASK}@db:5432/app"


class TestAssignments:
    @pytest.mark.parametrize("line, kept", [
        ('API_KEY = "a8f3k2m9q1"', 'API_KEY = "'),
        ("password: s3cr3tvalue", "password: "),
        ("DB_PASSWORD=hunter2hunter2", "DB_PASSWORD="),
        ("'client_secret': 'zzyyxxwwvv'", "'client_secret': '"),
    ])
    def test_masks_value_keeps_name(self, line, kept):
        result = redact(line)
        assert result.startswith(kept)
        assert MASK in result

    @pytest.mark.parametrize("line", [
        "token_count = 5",
        "max_tokens=2000",
        "password = get_password()",
        'api_key = os.environ["ANTHROPIC_API_KEY"]',
        "def login(password: str) -> bool:",
        "remember_token: true",
        "secret = None",
        "password: ${DB_PASSWORD}",
    ])
    def test_leaves_ordinary_code_alone(self, line):
        assert redact(line) == line


def test_plain_stack_trace_unchanged():
    trace = (
        "Traceback (most recent call last):\n"
        '  File "app/services/parser.py", line 42, in parse\n'
        "    value, extra = parse_response(raw)\n"
        "TypeError: cannot unpack non-iterable int object"
    )
    assert redact(trace) == trace
