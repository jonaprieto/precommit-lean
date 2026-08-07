# precommit-lean

Private [pre-commit](https://pre-commit.com/) hooks for Lean 4 repositories.

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
  rev: v0.1.3
  hooks:
  - id: lean-style
  - id: lean-modules
  - id: lean-axioms
    args:
    - --target=TermColor.Diagnostics.Properties
    - --namespace=TermColor.Diagnostics.Properties
```

The composite GitHub Action runs the same hooks after a Lean build:

```yaml
- uses: jonaprieto/precommit-lean/.github/actions/precommit@v0.1.3
  with:
    token: ${{ secrets.ECOSYSTEM_READ_TOKEN }}
```

`lean-style` checks line width, trailing whitespace, and tabs. `lean-modules` validates Lean
module paths. `lean-axioms` loads a configured Lake target and checks declaration dependencies.
`--ascii-only` is available for projects that require ASCII source.

## License

Apache-2.0.
