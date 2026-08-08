import sys
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from precommit_lean.modules import module_name, violations
from precommit_lean.partiality import violations as partiality_violations
from precommit_lean.style import ascii_violations


def main() -> None:
    assert module_name("TermColor/Diagnostics/Model.lean") == "TermColor.Diagnostics.Model"
    assert violations(["TermColor/Diagnostics/Model.lean", "bad-name.lean"])
    assert ascii_violations("Demo.lean", 1, "def α := 1") == [
        "Demo.lean:1:5: non-ASCII character U+03B1"
    ]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "Input.lean"
        source.write_text(
            "private partial def read : IO Unit := read\n", encoding="utf-8"
        )
        assert partiality_violations(root, ["Input.lean"], [])
        assert "needs a nearby" in partiality_violations(
            root, ["Input.lean"], ["Input.lean"]
        )[0]
        source.write_text(
            "-- partiality: retries external input until EOF\n"
            "private partial def read : IO Unit := read\n",
            encoding="utf-8",
        )
        findings = partiality_violations(root, ["Input.lean"], ["Input.lean"])
        assert len(findings) == 1 and "approved partiality" in findings[0]
        source.write_text("partial_fixpoint find : Nat := 0\n", encoding="utf-8")
        assert partiality_violations(root, ["Input.lean"], [])
    root = Path(__file__).resolve().parents[1]
    for module in ("precommit_lean.style", "precommit_lean.modules"):
        result = subprocess.run(
            [sys.executable, "-m", module, "precommit_lean/style.py"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr or result.stdout


if __name__ == "__main__":
    main()
