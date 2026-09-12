import json
from pathlib import Path

from nucleus import twopass
from nucleus.model import ModelReply
from nucleus.store import Store
from nucleus import NUCLEUS_FILES
from nucleus.graph import load_graph

FLOW_ID = "conn-obs-fable5-2026-07-10-affect-work-momentum-compass"
FLOW_QUOTE = "Momentum is Adam's compass"


def reading():
    return {"said": "q", "numbers": "", "outcome": "no", "heSaidTheWordItself": [], "hisRoutesSentItHere": [],
            "anotherRouteWasPossible": [], "noMeaningAddedYet": [], "mustAskFirst": None, "stopped": None}


def test_halves_cover_every_accepted_record_once():
    graph = load_graph(NUCLEUS_FILES["graph"], NUCLEUS_FILES["ledger"])
    first, second = twopass.split_records(graph)
    accepted = [r for r in graph.records.values() if graph.is_accepted(r)]
    ids = [line.split(" | ")[0] for half in (first, second) for line in half.split("\n")[1:] if line]
    assert sorted(ids) == sorted(r.leaf for r in accepted)
    assert abs(first.count("\n") - second.count("\n")) <= 1


def test_two_passes_then_judge_through_the_gate(tmp_path: Path):
    seen = []
    found = {"answer": "aligned", "words": [{"word": "FLOW", "why": "Your word names the state asked about."}],
             "records": [{"id": FLOW_ID, "quote": FLOW_QUOTE, "why": "Your compass points at this."}], "possibility": []}
    nothing = {"answer": "dont_know", "words": [], "records": [], "possibility": []}

    def fake(prompt: str) -> ModelReply:
        seen.append(prompt)
        if "===== pass one found =====" in prompt:
            assert FLOW_ID + " |" in prompt and "FLOW = " in prompt
            return ModelReply("fake", "fake", json.dumps(found))
        if "first half" in prompt[:60]:
            return ModelReply("fake", "fake", json.dumps(found))
        return ModelReply("fake", "fake", json.dumps(nothing))

    result = twopass.ask("What is FLOW?", store=Store(tmp_path / "n.sqlite3"), model_call=fake, brief=lambda q: reading())
    assert result.status == "answered", result.reason
    assert len(seen) == 3
    assert result.answer == "aligned"
    assert "Your compass points at this." in result.text
    names = [s["name"] for s in result.steps]
    assert twopass.STEP_PASS_1 in names and twopass.STEP_PASS_2 in names and twopass.STEP_JUDGE in names
