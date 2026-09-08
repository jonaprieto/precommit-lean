# precommit-lean

Private [pre-commit](https://pre-commit.com/) hooks for Lean 4 repositories.

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

## License

Apache-2.0.
