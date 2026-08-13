import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

from .style import repository_root


DECLARATION = re.compile(
    r"^\s*(?:(?:private|protected)\s+)*partial(?:\s+(?:def|fixpoint)|_fixpoint)\b"
)
RATIONALE = re.compile(r"partiality\s*:", re.IGNORECASE)


def files_from_git(root: Path) -> list[str]:
    return subprocess.check_output(
        ["git", "ls-files", "--", "*.lean"], cwd=root, text=True
    ).splitlines()


def is_allowed(filename: str, allow_globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in allow_globs)


def violations(
    root: Path, files: list[str], allow_globs: list[str]
) -> list[str]:
    result = []
    for filename in files:
        lines = (root / filename).read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, 1):
            if not DECLARATION.match(line):
                continue
            rationale = any(
                RATIONALE.search(previous)
                for previous in lines[max(0, line_number - 6) : line_number]
            )
            if is_allowed(filename, allow_globs) and rationale:
                result.append(
                    f"{filename}:{line_number}: approved partiality ({line.strip()})"
                )
            elif is_allowed(filename, allow_globs):
                result.append(
                    f"{filename}:{line_number}: allowed partiality needs a nearby "
                    "partiality: rationale"
                )
            else:
                result.append(
                    f"{filename}:{line_number}: partial definition; add a total "
                    "implementation or configure an explicit exception with a "
                    "nearby partiality: rationale"
                )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-glob",
        action="append",
        default=[],
        help="tracked Lean path allowed to retain partiality; repeat as needed",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Lean files to check; defaults to all tracked Lean files",
    )
    args = parser.parse_args()
    root = repository_root()
    files = args.files or files_from_git(root)
    findings = violations(root, files, args.allow_glob)
    for finding in findings:
        print(finding)
    failures = [finding for finding in findings if "approved partiality" not in finding]
    print(
        f"{'FAIL' if failures else 'OK'}: "
        f"{len(files)} Lean files, {len(findings)} partial definitions, "
        f"{len(failures)} requiring action"
    )
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
