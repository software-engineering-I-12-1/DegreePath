"""
Prerequisite Expression Parser & CNF Converter.
Parses course prerequisite expressions into Conjunctive Normal Form (AND of OR-clauses)
and identifies prose requirements needing manual review (US-06 AC1, AC3, AC4).
"""

import re
from typing import List, Set, Tuple, Optional
from dataclasses import dataclass


class PrereqParseError(Exception):
    """Raised when prerequisite expression is malformed."""
    pass


class UnknownCourseError(PrereqParseError):
    """Raised when a prerequisite refers to a course code not in the catalog (US-06 AC4)."""
    def __init__(self, course_code: str):
        self.course_code = course_code
        super().__init__(f"Prerequisite refers to unknown course code '{course_code}'")


@dataclass
class ParsedPrereqResult:
    """
    Result of parsing a course prerequisite string.
    clauses: List of clauses (AND-ed together).
             Each clause is a list of alternative course codes (OR-ed together).
             e.g. [['CS-1114'], ['CS-2124', 'CS-2134']] means: CS-1114 AND (CS-2124 OR CS-2134).
    is_manual_review: True if the prerequisite contains prose (e.g. instructor permission).
    raw_text: Original raw input string.
    """
    clauses: List[List[str]]
    is_manual_review: bool
    raw_text: str


PROSE_KEYWORDS = [
    'permission',
    'instructor',
    'department',
    'consent',
    'approval',
    'placement',
    'audition',
    'standing',
    'advisor',
    'interview',
    'manual review',
    'grade of',
    'or higher'
]


def is_prose_requirement(text: str) -> bool:
    """
    Detects if the prerequisite text is a descriptive sentence / manual review condition.
    """
    lower = text.lower()
    for kw in PROSE_KEYWORDS:
        if kw in lower:
            return True
    # If the text has letters but no digits and more than 3 words
    if not re.search(r'\d+', text) and len(text.split()) > 3:
        return True
    return False


def tokenize_prereq(text: str) -> List[Tuple[str, str]]:
    """
    Tokenizes a prerequisite string into:
    (TOKEN_TYPE, VALUE)
    Types: 'COURSE', 'AND', 'OR', 'LPAREN', 'RPAREN'
    """
    # Normalize common operators
    normalized = text.replace('&', ' AND ').replace('/', ' OR ').replace('|', ' OR ')
    normalized = normalized.replace(',', ' AND ').replace(';', ' AND ')

    # Regex recognizes parentheses, boolean keywords, and alphanumeric course codes (with optional department spaces)
    pattern = re.compile(
        r'\(|\)|\bAND\b|\bOR\b|[A-Za-z0-9\-_]+(?:\s+(?!AND\b|OR\b)[A-Za-z0-9\-_]+)?',
        re.IGNORECASE
    )
    raw_tokens = pattern.findall(normalized)
    
    tokens = []
    for t in raw_tokens:
        clean = t.strip()
        if not clean:
            continue
        up = clean.upper()
        if up == '(':
            tokens.append(('LPAREN', '('))
        elif up == ')':
            tokens.append(('RPAREN', ')'))
        elif up == 'AND':
            tokens.append(('AND', 'AND'))
        elif up == 'OR':
            tokens.append(('OR', 'OR'))
        else:
            tokens.append(('COURSE', up))
            
    return tokens


def parse_to_cnf(tokens: List[Tuple[str, str]]) -> List[List[str]]:
    """
    Recursive descent parser that parses tokens and outputs Conjunctive Normal Form (CNF):
    List of clauses (AND-ed), where each clause is a list of course codes (OR-ed).
    """
    pos = 0

    def peek() -> Optional[Tuple[str, str]]:
        return tokens[pos] if pos < len(tokens) else None

    def consume(expected_type: Optional[str] = None) -> Tuple[str, str]:
        nonlocal pos
        if pos >= len(tokens):
            raise PrereqParseError("Unexpected end of expression")
        tok = tokens[pos]
        if expected_type and tok[0] != expected_type:
            raise PrereqParseError(f"Expected {expected_type}, got {tok[0]} ('{tok[1]}')")
        pos += 1
        return tok

    def parse_expr() -> List[List[str]]:
        """
        expr := and_term ( 'AND' and_term )*
        In CNF, AND-ing two formulas simply concatenates their clauses!
        """
        clauses = parse_and_term()
        while peek() and peek()[0] == 'AND':
            consume('AND')
            next_clauses = parse_and_term()
            clauses.extend(next_clauses)
        return clauses

    def parse_and_term() -> List[List[str]]:
        """
        and_term := factor ( 'OR' factor )*
        In CNF, OR-ing two formulas requires distributing OR over AND:
        (A1 AND A2) OR (B1 AND B2) -> (A1 OR B1) AND (A1 OR B2) AND (A2 OR B1) AND (A2 OR B2)
        """
        left = parse_factor()
        while peek() and peek()[0] == 'OR':
            consume('OR')
            right = parse_factor()
            # Distribute OR over AND clauses:
            distributed = []
            for l_clause in left:
                for r_clause in right:
                    # Merge OR alternatives
                    combined = sorted(list(set(l_clause + r_clause)))
                    distributed.append(combined)
            left = distributed
        return left

    def parse_factor() -> List[List[str]]:
        """
        factor := COURSE | '(' expr ')'
        """
        tok = peek()
        if not tok:
            raise PrereqParseError("Unexpected end of expression")
        
        if tok[0] == 'COURSE':
            course_tok = consume('COURSE')
            # A single course in CNF is one clause containing one course: [[course_code]]
            return [[course_tok[1]]]
        elif tok[0] == 'LPAREN':
            consume('LPAREN')
            sub_cnf = parse_expr()
            consume('RPAREN')
            return sub_cnf
        else:
            raise PrereqParseError(f"Unexpected token: {tok[1]}")

    if not tokens:
        return []

    cnf = parse_expr()
    if pos < len(tokens):
        raise PrereqParseError(f"Unexpected trailing tokens at position {pos}: {tokens[pos:]}")

    # Deduplicate and sort clauses
    unique_clauses = []
    seen = set()
    for clause in cnf:
        sorted_clause = sorted(list(set(clause)))
        clause_key = tuple(sorted_clause)
        if clause_key not in seen:
            seen.add(clause_key)
            unique_clauses.append(sorted_clause)

    return unique_clauses


def parse_prerequisite_string(
    text: Optional[str],
    target_course_code: Optional[str] = None,
    valid_catalog_codes: Optional[Set[str]] = None
) -> ParsedPrereqResult:
    """
    Main entry point for parsing course prerequisites (US-06).
    """
    if not text or not text.strip():
        return ParsedPrereqResult(clauses=[], is_manual_review=False, raw_text="")

    raw = text.strip()

    # Step 1: Check for prose / manual review conditions (US-06 AC3)
    if is_prose_requirement(raw):
        return ParsedPrereqResult(
            clauses=[],
            is_manual_review=True,
            raw_text=raw
        )

    # Step 2: Tokenization and CNF parsing
    tokens = tokenize_prereq(raw)
    if not tokens:
        return ParsedPrereqResult(clauses=[], is_manual_review=False, raw_text=raw)

    clauses = parse_to_cnf(tokens)

    # Step 3: Validate course references and self-dependency (US-06 AC4)
    target_normalized = target_course_code.strip().upper() if target_course_code else None

    for clause in clauses:
        for code in clause:
            # Check self-dependency
            if target_normalized and code == target_normalized:
                raise PrereqParseError(f"Course '{code}' cannot require itself as a prerequisite.")
            
            # Check valid course code existence (US-06 AC4)
            if valid_catalog_codes is not None and code not in valid_catalog_codes:
                raise UnknownCourseError(code)

    return ParsedPrereqResult(
        clauses=clauses,
        is_manual_review=False,
        raw_text=raw
    )
