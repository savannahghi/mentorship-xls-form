from __future__ import annotations

from typing import Generic, TypeVar

from attrs import field, frozen

from .base import BoolExpr, Expr, IntExpr, NumberExpr, TextExpr, XPathExpr

# =============================================================================
# TYPES
# =============================================================================


_Number = int | float

_T = TypeVar("_T")


# =============================================================================
# LITERALS
# =============================================================================

@frozen
class LiteralValue(Expr, Generic[_T]):

    value: _T = field()

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"{self.value!s}")


@frozen
class Boolean(LiteralValue[bool], BoolExpr):

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f'{"yes" if self.value else "no"}')


@frozen
class Int(LiteralValue[int], IntExpr):
    ...


@frozen
class Number(LiteralValue[_Number], NumberExpr):
    ...


@frozen
class String(LiteralValue[str], TextExpr):

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"'{self.value!s}'")


bool_ = Boolean

int_ = Int

num = Number

str_ = String


# =============================================================================
# CONSTANTS
# =============================================================================

ONE: int_ = int_(1)

FALSE: bool_ = bool_(False)

THREE: num = num(3)

TRUE: bool_ = bool_(True)

TWO: int_ = int_(2)

ZERO: int_ = int_(0)
