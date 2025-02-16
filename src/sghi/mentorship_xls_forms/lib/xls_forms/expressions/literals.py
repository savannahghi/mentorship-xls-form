from __future__ import annotations

from attrs import field, frozen

from .base import BoolExpr, Expr, IntExpr, NumberExpr, TextExpr, XPathExpr

# =============================================================================
# TYPES
# =============================================================================


_Number = int | float


# =============================================================================
# LITERALS
# =============================================================================


@frozen
class LiteralValue[_T](Expr):
    value: _T = field()

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"{self.value!s}")


@frozen(eq=False)
class Boolean(BoolExpr, LiteralValue[bool]):
    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"{'true()' if self.value else 'false()'}")


@frozen(eq=False)
class Int(IntExpr, LiteralValue[int]): ...


@frozen(eq=False)
class Number(NumberExpr, LiteralValue[_Number]): ...


@frozen(eq=False)
class String(TextExpr, LiteralValue[str]):
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

THREE: int_ = int_(3)

TRUE: bool_ = bool_(True)

TWO: int_ = int_(2)

ZERO: int_ = int_(0)
