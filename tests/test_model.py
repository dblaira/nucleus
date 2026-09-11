from nucleus import model


def test_prompt_splits_into_his_files_and_this_question():
    prompt = "===== graph: x =====\nhis records\n" + model.NUCLEUS_MARKER + "\n{...}\n===== Adam's question =====\nWhat is FLOW?"
    head, turn = model.split_prompt(prompt)
    assert head == "===== graph: x =====\nhis records\n"
    assert turn.startswith(model.NUCLEUS_MARKER) and turn.endswith("What is FLOW?")
    assert model.nucleus_hash(head) == model.nucleus_hash(head) and model.nucleus_hash(head) != model.nucleus_hash(head + " ")


def test_a_prompt_without_the_nucleus_is_not_split():
    head, turn = model.split_prompt("just a line")
    assert head == "" and turn == "just a line"


def test_json_is_pulled_out_of_a_chatty_reply():
    assert model._extract_json('Here you go:\n```json\n{"answer": "dont_know"}\n```\n') == '{"answer": "dont_know"}'
