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
