"""Utilities for outputting to the console."""

from __future__ import annotations

import sys
import traceback

import click

from sghi.app import registry

from .constants import APP_VERBOSITY_REG_KEY


def print_debug(message: str, nl: bool = True) -> None:
    """Display a debug message on the console.

    :param message: The debug message to display on the console. This SHOULD BE
        a string.
    :param nl: Whether to print a new line after the message. This is enabled
        by default.

    :return: None.
    """
    click.echo(click.style(message, fg="magenta"), nl=nl)


def print_info(message: str) -> None:
    """Display an informational message on the console.

    :param message: The informational message to display on the console. This
        SHOULD BE a string.

    :return: None.
    """
    click.echo(click.style(message, fg="bright_blue"))


def print_error(message: str, exception: BaseException | None = None) -> None:
    """Display an error message on the console.

    When an exception is provided, the stacktrace of the exception is only
    displayed if application verbosity is set to 1 or above.

    :param message: The error message to display on the console. This
        SHOULD BE a string.
    :param exception: An optional exception that resulted in the error being
        displayed. To display the stacktrace of the exception, the application
        verbosity level must be set to 1 or above. Defaults to ``None``, in
        which case only the error message is displayed on the console.

    :return: None.
    """
    verbosity: int = registry.get(APP_VERBOSITY_REG_KEY, 0)
    click.echo(click.style(message, fg="red"), file=sys.stderr)
    match verbosity:
        case 1 if exception is not None:
            click.secho(
                "".join(traceback.format_exception(exception, chain=False)),
                fg="yellow",
                file=sys.stderr,
            )
        case _ if verbosity > 1 and exception is not None:
            click.secho(
                "".join(traceback.format_exception(exception, chain=True)),
                fg="yellow",
                file=sys.stderr,
            )


def print_success(message: str) -> None:
    """Display a success message on the console.

    :param message: The success message to display on the console. This
        SHOULD BE a string.

    :return: None.
    """
    click.echo(click.style(message, fg="green"))
