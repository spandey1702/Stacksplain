import sys
import click
from .explainer import Explainer


@click.command()
@click.argument("error", required=False)
@click.option("--file", "-f", "error_file", type=click.File("r"), help="Read error from a file.")
def main(error: str | None, error_file):
    """
    Explain any error or stack trace in plain English.

    \b
    Usage:
      wtferror "NullPointerException at UserService.java:42"
      wtferror --file error.log
      ./myapp 2>&1 | wtferror
    """
    if error_file:
        error_text = error_file.read().strip()
    elif error:
        error_text = error.strip()
    elif not sys.stdin.isatty():
        error_text = sys.stdin.read().strip()
    else:
        click.echo("No error provided. Run `wtferror --help` for usage.", err=True)
        sys.exit(1)

    if not error_text:
        click.echo("Error input is empty.", err=True)
        sys.exit(1)

    try:
        explainer = Explainer()
        result = explainer.explain(error_text)
        click.echo(f"\n{result}\n")
    except ValueError as e:
        click.echo(f"Config error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Failed to explain error: {e}", err=True)
        sys.exit(1)
