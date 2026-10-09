import sys
import click
from . import __version__
from .explainer import Explainer
from .locator import Locator
from .redact import redact

_DRY_RUN_LIST_LIMIT = 50


def _print_result(result: str) -> None:
    labels = {
        "LOCATION:": "blue",
        "WHAT:": "cyan",
        "WHY:": "yellow",
        "FIX:": "green",
        "AVOID:": "magenta",
    }
    for line in result.splitlines():
        color = next((c for label, c in labels.items() if line.startswith(label)), None)
        if color:
            click.echo(click.style(line, fg=color, bold=True))
        else:
            click.echo(line)


def _print_dry_run(error_text: str, scan: bool, scan_path: str) -> None:
    click.echo(click.style("DRY RUN: nothing was sent.", fg="yellow", bold=True))
    click.echo()
    click.echo(click.style("Error text, as it would be sent:", bold=True))
    click.echo(redact(error_text))
    click.echo()
    click.echo("Also sent: Stacksplain's built-in instructions (no data from your machine).")
    if not scan:
        return

    locator = Locator(root=scan_path, require_api_key=False)
    searchable, excluded = locator.scan_summary()
    click.echo()
    click.echo(click.style(f"--scan: Claude could search and read {searchable} files in {locator.root}", bold=True))
    click.echo("Search results and file excerpts are masked the same way before they're sent.")
    if excluded:
        click.echo()
        click.echo(click.style("Never opened:", bold=True))
        for rel, reason in excluded[:_DRY_RUN_LIST_LIMIT]:
            click.echo(f"  {rel}  ({reason})")
        if len(excluded) > _DRY_RUN_LIST_LIMIT:
            click.echo(f"  ...and {len(excluded) - _DRY_RUN_LIST_LIMIT} more")


@click.command()
@click.argument("error", required=False)
@click.option("--file", "-f", "error_file", type=click.File("r"), help="Read error from a file.")
@click.option(
    "--scan",
    "-s",
    is_flag=True,
    help="Search the current project's files to locate the error before explaining it.",
)
@click.option(
    "--path",
    "scan_path",
    default=".",
    show_default=True,
    help="Project root to search when using --scan.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be sent to the API, after masking, without sending anything.",
)
@click.version_option(version=__version__, prog_name="stacksplain")
def main(error: str | None, error_file, scan: bool, scan_path: str, dry_run: bool):
    """
    Explain any error or stack trace in plain English.

    \b
    Usage:
      stacksplain "NullPointerException at UserService.java:42"
      stacksplain --file error.log
      stacksplain --scan "NullPointerException at UserService.java:42"
      stacksplain --scan --dry-run --file error.log
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

    if dry_run:
        _print_dry_run(error_text, scan, scan_path)
        return

    try:
        if scan:
            locator = Locator(root=scan_path)
            result = locator.locate(error_text)
        else:
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
