from __future__ import annotations

from abc import ABCMeta
from typing import Self

from attrs import field, frozen

from sghi.utils import ensure_not_none

from .base import (
    BoolExpr,
    Expr,
    NumberExpr,
    TextExpr,
    XPathExpr,
    eval,  # noqa: A004
)

# =============================================================================
# TYPES
# =============================================================================


_AlphaNumeric = NumberExpr | TextExpr


# =============================================================================
# BASE OPERATORS
# =============================================================================


class Operator(Expr, metaclass=ABCMeta):
    """Marker interface indentify XLSForm operators.

    .. note::

        This is a `marker` interface and has no additional
        methods or properties.

    See `odk docs <https://docs.getodk.org/form-operators-functions/#operators>`_
    for more details.
    """

    __slots__ = ()


@frozen
class BiOperator[_LHT: Expr, _RHT: Expr](Operator):
    """An XLSForm binary operator."""

    operator: str = field()
    left_operand: _LHT = field()
    right_operand: _RHT = field()

    def __attrs_post_init__(self) -> None:
        ensure_not_none(self.operator, "'operator' MUST not be None.")
        ensure_not_none(self.left_operand, "'left_operand' MUST not be None.")
        ensure_not_none(
            self.right_operand,
            "'right_operand' MUST not be None.",
        )

    def __eval__(self) -> XPathExpr:
        return XPathExpr(
            "{}{}{}".format(  # noqa: UP032
                eval(self.left_operand),
                self.operator,
                eval(self.right_operand),
            ),
        )


# =============================================================================
# ARITHMETIC OPERATORS
# =============================================================================


@frozen
class Add(BiOperator[NumberExpr, NumberExpr], NumberExpr):
    """`+` XLSForm operator."""

    operator: str = " + "

    @classmethod
    def of(cls, left_operand: NumberExpr, right_operand: NumberExpr) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


@frozen
class Divide(BiOperator[NumberExpr, NumberExpr], NumberExpr):
    """`div` XLSForm operator."""

    operator: str = " div "

    @classmethod
    def of(cls, left_operand: NumberExpr, right_operand: NumberExpr) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


@frozen
class Multiply(BiOperator[NumberExpr, NumberExpr], NumberExpr):
    """`*` XLSForm operator."""

    operator: str = " * "

    @classmethod
    def of(cls, left_operand: NumberExpr, right_operand: NumberExpr) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


@frozen
class Subtract(BiOperator[NumberExpr, NumberExpr], NumberExpr):
    """`-` XLSForm operator."""

    operator: str = " - "

    @classmethod
    def of(cls, left_operand: NumberExpr, right_operand: NumberExpr) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


add = Add.of

div = Divide.of

mul = Multiply.of

sub = Subtract.of

# =============================================================================
# BOOLEAN OPERATORS
# =============================================================================


@frozen
class And(BoolExpr, BiOperator[BoolExpr, BoolExpr]):
    """`and` XLSForm operator."""

    operator: str = " and "

    @classmethod
    def of(cls, left_operand: BoolExpr, right_operand: BoolExpr) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


@frozen
class Or(BiOperator[BoolExpr, BoolExpr], BoolExpr):
    """`or` XLSForm operator."""

    operator: str = " or "

    @classmethod
    def of(cls, left_operand: BoolExpr, right_operand: BoolExpr) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


and_ = And.of

or_ = Or.of

# =============================================================================
# BOOLEAN OPERATORS
# =============================================================================


@frozen
class Eq(BiOperator[_AlphaNumeric, _AlphaNumeric], BoolExpr):
    """`=` XLSForm operator."""

    operator: str = " = "

    @classmethod
    def of(
        cls,
        left_operand: _AlphaNumeric,
        right_operand: _AlphaNumeric,
    ) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


@frozen
class Ge(BiOperator[NumberExpr, NumberExpr], BoolExpr):
    """`>=` XLSForm operator."""

    operator: str = " >= "

    @classmethod
    def of(cls, left_operand: NumberExpr, right_operand: NumberExpr) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


@frozen
class Gt(BiOperator[NumberExpr, NumberExpr], BoolExpr):
    """`>` XLSForm operator."""

    operator: str = " > "

    @classmethod
    def of(cls, left_operand: NumberExpr, right_operand: NumberExpr) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


@frozen
class Le(BiOperator[NumberExpr, NumberExpr], BoolExpr):
    """`<=` XLSForm operator."""

    operator: str = " <= "

    @classmethod
    def of(cls, left_operand: NumberExpr, right_operand: NumberExpr) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


@frozen
class Lt(BiOperator[NumberExpr, NumberExpr], BoolExpr):
    """`<` XLSForm operator."""

    operator: str = " < "

    @classmethod
    def of(cls, left_operand: NumberExpr, right_operand: NumberExpr) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


@frozen
class Ne(BiOperator[_AlphaNumeric, _AlphaNumeric], BoolExpr):
    """`!=` XLSForm operator."""

    operator: str = " != "

    @classmethod
    def of(
        cls,
        left_operand: _AlphaNumeric,
        right_operand: _AlphaNumeric,
    ) -> Self:
        return cls(left_operand=left_operand, right_operand=right_operand)


eq = Eq.of

ge = Ge.of

gt = Gt.of

le = Le.of

lt = Lt.of

ne = Ne.of
