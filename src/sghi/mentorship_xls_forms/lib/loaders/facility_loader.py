from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence
from logging import Logger
from typing import Final, Self, TextIO, TypedDict

import cattrs
from attrs import define, field

from sghi.disposable import not_disposed
from sghi.mentorship_xls_forms.core import Facility, Loader, LoadError
from sghi.utils import ensure_not_none, type_fqn

# =============================================================================
# TYPES
# =============================================================================


class _FacilityMapping(TypedDict):
    name: str
    mfl_code: int
    country: str
    sub_county: str
    ward: str


# =============================================================================
# CONSTANTS
# =============================================================================


_CONVERTER: Final[cattrs.Converter] = cattrs.Converter()


# =============================================================================
# LOADER
# =============================================================================


@define
class FacilityJSONMetadataLoader(Loader[Iterable[Facility]]):
    _metadata_source: Final[TextIO] = field(eq=False, hash=False, repr=False)
    _logger: Logger = field(init=False, repr=False)

    def __attrs_post_init__(self) -> None:
        self._logger = logging.getLogger(type_fqn(self.__class__))

    @property
    def is_disposed(self) -> bool:
        return self._metadata_source.closed

    def dispose(self) -> None:
        self._metadata_source.close()
        self._logger.info("Disposal complete.")

    @not_disposed
    def load(self) -> Iterable[Facility]:
        self._logger.info("Loading facilities from a JSON source.")
        try:
            raw_metadata: Sequence[_FacilityMapping] = json.load(
                fp=self._metadata_source,
            )
        except json.JSONDecodeError as exc:
            _err_msg: str = (
                f"Error loading facilities from JSON metadata: '{exc!s}'"
            )
            raise LoadError(message=_err_msg) from exc
        return _CONVERTER.structure(raw_metadata, Sequence[Facility])

    @classmethod
    def of(cls, metadata_source: TextIO) -> Self:
        ensure_not_none(metadata_source, "'metadata_source' MUST not be None.")
        return cls(metadata_source=metadata_source)  # pyright: ignore

    @classmethod
    def of_file_path(cls, metadata_file_path: str) -> Self:
        ensure_not_none(
            metadata_file_path,
            "'metadata_file_path' MUST bot be None.",
        )
        try:
            return cls.of(
                metadata_source=open(metadata_file_path),
            )
        except OSError as exc:
            _err_msg: str = (
                f"Error while opening metadata source file: '{exc!s}'"
            )
            raise LoadError(message=_err_msg) from exc
