from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, override

from attrs import define, field, validators

from sghi.disposable import not_disposed
from sghi.etl.commons import (
    GatherSource,
    SimpleWorkflowDefinition,
)
from sghi.etl.core import Processor, Sink
from sghi.mentorship_xls_forms.core import Facility, Loader, Serializer, Writer
from sghi.mentorship_xls_forms.core import MentorshipChecklist as Checklist
from sghi.mentorship_xls_forms.lib.loaders import (
    ChecklistsExcelMetadataLoader,
    KMHFLFacilityLoader,
)
from sghi.mentorship_xls_forms.lib.serializers.xls_form import (
    ChecklistXLSFormSerializer,
    FacilitiesXLSFormSerializer,
)
from sghi.mentorship_xls_forms.lib.writers import XLSFormWriter
from sghi.mentorship_xls_forms.lib.xls_forms import XLSForm, XLSFormItem
from sghi.utils import ensure_not_none

if TYPE_CHECKING:
    from sghi.etl.core import WorkflowDefinition

# =============================================================================
# TYPES
# =============================================================================


type _CLF = Callable[[str], Loader[Iterable[Checklist]]]
"""Checklist Loader Factory."""

type _CSF = Callable[[], Serializer[Checklist, XLSForm]]
"""Checklist Serializer Factory."""

type _CWF = Callable[[str], Writer[XLSForm]]
"""Checklist Writer Factory."""

type _FLF = Callable[[str], Loader[Iterable[Facility]]]
"""Facility Loader Factory."""

type _FSF = Callable[[], Serializer[Iterable[Facility], XLSFormItem]]
"""Facility Serializer Factory."""

type _RDT = tuple[Iterable[Checklist], Iterable[Facility]]

type _PDT = Iterable[tuple[Checklist, XLSForm]]


# =============================================================================
# HELPERS
# =============================================================================


@define
class _ChecklistProcessor(Processor[_RDT, _PDT]):

    _checklist_serializer_factory: _CSF = field(
        alias="checklist_serializer_factory",
        default=ChecklistXLSFormSerializer.of,
        repr=False,
        validator=validators.is_callable(),
    )
    _facilities_serializer_factory: _FSF = field(
        alias="facilities_serializer_factory",
        default=FacilitiesXLSFormSerializer.of,
        repr=False,
        validator=validators.is_callable(),
    )
    _is_disposed: bool = field(default=False, init=False, repr=False)

    @property
    @override
    def is_disposed(self) -> bool:
        return self._is_disposed

    @not_disposed
    @override
    def apply(self, raw_data: _RDT) -> _PDT:
        ensure_not_none(raw_data, "'raw_data' MUST not be None.")
        org_units: XLSFormItem
        org_units = self._facilities_serializer_factory().serialize(
            raw_data[1]
        )
        return tuple(
            self._checklist_to_form(checklist, org_units)
            for checklist in raw_data[0]
        )

    @override
    def dispose(self) -> None:
        self._is_disposed = True

    def _checklist_to_form(
        self,
        checklist: Checklist,
        org_units: XLSFormItem,
    ) -> tuple[Checklist, XLSForm]:
        ensure_not_none(checklist, "'checklist' MUST not be None.")
        serializer = self._checklist_serializer_factory()
        xls_form = serializer.serialize(checklist)
        xls_form.choices = (*xls_form.choices, *org_units.choices)
        return checklist, xls_form


@define
class _ChecklistSaver(Sink[_PDT]):

    _out_dir: str = field(
        alias="out_dir",
        validator=[validators.instance_of(str), validators.min_len(2)],
    )
    _checklist_writer_factory: _CWF = field(
        alias="checklist_writer_factory",
        default=XLSFormWriter.of_file_path,
        repr=False,
        validator=validators.is_callable(),
    )
    _is_disposed: bool = field(default=False, init=False, repr=False)

    @property
    @override
    def is_disposed(self) -> bool:
        return self._is_disposed

    @override
    def dispose(self) -> None:
        self._is_disposed = True

    @not_disposed
    @override
    def drain(self, processed_data: _PDT) -> None:
        ensure_not_none(processed_data, "'processed_data' MUST not be None.")
        for checklist in processed_data:
            file_name: str = checklist[0].name.replace("/", "_")
            out_path: str = f"{self._out_dir}/{file_name}.xlsx"
            with self._checklist_writer_factory(out_path) as writer:
                writer.write(checklist[1])


# =============================================================================
# APP WORKFLOW
# =============================================================================


def app_workflow_factory(
    checklist_metadata_path: str,
    facility_metadata_path: str,
    output_dir: str,
    checklist_loader_factory: _CLF = ChecklistsExcelMetadataLoader.of_file_path,
    facility_loader_factory: _FLF = KMHFLFacilityLoader.of_file_path,
    checklist_serializer_factory: _CSF = ChecklistXLSFormSerializer.of,
    facility_serializer_factory: _FSF = FacilitiesXLSFormSerializer.of,
    checklist_writer_factory: _CWF = XLSFormWriter.of_file_path,
) -> WorkflowDefinition[_RDT, _PDT]:
    return SimpleWorkflowDefinition(  # type: ignore
        id="fyj-mentorship-checklist",
        name="FyJ Mentorship Checklist",
        source_factory=lambda: GatherSource(
            sources=(
                checklist_loader_factory(checklist_metadata_path),
                facility_loader_factory(facility_metadata_path),
            )
        ),
        processor_factory=lambda: _ChecklistProcessor(
            checklist_serializer_factory=checklist_serializer_factory,
            facilities_serializer_factory=facility_serializer_factory,
        ),
        sink_factory=lambda: _ChecklistSaver(
            out_dir=output_dir,
            checklist_writer_factory=checklist_writer_factory,
        ),
    )


# =============================================================================
# MODULE EXPORTS
# =============================================================================


__all__ = ("app_workflow_factory",)
