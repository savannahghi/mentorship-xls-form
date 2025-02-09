from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, Literal

import click

import sghi.app
from sghi.config import Config, ConfigProxy
from sghi.etl.commons import run_workflow
from sghi.mentorship_xls_forms.use_cases import app_workflow_factory

from .constants import (
    APP_LOG_LEVEL_REG_KEY,
    APP_VERBOSITY_REG_KEY,
    DEFAULT_CONFIG,
)
from .printers import print_error, print_info, print_success

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from sghi.config import SettingInitializer
    from sghi.mentorship_xls_forms.lib.loaders import SupportedMetaFormats

# =============================================================================
# TYPES
# =============================================================================


MetadataFormats = Literal["auto", "excel"]


# =============================================================================
# SETUP
# =============================================================================


def setup(
    settings: Mapping[str, Any] | None = None,
    settings_initializers: Sequence[SettingInitializer] | None = None,
    log_level: int | str = "NOTSET",
    disable_default_initializers: bool = False,
) -> None:
    """Prepare the runtime and ready the application for use.

    :param settings: An optional mapping of settings and their values.
        When not provided, the runtime defaults as well as defaults set by the
        given setting initializers will be used instead.
    :param settings_initializers: An optional sequence of setting initializers
        to execute during runtime setup.
        Default initializers (set by the runtime) are always executed unless
        the ``disable_default_initializers`` param is set to ``True``.
    :param log_level: The log level to set for the root application logger.
        When not set, defaults to the value "NOTSET".
    :param disable_default_initializers: Exclude default setting initializers
        from being executed as part of the runtime setup.
        The default setting initializers set up logging and load SGHI ETL
        workflows into the application registry.
    """
    settings_dict: dict[str, Any] = dict(DEFAULT_CONFIG)
    settings_dict.update(settings or {})

    initializers: list[SettingInitializer] = list(settings_initializers or [])
    if not disable_default_initializers:
        from .settings_initializers import LoggingInitializer

        initializers.insert(0, LoggingInitializer())

    sghi.app.registry[APP_LOG_LEVEL_REG_KEY] = log_level
    config: Config = Config.of(
        settings=settings_dict,
        setting_initializers=initializers,
    )
    match sghi.app.conf:
        case ConfigProxy():
            sghi.app.conf.set_source(config)
        case _:
            setattr(sghi.app, "conf", config)  # noqa: B010


# =============================================================================
# MAIN
# =============================================================================


@click.command(epilog="Lets do this! ;)")
@click.option(
    "-o",
    "--out",
    "output_dir",
    envvar="M_CHECKLIST_OUTPUT_DIR",
    default=".",
    help=(
        "The output directory where generated XLSForms and other files are "
        "persisted."
    ),
    show_default=True,
    type=click.Path(
        allow_dash=False,
        dir_okay=True,
        exists=True,
        file_okay=False,
        resolve_path=True,
        writable=True,
    ),
)
@click.option(
    "--metadata-format",
    default="auto",
    envvar="M_CHECKLIST_METADATA_FORMAT",
    help=(
        "The format of the metadata file given. Only Excel metadata is "
        "currently supported. 'auto' determines the metadata format based on "
        "the extension of the file given and when that fails, defaults to "
        "assuming the file is an Excel file."
    ),
    show_default=True,
    type=click.Choice(choices=("auto", "excel")),
)
@click.option(
    "-l",
    "--log-level",
    default="WARNING",
    envvar="M_CHECKLIST_LOG_LEVEL",
    help='Set the log level of the "primary" application logger.',
    show_default=True,
    type=click.Choice(
        choices=(
            "CRITICAL",
            "ERROR",
            "WARNING",
            "INFO",
            "DEBUG",
            "NOTSET",
        ),
    ),
)
@click.option(
    "-v",
    "--verbose",
    "verbosity",
    count=True,
    default=0,
    envvar="M_CHECKLIST_VERBOSITY",
    help=(
        "Set the level of output to expect from the program on stdout. This "
        "is different from log level."
    ),
)
@click.version_option(
    package_name="mentorship-xls-forms",
    message="%(version)s",
)
@click.argument(
    "checklist_metadata",
    type=click.Path(
        allow_dash=False,
        dir_okay=False,
        exists=True,
        file_okay=True,
        readable=True,
        resolve_path=True,
    ),
)
@click.argument(
    "facility_metadata",
    type=click.Path(
        allow_dash=False,
        dir_okay=False,
        exists=True,
        file_okay=True,
        readable=True,
        resolve_path=True,
    ),
)
def main(
    checklist_metadata: str,
    facility_metadata: str,
    metadata_format: SupportedMetaFormats,
    output_dir: str,
    log_level: str,
    verbosity: int,
) -> None:
    """
    A tool used to generate XLSForms for mentorship checklists from metadata
    defined on an Excel file. The generated XLSForms can then be loaded to the
    ODK ecosystem tools and used to perform the assessment.

    \f

    :param checklist_metadata: The path to the Excel file containing the
        mentorship checklists metadata.
    :param facility_metadata: The path to the JSON file containing the
        facilities metadata.
    :param metadata_format: The format of the metadata file. Can be auto which
        allows the configuration format to be determined from the extension of
        the file name.
    :param output_dir: The output directory where generated XLSForms and other
        files are persisted. Must be writable.
    :param log_level: The log level of the "root application" logger.
    :param verbosity: The level of output to expect from the application on
        stdout. This is different from log level.

    :return: None.
    """

    sghi.app.registry[APP_VERBOSITY_REG_KEY] = verbosity
    try:
        print_info("Starting ...")

        sghi.app.setup = setup
        sghi.app.setup(settings=None, log_level=log_level)

        app_workflow = app_workflow_factory(
            checklist_metadata_path=checklist_metadata,
            facility_metadata_path=facility_metadata,
            output_dir=output_dir,
        )
        run_workflow(app_workflow)
        print_success("Done :)")
    except Exception as exp:  # noqa: BLE001
        _err_msg: str = (
            "An unhandled error occurred at runtime. The cause of the error "
            f"was: {exp!s}."
        )
        print_error(_err_msg, exception=exp)
        sys.exit(1)


if __name__ == "__main__":
    main(auto_envvar_prefix="M_CHECKLIST")
