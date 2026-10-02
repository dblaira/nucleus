"""Human Yes/No decisions. Only the approved file is read by the day picker."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time

from . import forms, forms_night, forms_patterns
from .store import Store


class Conflict(ValueError):
    """A stale page or an earlier decision; keep the existing evidence."""


def examples_for(store: Store, proposal_id: str) -> list[dict]:
    row = store.connection.execute(
        "SELECT r.examples_json FROM form_night_results r JOIN form_night_runs n ON n.id=r.run_id "
        "WHERE r.proposal_id=? AND r.reason IS NULL AND n.status='completed' "
        "ORDER BY n.finished DESC LIMIT 1", (proposal_id,)).fetchone()
    return json.loads(row[0]) if row else []


def version(proposal: dict, examples: list[dict], matches: list[dict]) -> str:
    raw = json.dumps([proposal['payload'], examples, matches], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def approved_form(proposal: dict) -> dict:
    return {**proposal['payload'], 'status': 'approved'}


def check_examples(proposal: dict, examples: list[dict], matches: list[dict]) -> None:
    form = {**proposal['payload'], 'status': 'proposed'}
    kinds = forms.load_kinds()
    reason = forms.check(form, kinds=kinds) or forms_patterns.check(form, kinds)
    if reason:
        raise forms.Refused(reason)
    if not examples or len(examples) > 3:
        raise forms.Refused('Saved examples are missing.')
    reason = forms_night.coverage_reason(matches)
    if reason:
        raise forms.Refused(reason)
    if examples != forms_night.diverse_examples(matches):
        raise forms.Refused('Saved examples differ from the measured answers.')
    for example in matches:
        try:
            filled = forms.preview(form, forms_night.restore_screen(example['screen']), kinds=kinds)
            if (filled is None or filled.text != example['text']
                    or [asdict(p) for p in filled.parts] != example['parts']):
                raise forms.Refused('Saved example differs from the form or its screen.')
        except (KeyError, TypeError, ValueError) as error:
            raise forms.Refused(f'Saved example cannot be checked: {error}') from error


def pending(store: Store, forms_path: Path) -> list[dict]:
    catalog = forms.load(forms_path)
    result = []
    for proposal in store.form_proposals():
        if proposal['status'] != 'proposed':
            continue
        # The file is authoritative, including a Yes whose receipt was interrupted.
        if approved_form(proposal) in catalog:
            continue
        examples = examples_for(store, proposal['id'])
        matches = forms_night.coverage_for(store, proposal['id'])
        fit_count, fit_word_count = forms_night.fit_counts(matches)
        reason = None
        try:
            check_examples(proposal, examples, matches)
        except forms.Refused as error:
            reason = str(error)
        result.append({**proposal, 'examples': examples, 'version': version(proposal, examples, matches),
                       'error': reason, 'fit_count': fit_count, 'fit_word_count': fit_word_count})
    return sorted(result, key=lambda p: (-p['fit_count'], int(p['number'][2:])
                  if re.fullmatch(r'F-[1-9][0-9]*', p['number'] or '') else float('inf')))


def _toml(value) -> str:
    if isinstance(value, dict):
        return '{ ' + ', '.join(f'{key} = {_toml(item)}' for key, item in value.items()) + ' }'
    return json.dumps(value, ensure_ascii=False)


def append_text(original: str, form: dict, catalog: list[dict]) -> str:
    """Preserve existing blocks and comments; replace only an empty root array."""
    if not catalog:
        original, count = re.subn(r'^forms[ \t]*=[ \t]*\[[ \t\r\n]*\][ \t]*(?=#|$)', '', original, count=1, flags=re.M)
        if count != 1:
            raise forms.Refused('Cannot add a form while preserving this file. Use forms = [] for an empty file.')
    lines = ['[[forms]]']
    lines += [f'{key} = {_toml(form[key])}' for key in ('number', 'sentence', 'status', 'author', 'date')]
    lines += ['[forms.when]'] + [f'{key} = {_toml(value)}' for key, value in form['when'].items()]
    return original.rstrip('\n') + '\n\n' + '\n'.join(lines) + '\n'


def write_atomic(path: Path, original: bytes, text: str) -> None:
    """Readers see the previous complete file or the new complete file."""
    fd, name = tempfile.mkstemp(prefix='.forms-', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as output:
            os.fchmod(output.fileno(), path.stat().st_mode & 0o777)
            output.write(text.encode('utf-8'))
            output.flush()
            os.fsync(output.fileno())
        forms.load(temporary)
        if path.read_bytes() != original:
            raise Conflict('Forms changed while saving. Reload the page.')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def decision_lock(store_path: Path, forms_path: Path):
    # Same database lock as the night pass, plus a lock for this branch's file.
    with store_path.with_suffix(store_path.suffix + '.forms.lock').open('a') as db_lock:
        fcntl.flock(db_lock, fcntl.LOCK_EX)
        with forms_path.with_suffix(forms_path.suffix + '.lock').open('a') as file_lock:
            fcntl.flock(file_lock, fcntl.LOCK_EX)
            yield


def decide(store_path: Path, forms_path: Path, proposal_id: str, choice: str, expected_version: str) -> str:
    if choice not in ('yes', 'no'):
        raise ValueError('Choose Yes or No.')
    with decision_lock(store_path, forms_path):
        store = Store(store_path)
        try:
            with store.connection:
                store.connection.execute('BEGIN IMMEDIATE')
                proposal = next((p for p in store.form_proposals() if p['id'] == proposal_id), None)
                if proposal is None:
                    raise Conflict('This form is no longer on this page.')
                examples = examples_for(store, proposal_id)
                matches = forms_night.coverage_for(store, proposal_id)
                if expected_version != version(proposal, examples, matches):
                    raise Conflict('This form changed. Reload the page before choosing.')
                catalog = forms.load(forms_path)
                approved = approved_form(proposal)
                already_written = approved in catalog
                if proposal['status'] == 'rejected':
                    if choice == 'no':
                        return proposal['number']
                    raise Conflict('This form was already rejected.')
                if proposal['status'] == 'approved' or already_written:
                    if choice == 'no':
                        raise Conflict('This form was already approved.')
                    if not already_written:
                        raise Conflict('The approved file changed. The earlier Yes is kept.')
                elif choice == 'no':
                    store.reject_form_proposal(proposal_id, 'Adam said no on /forms.', commit=False)
                    return proposal['number']
                else:
                    check_examples(proposal, examples, matches)
                    if any(f['number'] == approved['number'] for f in catalog):
                        raise Conflict('This form number already exists in forms.txt.')
                    original = forms_path.read_bytes()
                    write_atomic(forms_path, original, append_text(original.decode('utf-8'), approved, catalog))
                # Receipt follows the durable file. A retry can recover an interrupted
                # receipt without duplicating the block or changing Adam's decision.
                store.connection.execute(
                    'INSERT OR IGNORE INTO form_approvals(proposal_id,approved_at,forms_path) VALUES (?,?,?)',
                    (proposal_id, time.time(), str(forms_path)))
                return proposal['number']
        finally:
            store.connection.close()


def fires_when(when: dict) -> str:
    phrases = []
    answers = {'aligned': 'The answer is aligned', 'not_sure': 'The answer is not sure', 'dont_know': "The answer is I don't know"}
    if 'answer' in when:
        phrases.append(answers[when['answer']])
    for key, prefix in [('kinds_present', 'The rows include'), ('kinds_absent', 'The rows leave out')]:
        if key in when:
            phrases.append(prefix + ' ' + ' and '.join('“' + k + '”' for k in when[key]))
    for key, noun in [('record_count', 'row'), ('word_count', 'word')]:
        if key not in when:
            continue
        count = when[key]
        if type(count) is int:
            phrases.append(f'{count} {noun}' + ('' if count == 1 else 's'))
        elif 'min' in count and 'max' in count:
            phrases.append(f'{count["min"]} to {count["max"]} {noun}s')
        elif 'min' in count:
            phrases.append(f'At least {count["min"]} {noun}' + ('' if count['min'] == 1 else 's'))
        else:
            phrases.append(f'At most {count["max"]} {noun}' + ('' if count['max'] == 1 else 's'))
    if 'missing_links' in when:
        phrases.append('A word has missing links' if when['missing_links'] else 'Every word has links')
    return ' · '.join(phrases)
