from __future__ import annotations

from collections.abc import Iterable
from enum import UNIQUE, Enum, verify
from functools import cache, reduce
from typing import TYPE_CHECKING, Final, Self, assert_never

from attrs import frozen

from sghi.mentorship_xls_forms.core import (
    Facility,
    MentorshipChecklist,
    Question,
    QuestionType,
    Section,
    Serializer,
)
from sghi.mentorship_xls_forms.lib.antlr4 import parse_question_scoring_logic
from sghi.mentorship_xls_forms.lib.xls_forms import (
    XLSForm,
    XLSFormChoice,
    XLSFormItem,
    XLSFormRecord,
    XLSFormSettings,
)
from sghi.mentorship_xls_forms.lib.xls_forms.expressions import (
    FALSE,
    ONE,
    THREE,
    TRUE,
    TWO,
    ZERO,
    BoolExpr,
    Expr,
    NumberExpr,
    TextExpr,
    XPathExpr,
    eval,  # noqa: A004
    if_,
    number,
    str_,
    string,
    var,
)
from sghi.mentorship_xls_forms.lib.xls_forms.expressions import brkt as _
from sghi.utils import ensure_not_none, ensure_predicate

if TYPE_CHECKING:
    from collections.abc import Sequence

# =============================================================================
# CONSTANTS
# =============================================================================


@verify(UNIQUE)
class _CeeScoreCL(Enum):
    """CEE Score Choice List"""

    GRAY = "gray", "Gray", str_("gray")
    GREEN = "green", "Green", str_("green")
    RED = "red", "Red", str_("red")
    YELLOW = "yellow", "Yellow", str_("yellow")

    @property
    def choice_label(self) -> str:
        """The text of this choice to displayed to the user.

        :returns: The text of this choice to display to the user.
        """
        return self.value[1]

    @property
    def choice_name(self) -> str:
        """The unique variable name of this answer/choice.

        :returns: The unique variable name of this answer/choice.
        """
        return self.value[0]

    @property
    def expr(self) -> TextExpr:
        """
        The :class:`XLSForm expression <TextExpr>` equivalent of this choice.

        :returns: The XLSForm expression equivalent of this choice.
        """
        return self.value[2]

    @classmethod
    def list_name(cls) -> str:
        return "cee_score"


@verify(UNIQUE)
class _YesNoCL(Enum):
    """YES/NO Answers Choice List."""

    NO = "no", "No", str_("no")
    YES = "yes", "Yes", str_("yes")

    @property
    def choice_label(self) -> str:
        """The text of this choice to displayed to the user.

        :returns: The text of this choice to display to the user.
        """
        return self.value[1]

    @property
    def choice_name(self) -> str:
        """The unique variable name of this answer/choice.

        :returns: The unique variable name of this answer/choice.
        """
        return self.value[0]

    @property
    def expr(self) -> TextExpr:
        """
        The :class:`XLSForm expression <TextExpr>` equivalent of this choice.

        :returns: The XLSForm expression equivalent of this choice.
        """
        return self.value[2]

    @classmethod
    def list_name(cls) -> str:
        return "yes_no"


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
    XLSFormRecord.of_select_one(
        list_name="counties",
        appearance="minimal",
        label="County:",
        name="MCL.CS_ASMT_COUNTY",
        required="yes",
    ),
    XLSFormRecord.of_select_one(
        list_name="sub_counties",
        appearance="minimal,autocomplete",
        choice_filter="county=${MCL.CS_ASMT_COUNTY}",
        label="Sub County:",
        name="MCL.CS_ASMT_SUB_COUNTY",
        required="yes",
    ),
    XLSFormRecord.of_select_one(
        list_name="facilities",
        appearance="minimal,autocomplete",
        choice_filter="sub_county=${MCL.CS_ASMT_SUB_COUNTY}",
        label="Facility:",
        name="MCL.CS_ASMT_FACILITY",
        required="yes",
    ),
    XLSFormRecord.of_note(
        calculation="${MCL.CS_ASMT_FACILITY}",
        label="Selected Facility MFL-code:",
        name="MCL.CS_ASMT_FACILITY_MFL",
    ),
    XLSFormRecord(
        type="date",
        default="today()",
        label="Assessment Date:",
        name="MCL.CS_ASMT_DATE",
        required="yes",
    ),
    XLSFormRecord(
        type="time",
        default="now()",
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
        label=f'<span style="color:gray">{_CeeScoreCL.GRAY.choice_label}</span>',  # noqa: E501
        list_name=_CeeScoreCL.list_name(),
        name=_CeeScoreCL.GRAY.choice_name,
    ),
    XLSFormChoice(
        label=f'<span style="color:green">{_CeeScoreCL.GREEN.choice_label}</span>',  # noqa: E501
        list_name=_CeeScoreCL.list_name(),
        name=_CeeScoreCL.GREEN.choice_name,
    ),
    XLSFormChoice(
        label=f'<span style="color:red">{_CeeScoreCL.RED.choice_label}</span>',
        list_name=_CeeScoreCL.list_name(),
        name=_CeeScoreCL.RED.choice_name,
    ),
    XLSFormChoice(
        label=f'<span style="color:yellow">{_CeeScoreCL.YELLOW.choice_label}</span>',  # noqa: E501
        list_name=_CeeScoreCL.list_name(),
        name=_CeeScoreCL.YELLOW.choice_name,
    ),
    XLSFormChoice(
        label=_YesNoCL.YES.choice_label,
        list_name=_YesNoCL.list_name(),
        name=_YesNoCL.YES.choice_name,
    ),
    XLSFormChoice(
        label=_YesNoCL.NO.choice_label,
        list_name=_YesNoCL.list_name(),
        name=_YesNoCL.NO.choice_name,
    ),
)


_PERC_SUB_QUESTIONS_TYPES: Final[frozenset[QuestionType]] = frozenset(
    {
        QuestionType.DEN,
        QuestionType.NUM,
    },
)


_RELEVANCE_QUESTION_LABEL: Final[str] = "Is the question below applicable?"


# =============================================================================
# HELPERS
# =============================================================================


def _create_question_int_score_record(question: Question) -> XLSFormRecord:
    ensure_not_none(question, "'question_id' MUST not be None.")

    q_value: TextExpr = string(var(_get_question_score_record_id(question)))
    score_expr: Expr = if_(
        q_value == _CeeScoreCL.GREEN.expr,
        then=THREE,
        else_=if_(
            q_value == _CeeScoreCL.YELLOW.expr,
            then=TWO,
            else_=if_(q_value == _CeeScoreCL.RED.expr, then=ONE, else_=ZERO),
        ),
    )
    return XLSFormRecord(
        type="calculate",
        calculation=eval(score_expr),
        default="0",
        name=_get_question_int_score_record_id(question),
    )


def _create_question_max_score_record(question: Question) -> XLSFormRecord:
    ensure_not_none(question, "'question' MUST not be None.")

    max_score: str
    q_value: TextExpr
    q_value = string(var(_get_question_relevance_record_id(question)))
    match question.scoring_logic:
        case str() if question.na_option:
            max_score = eval(
                if_(q_value == _YesNoCL.YES.expr, then=THREE, else_=ZERO),
            )
        case str():
            max_score = "3"
        case None:
            max_score = "0"
        case _:
            assert_never(question.scoring_logic)

    return XLSFormRecord(
        type="calculate",
        calculation=max_score,
        default="0",
        name=_get_question_max_score_record_id(question),
    )


def _create_question_relevance_record(question: Question) -> XLSFormRecord:
    ensure_not_none(question, "'question' MUST not be None.")

    label: str = _RELEVANCE_QUESTION_LABEL
    if question.display_numbering is not None:
        label = f"{question.display_numbering}. {label}"
    return XLSFormRecord.of_select_one(
        list_name=_YesNoCL.list_name(),
        appearance="columns-pack",
        default=_YesNoCL.YES.choice_name,
        hint=(
            f"Select '{_YesNoCL.NO.choice_label}' to skip to the next "
            "question."
        ),
        label=label,
        name=_get_question_relevance_record_id(question),
        relevant="yes" if question.na_option else "no",
    )


def _create_question_score_record(question: Question) -> XLSFormRecord:
    ensure_not_none(question, "'question' MUST not be None.")

    gray_score: _CeeScoreCL = _CeeScoreCL.GRAY
    score_expr: Expr | None = parse_question_scoring_logic(question, None)
    return XLSFormRecord(
        type="calculate",
        calculation=eval(score_expr) if score_expr else gray_score.choice_name,
        default=gray_score.choice_name,
        name=_get_question_score_record_id(question),
    )


def _get_question_int_score_record_id(question: Question) -> str:
    ensure_not_none(question, "'question' MUST not be None.")
    return f"{question.id}_INT_SCORE"


def _get_question_max_score_record_id(question: Question) -> str:
    ensure_not_none(question, "'question' MUST not be None.")
    return f"{question.id}_MAX_SCORE"


def _get_question_relevance_record_id(question: Question) -> str:
    ensure_not_none(question, "'question' MUST not be None.")
    return f"{question.id}_RELEVANCE"


def _get_question_score_record_id(question: Question) -> str:
    ensure_not_none(question, "'question' MUST not be None.")
    return f"{question.id}_SCORE"


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
        ensure_predicate(
            bool(item.sections),
            f"checklist MUST have sections. {item.id} has no sections.",
        )
        choices: list[XLSFormChoice] = [*_DEFAULT_CHOICES]
        records: list[XLSFormRecord] = [*_COVER_SHEET_RECORDS]
        settings: XLSFormSettings = XLSFormSettings(
            form_id=item.id,
            form_title=escape_markdown(item.name),
        )

        assert item.sections  # Make Pyright happy!
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
        Create and return a new instance of
        :class:`ChecklistXLSFormSerializer`.

        :return: A new instance of ``ChecklistXLSFormSerializer``.

        .. seealso:: :py:meth:`ChecklistXLSFormSerializer.of`
        """
        return cls()


@frozen
class FacilitiesXLSFormSerializer(Serializer[Iterable[Facility], XLSFormItem]):
    def serialize(self, item: Iterable[Facility]) -> XLSFormItem:
        ensure_not_none(
            value=item,
            message="'item' MUST be a not None Iterable of Facilities.",
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
                (facility.ward, facility.sub_county, facility.county),
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
        org_units: Iterable[str],
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
        org_units: Iterable[tuple[str, str]],
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
        org_units: Iterable[tuple[str, str, str]],
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
                org_units,
                key=lambda _s: _s[0],
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
            case QuestionType.BOOL:
                return self._serialize_bool_question(question=item)
            case QuestionType.COUNT:
                return self._serialize_count_question(question=item)
            case QuestionType.MULTI:
                return self._serialize_multi_question(question=item)
            case QuestionType.PERC:
                return self._serialize_perc_question(question=item)
            case QuestionType.RATE:
                return self._serialize_rate_question(question=item)
            case QuestionType.SELECT:
                return self._serialize_select_question(question=item)
            # OTHER/GENERIC QUESTION TYPES
            # 1. Generic question type with sub-questions.
            case _ if item.sub_questions:
                return self._serialize_generic_compound_question(question=item)

            # 2. Generic question type with no sub-question.
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
    def _create_question_label(question: Question) -> str:
        ensure_not_none(question)
        question_label: str = escape_markdown(question.label)
        # Add display numbering when question is always applicable and the
        # display number is present.
        if not question.na_option and question.display_numbering is not None:
            question_label = f"{question.display_numbering}. {question_label}"
        return question_label

    @staticmethod
    def _get_perc_question_calculation(num_id: str, den_id: str) -> XPathExpr:
        ensure_not_none(num_id, "'num_id' MUST not be None.")
        ensure_not_none(den_id, "'den_id' MUST not be None.")

        q_num: NumberExpr = number(var(num_id) ^ ZERO)
        q_den: NumberExpr = number(var(den_id) ^ ONE)
        percentage: NumberExpr = round(_(q_num / q_den) * 100, 2)

        return eval(percentage)

    @staticmethod
    def _get_question_relevance_calculation(question: Question) -> XPathExpr:
        ensure_not_none(question)

        # THIS IS A HACK TO ENSURE APPLICABLE QUESTIONS ARE SHOWN ON COLLECT!!!
        # ---------------------------------------------------------------------
        #
        # Ideally, this should be a simple boolean expression, i.e.:
        #
        #      string(var(_get_question_relevance_record_id(question))) == _YesNoCL.YES.expr  # noqa: ERA001, E501
        #
        # Unfortunately, on Collect(both ODK and Kobo), this doesn't work.
        # This is because, in Collect, all values and expressions for
        # non-relevant questions are treated as blank. Here are more details
        # regarding this issue:
        # https://forum.getodk.org/t/enketo-uses-non-relevant-values-in-calculations-whereas-collect-does-not/35567
        # Specifically, see this comment:
        # https://forum.getodk.org/t/enketo-uses-non-relevant-values-in-calculations-whereas-collect-does-not/35567/9#
        # This is a Collect-only issue and does not occur in Enketo.
        #
        # To understand how this affects this tool, you need to know the
        # following:
        #
        # 1. Each "primary" question has an associated "relevance" question.
        # 2. Each "relevance" question accepts a yes/no answer(default "yes")
        #    that determines whether its associated primary question should be
        #    displayed. When the answer is yes, the associated primary question
        #    will be shown.
        # 3. Each applicable question has its associated relevance question
        #    hidden (relevant set to false) since we know its answer will
        #    always be yes.
        #
        # Taking all the above into account, when a simple boolean expression,
        # as shown above, is used, the result is that all applicable questions
        # are not shown in Collect. To fix this, we apply a short-circuiting if
        # expression that avoids reading the value of the "relevance" question
        # for applicable questions by always evaluating to true. This is
        # possible because all applicable questions are known beforehand at
        # form generation time.
        #
        # Another solution might be to remove "relevance" questions for
        # applicable questions. However, this might have the downside of
        # littering the code with dozens of "if, else" statements and
        # complicating the scoring calculations. In the future, this approach
        # may be considered. However, as of now, it's not clear whether this
        # is a good idea.
        short_circuit_value: BoolExpr = FALSE if question.na_option else TRUE
        relevant_expr: Expr = if_(
            short_circuit_value,
            then=TRUE,
            else_=(
                string(var(_get_question_relevance_record_id(question)))
                == _YesNoCL.YES.expr
            ),
        )
        return eval(relevant_expr)

    @staticmethod
    def _serialize_bool_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        self = QuestionXLSFormSerializer
        records: tuple[XLSFormRecord, ...] = (
            _create_question_relevance_record(question),
            XLSFormRecord.of_select_one(
                list_name=_YesNoCL.list_name(),
                appearance="columns-pack",
                hint=(
                    escape_markdown(question.prompt)
                    if question.prompt
                    else None
                ),
                label=self._create_question_label(question),
                name=question.id,
                relevant=self._get_question_relevance_calculation(question),
            ),
            _create_question_score_record(question),
            _create_question_int_score_record(question),
            _create_question_max_score_record(question),
        )

        return XLSFormItem.of_records(records=records)

    @staticmethod
    def _serialize_count_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        self = QuestionXLSFormSerializer
        records: tuple[XLSFormRecord, ...] = (
            _create_question_relevance_record(question),
            XLSFormRecord.of_positive_integer(
                hint=(
                    escape_markdown(question.prompt)
                    if question.prompt
                    else None
                ),
                label=self._create_question_label(question),
                name=question.id,
                relevant=self._get_question_relevance_calculation(question),
            ),
            _create_question_score_record(question),
            _create_question_int_score_record(question),
            _create_question_max_score_record(question),
        )

        return XLSFormItem.of_records(records=records)

    @staticmethod
    def _serialize_generic_compound_question(
        question: Question,
    ) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        self = QuestionXLSFormSerializer
        choices: list[XLSFormChoice] = []
        records: list[XLSFormRecord] = [
            _create_question_relevance_record(question),
            # Create a group for the question and then add its
            # sub-questions to the group.
            XLSFormRecord.begin_group(
                label=self._create_question_label(question),
                name=question.id,
                relevant=self._get_question_relevance_calculation(question),
            ),
        ]
        for sub_question in question.sub_questions.values():  # pyright: ignore
            sq_records = QuestionXLSFormSerializer.of().serialize(sub_question)
            choices.extend(sq_records.choices)
            records.extend(sq_records.records)
        records.extend(
            (
                # Add score for the question
                _create_question_score_record(question),
                _create_question_int_score_record(question),
                _create_question_max_score_record(question),
                # Close the group
                XLSFormRecord.end_group(),
            ),
        )
        return XLSFormItem(records=records, choices=choices)

    @staticmethod
    def _serialize_generic_simple_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        self = QuestionXLSFormSerializer
        records: tuple[XLSFormRecord, ...] = (
            _create_question_relevance_record(question),
            XLSFormRecord(
                type="text",
                hint=(
                    escape_markdown(question.prompt)
                    if question.prompt
                    else None
                ),
                label=self._create_question_label(question),
                name=question.id,
                relevant=self._get_question_relevance_calculation(question),
            ),
            _create_question_score_record(question),
            _create_question_int_score_record(question),
            _create_question_max_score_record(question),
        )

        return XLSFormItem.of_records(records=records)

    @staticmethod
    def _serialize_multi_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        # Sanity Checks
        ensure_not_none(
            bool(question.sub_questions),
            f"'MULTI' question MUST have sub-questions. '{question.id}' has "
            "no sub-question.",
        )
        assert question.sub_questions
        self = QuestionXLSFormSerializer
        choices: tuple[XLSFormChoice, ...] = tuple(
            XLSFormChoice(
                label=escape_markdown(sub_question.label),
                list_name=question.id,
                name=sub_question.id,
            )
            for sub_question in question.sub_questions.values()
        )
        records: tuple[XLSFormRecord, ...] = (
            _create_question_relevance_record(question),
            XLSFormRecord.of_select_multiple(
                list_name=question.id,
                hint=(
                    escape_markdown(question.prompt)
                    if question.prompt
                    else None
                ),
                label=self._create_question_label(question),
                name=question.id,
                relevant=self._get_question_relevance_calculation(question),
            ),
            _create_question_score_record(question),
            _create_question_int_score_record(question),
            _create_question_max_score_record(question),
        )
        return XLSFormItem(records=records, choices=choices)

    @staticmethod
    def _serialize_perc_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        # Sanity Checks
        ensure_predicate(
            bool(question.sub_questions),
            f"'PERC' question MUST have sub-questions. '{question.id}' has no "
            "sub-questions.",
        )
        assert question.sub_questions  # Make pyright happy.
        ensure_predicate(
            len(question.sub_questions) == 2,
            "'PERC' question MUST have exactly 2 sub-questions. "
            f"'{question.id}' has {len(question.sub_questions)} "
            "sub-questions.",
        )
        self = QuestionXLSFormSerializer
        available_sq_types: frozenset[str]
        available_sq_types = _PERC_SUB_QUESTIONS_TYPES.difference(
            {_q.question_type for _q in question.sub_questions.values()},
        )
        ensure_predicate(
            not available_sq_types,
            "'PERC' question MUST have one sub-question of type 'DEN', and "
            "sub-question of type 'NUM'. The following sub-question types "
            f"'{','.join(available_sq_types)}' are missing for question "
            f"'{question.id}'.",
        )

        denominator: Question = next(
            filter(
                lambda _q: _q.question_type == QuestionType.DEN,
                question.sub_questions.values(),
            ),
        )
        numerator: Question = next(
            filter(
                lambda _q: _q.question_type == QuestionType.NUM,
                question.sub_questions.values(),
            ),
        )

        records: tuple[XLSFormRecord, ...] = (
            _create_question_relevance_record(question),
            XLSFormRecord.begin_group(
                appearance="table-list",
                hint=(
                    escape_markdown(question.prompt)
                    if question.prompt
                    else None
                ),
                label=self._create_question_label(question),
                name=f"{question.id}_PERC_GRP",
                relevant=self._get_question_relevance_calculation(question),
            ),
            XLSFormRecord.of_positive_integer(
                label=escape_markdown(numerator.label),
                name=numerator.id,
            ),
            XLSFormRecord.of_positive_integer(
                label=escape_markdown(denominator.label),
                name=denominator.id,
            ),
            XLSFormRecord(
                type="calculate",
                calculation=self._get_perc_question_calculation(
                    num_id=numerator.id,
                    den_id=denominator.id,
                ),
                name=question.id,
            ),
            XLSFormRecord.of_note(
                label=None,
                hint=f"_**Result:** {eval(var(question.id))}%_",
                name=f"{question.id}_PERC_CALC_DISPLAY",
            ),
            _create_question_score_record(question),
            _create_question_int_score_record(question),
            _create_question_max_score_record(question),
            XLSFormRecord.end_group(),
        )
        return XLSFormItem.of_records(records=records)

    @staticmethod
    def _serialize_rate_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        self = QuestionXLSFormSerializer
        records: tuple[XLSFormRecord, ...] = (
            _create_question_relevance_record(question),
            XLSFormRecord(
                type="decimal",
                hint=(
                    escape_markdown(question.prompt)
                    if question.prompt
                    else None
                ),
                label=self._create_question_label(question),
                name=question.id,
                relevant=self._get_question_relevance_calculation(question),
            ),
            _create_question_score_record(question),
            _create_question_int_score_record(question),
            _create_question_max_score_record(question),
        )

        return XLSFormItem.of_records(records=records)

    @staticmethod
    def _serialize_select_question(question: Question) -> XLSFormItem:
        ensure_not_none(question, "'question' MUST not be None.")
        # Sanity Checks
        ensure_predicate(
            bool(question.options_set),
            f"'SELECT' question MUST have options. '{question.id}' has no "
            "options.",
        )
        assert question.options_set  # Make Pyright happy
        self = QuestionXLSFormSerializer
        choices: tuple[XLSFormChoice, ...] = tuple(
            XLSFormChoice(
                label=escape_markdown(choice),
                list_name=question.id,
                name=build_select_option_name(question.id, index),
            )
            for index, choice in enumerate(question.options_set, start=1)
        )
        records: tuple[XLSFormRecord, ...] = (
            _create_question_relevance_record(question),
            XLSFormRecord.of_select_one(
                list_name=question.id,
                hint=(
                    escape_markdown(question.prompt)
                    if question.prompt
                    else None
                ),
                label=self._create_question_label(question),
                name=question.id,
                relevant=self._get_question_relevance_calculation(question),
            ),
            _create_question_score_record(question),
            _create_question_int_score_record(question),
            _create_question_max_score_record(question),
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
            ),
        ]

        int_scr_rec_id: str = f"{item.id}_INT_SCORE"
        max_scr_rec_id: str = f"{item.id}_MAX_SCORE"
        na_optn_rec_id: str = f"{item.id}_NA"
        per_scr_rec_id: str = f"{item.id}_PERCENTAGE_SCORE"

        if item.standard:
            records.append(
                XLSFormRecord.of_note(
                    label=f"**STANDARD:** {escape_markdown(item.standard)}",
                    name=f"{item.id}_STANDARD",
                ),
            )
        if item.instructions:
            _inst: str = escape_markdown(item.instructions)
            records.append(
                XLSFormRecord.of_note(
                    label=f"_**Instructions:** {escape_markdown(_inst)}_",
                    name=f"{item.id}_INSTRUCTION",
                ),
            )
        if item.na_option:
            records.append(XLSFormRecord.of_trigger(name=na_optn_rec_id))

        # Serialize the section's top level questions.
        if item.questions:
            for question in item.questions.values():
                q_items = QuestionXLSFormSerializer.of().serialize(question)
                choices.extend(q_items.choices)
                records.extend(q_items.records)

        per_scr_calc: NumberExpr = round(
            _(number(var(int_scr_rec_id)) / number(var(max_scr_rec_id))) * 100,
            2,
        )
        sec_scr_calc: Expr = if_(
            number(var(per_scr_rec_id)) < 90,
            then=_CeeScoreCL.RED.expr,
            else_=if_(
                number(var(per_scr_rec_id)) < 95,
                then=_CeeScoreCL.YELLOW.expr,
                else_=_CeeScoreCL.GREEN.expr,
            ),
        )
        # Add an expression to handle not applicable sections.
        # When ticked, the section should score Gray.
        if item.na_option:
            sec_scr_calc: Expr = if_(
                string(var(na_optn_rec_id)) == str_("OK"),
                then=_CeeScoreCL.GRAY.expr,
                else_=sec_scr_calc,
            )

        records.extend(
            (
                # Comment
                XLSFormRecord(
                    type="text",
                    appearance="multiline",
                    label="Comments",
                    name=f"{item.id}_COMMENTS",
                ),
                # Section score
                XLSFormRecord(
                    type="calculate",
                    calculation=eval(
                        self._get_section_int_score_calculation(section=item),
                    ),
                    default="0",
                    name=int_scr_rec_id,
                ),
                XLSFormRecord(
                    type="calculate",
                    calculation=eval(
                        self._get_section_max_score_calculation(section=item),
                    ),
                    default="1",
                    name=max_scr_rec_id,
                ),
                XLSFormRecord(
                    type="calculate",
                    calculation=eval(per_scr_calc),
                    default="0",
                    name=per_scr_rec_id,
                ),
                XLSFormRecord.of_select_one(
                    list_name=_CeeScoreCL.list_name(),
                    appearance="minimal",
                    calculation=eval(sec_scr_calc),
                    default=_CeeScoreCL.RED.choice_name,
                    label="Score",
                    name=f"{item.id}_SCORE",
                    read_only="yes",
                ),
                # End group
                XLSFormRecord.end_group(),
            ),
        )

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

    @staticmethod
    def _get_section_int_score_calculation(section: Section) -> Expr:
        ensure_not_none(section, "'section' MUST not be None.")
        _acc: NumberExpr
        _qst: Question
        _qisr = _get_question_int_score_record_id
        return reduce(
            lambda _acc, _qst: _acc + number(var(_qisr(_qst))),
            section.questions.values() if section.questions else (),
            ZERO,
        )

    @staticmethod
    def _get_section_max_score_calculation(section: Section) -> Expr:
        ensure_not_none(section, "'section' MUST not be None.")
        _acc: NumberExpr
        _qst: Question
        _qmsr = _get_question_max_score_record_id
        return reduce(
            lambda _acc, _qst: _acc + number(var(_qmsr(_qst))),
            section.questions.values() if section.questions else (),
            ZERO,
        )


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
    "build_select_option_name",
]
