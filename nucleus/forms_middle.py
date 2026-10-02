"""Plain-code middle-option fills from exact displayed words, records and gaps.

No model, dictionary, graph or database is consulted here. The narrow negative
exception is for copied screen evidence; older row forms keep their style veto.
"""
from __future__ import annotations

import json
import re
import unicodedata

from . import explain, forms_style
from .gate import unescape_label

SLOTS = frozenset({'meaning', 'record_quote', 'missing_why', 'missing_word', 'absent_kind'})
HEADS = (
    '{word} — “{meaning}” — and “{record_quote}” line up here',
    '{word}: “{meaning}” and “{record_quote}” line up here',
    'Here, {word} — “{meaning}” — and “{record_quote}” line up',
)
TAILS = {
    'missing_why': ', while {missing_why}',
    'missing_word': ', while {missing_word} has no links.',
    'absent_kind': ', while the rows leave out “{absent_kind}”.',
}
# Only an explicitly stated absence of record evidence. A mere negative,
# uncertainty, or lack of a personal feeling is not a missing-evidence line.
_ABSENCE = re.compile(
    r'(?:\b(?:the |his |your |these |those )?(?:records?|evidence)\b.{0,35}?'
    r'\b(?:do(?:es)? not|doesn[’\']t|don[’\']t)\s+'
    r'(?:show|say|tell|describe|measure|identify|cover|prove|give|name)\b|'
    r'\bno\s+(?:record|evidence)\b.{0,25}?\b(?:shows?|says?|tells?|describes?|measures?|identifies?|of|that|showing)\b|'
    r'\bthere is no evidence\b)', re.I)


def is_middle(form: dict) -> bool:
    from . import forms
    return any(blank in SLOTS for _, blank in forms._parts(form['sentence']))


def is_filled(filled) -> bool:
    return any(p.source.startswith(('screen.meanings[', 'screen.whys[', 'screen.missing_words['))
               for p in filled.parts)


def source_reason(text: str) -> str | None:
    reason = explain.check(text, [])
    if reason:
        return reason
    normalized = unicodedata.normalize('NFKC', text).replace('’', "'")
    found = forms_style._ABSTRACT.search(normalized)
    if found:
        return 'blocked word: ' + found.group().lower()
    if '\n' in text or '\r' in text:
        return 'not one paragraph'
    return None


def gap_span(why: str) -> tuple[int, int] | None:
    """An entire displayed clause, copied with its original case and punctuation."""
    if not isinstance(why, str):
        return None
    starts = [0] + [m.end() for m in re.finditer(r', but |; ', why)]
    for start in starts:
        clause = why[start:]
        # Do not turn a whole mixed positive/negative line into the missing half.
        if (_ABSENCE.match(clause) and ', but ' not in clause and '; ' not in clause
                and not re.search(r'\b(?:probably|perhaps|possibly|might|maybe)\b', clause, re.I)
                and source_reason(clause) is None):
            return start, len(why)
    return None


def check(form: dict, kinds: list[str]) -> str | None:
    from . import forms
    when = form['when']
    blanks = {b for _, b in forms._parts(form['sentence']) if b}
    if when.get('answer') != 'not_sure':
        return 'middle-option forms fire only on not_sure'
    if not {'word', 'meaning', 'record_quote'} <= blanks:
        return 'middle-option form needs exact word and record quotes'
    gaps = blanks & {'missing_why', 'missing_word', 'absent_kind'}
    if len(gaps) != 1:
        return 'middle-option form needs one displayed missing half'
    gap = next(iter(gaps))
    if gap == 'missing_why' and when.get('missing_why') is not True:
        return 'missing_why blank needs missing_why=true'
    if gap == 'missing_word' and when.get('missing_links') is not True:
        return 'missing_word blank needs missing_links=true'
    if gap == 'absent_kind' and len(when.get('kinds_absent', [])) != 1:
        return 'absent_kind blank needs one absent middle word'
    if form['sentence'] not in {head + TAILS[gap] for head in HEADS}:
        return 'middle-option sentence must join exact quotes and a displayed gap'
    # Counts have the same fail-closed gate for approved files as night proposals.
    for name in ('record_count', 'word_count'):
        if name in when:
            value = when[name]
            if type(value) is int or (isinstance(value, dict) and value.get('min') == value.get('max')):
                return 'exact counts refused'
            if not isinstance(value, dict) or 'min' not in value:
                return 'counts must be minimums or ranges'
    return None


def positive_half(why: str) -> bool:
    """The displayed why itself must say that this part fits the question."""
    prefix = why.split(', but ', 1)[0].split('; ', 1)[0]
    contrast = why[len(prefix):].lower()
    if 'rather than' in contrast:
        return False
    marker = re.search(r'\b(?:match(?:es)?|fits?|aligns?|supports?|shows?|connects?|defines?|'
                       r'describes?|names?|identifies?|points?|places?|makes?|separates?|'
                       r'distinguishes?|establishes?)\b', prefix, re.I)
    return bool(marker and gap_span(prefix) is None and
                not re.search(r"\b(?:not|no|never|cannot|can[’']t|couldn[’']t|doesn[’']t|don[’']t|isn[’']t|aren[’']t|won[’']t|unable to|fails? to|failed to|might|may|could|perhaps|possibly)\s+(?:\w+\s+){0,2}$", prefix[:marker.start()], re.I))


def from_visible(answer: str, words: list[dict], records: list[dict], text: str, kinds=None):
    """Recover only values printed in this answer; never enrich with today's data."""
    from . import forms
    kinds = forms.load_kinds() if kinds is None else kinds
    if not isinstance(text, str) or not isinstance(words, list) or not isinstance(records, list):
        raise forms.Refused('invalid visible answer')
    names = tuple(w['word'] for w in words)
    positive_words = [w['word'] for w in words if isinstance(w.get('why'), str)
                      and ('\n' + w['why'] + '\n' in '\n' + text + '\n')
                      and positive_half(w['why'])]
    meanings, whys, rows, missing = [], [], [], []
    # Only the leading meaning lines inside this word's own block, before
    # its why. A quoted phrase in a why or record never becomes a meaning.
    cursor = text.find('\n') + 1
    for entry in words:
        word, why = entry['word'], entry.get('why', '')
        boundary = text.find('\n' + why + '\n', cursor) if why else -1
        chunk = text[cursor:boundary] if boundary >= 0 else ''
        pattern = re.compile(r'(?:\A|\n)' + re.escape(word) + r' — “(.*?)”(?=\n|\Z)', re.S)
        if boundary >= 0:
            for found in pattern.finditer(chunk):
                meanings.append(forms.Meaning(word, found[1]))
            cursor = boundary + len(why) + 2
        elif not why:
            # Painted words can have an empty why. Their exact dictionary quotes
            # are supplied by the painter and still must be visibly printed.
            for quote in entry.get('meanings', []):
                rendered = f'{word} — “{quote}”'
                if isinstance(quote, str) and rendered in text:
                    meanings.append(forms.Meaning(word, quote))
    for entry in [*words, *records]:
        why = entry.get('why')
        if isinstance(why, str) and why and ('\n' + why + '\n' in '\n' + text + '\n'):
            if forms.Why(why) not in whys:
                whys.append(forms.Why(why))
    for record in records:
        quote = unescape_label(record['quote'])
        # Record quote must be a printed row, not a substring in a meaning/why.
        bound = []
        for word in names:
            for kind in kinds:
                rendered = f'{word} {kind} “{quote}”'
                if rendered in text and re.search(r'(?:\A|\n\n)(?:(?:\d+(?:\.\d+)?(?: · \d{4}-\d{2}-\d{2})?|\d{4}-\d{2}-\d{2}) — )?' + re.escape(rendered) + r'(?=\n|\Z)', text):
                    bound.append((word, kind))
        why = record.get('why', '')
        visible_why = any(w.text == why for w in whys)
        if len(bound) == 1:
            word, kind = bound[0]
        elif not bound and re.search(r'(?:\A|\n\n)(?:(?:\d+(?:\.\d+)?(?: · \d{4}-\d{2}-\d{2})?|\d{4}-\d{2}-\d{2}) — )?' + re.escape(f'“{quote}”') + r'(?=\n|\Z)', text):
            # Both positive halves are printed as fitting this question. Pair
            # their contents without creating a link or a middle word. The
            # middle frame says they "line up here", never word -> kind -> record.
            if not visible_why or not positive_half(why) or not positive_words:
                continue
            word, kind = positive_words[0], None
        else:
            continue
        rows.append(forms.Row(word, record.get('leaf') or record['id'], kind, quote))
    positive = set(positive_words) | {row.word for row in rows if row.kind is not None
               and row.kind not in {'rejects', 'contradicts', 'prevents', 'inhibits', 'constrains', 'limits'}}
    meanings = [m for m in meanings if m.word in positive]
    for word in names:
        # Explicit printed no-links wording only; absence in a model's selected
        # record list does not prove a word has no links.
        if any(re.fullmatch(re.escape(word) + r' has no links[.!]?', why.text) for why in whys):
            missing.append(word)
    screen = forms.Screen(answer, names, tuple(rows), bool(missing), tuple(meanings), tuple(whys), tuple(missing),
                          len(rows) == len(records) and all(row.kind is not None for row in rows))
    forms._check_screen(screen, kinds)
    return screen


def saved_screen(raw: dict, kinds: list[str]):
    payload = json.loads(raw['reply_json'])
    if not isinstance(payload, dict) or payload.get('answer') != 'not_sure':
        from . import forms
        raise forms.Refused('saved answer is not not_sure')
    return from_visible(payload['answer'], payload['words'], payload['records'], raw['text'], kinds)


_COMMON = frozenset("adam blair a an and are as at be because been being but by can do does for from had has have he her here him his how i if in into is it its me my no not of on or our she so than that the their them there these they this those to was we were what when where which who will with without you your".split())


def shared_words(meaning: str, quote: str) -> set[str]:
    """Exact displayed content words, not an inferred link or a synonym lookup."""
    def content(text):
        return {word for word in re.findall(r"[a-z]+", text.lower()) if len(word) > 1} - _COMMON
    return content(meaning) & content(quote)


def values(form, screen):
    """Choose whole exact sources; a missing slot makes a form miss, never guesses."""
    from . import forms
    gaps = []
    for i, why in enumerate(screen.whys):
        span = gap_span(why.text)
        if span:
            start, end = span
            gaps.append(forms.Part(why.text[start:end], f'screen.whys[{i}].text[{start}:{end}]'))
    blanks = {b for _, b in forms._parts(form['sentence']) if b}
    if 'missing_why' in blanks and not gaps:
        return None
    if 'missing_word' in blanks and not screen.missing_words:
        return None
    if 'absent_kind' in blanks and (not screen.middle_words_complete or not screen.rows or any(row.kind is None for row in screen.rows)):
        return None  # An incomplete middle-word display cannot prove an absent kind.
    choices = []
    for ri, row in enumerate(screen.rows):
        if row.quote is None or source_reason(row.quote):
            continue
        for mi, meaning in enumerate(screen.meanings):
            if (row.kind is None or meaning.word == row.word) and not source_reason(meaning.quote):
                if row.kind is None and len(shared_words(meaning.quote, row.quote)) < 2:
                    continue
                choices.append((len(forms._TOKEN.findall(meaning.quote + ' ' + row.quote)), mi, ri))
    for _, mi, ri in sorted(choices):
        meaning, row = screen.meanings[mi], screen.rows[ri]
        result = {
            'word': forms.Part(meaning.word, f'screen.words[{screen.words.index(meaning.word)}]'),
            'meaning': forms.Part(meaning.quote, f'screen.meanings[{mi}].quote'),
            'record_quote': forms.Part(row.quote, f'screen.rows[{ri}].quote'),
        }
        if 'missing_why' in blanks:
            result['missing_why'] = min(gaps, key=lambda p: (len(forms._TOKEN.findall(p.text)), len(p.text), p.source))
        if 'missing_word' in blanks:
            result['missing_word'] = forms.Part(screen.missing_words[0], 'screen.missing_words[0]')
        if 'absent_kind' in blanks:
            result['absent_kind'] = forms.Part(form['when']['kinds_absent'][0], 'form.when.kinds_absent[0]')
        # Keep original punctuation even when a quote contains a full stop. The
        # frame's final full stop does not duplicate the gap's displayed stop.
        filled = ''.join(literal + (result[blank].text if blank else '')
                         for literal, blank in forms._parts(form['sentence']))
        if source_reason(filled) is None:
            return result
    return None
