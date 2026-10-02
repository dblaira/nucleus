import pytest

from nucleus.question_parts import split_question


@pytest.mark.parametrize('separator', ['but', 'yet', 'still', 'though', 'although', 'BUT', 'Although'])
def test_contrast_words_split_only_at_whole_words(separator):
    assert split_question('  ALPHA ' + separator + ' BETA?  ') == ('ALPHA', 'BETA?')


def test_word_fragments_do_not_split():
    question = 'butter, yeti, stillness, and thought are exact words.'
    assert split_question(question) == (question,)


def test_sentence_punctuation_and_inside_spacing_are_preserved():
    question = '  ALPHA  feels right! BETA is here? “A clear sign.”  Last part. '
    assert split_question(question) == ('ALPHA  feels right!', 'BETA is here?', '“A clear sign.”', 'Last part.')


def test_contrast_removes_only_the_separator_and_outside_spaces():
    assert split_question('ALPHA, but “I cannot tell.”') == ('ALPHA,', '“I cannot tell.”')


def test_newlines_are_sentence_breaks_and_do_not_create_empty_parts():
    assert split_question('ALPHA.\n\n  BETA\r\n but \n Still ALPHA?') == ('ALPHA.', 'BETA', 'ALPHA?')


def test_a_decimal_is_not_a_sentence_break():
    assert split_question('I tried 1.5 times, but BETA?') == ('I tried 1.5 times,', 'BETA?')


def test_empty_input_has_no_invented_part():
    assert split_question(' \n  ') == ()


def test_each_returned_part_is_an_exact_source_slice():
    question = 'Why “dependable output”? although I do not know how the app behaved.'
    for part in split_question(question):
        assert part in question
