# Changelog

## [Unreleased]

### Security
- Secrets are masked as `[REDACTED]` in error text, search results and file excerpts before anything is sent to the API
- `--scan` never opens credential files (`.env`, keys, certificates, Terraform vars/state)
- `--scan` skips symlinks that point outside the project and files over 1 MB
- `--scan` stops after 10 tool steps instead of looping

## [0.1.0] - 2026-06-26

### Added
- CLI entry point: `stacksplain "your error here"`
- Three input modes: argument, `--file` flag, and stdin pipe (`./app 2>&1 | stacksplain`)
- Gemini-powered structured output: WHAT / WHY / FIX / AVOID
- Colored terminal output — labels highlighted by section
- `--version` flag
- Retry logic with exponential backoff (1s, 2s, 4s) on transient API errors
- Language-agnostic: Java, Python, Node.js, Go, Rust stack traces
- GitHub Actions CI across Python 3.10, 3.11, 3.12
