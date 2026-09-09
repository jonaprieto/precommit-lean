# precommit-lean

[pre-commit](https://pre-commit.com/) hooks for Lean 4 repositories.

## Problem

Lean repositories need repeatable style, axiom, and module-name checks without each project
rebuilding the same local tooling.

## Development

This project is maintained by its author with AI-assisted development tools.
Changes are reviewed, tested, and remain the maintainer's responsibility.

## Use

```yaml
repos:
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v6.0.0
  hooks:
  - id: trailing-whitespace
  - id: end-of-file-fixer
  - id: check-yaml

- repo: https://github.com/jonaprieto/precommit-lean
  rev: v0.1.6
  hooks:
  - id: lean-style
  - id: lean-modules
  - id: lean-axioms
    args:
    - --target=TermColor.Diagnostics.Properties
    - --namespace=TermColor.Diagnostics.Properties
  - id: lean-partiality
    args:
    - --allow-glob=TermColor/Terminal/Input.lean
```

The composite GitHub Action runs the same hooks after a Lean build:

```yaml
- uses: jonaprieto/precommit-lean/.github/actions/precommit@v0.1.6
  with:
    token: ${{ secrets.ECOSYSTEM_READ_TOKEN }}
```

`lean-style` checks line width, trailing whitespace, and tabs. `lean-modules` validates Lean
module paths. `lean-axioms` loads a configured Lake target and checks declaration dependencies.
`lean-partiality` reports partial definitions; an allowed path must have a nearby
`partiality:` rationale comment. Pass one `--allow-glob` per deliberately operational or
benchmark-only path; all other partial definitions fail the hook. `--ascii-only` is available for
projects that require ASCII source.

## Claude Code command

`.claude/commands/lean-format.md` is a `/lean-format` command for
[Claude Code](https://claude.com/claude-code). It reformats Lean 4 declarations to a
diff-minimizing signature layout: name alone on the keyword line, one binder per line
indented 4, a leading colon before the type, body indented 2, and aligned field columns.
The pass is whitespace-only, and checks itself by comparing token streams before and
after and by rejecting any hunk that removes more lines than it adds. Copy the file into
your own `.claude/commands/` to use it. It pairs with the `lean-style` hook, which
enforces the width and whitespace rules the layout assumes.

## License

Apache-2.0.
