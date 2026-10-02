"""Plain-code middle-option fills from exact displayed words, records and gaps.

No model, dictionary, graph or database is consulted here. Source text stays
exact; vocabulary and style rules apply only to the author's joining frame.
"""
from __future__ import annotations

import json
import re
from .gate import unescape_label

PART_SLOTS = frozenset({'lined_up_part', 'open_part'})
SLOTS = frozenset({'meaning', 'record_quote', 'missing_why', 'missing_word', 'absent_kind'}) | PART_SLOTS
PART_FRAME = '“{lined_up_part}” lines up with {word}: “{meaning}”. “{open_part}” is still open.'
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


def is_graph_parts(form: dict) -> bool:
    """Only Adam's exact authorized frame receives the two-sentence exception."""
    return (form.get('sentence') == PART_FRAME and form.get('when', {}).get('answer') == 'not_sure'
            and form.get('when', {}).get('graph_parts') is True)


is_graph_part = is_graph_parts


def is_filled(filled) -> bool:
    return any(p.source.startswith(('screen.meanings[', 'screen.whys[', 'screen.missing_words[', 'screen.parts['))
               for p in filled.parts)


def source_reason(text: str) -> str | None:
    """A usable exact source, never a vocabulary or style judgment."""
    if not isinstance(text, str) or not text.strip():
        return 'empty source'
    return None


def graph_part_whys(parts, words=None) -> dict[str, str]:
    """Print the checked part sources; the same exact lines are checked on refill."""
    from . import forms
    parts = forms.restore_parts(parts)
    names = tuple(dict.fromkeys(word for part in parts for word in part.connected)) if words is None else words
    open_parts = [part for part in parts if not part.connected]
    result = {}
    for word in names:
        connected = [part for part in parts if word in part.connected]
        if connected:
            result[word] = ('you said ' + word + '. '
                            + ' '.join('“' + part.text + '” lines up here.' for part in connected)
                            + ((' ' + ' '.join('Your records do not show “' + part.text + '”.' for part in open_parts))
                               if open_parts else ''))
    return result


def _quoted_end(text: str, position: int) -> int | None:
    """End of one complete quoted source, including balanced nested quotes."""
    start, depth = position, 1
    while position < len(text) and depth:
        if text[position] == '“':
            depth += 1
        elif text[position] == '”':
            depth -= 1
        position += 1
    return position if not depth and position > start + 1 else None


def _quoted_question_gaps(text: str) -> bool:
    """Whole program clauses, with nested source quotes and no added assertion."""
    position = 0
    while position < len(text):
        opening = re.match(r'(?:Your|your) records do not show “', text[position:])
        if opening is None:
            return False
        position += opening.end()
        end = _quoted_end(text, position)
        if end is None or text[end:end + 1] != '.':
            return False
        position = end + 1
        if position == len(text):
            return True
        if text[position:position + 1] != ' ':
            return False
        position += 1
    return False


def _graph_gap_start(why: str) -> int | None:
    leading = re.match(r'you said [^\r\n]+?\. ', why)
    if leading is None:
        return None
    position = leading.end()
    while why[position:position + 1] == '“':
        end = _quoted_end(why, position + 1)
        if end is None or why[end:end + len(' lines up here. ')] != ' lines up here. ':
            return None
        position = end + len(' lines up here. ')
    return position if re.match(r'(?:Your|your) records do not show “', why[position:]) else None


def gap_span(why: str) -> tuple[int, int] | None:
    """An entire displayed clause, copied with its original case and punctuation."""
    if not isinstance(why, str):
        return None
    starts = [0] + [m.end() for m in re.finditer(r', but |; ', why)]
    # Graph-authored multipart why: split only its exact leading scaffold,
    # never arbitrary sentence punctuation inside Adam's quoted question.
    multipart = _graph_gap_start(why)
    if multipart is not None:
        starts.append(multipart)
    for start in starts:
        clause = why[start:]
        # The program's missing-question clause quotes the exact question part.
        # Words or punctuation inside that complete quote are source content,
        # never a hedge or a second assertion written into the joining frame.
        if _quoted_question_gaps(clause):
            return start, len(why)
        if re.match(r'(?:Your|your) records do not show “', clause):
            continue  # Never absorb another assertion after the complete quote.
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
    if blanks & PART_SLOTS:
        if when.get('graph_parts') is not True:
            return 'graph-part blanks need graph_parts=true'
        if form['sentence'] != PART_FRAME:
            return 'graph-part sentence must use the exact lined-up and open frame'
        for name in ('record_count', 'word_count'):
            if name in when:
                value = when[name]
                if type(value) is int or (isinstance(value, dict) and value.get('min') == value.get('max')):
                    return 'exact counts refused'
                if not isinstance(value, dict) or 'min' not in value:
                    return 'counts must be minimums or ranges'
        return None
    if 'graph_parts' in when:
        return 'graph_parts requires a graph-part form'
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


def from_visible(answer: str, words: list[dict], records: list[dict], text: str, kinds=None, *, parts=()):
    """Recover only values printed in this answer; never enrich with today's data."""
    from . import forms
    kinds = forms.load_kinds() if kinds is None else kinds
    if not isinstance(text, str) or not isinstance(words, list) or not isinstance(records, list):
        raise forms.Refused('invalid visible answer')
    graph_parts = forms.restore_parts(parts)
    for line in graph_part_whys(graph_parts).values():
        if '\n' + line + '\n' not in '\n' + text + '\n':
            raise forms.Refused('graph part source is not printed on the screen')
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
        boundary = (text + '\n').find('\n' + why + '\n', cursor) if why else -1
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
    positive.update(word for part in graph_parts for word in part.connected)
    meanings = [m for m in meanings if m.word in positive]
    for word in names:
        # Explicit printed no-links wording only; absence in a model's selected
        # record list does not prove a word has no links.
        if any(re.fullmatch(re.escape(word) + r' has no links[.!]?', why.text) for why in whys):
            missing.append(word)
    screen = forms.Screen(answer, names, tuple(rows), bool(missing), tuple(meanings), tuple(whys), tuple(missing),
                          len(rows) == len(records) and all(row.kind is not None for row in rows), graph_parts)
    forms._check_screen(screen, kinds)
    return screen


def saved_screen(raw: dict, kinds: list[str]):
    payload = json.loads(raw['reply_json'])
    if not isinstance(payload, dict) or payload.get('answer') != 'not_sure':
        from . import forms
        raise forms.Refused('saved answer is not not_sure')
    return from_visible(payload['answer'], payload['words'], payload['records'], raw['text'], kinds,
                        parts=payload.get('parts', ()))


_COMMON = frozenset("adam blair a an and are as at be because been being but by can do does for from had has have he her here him his how i if in into is it its me my no not of on or our she so than that the their them there these they this those to was we were what when where which who will with without you your".split())


def shared_words(meaning: str, quote: str) -> set[str]:
    """Exact displayed content words, not an inferred link or a synonym lookup."""
    def content(text):
        return {word for word in re.findall(r"[a-z]+", text.lower()) if len(word) > 1} - _COMMON
    return content(meaning) & content(quote)


def values(form, screen):
    """Choose whole exact sources; a missing slot makes a form miss, never guesses."""
    from . import forms
    if is_graph_parts(form):
        if screen.answer != 'not_sure' or len(screen.parts) < 2:
            return None
        open_index = next((i for i, part in enumerate(screen.parts) if not part.connected), None)
        if open_index is None:
            return None
        for pi, part in enumerate(screen.parts):
            for word in part.connected:
                if word not in screen.words:
                    continue
                for mi, meaning in enumerate(screen.meanings):
                    if meaning.word == word:
                        return {
                            'lined_up_part': forms.Part(part.text, f'screen.parts[{pi}].text'),
                            'word': forms.Part(word, f'screen.words[{screen.words.index(word)}]'),
                            'meaning': forms.Part(meaning.quote, f'screen.meanings[{mi}].quote'),
                            'open_part': forms.Part(screen.parts[open_index].text, f'screen.parts[{open_index}].text'),
                        }
        return None
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
