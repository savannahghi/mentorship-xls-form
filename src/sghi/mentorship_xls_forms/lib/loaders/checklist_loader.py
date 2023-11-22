from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterable
from itertools import zip_longest
from typing import TYPE_CHECKING, Final, Literal, Self, TypedDict

import pyexcel
from attrs import define, field

from sghi.disposable import not_disposed
from sghi.mentorship_xls_forms.core import (
    AnswerType,
    Loader,
    LoadError,
    MentorshipChecklist,
    Question,
    QuestionType,
    Section,
)
from sghi.utils import ensure_not_none

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from pyexcel.internal.generators import (
        BookStream as ExcelWorkbook,
    )
    from pyexcel.internal.generators import (
        SheetStream as ExcelWorksheet,
    )


# =============================================================================
# TYPES
# =============================================================================


_MetadataBool = Literal["Y", "N"]

_ChecklistMapping = TypedDict(
    "_ChecklistMapping",
    {"Checklist ID": str, "Checklist Name": str},
)

_QuestionMapping = TypedDict(
    "_QuestionMapping",
    {
        "Section ID": str,
        "Question ID": str,
        "Question Label": str,
        "Question Prompt": str,
        "Question Type": QuestionType,
        "Answer Type": AnswerType,
        "Select One Options": str,
        "Scoring Logic": str,
        "NA Option?": _MetadataBool,
    },
)

_SectionMapping = TypedDict(
    "_SectionMapping",
    {
        "Checklist ID": str,
        "Section ID": str,
        "Section Title": str,
        "Standard": str,
        "Instructions": str,
        "NA Option?": _MetadataBool,
        "Required?": _MetadataBool,
    },
)

_QuestionPredicate = Callable[[Question], bool]

_SectionPredicate = Callable[[Section], bool]


# =============================================================================
# CONSTANTS
# =============================================================================

_PARENT_QUESTION_TYPES: Final[tuple[QuestionType, ...]] = (
    QuestionType.BOOL,
    QuestionType.COUNT,
    QuestionType.MULTI,
    QuestionType.PERC,
    QuestionType.RATE,
    QuestionType.SELECT,
    QuestionType.TEXT,
)

CHECKLISTS_SHEET_NAME: Final[str] = "Mentorship Checklists"

DEFAULT_FILL_VALUE: Final[str] = ""

NA_VALUE = "N/A"

QUESTIONS_SHEET_NAME: Final[str] = "Questions"

SECTIONS_SHEET_NAME: Final[str] = "Sections"


# =============================================================================
# HELPERS
# =============================================================================


def _ensure_valid_metadata(check: bool, message: str | None = None) -> None:
    """Perform a check to ensure the validity of metadata.

    If the check fails, raise an :exp:`InvalidMetadataError` exception.

    :param check: A boolean or predicate expression indicating the validity of
        metadata. Must evaluate to either ``True`` or ``False``.
    :param message: An optional error message to use in the resulting exception
        if the check evaluates to ``False``.

    :return: None.

    :raises InvalidMetadataError: If the ``check`` parameter evaluates to
        ``False``.
    """
    if not check:
        raise InvalidMetadataError(message=message or "Invalid Metadata")


def _iget_records(sheet: ExcelWorksheet) -> Generator[OrderedDict, None, None]:
    """Stream records from an Excel Sheet.

    :param sheet: The source Excel Sheet.

    :return: A Generator.
    """
    try:
        headers: Sequence[str] = next(sheet.payload)
        for row in sheet.payload:
            yield OrderedDict(
                zip_longest(headers, row, fillvalue=DEFAULT_FILL_VALUE),
            )
    except StopIteration:
        return


# =============================================================================
# EXCEPTIONS
# =============================================================================


class InvalidMetadataError(LoadError):
    """
    Indicate that erroneous metadata was encountered while loading it from a
    source.
    """


# =============================================================================
# LOADER
# =============================================================================


@define
class ChecklistsExcelMetadataLoader(Loader[Iterable[MentorshipChecklist]]):
    _metadata_source: Final[ExcelWorkbook] = field(
        eq=False,
        hash=False,
        repr=False,
    )
    _is_disposed: bool = field(
        eq=False,
        default=False,
        hash=False,
        init=False,
        repr=False,
    )
    _questions: Sequence[Question] = field(
        eq=False,
        factory=tuple,
        hash=False,
        init=False,
        repr=False,
    )
    _sections: Sequence[Section] = field(
        eq=False,
        factory=tuple,
        hash=False,
        init=False,
        repr=False,
    )
    _checklists: Sequence[MentorshipChecklist] = field(
        eq=False,
        factory=tuple,
        hash=False,
        init=False,
        repr=False,
    )

    @property
    def is_disposed(self) -> bool:
        return self._is_disposed

    def dispose(self) -> None:
        self._is_disposed = True
        pyexcel.free_resources()

    @not_disposed()
    def load(self) -> Iterable[MentorshipChecklist]:
        checklists_meta: ExcelWorksheet
        checklists_meta = self._metadata_source.sheets[CHECKLISTS_SHEET_NAME]
        questions_meta: ExcelWorksheet
        questions_meta = self._metadata_source.sheets[QUESTIONS_SHEET_NAME]
        sections_meta: ExcelWorksheet
        sections_meta = self._metadata_source.sheets[SECTIONS_SHEET_NAME]
        self._questions = tuple(
            map(
                self._question_mapping_to_object,
                _iget_records(questions_meta),  # type: ignore
            ),
        )
        self._link_questions()
        self._sections = tuple(
            map(
                self._section_mapping_to_object,
                _iget_records(sections_meta),  # type: ignore
            ),
        )
        self._link_sections()
        self._checklists = tuple(
            map(
                self._checklist_mapping_to_object,
                _iget_records(checklists_meta),  # type: ignore
            ),
        )
        self._link_checklists()
        return self._checklists

    @classmethod
    def of(cls, metadata_source: ExcelWorkbook) -> Self:
        ensure_not_none(metadata_source, "'metadata_source' MUST not be None.")
        return cls(metadata_source=metadata_source)  # pyright: ignore

    @classmethod
    def of_file_path(cls, metadata_file_path: str) -> Self:
        ensure_not_none(
            metadata_file_path,
            "'metadata_file_path' MUST bot be None.",
        )
        return cls.of(pyexcel.iget_book(file_name=metadata_file_path))

    # -------------------------------------------------------------------------
    # LINKERS
    # -------------------------------------------------------------------------
    def _link_checklists(self) -> None:
        for checklist in self._checklists:
            sub_sections: Mapping[str, Section]
            sub_sections = {
                _sec.id: _sec
                # fmt: off
                for _sec in self._select_sections(
                    lambda _s: _s.id.startswith(f"{checklist.id}_"),  # noqa: B023
                    sections=self._sections,
                )
                # fmt: on
            }
            _ensure_valid_metadata(
                len(sub_sections) > 0,
                "Checklists must have at least one section. Checklist "
                f"'{checklist.id}' has no sections.",
            )
            checklist.sections = sub_sections

    def _link_questions(self) -> None:
        for question in self._questions:
            match question.question_type:
                case QuestionType.PERC:
                    sub_questions: Mapping[str, Question]
                    sub_questions = {
                        _sq.id: _sq
                        # fmt: off
                        for _sq in self._select_questions(
                            lambda _q: _q.id.startswith(f"{question.id}_"),  # noqa: B023
                            questions=self._questions,
                        )
                        # fmt: on
                    }
                    num_of_questions: int = len(sub_questions)
                    _ensure_valid_metadata(
                        num_of_questions == 2,
                        "PERC questions MUST have exactly 2 sub-questions, "
                        "a numerator(NUM) and denominator(DEN). Question "
                        f"'{question.id}' has {num_of_questions} "
                        f"sub-questions.",
                    )
                    question.sub_questions = sub_questions
                case QuestionType.MULTI:
                    sub_questions: Mapping[str, Question]
                    sub_questions = {
                        _sq.id: _sq
                        # fmt: off
                        for _sq in self._select_questions(
                            lambda _q: _q.id.startswith(f"{question.id}_"),  # noqa: B023
                            questions=self._questions,
                        )
                        # fmt: on
                    }
                    _ensure_valid_metadata(
                        len(sub_questions) > 0,
                        "MULTI questions MUST have at least one sub-question. "
                        f"Question '{question.id}' has no sub questions.",
                    )
                    question.sub_questions = sub_questions

    def _link_sections(self) -> None:
        for section in self._sections:
            sub_questions: Mapping[str, Question]
            sub_questions = {
                _sq.id: _sq
                for _sq in self._select_questions(
                    lambda _q: (
                        _q.id.startswith(f"{section.id}_")  # noqa: B023
                        and _q.question_type in _PARENT_QUESTION_TYPES
                    ),
                    questions=self._questions,
                )
            }
            _ensure_valid_metadata(
                len(sub_questions) > 0,
                "Sections MUST have at least one sub-questions. Section "
                f"'{section.id}' has no sub questions.",
            )
            section.questions = sub_questions

    # -------------------------------------------------------------------------
    # SELECTORS
    # -------------------------------------------------------------------------
    @staticmethod
    def _select_questions(
        question_predicate: _QuestionPredicate,
        questions: Iterable[Question],
    ) -> Iterable[Question]:
        ensure_not_none(question_predicate)
        ensure_not_none(questions)
        return filter(question_predicate, questions)

    @staticmethod
    def _select_sections(
        section_predicate: _SectionPredicate,
        sections: Iterable[Section],
    ) -> Iterable[Section]:
        ensure_not_none(section_predicate)
        ensure_not_none(sections)
        return filter(section_predicate, sections)

    # -------------------------------------------------------------------------
    # METADATA VALUE TO PYTHON VALUE TRANSLATORS
    # -------------------------------------------------------------------------
    @staticmethod
    def _metadata_bool_to_python(value: _MetadataBool) -> bool:
        ensure_not_none(value)
        return value == "Y"

    @staticmethod
    def _metadata_na_to_python(value: str) -> str | None:
        ensure_not_none(value)
        match value:
            case "" | "N/A":
                return None
            case _:
                return value

    @staticmethod
    def _select_one_options_as_set(
        select_one_options: str,
    ) -> AbstractSet[str] | None:
        ensure_not_none(select_one_options)
        eml = ChecklistsExcelMetadataLoader
        options: str | None = eml._metadata_na_to_python(select_one_options)
        return None if options is None else set(options.split(";"))

    # -------------------------------------------------------------------------
    # MAPPING TO OBJECT TRANSFORMERS
    # -------------------------------------------------------------------------
    @staticmethod
    def _checklist_mapping_to_object(
        checklist_mapping: _ChecklistMapping,
    ) -> MentorshipChecklist:
        ensure_not_none(checklist_mapping)
        return MentorshipChecklist(
            id=checklist_mapping["Checklist ID"].strip(),
            name=checklist_mapping["Checklist Name"].strip(),
        )

    @staticmethod
    def _question_mapping_to_object(
        question_mapping: _QuestionMapping,
    ) -> Question:
        ensure_not_none(question_mapping)
        eml = ChecklistsExcelMetadataLoader
        return Question(
            id=question_mapping["Question ID"].strip(),
            label=question_mapping["Question Label"].strip(),
            question_type=question_mapping["Question Type"],
            answer_type=question_mapping["Answer Type"],
            options_set=eml._select_one_options_as_set(
                question_mapping["Select One Options"].strip(),
            ),
            prompt=eml._metadata_na_to_python(
                question_mapping["Question Prompt"].strip(),
            ),
            scoring_logic=eml._metadata_na_to_python(
                question_mapping["Scoring Logic"].strip(),
            ),
            na_option=eml._metadata_bool_to_python(
                question_mapping["NA Option?"],
            ),
        )

    @staticmethod
    def _section_mapping_to_object(
        section_mapping: _SectionMapping,
    ) -> Section:
        ensure_not_none(section_mapping)
        eml = ChecklistsExcelMetadataLoader
        return Section(
            id=section_mapping["Section ID"].strip(),
            title=section_mapping["Section Title"].strip(),
            standard=eml._metadata_na_to_python(
                section_mapping["Standard"].strip(),
            ),
            instructions=eml._metadata_na_to_python(
                section_mapping["Instructions"].strip(),
            ),
            na_option=eml._metadata_bool_to_python(
                section_mapping["NA Option?"],
            ),
            required=eml._metadata_bool_to_python(
                section_mapping["Required?"],
            ),
        )
