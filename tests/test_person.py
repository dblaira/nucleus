from nucleus.person import adam_to_you, i_to_you, same_words, split_sentences


def test_his_sentences_are_cut_where_he_ended_them():
    text = "The lack of momentum.  It is a feeling of apathy, or boredom, or worse.  It means to stop what I am doing. Pause, and think BIGGER!"
    assert split_sentences(text) == ["The lack of momentum.", "It is a feeling of apathy, or boredom, or worse.",
                                     "It means to stop what I am doing.", "Pause, and think BIGGER!"]
    assert split_sentences("1. what do I want. 2. How would I think about it.  3. what done looks like.") == [
        "1. what do I want.", "2. How would I think about it.", "3. what done looks like."]
    assert split_sentences("A.I. agents suggest and add too many details. Otherwise FLOW is disrupted.") == [
        "A.I. agents suggest and add too many details.", "Otherwise FLOW is disrupted."]


def test_only_the_person_changes_in_his_own_sentence():
    his = "It means to stop what I am doing. Pause, and think BIGGER!"
    said = i_to_you(his)
    assert said == "It means to stop what you are doing. Pause, and think BIGGER!"
    assert same_words(his, said)
    assert i_to_you("Am I building a system or doing a task?") == "Are you building a system or doing a task?"
    assert i_to_you("Much of my stress comes from letting my focus narrow too sharply.") == \
        "Much of your stress comes from letting your focus narrow too sharply."
    assert "A.I. agents" in i_to_you("A.I. agents suggest too many details. That is my way of saying stay focused.")


def test_a_sentence_that_speaks_to_someone_else_is_not_turned():
    assert i_to_you("We're just working together. I write. You write. I build. you build.") is None


def test_a_record_about_him_is_said_to_him_and_the_verb_agrees():
    cases = {
        "Adam's mood drops hardest when tooling or setup blocks building, and lifts when something ships":
            "Your mood drops hardest when tooling or setup blocks building, and lifts when something ships",
        "Adam moves forward by default and experiences looking back as friction, so review and synthesis will not happen unless something does it for him automatically":
            "You move forward by default and experience looking back as friction, so review and synthesis will not happen unless something does it for you automatically",
        "'Borrowed motivation' is a warning sign Adam acts on: when the drive behind a project isn't his own, he pauses or kills it":
            "'Borrowed motivation' is a warning sign you act on: when the drive behind a project isn't your own, you pause or kill it",
        "Adam is deliberately narrowing his own role to only the things he is best at, and engineering everything else to be handed off":
            "You are deliberately narrowing your own role to only the things you are best at, and engineering everything else to be handed off",
        "Adam wants one hub that collects and combines the objective and subjective measurements of him":
            "You want one hub that collects and combines the objective and subjective measurements of you",
    }
    for about_him, to_him in cases.items():
        assert adam_to_you(about_him) == to_him
        assert same_words(about_him, to_him)


def test_his_quoted_words_inside_a_record_are_left_exactly():
    record = ('Adam starts with high energy but knows his discipline fades, so he purposely builds external rules like '
              '"if I can\'t say I can\'t play" and the Five Stop Signs to hold himself to plans')
    said = adam_to_you(record)
    assert '"if I can\'t say I can\'t play"' in said
    assert said.startswith("You start with high energy but know your discipline fades")


def test_a_proposal_written_by_an_agent_is_never_said_as_his():
    assert adam_to_you("AGENT PROPOSAL: When Adam explicitly says to do the work, agents should execute the task") is None


def test_same_words_catches_an_added_or_dropped_word():
    assert not same_words("Adam learns by shipping", "You learn by shipping fast")
    assert not same_words("Adam learns by shipping", "You learn")
