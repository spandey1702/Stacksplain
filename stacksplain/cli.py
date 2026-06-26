import sys
import click
from . import __version__
from .explainer import Explainer


def _print_result(result: str) -> None:
    labels = {"WHAT:": "cyan", "WHY:": "yellow", "FIX:": "green", "AVOID:": "magenta"}
    for line in result.splitlines():
        color = next((c for label, c in labels.items() if line.startswith(label)), None)
        if color:
            click.echo(click.style(line, fg=color, bold=True))
        else:
            click.echo(line)


@click.command()
@click.argument("error", required=False)
@click.option("--file", "-f", "error_file", type=click.File("r"), help="Read error from a file.")
@click.version_option(version=__version__, prog_name="stacksplain")
def main(error: str | None, error_file):
    """
    Explain any error or stack trace in plain English.

    \b
    Usage:
      stacksplain "NullPointerException at UserService.java:42"
      stacksplain --file error.log
      ./myapp 2>&1 | stacksplain
    """
    if error_file:
        error_text = error_file.read().strip()
    elif error:
        error_text = error.strip()
    elif not sys.stdin.isatty():
        error_text = sys.stdin.read().strip()
    else:
        click.echo("No error provided. Run `stacksplain --help` for usage.", err=True)
        sys.exit(1)

    if not error_text:
        click.echo("Error input is empty.", err=True)
        sys.exit(1)

    try:
        explainer = Explainer()
        result = explainer.explain(error_text)
        click.echo()
        _print_result(result)
        click.echo()
    except ValueError as e:
        click.echo(click.style(f"Config error: {e}", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Failed to explain error: {e}", fg="red"), err=True)
        sys.exit(1)
