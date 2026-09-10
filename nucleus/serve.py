"""Port 8766. POST /ask, GET /ask/<id>, and one page that shows the steps as they run."""

from __future__ import annotations

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import ask as ask_module
from .store import Store

PORT = 8766
STEP_NAMES = [ask_module.STEP_QUESTION, ask_module.STEP_DICTIONARY, ask_module.STEP_NUCLEUS,
              ask_module.STEP_MODEL, ask_module.STEP_GATE, ask_module.STEP_ANSWER]

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>nucleus</title>
<style>
body{margin:0;background:#F8F4ED;color:#111;font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:18px;line-height:1.5}
.page{max-width:760px;margin:0 auto;padding:28px 18px 60px}
h1{font-size:30px;margin:0 0 16px}
form{display:flex;gap:10px;margin:0 0 26px}
input{flex:1;font-size:18px;padding:12px 14px;border:1px solid #CCB394;border-radius:8px;background:#fff}
button{font-size:18px;padding:12px 18px;border:0;border-radius:8px;background:#E60E44;color:#fff}
button:disabled{opacity:.5}
.steps{display:grid;gap:8px;margin:0 0 26px}
.step{display:grid;grid-template-columns:1fr 90px;align-items:baseline;padding:10px 14px;border-radius:8px;background:#EFEBE4;color:#999}
.step.running{background:#08172D;color:#F8F4ED}
.step.done{color:#111}
.step .t{text-align:right;font-variant-numeric:tabular-nums}
.answer{white-space:pre-wrap;font-size:19px}
.answer .first{font-size:26px;font-weight:700;margin:0 0 14px}
.more{display:none}
.more.open{display:block}
.reveal{margin-top:14px;font-size:18px;background:none;color:#111;border:1px solid #CCB394;padding:10px 16px}
.stop{color:#B00124;font-size:20px}
</style></head><body><div class="page">
<h1>nucleus</h1>
<form id="f"><input id="q" placeholder="Write your question" autocomplete="off"><button id="b">Ask</button></form>
<div class="steps" id="steps"></div>
<div id="answer" class="answer"></div>
</div>
<script>
const NAMES = %s;
const FOLD = 4;
const stepsEl = document.getElementById('steps'), answerEl = document.getElementById('answer');
let current = null, timer = null;
function render(data){
  stepsEl.innerHTML = '';
  const byName = {};
  (data.steps||[]).forEach(s => byName[s.name] = s);
  const now = Date.now()/1000;
  for (const name of NAMES){
    const s = byName[name];
    const el = document.createElement('div');
    let cls = 'step', t = '';
    if (s){ cls += s.finished ? ' done' : ' running'; t = ((s.finished||now) - s.started).toFixed(1) + ' s'; }
    el.className = cls;
    el.innerHTML = '<span>' + name + '</span><span class="t">' + t + '</span>';
    stepsEl.appendChild(el);
  }
  const a = data.answer;
  if (!a){ answerEl.innerHTML = ''; return; }
  if (a.status !== 'answered'){ answerEl.innerHTML = '<div class="stop">' + esc(a.status + ': ' + (a.text || a.gate_reason || '')) + '</div>'; return; }
  const lines = (a.text||'').split('\\n');
  const first = lines.shift();
  const blocks = []; let cur = [];
  for (const l of lines){ if (l === '' ) { if (cur.length) blocks.push(cur); cur = []; } else cur.push(l); }
  if (cur.length) blocks.push(cur);
  const shown = blocks.slice(0, FOLD), hidden = blocks.slice(FOLD);
  let html = '<div class="first">' + esc(first) + '</div>' + shown.map(b => esc(b.join('\\n'))).join('\\n\\n');
  if (hidden.length){
    html += '<div class="more" id="more">\\n\\n' + hidden.map(b => esc(b.join('\\n'))).join('\\n\\n') + '</div>';
    html += '<button class="reveal" id="reveal">▾ ' + hidden.length + ' more</button>';
  }
  answerEl.innerHTML = html;
  const r = document.getElementById('reveal');
  if (r) r.onclick = () => { document.getElementById('more').classList.add('open'); r.remove(); };
}
function esc(s){ return s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
async function poll(){
  if (!current) return;
  const r = await fetch('/ask/' + current); const data = await r.json();
  render(data);
  if (data.answer){ clearInterval(timer); timer = null; document.getElementById('b').disabled = false; }
}
document.getElementById('f').onsubmit = async (e) => {
  e.preventDefault();
  const q = document.getElementById('q').value.trim(); if (!q) return;
  document.getElementById('b').disabled = true; answerEl.innerHTML = '';
  const r = await fetch('/ask', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({question:q})});
  const data = await r.json(); current = data.question_id; render({steps:[]});
  timer = setInterval(poll, 500);
};
</script></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    store: Store

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            body = (PAGE % json.dumps(STEP_NAMES)).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path.startswith("/ask/"):
            question_id = path[len("/ask/"):]
            question = self.store.question(question_id)
            if question is None:
                self._json(404, {"error": "no such question"})
                return
            self._json(200, {"question": question, "steps": self.store.steps(question_id), "answer": self.store.answer(question_id)})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/ask":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("content-length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "the body is not JSON"})
            return
        question = str(payload.get("question", "")).strip()
        if not question:
            self._json(400, {"error": "write a question"})
            return
        question_id = self.store.new_question(question, "web")
        thread = threading.Thread(target=self._run, args=(question_id, question), daemon=True)
        thread.start()
        self._json(202, {"question_id": question_id})

    def _run(self, question_id: str, question: str) -> None:
        ask_module.ask(question, store=self.store, surface="web", question_id=question_id)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), format % args))


def main() -> None:
    Handler.store = Store()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"nucleus on http://127.0.0.1:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
