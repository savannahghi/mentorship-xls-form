from __future__ import annotations

from abc import ABCMeta, abstractmethod
from functools import cache
from typing import Final, NewType, SupportsIndex, SupportsRound, overload
from typing import Self as _Self

from attrs import field, frozen, validators

from sghi.utils import ensure_not_none, ensure_not_none_nor_empty

# =============================================================================
# TYPES
# =============================================================================


XPathExpr = NewType("XPathExpr", str)
"""
The resulting, equivalent XPath expression after evaluating an
:class:`XLSForm expression<Expr>`.

This can then be used directly on XLSForms to define dynamic form behaviour.
See the `XLSForm docs <https://xlsform.org/en/#formulas>`_ for more details.
"""


# =============================================================================
# CONSTANTS
# =============================================================================


_SELF: Final[XPathExpr] = XPathExpr(".")

BLANK_RESULT: Final[XPathExpr] = XPathExpr("")
"""A blank :attr:`expression results<XPathExpr>`."""


# =============================================================================
# HELPERS
# =============================================================================


@overload
def python_number_to_xls_form_number(number: int | IntExpr) -> IntExpr: ...


@overload
def python_number_to_xls_form_number(
    number: float | NumberExpr,
) -> NumberExpr: ...


def python_number_to_xls_form_number(
    number: NumberExpr | float,
) -> IntExpr | NumberExpr:
    ensure_not_none(number, "'number' MUST not be None.")
    match number:
        case int():
            from .literals import int_

            return int_(number)
        case float():
            from .literals import num

            return num(number)
        case IntExpr() | NumberExpr():
            return number
        case _:
            err_message: str = f"Unknown number type: {type(number)}."
            raise TypeError(err_message)


def eval(expression: Expr) -> XPathExpr:  # noqa: A001
    """
    Evaluate an :class:`XLSForm expression<Expr>` `(written/composed using
    Python objects)` and return the equivalent XPath expression.

    :param expression: The XLSForm expression to be evaluated. This must not be
        ``None``.

    :return: The resulting, equivalent XPath expression.

    :raises ValueError: If the specified expression is ``None``.
    """
    ensure_not_none(expression, "'expression' MUST not be empty.")
    return expression.__eval__()


# =============================================================================
# BASE INTERFACE
# =============================================================================


class Expr(metaclass=ABCMeta):
    """Interface denoting an XLSForm expression.

    This interface serves as a basis for constructing and composing XLSForm
    expressions using Python objects. These can then later be translated to the
    equivalent `XPath` expression. All terms, formulas, operators, and
    functions used in the construction of XLSForm expressions are derived from
    this interface.
    """

    __slots__ = ()

    def __xor__(self, other: Expr) -> Expr:
        """Overload this to implement

        :param other:
        :return:
        """
        from .functions import coalesce

        return coalesce(self, other)

    @abstractmethod
    def __eval__(self) -> XPathExpr:
        """Evaluate this XLSForm expression and return the equivalent XPath
        expression.

        :return: The resulting, equivalent XPath expression.
        """
        ...


# =============================================================================
# MARKER INTERFACES
# =============================================================================


class BoolExpr(Expr, metaclass=ABCMeta):
    """Marker interface for expressions that evaluate to a boolean."""

    __slots__ = ()

    def __and__(self, other: BoolExpr) -> BoolExpr:
        from .operators import and_

        return and_(self, other)

    def __invert__(self) -> BoolExpr:
        from .functions import not_

        return not_(self)

    def __or__(self, other: BoolExpr) -> BoolExpr:
        from .operators import or_

        return or_(self, other)

    @classmethod
    def of_expression(cls, expr: Expr) -> BoolExpr:
        from .functions import boolean

        return boolean(expr)

    @classmethod
    def of_not(cls, expr: BoolExpr) -> BoolExpr:
        from .functions import not_

        return not_(expr)


class NumberExpr(Expr, SupportsIndex, SupportsRound, metaclass=ABCMeta):
    """Marker interface for expressions that evaluate to a number.

    A number can be an integer or floating-point decimal.
    """

    __slots__ = ()

    def __abs__(self) -> NumberExpr:
        from .functions import abs_

        return abs_(self)

    def __add__(self, other: NumberExpr | float) -> NumberExpr:
        if not isinstance(other, NumberExpr | int | float):
            return NotImplemented
        from .operators import add

        return add(self, python_number_to_xls_form_number(other))

    def __eq__(self, other: NumberExpr | float) -> BoolExpr:  # type: ignore
        if not isinstance(other, NumberExpr | int | float):
            return NotImplemented
        from .operators import eq

        return eq(self, python_number_to_xls_form_number(other))

    def __ge__(self, other: NumberExpr | float) -> BoolExpr:
        if not isinstance(other, NumberExpr | int | float):
            return NotImplemented
        from .operators import ge

        return ge(self, python_number_to_xls_form_number(other))

    def __gt__(self, other: NumberExpr | float) -> BoolExpr:
        if not isinstance(other, NumberExpr | int | float):
            return NotImplemented
        from .operators import gt

        return gt(self, python_number_to_xls_form_number(other))

    def __index__(self) -> int:
        return 0

    def __le__(self, other: NumberExpr | float) -> BoolExpr:
        if not isinstance(other, NumberExpr | int | float):
            return NotImplemented
        from .operators import le

        return le(self, python_number_to_xls_form_number(other))

    def __lt__(self, other: NumberExpr | float) -> BoolExpr:
        if not isinstance(other, NumberExpr | int | float):
            return NotImplemented
        from .operators import lt

        return lt(self, python_number_to_xls_form_number(other))

    def __ne__(self, other: NumberExpr | float) -> BoolExpr:  # type: ignore
        if not isinstance(other, NumberExpr | int | float):
            return NotImplemented
        from .operators import ne

        return ne(self, python_number_to_xls_form_number(other))

    def __mul__(self, other: NumberExpr | float) -> NumberExpr:
        if not isinstance(other, NumberExpr | int | float):
            return NotImplemented
        from .operators import mul

        return mul(self, python_number_to_xls_form_number(other))

    def __pow__(self, power: NumberExpr | float) -> NumberExpr:
        if not isinstance(power, NumberExpr | int | float):
            return NotImplemented
        from .functions import pow_

        return pow_(self, python_number_to_xls_form_number(power))

    @overload
    def __round__(self, places: int = 2) -> NumberExpr: ...

    @overload
    def __round__(self, places: IntExpr | None = None) -> NumberExpr: ...

    def __round__(self, places: int | IntExpr | None = None) -> NumberExpr:
        from .functions import round_
        from .literals import TWO, int_

        _places = int_(places) if isinstance(places, int) else places
        return round_(self, _places or TWO)

    def __sub__(self, other: NumberExpr | float) -> NumberExpr:
        if not isinstance(other, NumberExpr | int | float):
            return NotImplemented
        from .operators import sub

        return sub(self, python_number_to_xls_form_number(other))

    def __truediv__(self, other: NumberExpr | float) -> NumberExpr:
        if not isinstance(other, NumberExpr | int | float):
            return NotImplemented
        from .operators import div

        return div(self, python_number_to_xls_form_number(other))

    @classmethod
    def of_expression(cls, expr: Expr) -> NumberExpr:
        from .functions import number

        return number(expr)


class IntExpr(NumberExpr, metaclass=ABCMeta):
    """Marker interface for expressions that evaluate to an integer.

    An integer is a decimal number with the fractional portion truncated.

    .. note::

        This is a `marker` interface and has no additional methods or
        properties. It exists to identify expressions that evaluate to an
        integer.
    """

    @classmethod
    def of_number(cls, arg: NumberExpr) -> IntExpr:
        from .functions import intf

        return intf(arg)


class TextExpr(Expr, metaclass=ABCMeta):
    """Marker interface for expressions that evaluate to a string.

    The string can be on a single line or multiple line i.e., contain line
    breaks.

    .. note::

        This is a `marker` interface and has no additional methods or
        properties. It exists to identify expressions that evaluate to a
        string.
    """

    __slots__ = ()

    def __eq__(self, other: TextExpr) -> BoolExpr:  # type: ignore
        from .operators import eq

        return eq(self, other)

    def __ne__(self, other: TextExpr) -> BoolExpr:  # type: ignore
        from .operators import ne

        return ne(self, other)


# =============================================================================
# OTHER CORE COMPONENTS
# =============================================================================


@frozen
class Brackets(NumberExpr):
    expr: Expr = field(validator=validators.instance_of(Expr))

    def __attrs_post_init__(self) -> None:
        ensure_not_none(self.expr, "'expr' MUST not be None.")

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"({eval(self.expr)})")


@frozen
class Self(Expr):
    """The value of the current question.

    This translates to `.` once evaluated and mostly used when defining
    constraints. Eg::

        .>=18

    See `odk docs <https://docs.getodk.org/form-logic/#variables>`_ for more
    details.
    """

    def __eval__(self) -> XPathExpr:
        return _SELF

    @classmethod
    @cache
    def instance(cls) -> _Self:
        """Return an instance of ``Self``.

        This will return a cached instance and avoid unnecessary allocations.
        Prefer using this factory than direct instantiation using the
        constructor.

        :return: An instance of ``Self``.
        """
        return cls()


@frozen
class Variable(Expr):
    """A variable in an XLSForm.

    Variables reference the values of previously answered questions.

    See `odk docs <https://docs.getodk.org/form-logic/#variables>`_ for more
    details.
    """

    question_name: str = field()

    def __attrs_post_init__(self) -> None:
        ensure_not_none_nor_empty(
            self.question_name,
            "'question_name' MUST not be non or empty",
        )

    def __eval__(self) -> XPathExpr:
        return XPathExpr("${%s}" % self.question_name)  # noqa: UP031


brkt = Brackets

var = Variable
