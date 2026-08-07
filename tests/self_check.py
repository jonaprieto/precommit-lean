import subprocess
import sys
from pathlib import Path

from precommit_lean.modules import module_name, violations
from precommit_lean.style import ascii_violations


def main() -> None:
    assert module_name("TermColor/Diagnostics/Model.lean") == "TermColor.Diagnostics.Model"
    assert violations(["TermColor/Diagnostics/Model.lean", "bad-name.lean"])
    assert ascii_violations("Demo.lean", 1, "def α := 1") == [
        "Demo.lean:1:5: non-ASCII character U+03B1"
    ]
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
