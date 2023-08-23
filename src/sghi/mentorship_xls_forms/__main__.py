from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import click

from .use_cases import main_pipeline_factory

if TYPE_CHECKING:
    from .lib.loaders import SupportedMetaFormats

# =============================================================================
# TYPES
# =============================================================================

MetadataFormats = Literal["auto", "excel"]

# =============================================================================
# MAIN
# =============================================================================


@click.command(epilog="Lets do this! ;)")
@click.option(
    "-o",
    "--out",
    "output_dir",
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
    )
)
@click.option(
    "--metadata-format",
    default="auto",
    help=(
        "The format of the metadata file given. Only Excel metadata is "
        "currently supported. 'auto' determines the metadata format based on "
        "the extension of the file given and when that fails, defaults to "
        "assuming the file is an Excel file."
    ),
    show_default=True,
    type=click.Choice(choices=("auto", "excel")),
)
@click.version_option(
    package_name="mentorship-xls-forms",
    message="%(version)s"
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
    )
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
    )
)
def main(
    checklist_metadata: str,
    facility_metadata: str,
    metadata_format: SupportedMetaFormats,
    output_dir: str,
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

    :return: None.
    """

    click.secho("Starting ...", fg="bright_blue")
    main_pipeline_factory()((checklist_metadata, facility_metadata))
    click.secho("Done :)", fg="bright_blue")


if __name__ == "__main__":
    main(auto_envvar_prefix="M_CHECKLIST")
