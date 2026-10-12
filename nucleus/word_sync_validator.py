"""Offline Docker validator. Only the staged batch is mounted; no databases/keys."""
import hashlib
import json
from pathlib import Path

import pyshacl
import rdflib
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF
from word_sources import attribution_excluded, question_replies, owned_belief_quotes

B = Path("/batch")
U = Namespace("https://understood.app/ontology#")
SH = Namespace("http://www.w3.org/ns/shacl#")
P = "https://understood.app/ontology/connection/"
read = lambda n: json.loads((B / n).read_text())
sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
old = Graph().parse(B / "before-graph.ttl", format="turtle")
new = Graph().parse(B / "graph.ttl", format="turtle")
assert set(old) <= set(new), "Existing RDF was replaced or removed"
old_ledger, new_ledger = read("before-ledger.json"), read("ledger.json")
assert new_ledger[:len(old_ledger)] == old_ledger, "Earlier decisions changed"
manifest = read("sources.json")
assert len(new_ledger) - len(old_ledger) == len(manifest["entries"]) + len(manifest.get("quarantined", []))
for e in manifest.get("quarantined", []):
    assert attribution_excluded(e["source_text"]), "Quarantine lacks a deterministic source exclusion"
    assert sha(e["source_text"]) == e["source_sha256"]
    assert e["source_text"][e["char_start"]:e["char_end"]] == e["text"]
    s = URIRef(P + e["record_id"])
    assert (s, U.exactWords, Literal(e["text"])) in old
    assert (s, U.sourceAttribution, Literal("excluded_source_context")) in new
    decision = next(x for x in new_ledger[len(old_ledger):] if x["claim_id"] == e["record_id"])
    assert decision["claim"] == e["label"] and decision["decision"] == "rejected"
    assert decision["approval_basis"] == "source-authorship-correction"
for e in manifest["entries"]:
    assert sha(e["source_text"]) == e["source_sha256"]
    assert e["source_text"][e["char_start"]:e["char_end"]] == e["text"]
    assert sha(e["text"]) == e["text_sha256"]
    if ":owned-belief:" in e["identity"]:
        assert (e["char_start"], e["char_end"]) in owned_belief_quotes(e["source_text"]), "Quotation lacks explicit self-ownership"
    s = URIRef(P + e["record_id"])
    assert (s, RDF.type, U.SourceEntry) in new
    assert (s, U.exactWords, Literal(e["text"])) in new
    assert (s, U.label, Literal(e["label"])) in new
    assert not list(new.objects(s, U.strength)), "Invented strength"
    assert not list(new.objects(s, U.inLifeDomain)), "Invented classification"
    decision = next(x for x in new_ledger[len(old_ledger):] if x["claim_id"] == e["record_id"])
    assert decision["claim"] == e["label"] and decision["decision"] == "accepted"
    assert decision["approval_basis"] == "standing-exact-words-2026-10-10"
    if e["context"].get("complete_field") is not None:
        assert e["source_text"] in e["context"]["complete_field"]
    if e["context"].get("complete_reply_envelope") is not None:
        envelope = e["context"]["complete_reply_envelope"]
        assert sha(envelope) == e["context"]["reply_envelope_sha256"]
        replies = question_replies(envelope)
        reply = replies[e["context"]["reply_index"]]
        assert reply['answer'] == e['source_text']
        assert reply['questionItemId'] == e['context']['question_item_id']

shapes = Graph().parse(B / "shape.ttl", format="turtle")
source_shapes = Graph().parse(data='''
@prefix u: <https://understood.app/ontology#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
u:SourceEntryShape a sh:NodeShape ; sh:targetClass u:SourceEntry ;
 sh:property [ sh:path u:label ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:string ] ;
 sh:property [ sh:path u:exactWords ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:string ] ;
 sh:property [ sh:path u:sourceIdentity ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:string ] ;
 sh:property [ sh:path u:sourceRole ; sh:minCount 1 ; sh:maxCount 1 ; sh:in ("input" "question" "reflection") ] ;
 sh:property [ sh:path u:acceptedAt ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:dateTime ] ;
 sh:property [ sh:path <http://purl.org/dc/terms/created> ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:dateTime ] ;
 sh:property [ sh:path <http://www.w3.org/ns/prov#wasDerivedFrom> ; sh:minCount 1 ; sh:nodeKind sh:IRI ] .
''', format="turtle")
shapes += source_shapes


def validate(g):
    conforms, report, _ = pyshacl.validate(g, shacl_graph=shapes, inference="none")
    failures = sorted((str(report.value(r, SH.focusNode)), str(report.value(r, SH.resultPath)),
                       str(report.value(r, SH.value)), str(report.value(r, SH.sourceConstraintComponent)))
                      for r in report.subjects(RDF.type, SH.ValidationResult))
    return conforms, failures


before, after = validate(old), validate(new)
assert before[1] == after[1], "Introduced SHACL violations"
affected = Graph()
for e in manifest["entries"]:
    for triple in new.triples((URIRef(P + e["record_id"]), None, None)):
        affected.add(triple)
assert validate(affected)[0], "New source entries fail SHACL"
print(json.dumps({"status": "passed", "rdflib": rdflib.__version__, "pyshacl": pyshacl.__version__,
                  "exact_entries_checked": len(manifest["entries"]), "old_triples": len(old),
                  "generated_entries_quarantined": len(manifest.get("quarantined", [])),
                  "new_triples": len(new), "added_triples": len(new) - len(old),
                  "previous_RDF_and_decisions_preserved": True, "new_entries_conform": True,
                  "full_graph_conforms": after[0], "unchanged_preexisting_violations": after[1]}))
