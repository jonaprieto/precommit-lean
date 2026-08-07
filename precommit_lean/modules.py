import argparse
import re
import subprocess
import sys

from .style import repository_root

IDENTIFIER = re.compile(r"^[^\W\d]\w*'?$")


def module_name(filename: str) -> str:
    return ".".join(filename[:-5].split("/"))


def violations(files: list[str]) -> list[str]:
    result = []
    for filename in files:
        module = module_name(filename)
        for component in module.split("."):
            if not IDENTIFIER.fullmatch(component):
                result.append(
                    f"{filename}: invalid Lean module component {component!r}"
                )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    root = repository_root()
    files = subprocess.check_output(
        ["git", "ls-files", "--", "*.lean"], cwd=root, text=True
    ).splitlines()
    failures = violations(files)
    for failure in failures:
        print(failure)
    print(
        f"{'FAIL' if failures else 'OK'}: "
        f"{len(files)} Lean files, {len(failures)} module-path violations"
    )
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())

