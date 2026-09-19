"""Checks for the signature layout formatter.

Every case in CORPUS is a shape that broke the formatter at some point while it was
being applied to the Lean repositories, so each one is a regression test rather than
a hypothetical. `expected is None` means the input must be left exactly as it is.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from precommit_lean.format import convert_text

CORPUS: list[tuple[str, str, str | None]] = [
    (
        "a one-line declaration is left alone",
        "theorem trivial_eq (a : Nat) : a = a := rfl\n",
        None,
    ),
    (
        "binders, type operands and the assignment each get a line",
        "theorem add_comm_like (a : Nat) (b : Nat) : a + b = b + a := by\n  omega\n",
        "theorem add_comm_like\n"
        "    (a : Nat)\n"
        "    (b : Nat)\n"
        "    : a + b = b + a\n"
        "    := by\n"
        "  omega\n",
    ),
    (
        "modifiers and attributes stack above the keyword line",
        "@[simp] private def size (xs : List Nat) : Nat :=\n  xs.length\n",
        "@[simp]\n"
        "private\n"
        "def size\n"
        "    (xs : List Nat)\n"
        "    : Nat\n"
        "    :=\n"
        "  xs.length\n",
    ),
    (
        "a do block opens a body exactly as by does",
        "def emit (message : String) : IO Unit := do\n  IO.println message\n",
        "def emit\n"
        "    (message : String)\n"
        "    : IO Unit\n"
        "    := do\n"
        "  IO.println message\n",
    ),
    (
        "an arrow chain splits one operand per line",
        "def apply2 : Nat → Nat → Nat\n  | a, b => a + b\n",
        "def apply2\n"
        "    : Nat →\n"
        "      Nat →\n"
        "      Nat\n"
        "  | a, b => a + b\n",
    ),
    (
        "a let binding inside a statement owns its own assignment",
        "theorem uses_let (n : Nat) :\n"
        "    let doubled := n + n\n"
        "    doubled = 2 * n := by\n"
        "  omega\n",
        None,
    ),
    (
        "a record literal before the real tail does not end the header",
        "theorem with_record (k : Config) :\n"
        "    ({ k with retries := 3 } : Config).retries = 3 := rfl\n",
        "theorem with_record\n"
        "    (k : Config)\n"
        "    : ({ k with retries := 3 } : Config).retries = 3\n"
        "    := rfl\n",
    ),
    (
        "a declaration keyword inside a docstring is prose",
        "/-- Example:\n"
        "```lean\n"
        "def sample (a : Nat) : Nat := a\n"
        "```\n"
        "-/\n"
        "def real (a : Nat) : Nat := a\n",
        None,
    ),
    (
        "a bracket inside a string literal does not confuse the splitter",
        'theorem escape_stays (s : String) : s ++ "\\u001b[A" = s ++ "\\u001b[A" := rfl\n',
        None,
    ),
    (
        "a pipe continuation is not a pattern alternative",
        "def piped (xs : List Nat) : List Nat :=\n"
        "  xs |>.reverse\n"
        "     |>.take 3\n",
        "def piped\n"
        "    (xs : List Nat)\n"
        "    : List Nat\n"
        "    :=\n"
        "  xs |>.reverse\n"
        "     |>.take 3\n",
    ),
    (
        "a conversion that would pass 100 columns keeps the author's line breaks",
        "theorem wide (source : Source) (error : ParseError) :\n"
        "    (diagnostic source error).labels =\n"
        "      [Label.primary (Span.point 0 (min error.pos (Source.utf8Bytes source).size))\n"
        "        error.message] := by\n"
        "  rfl\n",
        "theorem wide\n"
        "    (source : Source)\n"
        "    (error : ParseError)\n"
        "    : (diagnostic source error).labels =\n"
        "      [Label.primary (Span.point 0 (min error.pos (Source.utf8Bytes source).size))\n"
        "        error.message]\n"
        "    := by\n"
        "  rfl\n",
    ),
]


def strip_space(text: str) -> str:
    return "".join(text.split())


def main() -> None:
    failures = 0
    for name, source, expected in CORPUS:
        produced, _ = convert_text(source)
        want = source if expected is None else expected
        if produced != want:
            failures += 1
            print(f"FAIL {name}\n--- want ---\n{want}\n--- got ---\n{produced}")
            continue

        # the formatter is whitespace-only
        assert strip_space(produced) == strip_space(source), name
        # and it never removes a line
        assert len(produced.split("\n")) >= len(source.split("\n")), name
        # and it never widens past the wrap column unless the input already did
        if max(map(len, source.split("\n"))) <= 100:
            assert max(map(len, produced.split("\n"))) <= 100, name
        # and running it again changes nothing
        again, _ = convert_text(produced)
        assert again == produced, f"not idempotent: {name}"

    if failures:
        raise SystemExit(f"{failures} of {len(CORPUS)} layout cases failed")
    print(f"format: {len(CORPUS)} cases pass, each idempotent and whitespace-only")


if __name__ == "__main__":
    main()
