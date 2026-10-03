"""Split a question into exact source slices, without interpreting its words."""
from __future__ import annotations

import re


_BREAK = re.compile(
    r'(?P<contrast>\b(?:even\s+though|but|yet|still|though|although)\b)'
    r'|(?P<sentence>[.!?]+["”’\']*(?=\s|$))'
    r'|(?P<line>\r?\n+)',
    re.IGNORECASE,
)


def split_question(question: str) -> tuple[str, ...]:
    """Keep each part verbatim, trimming only its outside whitespace.

    A contrast word is the separator. A sentence's closing punctuation stays
    with that sentence. Empty parts from repeated separators are omitted.
    """
    parts = []
    start = 0
    for match in _BREAK.finditer(question):
        end = match.end() if match.lastgroup == 'sentence' else match.start()
        part = question[start:end].strip()
        if part:
            parts.append(part)
        start = match.end()
    part = question[start:].strip()
    if part:
        parts.append(part)
    return tuple(parts)
