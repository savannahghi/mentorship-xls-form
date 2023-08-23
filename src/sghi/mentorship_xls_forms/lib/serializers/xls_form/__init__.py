from __future__ import annotations

from collections.abc import Iterable
from functools import cache
from typing import TYPE_CHECKING, Final, Self

from attrs import frozen

from sghi.mentorship_xls_forms.core import (
    Facility,
    MentorshipChecklist,
    Question,
    Section,
    Serializer,
)
from sghi.mentorship_xls_forms.lib.xls_forms import (
    XLSForm,
    XLSFormChoice,
    XLSFormItem,
    XLSFormRecord,
    XLSFormSettings,
)
from sghi.utils import ensure_not_none

if TYPE_CHECKING:
    from collections.abc import Sequence

# =============================================================================
# CONSTANTS
# =============================================================================


_CEE_SCORE_CHOICE_LIST_NAME: Final[str] = "cee_score"

_YES_NO_CHOICE_LIST_NAME: Final[str] = "yes_no"

_COVER_SHEET_RECORDS: Final[Sequence[XLSFormRecord]] = (
    XLSFormRecord.begin_field_list(
        label="SITE AND ASSESSORS DETAILS",
        name="MCL.ASSESSMENT_DETAILS",
    ),
    XLSFormRecord(
        type="text",
        label="Name:",
        name="MCL.CS_ASSR_NAME",
        required="yes",
    ),
    XLSFormRecord(
        type="select_one counties",  # type: ignore
        appearance="minimal",
        label="County:",
        name="MCL.CS_ASMT_COUNTY",
        required="yes",
    ),
    XLSFormRecord(
        type="select_one sub_counties",  # type: ignore
        appearance="minimal,autocomplete",
        choice_filter="county=${MCL.CS_ASMT_COUNTY}",
        label="Sub County:",
        name="MCL.CS_ASMT_SUB_COUNTY",
        required="yes",
    ),
    XLSFormRecord(
        type="select_one facilities",  # type: ignore
        appearance="minimal,autocomplete",
        choice_filter="sub_county=${MCL.CS_ASMT_SUB_COUNTY}",
        label="Facility:",
        name="MCL.CS_ASMT_FACILITY",
        required="yes"
    ),
    XLSFormRecord.of_note(
        calculation="${MCL.CS_ASMT_FACILITY}",
        label="Selected Facility MFL-code:",
        name="MCL.CS_ASMT_FACILITY_MFL",
    ),
    XLSFormRecord(
        type="date",
        calculation="today()",
        label="Assessment Date:",
        name="MCL.CS_ASMT_DATE",
        required="yes",
    ),
    XLSFormRecord(
        type="time",
        calculation="now()",
        label="Assessment Start Time:",
        name="MCL.CS_ASMT_START_TIME",
    ),
    XLSFormRecord(
        type="geopoint",
        label="Location:",
        name="MCL.CS_ASMT_LOCATION",
    ),
    XLSFormRecord.end_group(),
)

_DEFAULT_CHOICES: Final[Sequence[XLSFormChoice]] = (
    XLSFormChoice(
        label='<span style="color:gray">Gray</span>',
        list_name=_CEE_SCORE_CHOICE_LIST_NAME,
        name="gray",
    ),
    XLSFormChoice(
        label='<span style="color:green">Green</span>',
        list_name=_CEE_SCORE_CHOICE_LIST_NAME,
        name="green",
    ),
    XLSFormChoice(
        label='<span style="color:red">Red</span>',
        list_name=_CEE_SCORE_CHOICE_LIST_NAME,
        name="red",
    ),
    XLSFormChoice(
        label='<span style="color:yellow">Yellow</span>',
        list_name=_CEE_SCORE_CHOICE_LIST_NAME,
        name="yellow",
    ),
    XLSFormChoice(
        label="Yes",
        list_name=_YES_NO_CHOICE_LIST_NAME,
        name="yes",
    ),
    XLSFormChoice(
        label="No",
        list_name=_YES_NO_CHOICE_LIST_NAME,
        name="no",
    ),
)

_PERC_SUB_QUESTIONS_TYPES: Final[frozenset[str]] = frozenset({"DEN", "NUM"})

# =============================================================================
# HELPERS
# =============================================================================


def build_select_option_name(question_id: str, option_index: int) -> str:
    ensure_not_none(question_id, "'question_id' MUST not be None.")
    ensure_not_none(option_index, "'option_index' MUST not be none.")
    return f"{question_id}_{option_index}"


def escape_markdown(text: str) -> str:
    ensure_not_none(text, "'text' MUST not be None.")
    return text.replace("_", "\\_").replace("*", "\\*").replace("#", "\\#")


def org_unit_name_as_list_name(org_unit_name: str) -> str:
    ensure_not_none(org_unit_name, "'org_unit_name' MUST not be None.")
    return org_unit_name.replace(" ", "_").lower()


# =============================================================================
# SERIALIZERS
# =============================================================================


@frozen
class ChecklistXLSFormSerializer(Serializer[MentorshipChecklist, XLSForm]):

    def serialize(self, item: MentorshipChecklist) -> XLSForm:
        ensure_not_none(item, "'item' MUST be a not None MentorshipChecklist.")
        assert item.sections, (
            f"checklist MUST have sections. {item.id} has no sections."
        )
        choices: list[XLSFormChoice] = [*_DEFAULT_CHOICES]
        records: list[XLSFormRecord] = [*_COVER_SHEET_RECORDS]
        settings: XLSFormSettings = XLSFormSettings(
            form_id=item.id,
            form_title=escape_markdown(item.name)
        )

        for section in item.sections.values():
            section_items: XLSFormItem
            section_items = SectionXLSFormSerializer.of().serialize(section)
            choices.extend(section_items.choices)
            records.extend(section_items.records)

        return XLSForm(survey=records, choices=choices, settings=settings)

    @classmethod
    @cache
    def of(cls) -> Self:
        """Return an instance of :class:`ChecklistXLSFormSerializer`.

        .. note::

            The returned instance is not guaranteed to be a newly created
            instance on each invocation. If a new instance is required, prefer
            :meth:`ChecklistXLSFormSerializer.of_new`.

        :return: An instance of ``ChecklistXLSFormSerializer``.

        .. seealso:: :py:meth:`ChecklistXLSFormSerializer.of_new`
        """
        return cls.of_new()

    @classmethod
    def of_new(cls) -> Self:
        """
        Create and return a new instance of :class:`ChecklistXLSFormSerializer`.

        :return: A new instance of ``ChecklistXLSFormSerializer``.

        .. seealso:: :py:meth:`ChecklistXLSFormSerializer.of`
        """
        return cls()


@frozen
class FacilitiesXLSFormSerializer(Serializer[Iterable[Facility], XLSFormItem]):

    def serialize(self, item: Iterable[Facility]) -> XLSFormItem:
        ensure_not_none(
            item, "'item' MUST be a not None Iterable of Facilities."
        )
        choices: list[XLSFormChoice] = []
        records: list[XLSFormRecord] = []

        counties_cache: set[str] = set()
        sub_counties_cache: set[tuple[str, str]] = set()
        wards_cache: set[tuple[str, str, str]] = set()
        for facility in sorted(item, key=lambda _f: _f.name):
            f_items = FacilityXLSFormSerializer.of().serialize(facility)
            choices.extend(f_items.choices)
            records.extend(f_items.records)

            # Cache org unit hierarchy
            counties_cache.add(facility.county)
            sub_counties_cache.add((facility.sub_county, facility.county))
            wards_cache.add(
                (facility.ward, facility.sub_county, facility.county)
            )

        # Create org unit hierarchy by prepending upper level org units to the
        # beginning of the `choices` collection
        choices[:0] = self._wards_to_xls_forms(wards_cache)
        choices[:0] = self._sub_counties_to_xls_choice(sub_counties_cache)
        choices[:0] = self._counties_to_xls_choice(counties_cache)

        return XLSFormItem(records=records, choices=choices)

    @classmethod
    @cache
    def of(cls) -> Self:
        """Return an instance of :class:`FacilitiesXLSFormSerializer`.

        .. note::

            The returned instance is not guaranteed to be a newly created
            instance on each invocation. If a new instance is required, prefer
            :meth:`FacilitiesXLSFormSerializer.of_new`.

        :return: An instance of ``FacilitiesXLSFormSerializer``.

        .. seealso:: :py:meth:`FacilitiesXLSFormSerializer.of_new`
        """
        return cls.of_new()

    @classmethod
    def of_new(cls) -> Self:
        """
        Create and return a new instance of
        :class:`FacilitiesXLSFormSerializer`.

        :return: A new instance of ``FacilitiesXLSFormSerializer``.

        .. seealso:: :py:meth:`FacilitiesXLSFormSerializer.of`
        """
        return cls()

    @staticmethod
    def _counties_to_xls_choice(
        org_units: Iterable[str]
    ) -> Iterable[XLSFormChoice]:
        ensure_not_none(org_units, "'org_units' MUST not be None.")
        return tuple(
            XLSFormChoice(
                label=escape_markdown(county),
                list_name="counties",
                name=org_unit_name_as_list_name(county),
            )
            for county in sorted(org_units)
        )

    @staticmethod
    def _sub_counties_to_xls_choice(
        org_units: Iterable[tuple[str, str]]
    ) -> Iterable[XLSFormChoice]:
        ensure_not_none(org_units, "'org_units' MUST not be None.")
        return tuple(
            XLSFormChoice(
                label=escape_markdown(sub_county),
                list_name="sub_counties",
                name=org_unit_name_as_list_name(sub_county),
                county=org_unit_name_as_list_name(county),
            )
            for sub_county, county in sorted(org_units, key=lambda _s: _s[0])
        )

    @staticmethod
    def _wards_to_xls_forms(
        org_units: Iterable[tuple[str, str, str]]
    ) -> Iterable[XLSFormChoice]:
        ensure_not_none(org_units, "'org_units' MUST not be None.")
        return tuple(
            XLSFormChoice(
                label=escape_markdown(ward),
                list_name="wards",
                name=org_unit_name_as_list_name(ward),
                county=org_unit_name_as_list_name(county),
                sub_county=org_unit_name_as_list_name(sub_county),
            )
            for ward, sub_county, county in sorted(
                org_units, key=lambda _s: _s[0]
            )
        )


@frozen
class FacilityXLSFormSerializer(Serializer[Facility, XLSFormItem]):

    def serialize(self, item: Facility) -> XLSFormItem:
        ensure_not_none(item, "'item' MUST be a not None Facility.")
        facility_as_choice = XLSFormChoice(
            label=escape_markdown(item.name),
            list_name="facilities",
            name=item.mfl_code,
            county=org_unit_name_as_list_name(item.county),
            sub_county=org_unit_name_as_list_name(item.sub_county),
            ward=org_unit_name_as_list_name(item.ward),
        )
        return XLSFormItem(records=(), choices=(facility_as_choice,))

    @classmethod
    @cache
    def of(cls) -> Self:
        """Return an instance of :class:`FacilityXLSFormSerializer`.

        .. note::

            The returned instance is not guaranteed to be a newly created
            instance on each invocation. If a new instance is required, prefer
            :meth:`FacilityXLSFormSerializer.of_new`.

        :return: An instance of ``FacilityXLSFormSerializer``.

        .. seealso:: :py:meth:`FacilityXLSFormSerializer.of_new`
        """
        return cls.of_new()

    @classmethod
    def of_new(cls) -> Self:
        """
        Create and return a new instance of :class:`FacilityXLSFormSerializer`.

        :return: A new instance of ``FacilityXLSFormSerializer``.

        .. seealso:: :py:meth:`FacilityXLSFormSerializer.of`
        """
        return cls()


@frozen
class QuestionXLSFormSerializer(Serializer[Question, XLSFormItem]):

    def serialize(self, item: Question) -> XLSFormItem:
        ensure_not_none(item, "'item' MUST be a not None Question.")

        match item.question_type:
            case "BOOL":
                return self._serialize_bool_question(question=item)
            case "COUNT":
                return self._serialize_count_question(question=item)
            case "MULTI":
                return self._serialize_multi_question(question=item)
            case "PERC":
                return self._serialize_perc_question(question=item)
            case "SELECT":
                return self._serialize_select_question(question=item)
            # OTHER/GENERIC QUESTION TYPES
            # 1. Generic question type with sub-questions.
            case _ if item.sub_questions:
                return self._serialize_generic_compound_question(question=item)

            # 2. Generic question type with no sub-question
        return self._serialize_generic_simple_question(question=item)

    @classmethod
    @cache
    def of(cls) -> Self:
        """Return an instance of :class:`QuestionXLSFormSerializer`.

        .. note::

            The returned instance is not guaranteed to be a newly created
            instance on each invocation. If a new instance is required, prefer
            :meth:`QuestionXLSFormSerializer.of_new`.

        :return: An instance of ``QuestionXLSFormSerializer``.

        .. seealso:: :py:meth:`QuestionXLSFormSerializer.of_new`
        """
        return cls.of_new()

    @classmethod
    def of_new(cls) -> Self:
        """
        Create and return a new instance of :class:`QuestionXLSFormSerializer`.

        :return: A new instance of ``QuestionXLSFormSerializer``.

        .. seealso:: :py:meth:`QuestionXLSFormSerializer.of`
        """
        return cls()

    @staticmethod
    def _serialize_bool_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        record = XLSFormRecord(
            type=f"select_one {_YES_NO_CHOICE_LIST_NAME}",  # type: ignore
            hint=escape_markdown(question.prompt) if question.prompt else None,
            label=escape_markdown(question.label),
            name=question.id,
        )

        return XLSFormItem.of_single_record(record=record)

    @staticmethod
    def _serialize_count_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        record = XLSFormRecord.of_positive_integer(
            hint=escape_markdown(question.prompt) if question.prompt else None,
            label=escape_markdown(question.label),
            name=question.id,
        )

        return XLSFormItem.of_single_record(record=record)

    @staticmethod
    def _serialize_generic_compound_question(question: Question) -> XLSFormItem:  # noqa: E501
        ensure_not_none(question, "'question' MUST not be None.")
        choices: list[XLSFormChoice] = []
        records: list[XLSFormRecord] = []

        # Create a group for the question and then add its
        # sub-questions to the group.
        records.append(
            XLSFormRecord.begin_group(
                label=escape_markdown(question.label),
                name=question.id
            )
        )
        for sub_question in question.sub_questions.values():  # pyright: ignore
            sq_records = QuestionXLSFormSerializer.of().serialize(sub_question)
            choices.extend(sq_records.choices)
            records.extend(sq_records.records)
        # Close the group
        records.append(XLSFormRecord.end_group())
        return XLSFormItem(records=records, choices=choices)

    @staticmethod
    def _serialize_generic_simple_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        record = XLSFormRecord(
            type="text",
            hint=escape_markdown(question.prompt) if question.prompt else None,
            label=question.label,
            name=question.id,
        )

        return XLSFormItem.of_single_record(record=record)

    @staticmethod
    def _serialize_perc_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        # Sanity Checks
        assert question.sub_questions, (
            f"'PERC' question MUST have sub-questions. '{question.id}' has "
            "no sub-questions."
        )
        assert len(question.sub_questions) == 2, (
            "'PERC' question MUST have exactly 2 sub-questions. "
            f"'{question.id}' has {len(question.sub_questions)} sub-questions."
        )
        available_sq_types: frozenset[str]
        available_sq_types = _PERC_SUB_QUESTIONS_TYPES.difference(
            {_q.question_type for _q in question.sub_questions.values()}
        )
        assert not available_sq_types, (
            "'PERC' question MUST have one sub-question of type 'DEN', and "
            "sub-question of type 'NUM'. The following sub-question types "
            f"'{','.join(available_sq_types)}' are missing for question "
            f"'{question.id}'."
        )

        denominator: Question = next(
            filter(
                lambda _q: _q.question_type == "DEN",
                question.sub_questions.values()
            )
        )
        numerator: Question = next(
            filter(
                lambda _q: _q.question_type == "NUM",
                question.sub_questions.values()
            )
        )

        records: tuple[XLSFormRecord, ...] = (
            XLSFormRecord.begin_group(
                appearance="table-list",
                hint=(
                    escape_markdown(question.prompt)
                    if question.prompt else None
                ),
                label=escape_markdown(question.label),
                name=f"{question.id}_PERC_GRP"
            ),
            XLSFormRecord.of_positive_integer(
                label=escape_markdown(numerator.label),
                name=numerator.id,
            ),
            XLSFormRecord.of_positive_integer(
                label=escape_markdown(denominator.label),
                name=denominator.id,
            ),
            XLSFormRecord.end_group(),
        )
        return XLSFormItem.of_records(records=records)

    @staticmethod
    def _serialize_multi_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        assert question.sub_questions, (  # Sanity check
            f"'MULTI' question MUST have sub-questions. '{question.id}' has "
            "no sub-question."
        )
        choices: tuple[XLSFormChoice] = tuple(
            XLSFormChoice(
                label=escape_markdown(sub_question.label),
                list_name=question.id,
                name=sub_question.id,
            )
            for sub_question in question.sub_questions.values()
        )
        records: tuple[XLSFormRecord] = (
            XLSFormRecord(
                type=f"select_multiple {question.id}",  # type: ignore
                hint=(
                    escape_markdown(question.prompt)
                    if question.prompt else None
                ),
                label=escape_markdown(question.label),
                name=question.id,
            ),
        )
        return XLSFormItem(records=records, choices=choices)

    @staticmethod
    def _serialize_select_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        assert question.options_set, (  # Sanity Check
            f"'SELECT' question MUST have options. '{question.id}' has no "
            "options."
        )
        choices: tuple[XLSFormChoice] = tuple(
            XLSFormChoice(
                label=escape_markdown(choice),
                list_name=question.id,
                name=build_select_option_name(question.id, index),
            )
            for index, choice in enumerate(question.options_set, start=1)
        )
        records: tuple[XLSFormRecord] = (
            XLSFormRecord(
                type=f"select_one {question.id}",  # type: ignore
                hint=(
                    escape_markdown(question.prompt)
                    if question.prompt else None
                ),
                label=escape_markdown(question.label),
                name=question.id,
            ),
        )
        return XLSFormItem(records=records, choices=choices)


@frozen
class SectionXLSFormSerializer(Serializer[Section, XLSFormItem]):

    def serialize(self, item: Section) -> XLSFormItem:
        ensure_not_none(item, "'item' MUST be a not None Section.")
        choices: list[XLSFormChoice] = []
        records: list[XLSFormRecord] = [
            XLSFormRecord.begin_field_list(
                name=item.id,
                label=escape_markdown(f"SEC #: {item.id} {item.title}"),
            )
        ]
        if item.standard:
            records.append(
                XLSFormRecord.of_note(
                    label=f"**STANDARD:** {escape_markdown(item.standard)}",
                    name=f"{item.id}_STANDARD",
                )
            )
        if item.instructions:
            _inst: str = escape_markdown(item.instructions)
            records.append(
                XLSFormRecord.of_note(
                    label=f"_**Instructions:** {escape_markdown(_inst)}_",
                    name=f"{item.id}_INSTRUCTION",
                )
            )
        if item.na_option:
            records.append(XLSFormRecord.of_trigger(name=f"{item.id}_NA"))

        # Serialize the question's sub-questions.
        if item.questions:
            for question in item.questions.values():
                q_items = QuestionXLSFormSerializer.of().serialize(question)
                choices.extend(q_items.choices)
                records.extend(q_items.records)

        records.extend((
            # Comment
            XLSFormRecord(
                type="text",
                appearance="multiline",
                label="Comments",
                name=f"{item.id}_COMMENTS",
            ),
            # Section score
            XLSFormRecord(
                type=f"select_one {_CEE_SCORE_CHOICE_LIST_NAME}",  # type: ignore  # noqa: E501
                appearance="minimal",
                calculation="",  # TODO: create expression
                default="red",
                label="Score",
                name=f"{item.id}_SCORE",
                read_only="yes",
            ),
            # End group
            XLSFormRecord.end_group(),
        ))

        return XLSFormItem(records=records, choices=choices)

    @classmethod
    @cache
    def of(cls) -> Self:
        """Return an instance of :class:`SectionXLSFormSerializer`.

        .. note::

            The returned instance is not guaranteed to be a newly created
            instance on each invocation. If a new instance is required, prefer
            :meth:`SectionXLSFormSerializer.of_new`.

        :return: An instance of ``SectionXLSFormSerializer``.

        .. seealso:: :py:meth:`SectionXLSFormSerializer.of_new`
        """
        return cls.of_new()

    @classmethod
    def of_new(cls) -> Self:
        """
        Create and return a new instance of :class:`SectionXLSFormSerializer`.

        :return: A new instance of ``SectionXLSFormSerializer``.

        .. seealso:: :py:meth:`SectionXLSFormSerializer.of`
        """
        return cls()

# =============================================================================
# MODULE EXPORTS
# =============================================================================


__all__ = [
    "ChecklistXLSFormSerializer",
    "FacilitiesXLSFormSerializer",
    "FacilityXLSFormSerializer",
    "QuestionXLSFormSerializer",
    "SectionXLSFormSerializer",
    "XLSForm",
    "XLSFormChoice",
    "XLSFormItem",
    "XLSFormRecord",
    "XLSFormSettings",
]
