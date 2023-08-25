from __future__ import annotations

from abc import ABCMeta

from attrs import field, frozen, validators

from .base import (
    BoolExpr,
    Expr,
    IntExpr,
    NumberExpr,
    TextExpr,
    XPathExpr,
    eval,
)

# =============================================================================
# BASE FUNCTIONS
# =============================================================================


class FunctionExpr(Expr, metaclass=ABCMeta):
    """Marker interface indentify XLSForm operators.

    .. note::

        This is a `marker` interface and has no additional
        methods or properties.

    See `odk docs <https://docs.getodk.org/form-operators-functions/#functions>`_
    for more details.
    """


# =============================================================================
# ACCESSOR FUNCTIONS
# =============================================================================


class Select(FunctionExpr, TextExpr):

    space_delimited_array: Expr = field(validator=validators.instance_of(Expr))
    string: TextExpr = field(validator=validators.instance_of(TextExpr))

    def __eval__(self) -> XPathExpr:
        sda = eval(self.space_delimited_array)
        string = eval(self.string)
        return XPathExpr(f"selected({sda}, {string})")


select = Select


# =============================================================================
# CONTROL FLOW FUNCTIONS
# =============================================================================


@frozen
class If(FunctionExpr):

    condition: BoolExpr = field(validator=validators.instance_of(BoolExpr))
    then: Expr = field(validator=validators.instance_of(Expr))
    else_: Expr = field(validator=validators.instance_of(Expr))

    def __eval__(self) -> XPathExpr:
        return XPathExpr(
            f"if({eval(self.condition)}, {self.then}, {self.else_})"
        )


if_ = If


# =============================================================================
# MATH FUNCTIONS
# =============================================================================


@frozen
class Abs(FunctionExpr, NumberExpr):

    value: NumberExpr = field(validator=validators.instance_of(NumberExpr))

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"abs({eval(self.value)})")


@frozen
class Round(FunctionExpr, NumberExpr):

    number: NumberExpr = field(validator=validators.instance_of(NumberExpr))
    places: IntExpr = field(validator=validators.instance_of(IntExpr))

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"round({eval(self.number)}, {eval(self.places)})")


@frozen
class IntF(FunctionExpr, IntExpr):

    number: NumberExpr = field(validator=validators.instance_of(NumberExpr))

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"int({self.number})")


@frozen
class NumberF(FunctionExpr, NumberExpr):

    expr: Expr = field(validator=validators.instance_of(Expr))

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"number({eval(self.expr)})")


@frozen
class Pow(FunctionExpr, NumberExpr):

    value: NumberExpr = field(validator=validators.instance_of(NumberExpr))
    power: IntExpr = field(validator=validators.instance_of(IntExpr))

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"pow({eval(self.value)}, {eval(self.power)})")


abs_ = Abs

round_ = Round

intf = IntF

number = NumberF

pow_ = Pow


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

@frozen
class BooleanF(FunctionExpr, BoolExpr):

    arg: Expr = field(validator=validators.instance_of(Expr))

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"boolean({eval(self.arg)})")


@frozen
class Coalesce(FunctionExpr, BoolExpr, IntExpr, NumberExpr, TextExpr):

    arg1: Expr = field(validator=validators.instance_of(Expr))
    arg2: Expr = field(validator=validators.instance_of(Expr))

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"coalesce({eval(self.arg1)}, {eval(self.arg2)})")


@frozen
class Not(FunctionExpr, BoolExpr):

    arg: Expr = field(validator=validators.instance_of(Expr))

    def __eval__(self) -> XPathExpr:
        return XPathExpr(f"not({eval(self.arg)})")


boolean = BooleanF

coalesce = Coalesce

not_ = Not
