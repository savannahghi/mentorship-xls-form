grammar SGHI_XLSForm;

/*
 * Parser Rules
 */

scoring_logic : ( if_bool_literal_equals_score
                | if_count_equals_score
                | if_comparison_equals_score
                | if_range_equals_score
                | if_selection_equals_score
                )
                ;
skip_logic : ( if_bool_literal_then_question
             | if_count_then_question
             | if_comparison_then_question
             )
             ;

if_bool_literal_equals_score : IF BOOLEAN EQUAL CEE_SCORE;
if_bool_literal_then_question : IF BOOLEAN COMMA THEN QUESTION; 
if_count_equals_score : IF DIGITS EQUAL CEE_SCORE;
if_count_then_question: IF DIGITS COMMA THEN QUESTION;
if_comparison_equals_score: IF comparison_expression EQUAL CEE_SCORE;
if_comparison_then_question: IF comparison_expression COMMA THEN QUESTION;
if_range_equals_score: IF range_expression EQUAL CEE_SCORE;
if_selection_equals_score: IF selection_expression EQUAL CEE_SCORE;

range_expression : DIGITS RANGE DIGITS;

comparison_expression : comparison_expression (AND | OR) comparison_expression
                      | ( GE | GT | LE | LT ) DIGITS PERCENT?
                      ;

selection_expression : selection_expression OR selection_expression
                     | SELECTION DIGITS
                     ;



/*
 * Lexer Rules
 */

// =======================================================================
// Fragments
// =======================================================================

fragment BOOLEAN_NO: 'N';
fragment BOOLEAN_YES: 'Y';
fragment CEE_SCORE_0: 'Gray' ;
fragment CEE_SCORE_G: 'Green';
fragment CEE_SCORE_R: 'Red';
fragment CEE_SCORE_Y: 'Yellow' ;
fragment DIGIT : [0-9];



// =======================================================================
// Literals
// =======================================================================

BOOLEAN: BOOLEAN_NO | BOOLEAN_YES;
CEE_SCORE: CEE_SCORE_0 | CEE_SCORE_G | CEE_SCORE_R | CEE_SCORE_Y;
DIGITS : DIGIT+;
PERCENT : '%';
QUESTION: ('Q' DIGITS);
SELECTION: '#';
WHITESPACE : (' ' | [\r\n\t]) -> skip;



// =======================================================================
// Seperators
// =======================================================================

COMMA : ',';
SEMI: ';';



// =======================================================================
// Key Words
// =======================================================================

IF : ('If' | 'if');
THEN: 'then';



// =======================================================================
// Operators
// =======================================================================

AND : 'and';
EQUAL : '=';
GE : ('>=' | '≥');
GT : '>';
LE : ('=<' | '≤');
LT : '<';
OR : 'or';
RANGE: '-';
