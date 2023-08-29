# ruff: noqa: N802, N803
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from functools import reduce
from typing import TYPE_CHECKING, Any, Final, Literal, Protocol

from antlr4 import (
    CommonTokenStream,
    InputStream,
    ParseTreeWalker,
    Recognizer,
    TerminalNode,
)
from antlr4.error.ErrorListener import ErrorListener
from antlr4.tree.Tree import TerminalNodeImpl
from attrs import define, field, frozen
from attrs import validators as vlds

from sghi.exceptions import SGHIError
from sghi.mentorship_xls_forms.lib.xls_forms.expressions import (
    BoolExpr,
    Expr,
    NumberExpr,
    count_selected,
    if_,
    num,
    number,
    select,
    str_,
    var,
)
from sghi.utils import ensure_not_none, ensure_not_none_nor_empty

from .generated.SGHI_XLSFormLexer import SGHI_XLSFormLexer
from .generated.SGHI_XLSFormListener import SGHI_XLSFormListener
from .generated.SGHI_XLSFormParser import SGHI_XLSFormParser

if TYPE_CHECKING:
    from collections.abc import Sequence
    from sghi.mentorship_xls_forms.core import Question, Section

# =============================================================================
# TYPES
# =============================================================================


MetaCeeScore = Literal["Gray", "Green", "Red", "Yellow"]


class _HasCeeScore(Protocol):

    @abstractmethod
    def CEE_SCORE(self) -> TerminalNode | None:
        ...


# =============================================================================
# CONSTANTS
# =============================================================================

CEE_SCORE_GRAY: Final[str_] = str_("gray")

CEE_SCORE_GREEN: Final[str_] = str_("green")

CEE_SCORE_RED: Final[str_] = str_("red")

CEE_SCORE_YELLOW: Final[str_] = str_("yellow")

META_NO: Final[str_] = str_("no")

META_YES: Final[str_] = str_("yes")


# =============================================================================
# HELPERS
# =============================================================================


def _get_term_node_txt(terminal_node: TerminalNode | None) -> str:
    assert isinstance(terminal_node, TerminalNodeImpl)
    return terminal_node.getText()


def _meta_cee_score_to_xls_form(meta_cee_score: MetaCeeScore | str) -> str_:
    ensure_not_none_nor_empty(
        meta_cee_score, "'meta_cee_score' MUST not be None or empty."
    )
    match meta_cee_score:
        case "Gray":
            return CEE_SCORE_GRAY
        case "Green":
            return CEE_SCORE_GREEN
        case "Red":
            return CEE_SCORE_RED
        case "Yellow":
            return CEE_SCORE_YELLOW
        case _:
            _err_msg: str = f"Unknown cee score '{meta_cee_score}'"
            raise ParseError(message=_err_msg)


def _scoring_logic_txt_to_expr(
    question_id: str, scoring_logic_text: str
) -> ListenerWalkResults:
    ensure_not_none_nor_empty(
        question_id, "'question_id' MUST not be None or empty."
    )
    ensure_not_none_nor_empty(
        scoring_logic_text,
        "'scoring_logic_text' MUST not be None or empty."
    )

    lexer = SGHI_XLSFormLexer(input=InputStream(data=scoring_logic_text))
    parser = SGHI_XLSFormParser(input=CommonTokenStream(lexer=lexer))
    parser.addErrorListener(XLSFormErrorListener(question_id=question_id))
    scoring_logic_parser = ScoringLogicListener(question_id=question_id)
    walker = ParseTreeWalker()
    walker.walk(scoring_logic_parser, parser.scoring_logic())

    return scoring_logic_parser.walk_results


@frozen
class ListenerWalkResults:
    conditional_expr: BoolExpr = field(validator=vlds.instance_of(BoolExpr))
    then_expr: Expr = field(validator=vlds.instance_of(Expr))


@frozen
class XLSFormErrorListener(ErrorListener):

    question_id: str = field(validator=vlds.instance_of(str))

    def syntaxError(
        self,
        recognizer: Recognizer,
        offendingSymbol: Any,  # noqa
        line: int,
        column: int,
        msg: str,
        e: Recognizer.RecognitionException
    ) -> None:
        err_msg: str = (
            f"Error parsing expression on question '{self.question_id}': "
            f"line {line}: {column} - {msg}"
        )
        raise ParseError(message=err_msg)


# =============================================================================
# EXCEPTIONS
# =============================================================================


class ParseError(SGHIError):
    """Error while parsing expressions on XLSForm metadata."""


# =============================================================================
# LISTENERS
# =============================================================================


class Listener(metaclass=ABCMeta):

    @property
    @abstractmethod
    def walk_results(self) -> ListenerWalkResults:
        ...


@define
class ScoringLogicListener(SGHI_XLSFormListener, Listener):

    _question_id: str = field(validator=vlds.instance_of(str))
    _conditional_expr: BoolExpr | None = field(default=None, init=False)
    _then_expr: Expr | None = field(default=None, init=False)
    _expr_cache: list[BoolExpr] = field(factory=list, init=False)

    @property
    def walk_results(self) -> ListenerWalkResults:
        assert self._conditional_expr, (
            "Invalid state. Conditional expression not available. Has the "
            "walk happened?"
        )
        assert self._then_expr, (
            "Invalid state. Then expression not available. Has the walk "
            "happened?"
        )
        return ListenerWalkResults(
            conditional_expr=self._conditional_expr,
            then_expr=self._then_expr
        )

    def exitIf_bool_literal_equals_score(
        self,
        ctx: SGHI_XLSFormParser.If_bool_literal_equals_scoreContext
    ) -> None:
        meta_bool: str_ = (
            # This might seem unintuitive or wrong, but it is correct.
            # The intention is to create an inverse of the conditional
            # expression as it works better on XForms tools such as ODK.
            # In short, instead of:
            #
            #   if(selected(${SIMS.S_01_02_CondomAvail_Q2_RESP}, 'no'), 'yellow', 'green'))
            #
            # make the following expression:
            #
            #   if(not(selected(${SIMS.S_01_02_CondomAvail_Q2_RESP}, 'yes')), 'yellow', 'green'))
            #
            # The latter produces a better expression when working with XForm tools.
            META_NO if _get_term_node_txt(ctx.BOOLEAN()) == "Y" else META_YES
        )
        meta_cee_score: str_ = _meta_cee_score_to_xls_form(
            meta_cee_score=_get_term_node_txt(ctx.CEE_SCORE())
        )
        self._conditional_expr = ~select(var(self._question_id), meta_bool)
        self._then_expr = meta_cee_score

    def exitComparison_expression(
        self,
        ctx: SGHI_XLSFormParser.Comparison_expressionContext
    ) -> None:
        if self._conditional_expr is not None and self._expr_cache:
            # If True, this is a compound comparison expression. Thus compose
            # the last expression in expressions cache with the current value
            # of `self._conditional_expr` to form the compound expression.
            meta_compound_operator: str = _get_term_node_txt(
                next(filter(lambda _o: _o is not None, (ctx.AND(), ctx.OR())))
            )
            match meta_compound_operator:
                case "and":
                    self._conditional_expr = (
                        self._conditional_expr & self._expr_cache[-1]
                    )
                case "or":
                    self._conditional_expr = (
                        self._conditional_expr | self._expr_cache[-1]
                    )
                case _:
                    err_msg: str = (
                        f"Unexpected operator '{meta_compound_operator}' "
                        f"while parsing question '{self._question_id}'. "
                        "Expected one of 'and', 'or' operators."

                    )
                    raise ParseError(message=err_msg)
            # Clear the cache
            self._expr_cache.pop()
        else:
            digits: float = float(_get_term_node_txt(ctx.DIGITS()))
            left_operand: NumberExpr = (
                number(var(self._question_id)) if ctx.PERCENT() is not None
                else count_selected(var(self._question_id))
            )
            right_operand: NumberExpr = num(digits)

            # If `self._conditional_expr` already has a value, move it to the
            # cache. The assumption is that if there exists more than one
            # conditional expression during a single listener walk, then the
            # final conditional expression will be a composite expression i.e.,
            # composed of multiple comparison expressions joined together by
            # either the AND/OR operators.
            # The conditional expression will then be retrieved from the cache
            # and composed with the new expression and an operator (AND/OR) to
            # form the final conditional expression.
            if self._conditional_expr is not None:
                self._expr_cache.append(self._conditional_expr)

            cmp_operators: tuple[TerminalNode | None, ...]
            cmp_operators = (ctx.GE(), ctx.GT(), ctx.LE(), ctx.LT())
            meta_comparison_operator: str = _get_term_node_txt(
                next(filter(lambda _o: _o is not None, cmp_operators))
            )
            match meta_comparison_operator:
                case ">=" | "≥":
                    self._conditional_expr = left_operand >= right_operand
                case ">":
                    self._conditional_expr = left_operand > right_operand
                case "=<" | "≤":
                    self._conditional_expr = left_operand <= right_operand
                case "<":
                    self._conditional_expr = left_operand < right_operand
                case _:
                    err_msg: str = (
                        f"Unexpected operator '{meta_comparison_operator}' "
                        f"while parsing question '{self._question_id}'. "
                        "Expected one of '<', '=<', '>' or '>=' operators."
                    )
                    raise ParseError(message=err_msg)

    def exitIf_count_equals_score(
        self,
        ctx: SGHI_XLSFormParser.If_count_equals_scoreContext
    ) -> None:
        meta_count: float = float(_get_term_node_txt(ctx.DIGITS()))
        cee_score: str_ = _meta_cee_score_to_xls_form(
            meta_cee_score=_get_term_node_txt(ctx.CEE_SCORE())
        )
        count: NumberExpr = num(meta_count)

        self._conditional_expr = (
            count_selected(var(self._question_id)) == count
        )
        self._then_expr = cee_score

    def exitIf_comparison_equals_score(
        self,
        ctx: SGHI_XLSFormParser.If_comparison_equals_scoreContext
    ) -> None:
        self._finalize_complex_expression(ctx=ctx)

    def exitIf_range_equals_score(
        self,
        ctx: SGHI_XLSFormParser.If_range_equals_scoreContext
    ) -> None:
        self._finalize_complex_expression(ctx=ctx)

    def exitIf_selection_equals_score(
        self,
        ctx: SGHI_XLSFormParser.If_selection_equals_scoreContext
    ) -> None:
        self._finalize_complex_expression(ctx=ctx)

    def exitRange_expression(
        self,
        ctx: SGHI_XLSFormParser.Range_expressionContext
    ) -> None:
        meta_lower_bound: float = float(_get_term_node_txt(ctx.DIGITS(0)))
        meta_upper_bound: float = float(_get_term_node_txt(ctx.DIGITS(1)))

        lower_bound: NumberExpr = num(meta_lower_bound)
        upper_bound: NumberExpr = num(meta_upper_bound)
        question: NumberExpr = count_selected(var(self._question_id))

        # Evaluate to something similar to:
        #   -> lower_bound <= question <= upper_bound
        self._conditional_expr = (question >= lower_bound) & (question <= upper_bound)  # noqa: E501

    def exitSelection_expression(
        self,
        ctx: SGHI_XLSFormParser.Selection_expressionContext
    ) -> None:
        if self._conditional_expr is not None and self._expr_cache:
            # Compound expression encountered, compose it.
            self._conditional_expr = (
                self._conditional_expr | self._expr_cache.pop()
            )
        else:
            from sghi.mentorship_xls_forms.lib.serializers.xls_form import (
                build_select_option_name
            )

            meta_option_index: int = int(_get_term_node_txt(ctx.DIGITS()))
            option_name: str_ = str_(
                build_select_option_name(
                    question_id=self._question_id,
                    option_index=meta_option_index
                )
            )

            if self._conditional_expr is not None:
                self._expr_cache.append(self._conditional_expr)
            self._conditional_expr = select(
                var(self._question_id), option_name
            )

    def _finalize_complex_expression(self, ctx: _HasCeeScore) -> None:
        assert self._conditional_expr, (
            "Unexpected state. The conditional expression should be "
            "available/initialized at this point."
        )
        cee_score: str_ = _meta_cee_score_to_xls_form(
            meta_cee_score=_get_term_node_txt(ctx.CEE_SCORE())
        )
        self._then_expr = cee_score


# =============================================================================
# PARSERS
# =============================================================================


def parse_question_scoring_logic(
    question: Question, else_expr: Expr | None
) -> Expr | None:
    ensure_not_none(question, "'question' MUST not be None.")
    if not question.scoring_logic:
        return None

    scoring_rules: Sequence[str] = question.scoring_logic.split(sep=";")
    scoring_expressions: Sequence[ListenerWalkResults] = tuple(
        _scoring_logic_txt_to_expr(question.id, rule)
        for rule in scoring_rules
    )

    # An assumption is made here that for every last question within a Section,
    # the question has multiple scoring rules delimited by a semicolon. That
    # is, for every last question within a Section, the expectation is that the
    # scoring_logic will be something like:
    #
    # 1. If >10% = Red ; If >5% and =<10%
    # 2. If >10% = Red ; If >5% and =<10% = Yellow; If <5% = Green
    # 3. etc
    #
    # The last 'rule' is then treated like the else, expression in the final
    # scoring logic expression.
    if not else_expr and len(scoring_expressions) < 2:
        err_msg: str = (
            "Error parsing the scoring logic for question {}. the 'else_expr' "
            "parameter is needed for questions with a single scoring "
            "rule/predicate.".format(question.id)
        )
        raise AssertionError(err_msg)

    return reduce(
        lambda _acc, _lwr: if_(
            condition=_lwr.conditional_expr,
            then=_lwr.then_expr,
            else_=_acc,
        ),
        reversed(
            scoring_expressions if else_expr else scoring_expressions[:-1]
        ),
        else_expr or scoring_expressions[-1].then_expr
    )


def parse_section_scoring_logic(section: Section) -> Expr | None:
    ensure_not_none(section, "'section' MUST not be None.")

    # An assumption is made here that sub-questions don't have scoring logic,
    # so only top level questions are parsed for scoring logic rules.
    return reduce(
        lambda _acc, _qtn: parse_question_scoring_logic(_qtn, _acc) or _acc,
        reversed(section.questions.values()),
        None
    )


# =============================================================================
# MODULE EXPORTS
# =============================================================================


__all__ = (
    "parse_question_scoring_logic",
    "parse_section_scoring_logic",
)