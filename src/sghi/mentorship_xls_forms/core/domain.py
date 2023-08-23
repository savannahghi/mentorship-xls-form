from __future__ import annotations

from abc import ABCMeta
from typing import TYPE_CHECKING, Literal

from attrs import define, field

if TYPE_CHECKING:
    from collections.abc import Mapping, Set as AbstractSet

# =============================================================================
# TYPES
# =============================================================================

AnswerType = Literal[
    "BOOLEAN",
    "FLOAT",
    "INTEGER_ZERO_OR_POSITIVE",
    "STRING",
]


QuestionType = Literal[
    "BOOL",
    "CN",  # C1, C2, ..., CN
    "COUNT",
    "DEN",
    "MULTI",
    "NUM",
    "PERC",
    "SELECT",
    "TEXT"
]


# =============================================================================
# BASE INTERFACES
# =============================================================================


class DomainObject(metaclass=ABCMeta):
    """Marker interface that identifies a domain object.

    All domain objects should implement this interface.
    """

    __slots__ = ()


# =============================================================================
# DOMAIN MODELS
# =============================================================================

@define
class Facility(DomainObject):
    name: str = field()
    mfl_code: str = field()
    county: str = field()
    sub_county: str = field(repr=False)
    ward: str = field(repr=False)


@define
class Question(DomainObject):
    """A question in a mentorship checklist."""

    id: str = field()  # noqa: A003
    label: str = field(hash=False)
    question_type: QuestionType = field()
    answer_type: AnswerType = field(repr=False)
    options_set: AbstractSet[str] | None = field(
        default=None, hash=False, kw_only=True, repr=False
    )
    prompt: str | None = field(
        default=None, hash=False, kw_only=True, repr=False
    )
    scoring_logic: str | None = field(
        default=None, hash=False, kw_only=True, repr=False
    )
    sub_questions: Mapping[str, Question] | None = field(
        default=None, hash=False, kw_only=True, repr=False
    )
    na_option: bool = field(
        default=False, hash=False, kw_only=True, repr=False
    )

    @property
    def has_sub_questions(self) -> bool:
        return bool(self.sub_questions)


@define
class Section(DomainObject):
    """A section in a mentorship checklist."""

    id: str = field()  # noqa: A003
    title: str = field(hash=False)
    standard: str | None = field(
        default=None, hash=False, kw_only=True, repr=False
    )
    instructions: str | None = field(
        default=None, hash=False, kw_only=True, repr=False
    )
    na_option: bool = field(
        default=False, hash=False, kw_only=True, repr=False
    )
    required: bool = field(
        default=True, hash=False, kw_only=True, repr=False
    )
    questions: Mapping[str, Question] | None = field(
        default=None, hash=False, kw_only=True, repr=False
    )

    @property
    def has_questions(self) -> bool:
        return bool(self.questions)


@define
class MentorshipChecklist(DomainObject):
    """A mentorship checklist."""

    id: str = field()  # noqa: A003
    name: str = field(hash=False)
    sections: Mapping[str, Section] | None = field(
        default=None, hash=False, kw_only=True, repr=False
    )

    @property
    def has_sections(self) -> bool:
        return bool(self.sections)
