from pathlib import Path
import subprocess
import sys

MAX_COLUMNS = 100


def repository_root() -> Path:
    return Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )


def ascii_violations(filename: str, line_number: int, line: str) -> list[str]:
    return [
        f"{filename}:{line_number}:{column}: non-ASCII character U+{ord(character):04X}"
        for column, character in enumerate(line, 1)
        if not character.isascii()
    ]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ascii-only",
        action="store_true",
        help="reject non-ASCII characters in Lean paths and source",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Lean files to check; defaults to all tracked Lean files",
    )
    args = parser.parse_args()

    root = repository_root()
    files = args.files or subprocess.check_output(
        ["git", "ls-files", "--", "*.lean"], cwd=root, text=True
    ).splitlines()
    violations = []
    for filename in files:
        if args.ascii_only and not filename.isascii():
            violations.append(f"{filename}: non-ASCII path")
        for line_number, line in enumerate(
            (root / filename).read_text(encoding="utf-8").splitlines(), 1
        ):
            if len(line) > MAX_COLUMNS:
                violations.append(
                    f"{filename}:{line_number}: line is {len(line)} cols (>{MAX_COLUMNS})"
                )
            if line != line.rstrip():
                violations.append(f"{filename}:{line_number}: trailing whitespace")
            if "\t" in line:
                violations.append(f"{filename}:{line_number}: tab character")
            if args.ascii_only:
                violations.extend(ascii_violations(filename, line_number, line))

    for violation in violations:
        print(violation)
    print(
        f"{'FAIL' if violations else 'OK'}: "
        f"{len(files)} Lean files, {len(violations)} violations"
    )
    return bool(violations)


if __name__ == "__main__":
    sys.exit(main())
