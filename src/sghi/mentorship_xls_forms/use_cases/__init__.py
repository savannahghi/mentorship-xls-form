from collections.abc import Callable, Iterable

from attrs import field, frozen

from sghi.mentorship_xls_forms.core import Facility, Loader, Serializer, Writer
from sghi.mentorship_xls_forms.core import MentorshipChecklist as Checklist
from sghi.mentorship_xls_forms.lib.loaders import (
    ChecklistsExcelMetadataLoader,
    FacilityJSONMetadataLoader,
)
from sghi.mentorship_xls_forms.lib.serializers.xls_form import (
    ChecklistXLSFormSerializer,
    FacilitiesXLSFormSerializer,
)
from sghi.mentorship_xls_forms.lib.writers import XLSFormWriter
from sghi.mentorship_xls_forms.lib.xls_forms import XLSForm, XLSFormItem
from sghi.task import Pipe, Task
from sghi.utils import ensure_not_none, ensure_not_none_nor_empty

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


# =============================================================================
# MAIN PIPELINE TASKS
# =============================================================================


@frozen
class LoadMetadata(
    Task[tuple[str, str], tuple[Iterable[Checklist], Iterable[Facility]]],
):
    checklist_loader_factory: _CLF = field(
        default=ChecklistsExcelMetadataLoader.of_file_path,
    )
    facility_loader_factory: _FLF = field(
        default=FacilityJSONMetadataLoader.of_file_path,
    )

    def execute(
        self,
        an_input: tuple[str, str],
    ) -> tuple[Iterable[Checklist], Iterable[Facility]]:
        ensure_not_none_nor_empty(
            an_input,
            "'an_input' MUST not be None or empty.",
        )
        checklist_loader = self.checklist_loader_factory(an_input[0])
        facility_loader = self.facility_loader_factory(an_input[1])
        with checklist_loader, facility_loader:
            return checklist_loader.load(), facility_loader.load()


@frozen
class ProcessChecklist(
    Task[
        tuple[Iterable[Checklist], Iterable[Facility]],
        Iterable[tuple[Checklist, XLSForm]],
    ],
):
    checklist_serializer_factory: _CSF = field(
        default=ChecklistXLSFormSerializer.of,
    )
    facilities_serializer_factory: _FSF = field(
        default=FacilitiesXLSFormSerializer.of,
    )

    def execute(
        self,
        an_input: tuple[Iterable[Checklist], Iterable[Facility]],
    ) -> Iterable[tuple[Checklist, XLSForm]]:
        ensure_not_none(an_input, "'an_input' MUST not be None.")
        org_units: XLSFormItem
        org_units = self.facilities_serializer_factory().serialize(an_input[1])
        return tuple(
            self._checklist_to_form(checklist, org_units)
            for checklist in an_input[0]
        )

    def _checklist_to_form(
        self,
        checklist: Checklist,
        org_units: XLSFormItem,
    ) -> tuple[Checklist, XLSForm]:
        ensure_not_none(checklist, "'checklist' MUST not be None.")
        serializer = self.checklist_serializer_factory()
        xls_form = serializer.serialize(checklist)
        xls_form.choices = (*xls_form.choices, *org_units.choices)
        return checklist, xls_form


@frozen
class WriteResult(Task[Iterable[tuple[Checklist, XLSForm]], None]):
    checklist_writer_factor: _CWF = field(default=XLSFormWriter.of_file_path)

    def execute(self, an_input: Iterable[tuple[Checklist, XLSForm]]) -> None:
        ensure_not_none(an_input, "'an_input' MUST not be None.")
        for checklist in an_input:
            file_name: str = checklist[0].name.replace("/", "_")
            out_path: str = f"out/{file_name}.xlsx"
            with self.checklist_writer_factor(out_path) as writer:
                writer.write(checklist[1])


# =============================================================================
# MAIN PIPELINE TASKS
# =============================================================================


def main_pipeline_factory() -> Pipe[tuple[str, str], None]:
    return Pipe(
        LoadMetadata(),
        ProcessChecklist(),
        WriteResult(),
    )


# =============================================================================
# MODULE EXPORTS
# =============================================================================


__all__ = ("main_pipeline_factory",)
