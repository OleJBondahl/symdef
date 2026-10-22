"""No tracked file names an application that uses the toolkit (R459, D112).

Every word of every tracked text file is lowercased and hashed; a word whose SHA-256 is
listed is a failure. The hashes stand for two application names and their plural forms,
so this file spells neither. A possessive splits into the name and "s", so the name catches it.
"""

import hashlib
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNED = frozenset(
    {
        "01aa28fcf8c8ead78b7c2a4369b8015848e9d9dfeeff133289ffdb2cc819b254",
        "d51efe19f97fe25d099b3a56085aae219f9154b6b2278b70dcb3b00e40c20bdf",
        "24e96e9171edb34725e95db860f8d8659b7333b3d363411a65783443bdcb6861",
        "b53ebc9d2b1124dd0af080ac6e1ab3135035040b987ec40e6445f774c3fafaee",
        "f88fd5d38492f15bb99bd49224d5e443047cec09086521e4aa25c4dfd3ff9df1",
        "c237b623df962e71e9a27140a1e954a94bd33c348296420ba9830e021aee1166",
    }
)
WORD = re.compile(r"[a-z]+")


def _tracked() -> list[str]:
    out = subprocess.run(  # noqa: S603 - fixed argv, no user input
        [shutil.which("git") or "git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout
    return [p for p in out.decode().split("\0") if p]


def _hits(text: str) -> set[str]:
    return {
        w
        for w in set(WORD.findall(text.lower()))
        if hashlib.sha256(w.encode()).hexdigest() in BANNED
    }


def test_hits_catch_names_and_forms() -> None:
    """The scanner bites: it flags a banned word in prose, a path and a possessive."""
    probe = "".join(chr(c) for c in (102, 114, 97, 110, 115, 121, 115))
    assert _hits(f"see {probe.upper()}'s repo") == {probe}
    assert _hits("an application") == set()


def test_no_tracked_file_names_an_application() -> None:
    bad: dict[str, set[str]] = {}
    for rel in _tracked():
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        found = _hits(text) | _hits(rel)
        if found:
            bad[rel] = found
    assert not bad, f"files naming an application: {sorted(bad)}"
