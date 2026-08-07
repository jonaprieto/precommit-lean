# precommit-lean

Private [pre-commit](https://pre-commit.com/) hooks for Lean 4 repositories.

## Use

Add this to a repository's `.pre-commit-config.yaml`:

```yaml
repos:
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v6.0.0
  hooks:
  - id: trailing-whitespace
  - id: end-of-file-fixer
  - id: mixed-line-ending
    args: [--fix=lf]
  - id: check-merge-conflict
  - id: check-added-large-files
  - id: check-case-conflict
  - id: check-symlinks
  - id: check-json
  - id: check-toml
  - id: check-yaml
  - id: check-xml
  - id: fix-byte-order-marker
  - id: check-executables-have-shebangs
  - id: detect-private-key

- repo: git@github.com:jonaprieto/precommit-lean
  rev: v0.1.0
  hooks:
  - id: lean-style
  - id: lean-axioms
    args:
    - --target=TermColor.Diagnostics.Properties
    - --namespace=TermColor.Diagnostics.Properties
    - --native=line_split_example
    - --native=fix_it_replaces_utf8_bytes
    - --native=fix_it_render_example
  - id: lean-modules
```

For an ASCII-only policy, add `args: [--ascii-only]` under `lean-style`.

`precommit-lean` owns Lean-specific checks; it does not fork generic hooks.
Consumers need SSH access to the private repository (or may substitute an
authenticated HTTPS URL). The Python hook has no third-party dependencies;
the semantic check itself runs in the target project's Lean toolchain.

The shared GitHub Actions setup is available as a composite action:

```yaml
- uses: jonaprieto/precommit-lean/.github/actions/precommit@v0.1.1
  with:
    token: ${{ secrets.ECOSYSTEM_READ_TOKEN || github.token }}
```

Pass `skip: lean-axioms` for a fast quality job and `hooks: lean-axioms`
after the repository's Lean build.

If Python is unavailable, standard `pre-commit` cannot run. Put the same Lean
driver behind a project-local Git hook or Lake tool instead; a generic
`language: system` hook cannot reliably locate the consumer project's Lake
artifacts from the hook checkout.

`lean-style` checks tracked Lean files for 100-column lines, trailing whitespace,
and tabs. `lean-axioms` builds a configured Lake target, imports the configured
module with Lean itself, and walks its declarations using `Lean.collectAxioms`.
It permits only `propext`, `Classical.choice`, `Quot.sound`, plus explicitly
named `native_decide` declarations. `lean-modules` checks that each `.lean` path
maps to valid dotted Lean module components. `--ascii-only` is intentionally
opt-in: normal Lean code uses Unicode notation and identifiers.
