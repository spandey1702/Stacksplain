# stacksplain

Paste any error or stack trace and get a plain-English explanation with a suggested fix — in seconds.

```
stacksplain "NullPointerException at UserService.java:42"
```

## Install

```bash
pip install stacksplain
```

Requires a [Google Gemini API key](https://aistudio.google.com).

## Setup

```bash
export GOOGLE_API_KEY=your_key_here
```

Or add it to a `.env` file in your working directory:

```
GOOGLE_API_KEY=your_key_here
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

## Supported languages

Language-agnostic. Works with Java, Python, Node.js, Go, Rust, and any other stack trace format.

## License

MIT
