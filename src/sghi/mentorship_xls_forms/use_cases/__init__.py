from collections.abc import Callable, Iterable

from attrs import field, frozen

from sghi.mentorship_xls_forms.core import Loader, Serializer, Writer
from sghi.mentorship_xls_forms.core import MentorshipChecklist as Checklist
from sghi.mentorship_xls_forms.lib.loaders import ExcelChecklistsMetadataLoader
from sghi.mentorship_xls_forms.lib.serializers.xls_form import (
    ChecklistXLSFormSerializer,
)
from sghi.mentorship_xls_forms.lib.writers import XLSFormWriter
from sghi.mentorship_xls_forms.lib.xls_forms import XLSForm
from sghi.tasks import Pipe, Task
from sghi.utils import ensure_not_none, ensure_not_none_nor_empty

# =============================================================================
# TYPES
# =============================================================================

_CLF = Callable[[str], Loader[Iterable[Checklist]]]

_CSF = Callable[[], Serializer[Checklist, XLSForm]]

_CWF = Callable[[str], Writer[XLSForm]]


# =============================================================================
# MAIN PIPELINE TASKS
# =============================================================================


@frozen
class LoadMetadata(Task[str, Iterable[Checklist]]):

    checklist_loader_factory: _CLF = field(
        default=ExcelChecklistsMetadataLoader.of_file_path
    )

    def execute(self, an_input: str) -> Iterable[Checklist]:
        ensure_not_none_nor_empty(
            an_input, "'an_input' MUST not be None or empty."
        )
        with self.checklist_loader_factory(an_input) as loader:
            return loader.load()


@frozen
class ProcessChecklist(
    Task[Iterable[Checklist], Iterable[tuple[Checklist, XLSForm]]]
):

    checklist_serializer_factory: _CSF = field(
        default=ChecklistXLSFormSerializer.of
    )

    def execute(
        self, an_input: Iterable[Checklist]
    ) -> Iterable[tuple[Checklist, XLSForm]]:
        ensure_not_none(an_input, "'an_input' MUST not be None.")
        return tuple(
            self._checklist_to_form(checklist)
            for checklist in an_input
        )

    def _checklist_to_form(
        self, checklist: Checklist
    ) -> tuple[Checklist, XLSForm]:
        ensure_not_none(checklist, "'checklist' MUST not be None.")
        serializer = self.checklist_serializer_factory()
        return checklist, serializer.serialize(checklist)


@frozen
class WriteResult(Task[Iterable[tuple[Checklist, XLSForm]], None]):

    checklist_writer_factor: _CWF = field(default=XLSFormWriter.of_file_path)

    def execute(self, an_input: Iterable[tuple[Checklist, XLSForm]]) -> None:
        ensure_not_none(an_input, "'an_input' MUST not be None.")
        for checklist in an_input:
            out_path: str = f"out/{checklist[0].name}.xlsx"
            with self.checklist_writer_factor(out_path) as writer:
                writer.write(checklist[1])

# =============================================================================
# MAIN PIPELINE TASKS
# =============================================================================


def main_pipeline_factory() -> Pipe[str, None]:
    return Pipe(
        LoadMetadata(),
        ProcessChecklist(),
        WriteResult(),
    )


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = (
    "main_pipeline_factory",
)
