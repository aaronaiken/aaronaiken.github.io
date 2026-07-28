"""48pages side-door client for Python (spec §7).

Zero-knowledge stays intact: an API token is a *device* that wraps your master
key. This client derives the wrap-KEK from the token secret, fetches the sealed
wrap, unwraps the master key on THIS machine, verifies it, and encrypts/decrypts
everything locally. The server only ever sees ciphertext.

Byte-for-byte compatible with the app + the Node client (`clients/js/slip.mjs`):
HKDF-SHA256 for the key split, AES-256-GCM for the wrap + every record.

Scopes (set when the token is minted, Settings → THE SIDE DOOR):
  - `slip`  → capture() into the review queue
  - `read`  → read_page(), list_cabinet(), list_tasks()
  - `write` → write_page(), file_cabinet()/update_cabinet()/delete_cabinet()
A "capture only" token has just `slip`; a "full access" token has all three.

Deps: `cryptography` (AES-GCM + HKDF) and `requests` (HTTP) — both ubiquitous and
already present in the cockpit.

Usage (library):
    from slip import Slip
    nb = Slip(os.environ["SLIP_TOKEN"])          # "48p_<id>.<secret>"
    nb.capture("the half-formed thought from the drive home")   # needs `slip`
    page = nb.read_page()                                        # needs `read`
    nb.write_page(page + "\n\nanother line")                     # needs `write`

Usage (CLI — capture only):
    SLIP_TOKEN=48p_… python slip.py "call the arborist back re: the split oak"
    (override the API with SLIP_API_BASE, default https://api.48pages.app)
"""
from __future__ import annotations

import base64
import json
import os
import sys
from datetime import datetime, timezone

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Domain-separated HKDF info strings + the check plaintext — must match
# frontend/src/lib/crypto/params.ts exactly (they're the wire contract).
_WRAP_INFO = b"48pages-token-wrap-v1"
_AUTH_INFO = b"48pages-token-auth-v1"
_CHECK_PLAINTEXT = b"48pages-check-v1"
_TOKEN_PREFIX = "48p_"


def _b64d(s: str) -> bytes:
    return base64.b64decode(s)


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _b64url_to_bytes(s: str) -> bytes:
    # The token secret is base64url with padding stripped (encoding.ts).
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_token(token: str) -> tuple[str, bytes]:
    body = token[len(_TOKEN_PREFIX):] if token.startswith(_TOKEN_PREFIX) else token
    dot = body.find(".")
    if dot < 0:
        raise ValueError("Malformed 48pages token")
    return body[:dot], _b64url_to_bytes(body[dot + 1:])


def _hkdf(secret: bytes, salt: bytes, info: bytes) -> bytes:
    return HKDF(algorithm=SHA256(), length=32, salt=salt, info=info).derive(secret)


# ---- budget geometry (mirrors frontend/src/lib/budget.ts) -------------------
LINE_UNITS_PER_PAGE = 20
TOTAL_PAGES = 48
TRIAGE_PAGE = 39
TOTAL_LINE_UNITS = LINE_UNITS_PER_PAGE * TOTAL_PAGES  # 960


def _budget(line_units: int) -> dict:
    """Turn a measured line-unit count into the same budget shape the app shows.
    Pure arithmetic on shared constants — NOT a re-measurement (only an editor can
    measure); this just formats the one authoritative number every surface reads."""
    clamped = max(0, int(line_units))
    page = 1 if clamped <= 0 else min(TOTAL_PAGES, -(-clamped // LINE_UNITS_PER_PAGE))
    return {
        "line_units": clamped,
        "page": page,
        "pages_left": max(0, TOTAL_PAGES - page),
        "page_budget": TOTAL_PAGES,
        "fill": min(1.0, clamped / TOTAL_LINE_UNITS),
        "triage": page >= TRIAGE_PAGE,
        "full": clamped >= TOTAL_LINE_UNITS,
    }


# ---- ROLL: stub + task-split logic (ported from scraps.ts / tasks.ts) -------
import re

_STUB_ICON = {"rolled": "↑", "filed": "→", "torn": "✂", "gathered": "⤿"}
_LIST_MARKER = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")
_LEADING_CHECKBOX = re.compile(r"^\s*(?:[-*]\s+)?\[([ xX]?)\]\s?")


def _make_stub(verb: str, label: str) -> str:
    clean = re.sub(r"\s+", " ", label).strip()[:48] or "untitled"
    return f"{_STUB_ICON[verb]} {verb} · {clean}"


def _strip_checkbox(text: str):
    m = _LEADING_CHECKBOX.match(text)
    if not m:
        return text, False
    return text[m.end():].lstrip(), m.group(1).lower() == "x"


def _split_into_tasks(text: str) -> list:
    """A scrap → one task per non-empty line, list markers + checkboxes stripped."""
    out = []
    for line in text.split("\n"):
        bare = _LIST_MARKER.sub("", line.strip())
        clean, done = _strip_checkbox(bare)
        clean = clean.strip()
        if clean:
            out.append({"text": clean, "done": done})
    return out


def _replace_scrap_with_stub(text: str, start: int, end: int, stub: str) -> str:
    """Splice a scrap [start:end) out for its stub, tidying the surrounding blanks."""
    joined = text[:start] + stub + text[end:]
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    joined = re.sub(r"^\n+", "", joined)
    joined = re.sub(r"\n+$", "\n", joined)
    return joined


# ---- FILE: title/body + inline-tag derivation (ported from cabinet.ts/tags.ts)
_ATX_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_TAG_SCAN = re.compile(r"(^|[^\w#])#([a-z0-9][\w-]*)", re.I)


def _suggest_title_body(text: str) -> tuple:
    """First line as the title; a markdown heading becomes the title sans #, and
    is dropped from the body so the two don't duplicate. Mirrors cabinet.ts."""
    lines = text.split("\n")
    m = _ATX_HEADING.match(lines[0] if lines else "")
    if m:
        rest = lines[1:]
        while rest and rest[0].strip() == "":
            rest.pop(0)
        return m.group(2).strip()[:80], "\n".join(rest)
    return (lines[0] if lines else "")[:80], text


def _extract_tags(text: str) -> list:
    """Inline #tags, deduped + lowercased, in first-seen order."""
    seen, out = set(), []
    for m in _TAG_SCAN.finditer(text):
        tag = m.group(2).lower()
        if tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out


class Slip:
    """A side-door client bound to one API token. Capture, and (with read/write
    scopes) read + write the notebook the token unwraps."""

    def __init__(self, token: str, api_base: str | None = None):
        self.api = (
            api_base or os.environ.get("SLIP_API_BASE") or "https://api.48pages.app"
        ).rstrip("/")
        self.token_id, self._secret = _parse_token(token)
        self._kek: bytes | None = None
        self._auth_header: str | None = None
        self._master: bytes | None = None

    # -- key management --------------------------------------------------------

    # Derive the wrap-KEK + auth key from the token secret, once. The salt is the
    # token_id (utf-8). We present the auth key; the KEK never leaves this process.
    def _ensure_keys(self) -> None:
        if self._kek is not None:
            return
        salt = self.token_id.encode("utf-8")
        self._kek = _hkdf(self._secret, salt, _WRAP_INFO)
        auth_key = _hkdf(self._secret, salt, _AUTH_INFO)
        self._auth_header = f"Bearer {self.token_id}.{_b64(auth_key)}"

    def _headers(self) -> dict[str, str]:
        self._ensure_keys()
        return {"Authorization": self._auth_header, "Content-Type": "application/json"}

    # Fetch the sealed wrap, unwrap the master key on this device, verify it. Cached.
    def _master_key(self) -> bytes:
        if self._master is not None:
            return self._master
        self._ensure_keys()
        keys = self._get("/v1/tokens/keys")
        master = AESGCM(self._kek).decrypt(
            _b64d(keys["wrap_iv"]), _b64d(keys["wrapped_master_key"]), None
        )
        # Verify: master_key_check = iv(12) ‖ AES-GCM(master, "48pages-check-v1")
        chk = _b64d(keys["master_key_check"])
        if AESGCM(master).decrypt(chk[:12], chk[12:], None) != _CHECK_PLAINTEXT:
            raise ValueError("master-key check failed — token/wrap mismatch")
        self._master = master
        return master

    # -- record crypto (matches frontend/src/lib/crypto/record.ts) -------------

    def _seal(self, plaintext: str) -> dict:
        iv = os.urandom(12)
        ct = AESGCM(self._master_key()).encrypt(iv, plaintext.encode("utf-8"), None)
        return {"iv": _b64(iv), "ciphertext": _b64(ct)}

    def _open(self, iv_b64: str, ct_b64: str) -> str:
        return AESGCM(self._master_key()).decrypt(
            _b64d(iv_b64), _b64d(ct_b64), None
        ).decode("utf-8")

    # -- HTTP ------------------------------------------------------------------

    def _req(self, method: str, path: str, body: dict | None = None):
        r = requests.request(
            method, self.api + path, headers=self._headers(), json=body, timeout=15
        )
        r.raise_for_status()
        if r.status_code == 204 or not r.content:
            return None
        return r.json()

    def _get(self, path):
        return self._req("GET", path)

    def _post(self, path, body):
        return self._req("POST", path, body)

    def _put(self, path, body):
        return self._req("PUT", path, body)

    def _delete(self, path):
        return self._req("DELETE", path)

    # -- capture (scope: slip) -------------------------------------------------

    def capture(self, text: str) -> dict:
        """Encrypt `text` and append it to the notebook's capture queue."""
        return self._post("/v1/slip", self._seal(text))

    # -- page (scopes: read / write) -------------------------------------------

    def read_page(self) -> str | None:
        """The full page markdown, decrypted — or None for a fresh notebook."""
        row = self._get("/v1/page")
        if not row:
            return None
        return self._open(row["iv"], row["ciphertext"])

    def write_page(self, text: str, version: int = 1) -> None:
        """Encrypt + upload the whole page (last-writer-wins, like the app)."""
        self._put("/v1/page", {**self._seal(text), "version": version})

    # -- cabinet (scopes: read / write) ----------------------------------------

    def list_cabinet(self) -> list[dict]:
        """Every filed entry, decrypted to {id, title, body, tags, filedAt}."""
        out = []
        for row in self._get("/v1/cabinet") or []:
            p = json.loads(self._open(row["iv"], row["ciphertext"]))
            out.append(
                {
                    "id": row["id"],
                    "title": p.get("title", ""),
                    "body": p.get("body", ""),
                    "tags": p.get("tags", []),
                    "filedAt": p.get("filedAt"),
                }
            )
        return out

    def file_cabinet(self, title: str, body: str, tags: list[str] | None = None) -> dict:
        """File a new entry. Returns {id, title, body, tags, filedAt}."""
        payload = {
            "title": title,
            "body": body,
            "tags": list(tags or []),
            "filedAt": _now_iso(),
        }
        row = self._post("/v1/cabinet", self._seal(json.dumps(payload)))
        return {"id": row["id"], **payload}

    def update_cabinet(
        self, entry_id: str, title: str, body: str, tags: list[str] | None = None,
        filed_at: str | None = None,
    ) -> dict:
        """Re-seal + save an edited entry (title / body / tags)."""
        payload = {
            "title": title,
            "body": body,
            "tags": list(tags or []),
            "filedAt": filed_at or _now_iso(),
        }
        self._put(f"/v1/cabinet/{entry_id}", self._seal(json.dumps(payload)))
        return {"id": entry_id, **payload}

    def delete_cabinet(self, entry_id: str) -> None:
        self._delete(f"/v1/cabinet/{entry_id}")

    # -- tasks (scope: read) ---------------------------------------------------

    def list_tasks(self) -> list[dict]:
        """Every rolled task, decrypted to {id, text, done, rolledAt}."""
        out = []
        for row in self._get("/v1/tasks") or []:
            p = json.loads(self._open(row["iv"], row["ciphertext"]))
            out.append(
                {
                    "id": row["id"],
                    "text": p.get("text", ""),
                    "done": bool(p.get("done")),
                    "rolledAt": p.get("rolledAt"),
                }
            )
        return out

    def create_task(self, text: str, done: bool = False) -> dict:
        """Add a task directly (the raw create — see roll() for the full verb)."""
        payload = {"text": text, "done": done, "rolledAt": _now_iso()}
        row = self._post("/v1/tasks", self._seal(json.dumps(payload)))
        return {"id": row["id"], **payload}

    def update_task(
        self, task_id: str, text: str, done: bool = False, rolled_at: str | None = None
    ) -> dict:
        """Edit a task — check it done (flip `done`), rename it, etc. Re-seals the
        whole payload like the app; pass the current text back (from list_tasks)."""
        payload = {"text": text, "done": done, "rolledAt": rolled_at or _now_iso()}
        self._put(f"/v1/tasks/{task_id}", self._seal(json.dumps(payload)))
        return {"id": task_id, **payload}

    def delete_task(self, task_id: str) -> None:
        """Remove a task from the list."""
        self._delete(f"/v1/tasks/{task_id}")

    # -- usage / ink budget (scopes: read / write) -----------------------------

    def read_usage(self) -> dict | None:
        """The one authoritative ink budget — {line_units, page, pages_left, fill,
        triage, full}. None if nothing's been measured yet (show an empty gauge)."""
        row = self._get("/v1/usage")
        if not row:
            return None
        return _budget(int(self._open(row["iv"], row["ciphertext"])))

    def write_usage(self, line_units: int) -> None:
        """Persist a freshly-measured line-unit count (encrypted). Call this from an
        editor-bearing surface with `editor.contentHeight / 30` — never a guess."""
        self._put("/v1/usage", self._seal(str(int(line_units))))

    # -- ROLL (scope: write) ---------------------------------------------------

    def roll(self, page_text: str, scrap_text: str) -> dict:
        """The ROLL verb: a scrap leaves the page for the task list, and collapses
        to a one-line `↑ rolled ·` stub in place (so the book still fills). Creates
        one task per line; returns {tasks, page}. Pass the CURRENT page text (from
        your editor) and the exact scrap text to roll."""
        start = page_text.find(scrap_text)
        if start < 0:
            raise ValueError("scrap not found in page")
        items = _split_into_tasks(scrap_text)
        if not items:
            return {"tasks": [], "page": page_text}
        tasks = [self.create_task(it["text"], it["done"]) for it in items]
        stub = _make_stub("rolled", scrap_text.split("\n")[0])
        new_page = _replace_scrap_with_stub(page_text, start, start + len(scrap_text), stub)
        self.write_page(new_page)
        return {"tasks": tasks, "page": new_page}

    def file(
        self, page_text: str, scrap_text: str, tags: list | None = None,
        title: str | None = None,
    ) -> dict:
        """The FILE verb: copy a scrap into the cabinet, then collapse it to a
        `→ filed ·` stub on the page. Title defaults to the first line (heading sans
        #) — pass `title` to override (a native filing UI). Inline #tags seed the
        entry's tags (plus any passed). Returns {entry, page}. (Use file_cabinet()
        for FILE+KEEP — copy without stubbing the page.)"""
        start = page_text.find(scrap_text)
        if start < 0:
            raise ValueError("scrap not found in page")
        derived_title, body = _suggest_title_body(scrap_text)
        title = derived_title if title is None else title
        all_tags = _extract_tags(scrap_text) + list(tags or [])
        entry = self.file_cabinet(title, body, all_tags)
        stub = _make_stub("filed", title or (body.split("\n")[0] if body else ""))
        new_page = _replace_scrap_with_stub(page_text, start, start + len(scrap_text), stub)
        self.write_page(new_page)
        return {"entry": entry, "page": new_page}

    def tear(self, page_text: str, scrap_text: str) -> dict:
        """The TEAR verb: strike a scrap out — it collapses to a struck `✂ torn ·`
        stub in place. Nothing is copied anywhere; just a page write. Returns {page}."""
        start = page_text.find(scrap_text)
        if start < 0:
            raise ValueError("scrap not found in page")
        stub = _make_stub("torn", scrap_text.split("\n")[0])
        new_page = _replace_scrap_with_stub(page_text, start, start + len(scrap_text), stub)
        self.write_page(new_page)
        return {"page": new_page}


def main(argv: list[str]) -> int:
    text = " ".join(argv[1:]).strip()
    token = os.environ.get("SLIP_TOKEN")
    if not token or not text:
        print('usage: SLIP_TOKEN=48p_… python slip.py "your note"', file=sys.stderr)
        return 1
    out = Slip(token).capture(text)
    print("slipped ✓", out.get("id"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
