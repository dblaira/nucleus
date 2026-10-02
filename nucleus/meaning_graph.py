"""An in-memory RDF document and forward asserted paths, built at service start.

The original graph/ledger checker remains the authority for record acceptance.
Source Turtle is read only. No OWL imports, reasoner, reverse edges or new meanings.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import threading
import time
from urllib.parse import quote

from rdflib import Dataset, Graph as RDFGraph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS
from rdflib.plugins.sparql import prepareQuery

from . import NUCLEUS_FILES
from .dictionary import Meaning
from .graph import Graph
from .store import Store, require_practice_copy

ACCEPTED_DIR = NUCLEUS_FILES['graph'].parent
UPPER_PATH = NUCLEUS_FILES['upper']
AXIOMS_PATH = Path('/Users/adamblair/Documents/Cowboyai-verified-live-deployment/ontology-promotion/generated/personal-authority-axioms-20260717.ttl')
EXCLUDED_FILE = 'accepted-graph (from github).ttl'
UNDERSTOOD = Namespace('https://understood.app/ontology#')
MG = Namespace('https://understood.app/nucleus/meaning-graph/')
ACCEPTED_RECORD = MG.acceptedRecord
FORWARD_EDGE = MG.forwardEdge
BUDGET_MS = 300.0
SPARQL_PARSE_LOCK = threading.RLock()
_SCHEMA_TYPES = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty,
                 OWL.Ontology, RDF.Property, RDFS.Class, RDFS.Datatype}
_METADATA_NAMES = {'provenanceSource', 'source', 'sourceHash', 'sourceCandidateId', 'reviewSurface',
                   'reviewDecision', 'derivedFrom', 'wasDerivedFrom', 'wasAttributedTo', 'seeAlso',
                   'isDefinedBy', 'hasVersion', 'isVersionOf'}


def word_node(word: str) -> URIRef:
    """Exact text is encoded, never normalized into a different word."""
    return URIRef('https://understood.app/nucleus/word/' + quote(word, safe=''))


def kind_node(kind: str) -> URIRef:
    return URIRef('https://understood.app/nucleus/middle-word/' + quote(kind, safe=''))


def source_paths(accepted_dir: Path = ACCEPTED_DIR, upper_path: Path = UPPER_PATH,
                 axioms_path: Path = AXIOMS_PATH) -> tuple[Path, ...]:
    accepted_dir = Path(accepted_dir).expanduser().resolve()
    if not accepted_dir.is_dir():
        raise ValueError('accepted Turtle directory must exist')
    files = [p.resolve() for p in sorted(accepted_dir.glob('*.ttl')) if p.name != EXCLUDED_FILE]
    if not files:
        raise ValueError('accepted Turtle directory has no source files')
    for extra in (upper_path, axioms_path):
        path = Path(extra).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f'missing meaning graph source: {path}')
        files.append(path)
    return tuple(dict.fromkeys(files))


def _instance_edges(graph: RDFGraph) -> set[tuple]:
    """Only asserted forward URI relations; schema and source metadata are not meaning paths."""
    schema_nodes = {s for s, _, o in graph.triples((None, RDF.type, None)) if o in _SCHEMA_TYPES}
    edges = set()
    for s, p, o in graph:
        if not isinstance(s, URIRef) or not isinstance(o, URIRef) or s in schema_nodes:
            continue
        if any(str(p).startswith(str(ns)) for ns in (RDF, RDFS, OWL, DCTERMS)):
            continue
        local = str(p).rsplit('#', 1)[-1].rsplit('/', 1)[-1]
        if local in _METADATA_NAMES:
            continue
        edges.add((s, p, o))
    return edges


def _check_export(output: Path, copy_path: Path, accepted_dir: Path, paths: tuple[Path, ...]) -> None:
    require_practice_copy(copy_path)
    copy_area, protected_area = copy_path.resolve().parent, accepted_dir.resolve().parent
    protected_files = tuple(dict.fromkeys((*paths, *(p.resolve() for p in accepted_dir.glob('*.ttl')))))
    if not output.is_relative_to(copy_area) or output == copy_area or output == copy_path.resolve():
        raise ValueError('derived graph export must stay inside the database copy area')
    for candidate in (output, output.with_name(output.name + '.tmp')):
        if not candidate.resolve().is_relative_to(copy_area):
            raise ValueError('derived graph export must stay inside the database copy area')
        if candidate.resolve().is_relative_to(protected_area):
            raise ValueError('source Turtle files are read only')
        if candidate.exists():
            require_practice_copy(candidate)
            if candidate.samefile(copy_path):
                raise ValueError('derived graph export cannot overwrite the database copy')
        if candidate in protected_files or (candidate.exists() and any(candidate.samefile(p) for p in protected_files)):
            raise ValueError('source Turtle files are read only')


@dataclass(frozen=True)
class Label:
    answer: str | None
    connected: tuple[str, ...]
    missing: tuple[str, ...]
    records: dict[str, tuple[str, ...]]
    ms: float
    budget_miss: bool

    def to_dict(self) -> dict:
        return asdict(self)


class MeaningGraph:
    def __init__(self, source: RDFGraph, source_hashes: dict[str, str], paths: tuple[Path, ...],
                 legacy_graph: Graph, meanings: list[Meaning], kinds: list[str]) -> None:
        self.legacy_graph = legacy_graph
        self.meanings = tuple(meanings)
        self.kinds = tuple(dict.fromkeys(kinds))
        self.known_words = frozenset(m.word for m in meanings)
        self.paths = paths
        self.graph = Dataset(default_union=True)
        for triple in source:
            self.graph.default_graph.add(triple)
        self._source_triples = set(source)
        self._source_edges = _instance_edges(source)
        self._lock = threading.RLock()
        labels: dict[str, set[URIRef]] = {}
        for predicate in (UNDERSTOOD.label, RDFS.label):
            for subject, value in source.subject_objects(predicate):
                if isinstance(subject, URIRef) and isinstance(value, Literal) and str(value) in self.known_words:
                    labels.setdefault(str(value), set()).add(subject)
        self.word_nodes = {word: next(iter(labels[word])) if len(labels.get(word, ())) == 1 else word_node(word)
                           for word in self.known_words}
        self.accepted_records = frozenset(URIRef(r.uri) for r in legacy_graph.records.values()
                                          if legacy_graph.is_accepted(r))
        self._fixed_derived = RDFGraph()
        for word, node in self.word_nodes.items():
            self._fixed_derived.add((node, RDFS.label, Literal(word)))
        for kind in self.kinds:
            self._fixed_derived.add((kind_node(kind), RDFS.label, Literal(kind)))
        for record in self.accepted_records:
            self._fixed_derived.add((record, ACCEPTED_RECORD, Literal(True)))
        for triple in self._fixed_derived:
            self.graph.default_graph.add(triple)
        self.relations = RDFGraph()
        for triple in self._source_edges:
            self.relations.add(triple)
        for record in self.accepted_records:
            self.relations.add((record, ACCEPTED_RECORD, Literal(True)))
        self.predicates = tuple(sorted({p for _, p, _ in self._source_edges} | {kind_node(k) for k in self.kinds}, key=str))
        # This adjacency index changes no relationship: each edge retains its exact
        # asserted predicate in forward_sources, and the full document is untouched.
        # A single predicate avoids testing every allowed predicate at every hop.
        self.forward = RDFGraph()
        self.forward_sources: dict[tuple[URIRef, URIRef], tuple[tuple, ...]] = {}
        self.path_query = ('SELECT DISTINCT ?record WHERE { ?start (' + FORWARD_EDGE.n3() + ')+ ?record . '
                           '?record ' + ACCEPTED_RECORD.n3() + ' true . }')
        with SPARQL_PARSE_LOCK:
            self._prepared = prepareQuery(self.path_query)
        self._link_triples: set[tuple] = set()
        self._links: dict[str, list[dict]] = {}
        self.stats = {'source_hashes': dict(source_hashes), 'source_files': len(paths),
                      'source_triples': len(source), 'source_relation_triples': len(self._source_edges),
                      'dictionary_words': len(self.known_words), 'accepted_records': len(self.accepted_records),
                      'build_ms': 0.0, 'link_triples': 0, 'triples': len(self.graph),
                      'rejected_links': [], 'link_refusal_reasons': {}, 'sparql_budget_ms': BUDGET_MS}
        self._output_path: Path | None = None
        self._export_config: tuple[Path, Path] | None = None
        self._refresh_forward()

    def word_node(self, word: str) -> URIRef:
        return self.word_nodes.get(word, word_node(word))

    def links_for(self, word: str) -> list[dict]:
        with self._lock:
            return [dict(link) for link in self._links.get(word, ())]

    def _refresh_forward(self) -> None:
        """Index only existing forward edges, retaining their exact source triples."""
        graph, origins = RDFGraph(), {}
        for s, p, o in self._source_edges | self._link_triples:
            graph.add((s, FORWARD_EDGE, o))
            origins.setdefault((s, o), []).append((s, p, o))
        for record in self.accepted_records:
            graph.add((record, ACCEPTED_RECORD, Literal(True)))
        self.forward = graph
        self.forward_sources = {pair: tuple(sorted(triples, key=lambda triple: tuple(map(str, triple))))
                                for pair, triples in origins.items()}

    def asserted_path(self, word: str, record: str) -> tuple[tuple, ...]:
        """One shortest path of original triples for inspection; no invented predicates."""
        from collections import deque
        start, end = self.word_node(word), URIRef(record)
        with self._lock:
            queue, seen = deque([(start, ())]), {start}
            while queue:
                node, steps = queue.popleft()
                for target in sorted(self.forward.objects(node, FORWARD_EDGE), key=str):
                    edge = self.forward_sources[(node, target)][0]
                    path = (*steps, edge)
                    if target == end:
                        return path
                    if target not in seen:
                        seen.add(target)
                        queue.append((target, path))
        return ()

    def refresh_links(self, store: Store) -> None:
        """Refresh explicit copy links after a thumb; ontology triples remain untouched."""
        store.require_practice_copy()
        started = time.perf_counter()
        triples, links, refused = set(), {}, []
        rows = store.connection.execute(
            'SELECT word,record,quote,why,source,provider,model,found_at,thumb,kind FROM links ORDER BY word,record')
        for word, record_id, text, why, source, provider, engine, found_at, thumb, kind in rows:
            reason = None
            record = self.legacy_graph.find(record_id)
            if thumb == 0:
                reason = 'thumbed down'
            elif word not in self.known_words:
                reason = 'unknown dictionary word'
            elif kind not in self.kinds:
                reason = 'unknown middle word'
            elif record is None or not self.legacy_graph.is_accepted(record):
                reason = 'record is not accepted'
            elif not isinstance(text, str) or not self.legacy_graph.quote_is_in(record, text):
                reason = 'quote is not exact'
            if reason:
                refused.append({'word': word, 'record': record_id, 'reason': reason})
                continue
            triple = (self.word_node(word), kind_node(kind), URIRef(record.uri))
            triples.add(triple)
            links.setdefault(word, []).append({'word': word, 'record': record.leaf, 'quote': text, 'why': why,
                'source': source, 'provider': provider, 'model': engine, 'found_at': found_at, 'thumb': thumb, 'kind': kind})
        with self._lock:
            for triple in self._link_triples - triples:
                if triple not in self._source_triples:
                    self.graph.default_graph.remove(triple)
                if triple not in self._source_edges:
                    self.relations.remove(triple)
            for triple in triples:
                self.graph.default_graph.add(triple)
                self.relations.add(triple)
            self._link_triples, self._links = triples, links
            self._refresh_forward()
            self.stats.update(link_triples=len(triples), triples=len(self.graph), rejected_links=refused,
                              link_refusal_reasons=dict(Counter(r['reason'] for r in refused)),
                              refresh_ms=round((time.perf_counter() - started) * 1000, 3))
            if self._output_path is not None:
                self._export(self._output_path)

    def label(self, words: list[str] | tuple[str, ...]) -> Label:
        """Each touched word must reach an accepted record along a forward SPARQL path."""
        started = time.perf_counter()
        ordered = tuple(dict.fromkeys(words))
        records = {}
        with self._lock:
            for word in ordered:
                if word not in self.known_words or self._prepared is None:
                    continue
                reached = tuple(sorted({str(row.record) for row in self.forward.query(
                    self._prepared, initBindings={'start': self.word_node(word)})}))
                if reached:
                    records[word] = reached
        connected = tuple(word for word in ordered if word in records)
        missing = tuple(word for word in ordered if word not in records)
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        missed = elapsed > BUDGET_MS
        answer = None if missed else ('aligned' if connected and not missing else 'not_sure' if connected else 'dont_know')
        return Label(answer, connected, missing, records, elapsed, missed)

    def _export(self, path: Path) -> None:
        if self._export_config is None:
            raise ValueError('derived graph export requires a database copy')
        copy_path, accepted_dir = self._export_config
        _check_export(path, copy_path, accepted_dir, self.paths)
        derived = RDFGraph()
        derived += self._fixed_derived
        for triple in self._link_triples:
            derived.add(triple)
        # Replace only this derived copy artifact; never a source Turtle document.
        temporary = path.with_name(path.name + '.tmp')
        temporary.write_text(derived.serialize(format='turtle'), encoding='utf-8')
        temporary.replace(path)


def build(store: Store | None, legacy_graph: Graph, meanings: list[Meaning], kinds: list[str], *,
          accepted_dir: Path = ACCEPTED_DIR, upper_path: Path = UPPER_PATH,
          axioms_path: Path = AXIOMS_PATH, output_path: Path | None = None) -> MeaningGraph:
    """Build once explicitly. Source-only loading needs no database; copied links do."""
    started = time.perf_counter()
    if store is not None:
        store.require_practice_copy()
    paths = source_paths(accepted_dir, upper_path, axioms_path)
    accepted_dir = Path(accepted_dir).expanduser().resolve()
    output = None
    if output_path is not None:
        if store is None:
            raise ValueError('derived graph export requires a database copy')
        output = Path(output_path).expanduser().resolve()
        _check_export(output, Path(store.path).expanduser().resolve(), accepted_dir, paths)
        output.parent.mkdir(parents=True, exist_ok=True)
    source, hashes = RDFGraph(), {}
    for path in paths:
        raw = path.read_bytes()
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        try:
            source.parse(data=raw, format='turtle', publicID=path.as_uri())
        except Exception as error:
            raise ValueError(f'meaning graph source refused: {path}: {error}') from error
    built = MeaningGraph(source, hashes, paths, legacy_graph, meanings, kinds)
    if store is not None:
        built.refresh_links(store)
    # Warm the query implementation at startup; every label still executes SPARQL.
    if built._prepared is not None:
        list(built.forward.query(built._prepared, initBindings={'start': URIRef(MG.startupProbe)}))
    if output is not None:
        built._output_path = output
        built._export_config = (Path(store.path).expanduser().resolve(), accepted_dir)
        built._export(output)
    built.stats['build_ms'] = round((time.perf_counter() - started) * 1000, 3)
    return built
