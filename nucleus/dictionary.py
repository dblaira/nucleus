"""Adam's dictionary, used through its own product and read as it is on disk.

The product at /Users/adamblair/Documents/adams-language reads a sentence with
`npm run brief-json -- "<sentence>"` and returns JSON. Its code is not copied here.
meanings.txt is read for the list of his words so the gate can check that a word the
model names is really one of his. Each line is numbers, two spaces, an index, " = ",
then his words. The numbers are his: 1-26 letters, 27-36 digits, 37 space, then the
keyboard marks in the order of KEYBOARD-NUMBERS.md.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import DICTIONARY_ROOT

_NUMBER_TO_MARK: dict[int, str] = {}
for _i, _c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=1):
    _NUMBER_TO_MARK[_i] = _c
for _i, _c in enumerate("0123456789", start=27):
    _NUMBER_TO_MARK[_i] = _c
for _i, _c in enumerate([" ", "`", "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/", "~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "{", "}", "|", ":", '"', "<", ">", "?", "\n", "’"], start=37):
    _NUMBER_TO_MARK[_i] = _c


def word_from_numbers(numbers: str) -> str:
    out = []
    for part in numbers.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(_NUMBER_TO_MARK.get(int(part), "?"))
    return "".join(out)


@dataclass(frozen=True)
class Meaning:
    word: str
    identifier: str
    index: int
    text: str


def load_meanings(path: Path) -> list[Meaning]:
    meanings: list[Meaning] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        head, sep, text = line.partition(" = ")
        if not sep:
            continue
        numbers, _, index = head.rpartition("  ")
        try:
            meanings.append(Meaning(word=word_from_numbers(numbers), identifier=numbers.strip(), index=int(index), text=text))
        except ValueError:
            continue
    return meanings


def known_words(meanings: list[Meaning]) -> set[str]:
    return {m.word for m in meanings}


def meanings_for(meanings: list[Meaning], word: str) -> list[Meaning]:
    return [m for m in meanings if m.word == word]


def brief(question: str, root: Path = DICTIONARY_ROOT, timeout: float = 60.0) -> dict:
    """Run the product's own reader on the question. Returns its JSON as a dict."""
    completed = subprocess.run(
        ["npm", "run", "-s", "brief-json", "--", question],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    raw = completed.stdout.strip()
    if not raw:
        raise RuntimeError(f"The dictionary returned nothing. stderr: {completed.stderr.strip()[:400]}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"The dictionary did not return JSON: {raw[:200]}") from error
