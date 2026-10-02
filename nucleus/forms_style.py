"""Literal and filled-text vetoes. Checking never changes the saved wording."""
import re
import unicodedata

_NEGATIVE = re.compile(
    r"\b(?:not|cannot|can't|won't|ain't|no|never|neither|nor|without|unless|although|though|"
    r"however|but|yet|may|might|could|maybe|perhaps|possibly|probably|apparently|"
    r"uncertain|uncertainty|unlikely|lack|lacks|lacking|missing)\b|\b\w+n't\b", re.I)
_ABSTRACT = re.compile(
    r"\b(?:establish(?:es|ed|ing|ment|ments)?|claim(?:s|ed|ing)?|prerequisites?|"
    r"containments?|necessit(?:y|ies)|coexistence)\b", re.I)


def check(text: str) -> str | None:
    normalized = unicodedata.normalize('NFKC', text).replace('’', "'").replace('‘', "'")
    found = _NEGATIVE.search(normalized)
    if found:
        return 'negative or caveat: ' + found.group().lower()
    found = _ABSTRACT.search(normalized)
    if found:
        return 'blocked word: ' + found.group().lower()
    return None
