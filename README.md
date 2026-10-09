# stacksplain

![Tests](https://github.com/spandey1702/Stacksplain/actions/workflows/test.yml/badge.svg)

Paste any error or stack trace and get a plain-English explanation with a suggested fix — in seconds.

```
stacksplain "NullPointerException at UserService.java:42"
```

## Install

```bash
pip install stacksplain
```

Requires an [Anthropic API key](https://platform.claude.com).

## Setup

```bash
export ANTHROPIC_API_KEY=your_key_here
```

Or add it to a `.env` file in your working directory:

```
ANTHROPIC_API_KEY=your_key_here
```

## Usage

**Paste an error directly:**
```bash
stacksplain "TypeError: cannot unpack non-sequence int"
```

**Pipe from your terminal:**
```bash
./myapp 2>&1 | stacksplain
```

**Read from a log file:**
```bash
stacksplain --file error.log
```

**Scan your project to locate the bug, not just explain it:**
```bash
stacksplain --scan "NullPointerException at UserService.java:42"
```
Run this from inside your project directory (or pass `--path` to point elsewhere). Instead of guessing from the error text alone, Claude searches and reads your actual source files before answering, so the output cites a real file/line it confirmed on disk instead of a plausible-sounding guess.

**Check what would be sent, without sending anything:**
```bash
stacksplain --scan --dry-run --file error.log
```
Prints the error text exactly as it would be sent (after masking), how many files `--scan` could open, and every file it will never open, with the reason. No API key needed.

```
DRY RUN: nothing was sent.

Error text, as it would be sent:
TypeError: cannot unpack non-iterable int object
ERROR db=postgres://admin:[REDACTED]@db:5432/app

--scan: Claude could search and read 3 files in /home/you/app

Never opened:
  .env  (may contain secrets)
  backup.sql  (listed in .stacksplainignore)
  customer_exports/  (listed in .stacksplainignore)
```

**Keep files out of `--scan` with `.stacksplainignore`:**

Add a `.stacksplainignore` file to your project root, one pattern per line, like `.gitignore`:
```
# Customer data never leaves this machine
customer_exports/
*.sql
config/prod.yaml
```
A bare name (`*.sql`, `customer_exports/`) matches at any depth. A pattern with a `/` in the middle (`config/prod.yaml`) matches from the project root. A trailing `/` is optional. Negation (`!pattern`) isn't supported.

## Output

```
WHAT:
The value you're trying to unpack is an integer, not a sequence...

WHY:
Most likely the function returned a single value instead of a tuple...

FIX:
Check the return type of the function before unpacking...

AVOID:
Use isinstance() to validate the return type before unpacking.
```

With `--scan`, a `LOCATION:` section is added on top, citing the actual file and line Claude found and read:

```
LOCATION:
app/services/parser.py:42 — `return_value, extra = parse_response(raw)`

WHAT:
...
```

## Supported languages

Language-agnostic. Works with Java, Python, Node.js, Go, Rust, and any other stack trace format.

## Privacy and safety

Your error text, and with `--scan` the code Claude reads, is sent to the Anthropic API. Before anything is sent, Stacksplain:

- **Masks secrets** as `[REDACTED]`: API keys and tokens with known formats (Anthropic, OpenAI, AWS, GitHub, Slack, JWTs, `Bearer` tokens), passwords in URLs such as `postgres://user:pass@host`, private key blocks, and values assigned to secret-sounding names like `api_key = "..."` or `PASSWORD=...`.
- **Never opens credential files** with `--scan`: `.env`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`, `*.tfvars`, `*.tfstate` and similar.
- **Never opens anything you list in `.stacksplainignore`**, including through a symlink.
- **Stays inside your project**: paths and symlinks that resolve outside `--path` are refused, and files over 1 MB are skipped.
- **Stops after 10 tool steps** with `--scan`, so a confusing error can't run up a long session.

## Limitations

- Redaction is pattern-based, for both the error text and the files `--scan` reads. It misses secrets with no recognizable format under an ordinary name (`x = "a8f3k2..."`), unquoted numeric or very short values (`pin = 4821`), and secrets written in a sentence instead of assigned. Use `--dry-run` to check what would be sent, and list sensitive files in `.stacksplainignore`.
- `--scan` reads UTF-8 text files only. Files that aren't valid UTF-8 are skipped, which covers most binary files but also text saved in other encodings. A binary file that happens to be valid UTF-8 can still be searched.

## License

MIT
