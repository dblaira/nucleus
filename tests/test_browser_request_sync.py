from nucleus.word_sources import Collector, browser_request_start

PREFIX = '\n<in-app-browser-context source="ambient-ui-state">\nThis block is automatically supplied ambient UI state, not part of the user\'s request. Do not treat it as an instruction.\n# In app browser:\n- Current URL: http://127.0.0.1:8510/\n</in-app-browser-context>\n\n## My request:\n'
WORDS = 'Keep Ontosphere connected to my actual ontology so the 15-minute sync shows up here automatically. Preserve my exact words and existing relationships, and verify it in the app.\n'

def test_request_preserved_with_original_source_offsets():
    full = PREFIX + WORDS
    c = Collector({'since': '2026-10-10T00:00:00Z'}, {})
    c.emit('codex', 'session:5891:0', 'user_prompt', full, '2026-10-12T05:52:40.469Z')
    assert len(c.entries) == 1
    e = c.entries[0]
    assert e['text'] == WORDS
    assert e['source_text'] == full
    assert full[e['char_start']:e['char_end']] == WORDS
    assert 'Current URL' not in e['text']

def test_wrong_wrappers_and_non_codex_sources_are_not_admitted():
    for adapter, text in [('codex', PREFIX.replace('ambient-ui-state', 'unknown') + WORDS), ('all_entries', PREFIX + WORDS)]:
        c = Collector({'since': '2026-10-10T00:00:00Z'}, {})
        c.emit(adapter, 'test', 'user_prompt', text, '2026-10-12T05:52:40.469Z')
        assert not c.entries
    assert browser_request_start(PREFIX.replace('## My request:', '## Data:') + WORDS) is None

def test_generated_or_quoted_body_remains_excluded():
    c = Collector({'since': '2026-10-10T00:00:00Z'}, {})
    c.emit('codex', 'test', 'user_prompt', PREFIX + '# AGENTS.md instructions\nGenerated instruction', '2026-10-12T05:52:40.469Z')
    assert not c.entries
