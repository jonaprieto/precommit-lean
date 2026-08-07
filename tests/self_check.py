from precommit_lean.modules import module_name, violations
from precommit_lean.style import ascii_violations


def main() -> None:
    assert module_name("TermColor/Diagnostics/Model.lean") == "TermColor.Diagnostics.Model"
    assert violations(["TermColor/Diagnostics/Model.lean", "bad-name.lean"])
    assert ascii_violations("Demo.lean", 1, "def α := 1") == [
        "Demo.lean:1:5: non-ASCII character U+03B1"
    ]


if __name__ == "__main__":
    main()
