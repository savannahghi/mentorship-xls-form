from collections.abc import Iterable, Sequence
from typing import Any, BinaryIO, Final, Self, cast, override

import cattrs
import pyexcel
from attrs import define, field, fields

from sghi.disposable import not_disposed
from sghi.mentorship_xls_forms.core import Writer
from sghi.mentorship_xls_forms.lib.xls_forms import (
    XLSForm,
    XLSFormChoice,
    XLSFormRecord,
    XLSFormSettings,
)
from sghi.utils import ensure_not_none

# =============================================================================
# CONSTANT
# =============================================================================


_CHOICES_SHEET_NAME: Final[str] = "choices"

_CONVERTER: Final[cattrs.Converter] = cattrs.Converter(
    unstruct_strat=cattrs.UnstructureStrategy.AS_TUPLE,
)

_SETTINGS_SHEET_NAME: Final[str] = "settings"

_SURVEY_SHEET_NAME: Final[str] = "survey"


# =============================================================================
# HELPERS
# =============================================================================


def _setup_converter() -> None:
    # Convert all `None` values to an empty string.
    _CONVERTER.register_unstructure_hook(type(None), lambda _: "")


_setup_converter()


# =============================================================================
# WRITER
# =============================================================================


@define
class XLSFormWriter(Writer[XLSForm]):
    _target_file: BinaryIO = field(eq=False, hash=False, repr=False)

    @property
    def is_disposed(self) -> bool:
        return self._target_file.closed

    @override
    def dispose(self) -> None:
        self._target_file.close()

    @not_disposed()
    def write(self, data: XLSForm) -> None:
        ensure_not_none(data, "'data' MUST not be None.")
        workbook = {
            _SURVEY_SHEET_NAME: self._objects_to_xls(
                XLSFormRecord,
                data.survey,
            ),
            _CHOICES_SHEET_NAME: self._objects_to_xls(
                XLSFormChoice,
                data.choices,
            ),
            _SETTINGS_SHEET_NAME: self._objects_to_xls(
                XLSFormSettings,
                (data.settings,),
            ),
        }
        stream: BinaryIO = cast(
            BinaryIO,
            pyexcel.save_book_as(bookdict=workbook, dest_file_type="xlsx"),
        )
        self._target_file.write(stream.read())

    @classmethod
    def of(cls, target_file: BinaryIO) -> Self:
        ensure_not_none(target_file, "'target_file' MUST not be None.")
        return cls(target_file=target_file)  # pyright: ignore

    @classmethod
    def of_file_path(cls, write_file_path: str) -> Self:
        ensure_not_none(write_file_path, "'write_file_path' MUST not be None.")
        return cls.of(
            target_file=open(file=write_file_path, mode="wb"),
        )

    @staticmethod
    def _objects_to_xls[_AT](
        object_klass: type[_AT],
        objects: Iterable[_AT],
    ) -> Sequence[Sequence[Any]]:
        ensure_not_none(object_klass, "'object_klass' MUST not be None.")
        ensure_not_none(objects, "'objects' MUST not be None.")
        xls_entries: list[Any] = [
            list(_CONVERTER.unstructure(an_object)) for an_object in objects
        ]
        header_row: Sequence[str] = [
            attribute.name for attribute in fields(object_klass)
        ]
        xls_entries.insert(0, header_row)

        return xls_entries
