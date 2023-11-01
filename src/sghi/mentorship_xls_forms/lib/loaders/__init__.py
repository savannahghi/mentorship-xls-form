from collections.abc import Iterable
from typing import Literal

from sghi.mentorship_xls_forms.core import (
    Loader,
    LoadError,
    MentorshipChecklist,
)

from .checklist_loader import ChecklistsExcelMetadataLoader
from .facility_loader import FacilityJSONMetadataLoader

# =============================================================================
# TYPES
# =============================================================================

SupportedMetaFormats = Literal["auto", "excel"]
"""The supported metadata formats.

`auto` indicates that the metadata format should be determined automatically
from the file extension of the metadata file given.
"""


# =============================================================================
# LOADER
# =============================================================================


def load_metadata(
    metadata_file_path: str,
    metadata_format: SupportedMetaFormats,
) -> Iterable[MentorshipChecklist]:
    """Helper that loads metadata from a file and returns an ``Iterable`` of
    the loaded :class:`checklists<MentorshipChecklist>`.

    :param metadata_file_path: A path to the metadata containing file that is
        to be loaded. The file should be of the format specified on the
        ``metadata_format`` parameter. If ``auto`` is given, then the file
        should be of one of the formats specified by :attr:`SupportedMetaFormats`
        and have a file extension corresponding to the given format.
    :param metadata_format: The format of the given metadata file or `auto`.
        The format should be one of the formats specified by
        the :attr:`SupportedMetaFormats`. ``auto`` indicates that the format
        should be determined based on the file extension of the given metadata
        source file. When that fails, then the file will treated as an `Excel`
        file.

    :return: An ``Iterable``  of the loaded ``MentorshipChecklist`` instances.

    :raise LoadError: If the metadata format specified is not one of the ones
        specified by the :attr:`SupportedMetaFormats` attribute or incase any
        errors when loading.
    """
    loader: Loader[Iterable[MentorshipChecklist]]
    match metadata_format:
        # FIXME: These two are not the same!!!. Add code to load data for the
        #  `auto` case.
        case "auto" | "excel":
            loader = ChecklistsExcelMetadataLoader.of_file_path(
                metadata_file_path=metadata_file_path,
            )
        case _:
            _err_msg: str = f"Unknown metadata format '{metadata_format}'."
            raise LoadError(message=metadata_format)

    with loader:
        return loader.load()


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "ChecklistsExcelMetadataLoader",
    "FacilityJSONMetadataLoader",
    "LoadError",
    "SupportedMetaFormats",
    "load_metadata",
]
