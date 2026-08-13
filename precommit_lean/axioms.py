import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Lake target to build")
    parser.add_argument(
        "--namespace",
        required=True,
        help="Namespace printed by #print axioms, usually target or target without .Properties",
    )
    parser.add_argument(
        "--native",
        action="append",
        default=[],
        help="Declaration allowed to use native_decide axioms; repeat as needed",
    )
    parser.add_argument(
        "--module",
        action="append",
        help="Lean module to import; defaults to --target; repeat as needed",
    )
    args = parser.parse_args()

    modules = args.module or [args.target]
    module_pattern = r"[A-Za-z_][A-Za-z0-9_']*(\.[A-Za-z_][A-Za-z0-9_']*)*"
    if any(not re.fullmatch(module_pattern, module) for module in modules):
        print("axiom check failed: invalid --module name", file=sys.stderr)
        return 2

    root = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )

    result = subprocess.run(
        ["lake", "build", args.target], cwd=root, text=True, capture_output=True
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    sys.stdout.flush()
    sys.stderr.flush()
    if result.returncode:
        return result.returncode

    template = Path(__file__).with_name("axiom_driver.lean").read_text(encoding="utf-8")
    setup_path = root / ".lake" / "build" / "ir" / Path(*modules[0].split("."))
    setup_path = setup_path.with_suffix(".setup.json")
    if not setup_path.is_file():
        print(f"axiom check failed: missing Lake setup {setup_path}", file=sys.stderr)
        return 1
    setup = json.loads(setup_path.read_text(encoding="utf-8"))
    import_arts = setup.setdefault("importArts", {})
    for module in modules:
        olean = root / ".lake" / "build" / "lib" / "lean" / Path(*module.split("."))
        olean = olean.with_suffix(".olean")
        if not olean.is_file():
            print(f"axiom check failed: missing OLean {olean}", file=sys.stderr)
            return 1
        import_arts[module] = [[str(olean)]]
    setup["name"] = "PrecommitLean.AxiomDriver"
    setup["isModule"] = False
    driver = "\n".join(f"import {module}" for module in modules) + "\n" + template
    env = os.environ | {
        "PRECOMMIT_LEAN_NAMESPACE": args.namespace,
        "PRECOMMIT_LEAN_NATIVE": "\n".join(
            f"{args.namespace}.{name}" for name in args.native
        ),
        "PRECOMMIT_LEAN_MODULES": "\n".join(modules),
    }
    with tempfile.TemporaryDirectory(prefix="precommit-lean-") as directory:
        filename = Path(directory) / "axiom_driver.lean"
        filename.write_text(driver, encoding="utf-8")
        setup_filename = Path(directory) / "setup.json"
        setup_filename.write_text(json.dumps(setup), encoding="utf-8")
        result = subprocess.run(
            [
                "lake",
                "env",
                "lean",
                str(filename),
                "--setup",
                str(setup_filename),
            ],
            cwd=root,
            env=env,
            text=True,
        )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
