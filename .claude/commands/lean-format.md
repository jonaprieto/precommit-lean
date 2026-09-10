---
description: Reformat Lean 4 declarations to the project's diff-minimizing signature layout - name alone on the keyword line, one binder per line indented 4, leading colon, body indented 2, field and record columns aligned. Whitespace only, never changes meaning.
argument-hint: "[file, directory or glob to format; defaults to every .lean file in the project]"
allowed-tools: Read, Edit, Bash, Grep, Glob
---

Reformat Lean 4 declarations in $ARGUMENTS (default: every `.lean` file in the
project) to the layout below. This is a whitespace-only pass:
never rename anything, never reorder binders, never change a proof or a term.

## The layout

A declaration whose signature does not fit comfortably on one line is written as:

```
<keyword> <Name>
    [one instance binder]
    [one instance binder]
    {one implicit binder}
    (one explicit binder)
    : <type> :=
  <body>
```

The layout exists to make a later edit cost as few diff lines as possible. Every rule
below follows from that, and each one is measured, not assumed.

- The keyword and the name share the first line, with nothing else on it. This is what
  makes a declaration greppable as `^def Foo.bar` and stops the name being buried behind
  a run of instance binders.
- Signature continuation lines indent by **4**.
- The body indents by **2**. The contrast between 4 and 2 is what shows where the type
  ends and the body begins, so do not use 2 for both.
- **One binder per line.** Grouping binders means adding one rewrites the group: 1 added,
  1 removed. One per line makes it a pure insertion: 1 added, 0 removed.
- **The `: <type> :=` goes on its own line, colon leading.** With the colon trailing the
  last binder, appending a binder costs 2 added and 1 removed, because that line has to
  be split. With it on its own line the append is 1 added, 0 removed.
- **`where` starts its own line whenever the signature is already split across lines.** A
  header that fits on one line, such as `class PositionSpec (α : Type) where`, keeps it
  joined; splitting one is cheaper on a later binder insert, but those declarations do not
  gain binders, so it would be churn. Never join a `where` that is already on its own line.
- A declaration with no ascribed type puts a bare `:=` where the colon line would go, at
  the same indent 4, so the body still starts on its own line at indent 2.
- Instance binders come before value binders, keeping the order they already had.
- **Never join lines.** This pass only splits and re-indents. If a declaration is already
  spread over several lines, keep it spread and fix its indentation; do not pull it back
  onto one line. A declaration's line count must never go down.
- **One name per line inside a binder group, when the group is a parameter list.**
  `(Position Content Peer : Type)` groups three parameters on one line, so adding a fourth
  is a modify. Written as

  ```
  variable
    (
      Position
      Content
      Peer
      : Type
    )
  ```

  adding one is an insert. If a group is already vertical, leave it vertical. Short groups
  of statement-local variables are the exception - see below.
- Wrap at 100 columns.

This deviates from Mathlib, which puts a trailing `:` at the end of the last binder line.
That is the deliberate trade: Mathlib optimizes for vertical compactness, this optimizes
for diff size.

For `theorem`, put the hypotheses after the binders and let `:` start the conclusion,
following the same indents.

### Keep short groups of statement-local variables on one line

A binder group stays on one line when its names are variables local to this one
declaration rather than parameters of a family:

```
    {a b : α}
    (a b : Line Position Content Peer)
```

Splitting pays only when adding a name to the group is a pure insertion, and that holds
for a type parameter list: a structure can gain a fourth type parameter without any
existing proof changing, so one-per-line saves a rewritten line for free. It does not hold
for `{a b : α}` in `exists_middle`. A third variable there makes it a different theorem -
the hypotheses and the proof body both have to change - so the single line saved on the
binder group is noise beside the edit you were already making.

The vertical form also costs clarity at this size. The rest of the signature puts one
*binder* per line, so

```
    {
      a
      b
      : α
    }
```

reads at a glance as three binders when it is one. That ambiguity is worth paying for a
list that grows and is not worth paying for a pair that does not.

The test: split the group if it is the declaration's exported parameter list (`structure`,
`class`, `abbrev`, `inductive` type parameters). Leave it inline if the names appear only
inside this declaration's own statement.

## Instance binders: one order, and where they live

Instance binders are written in a single canonical order, so that `@`-applications and
explicit instance arguments line up across a family of declarations. Order by the type
parameter they constrain, following the parameter list itself (`Position`, `Content`,
`Peer`, `Tag`, `Key`), and within one parameter put the structural class before its
decidability companions:

```
    [PositionSpec Position]
    [DecidableEq Position]
    [DecidableLT Position]
    [LT Peer]
    [DecidableEq Peer]
    [DecidableLT Peer]
```

A top-level `variable` block carrying instances uses the same one-per-line layout, at
indent 2:

```
variable
  [PositionSpec Position]
  [LT Peer]
  [DecidableEq Peer]
```

Hoisting a shared instance set into a `variable` block is worth it when a contiguous run
of declarations needs *exactly* that set: adding a fourth class later is then one inserted
line rather than one per declaration. It is not a blanket win, because Lean 4.33 includes
section variables differently for definitions and for theorems:

- `def`, `abbrev`, `instance`, `structure` and `inductive` pick up an instance variable
  only when the declaration actually uses it.
- A `theorem` picks up **every** in-scope instance variable whose type mentions an
  included variable, used or not, and `linter.unusedSectionVars` fires with an
  `omit [C α] in` suggestion.

So a hoist that spans a theorem needing fewer instances over-generalizes that theorem's
statement. Scope the hoist with a named `section` around the run that genuinely shares the
set, and leave declarations with a
different set outside it with their binders written locally. Reach for `omit` only when
moving the declaration out of the section would break the file's reading order.

`namespace` scopes `variable` exactly as `section` does, and it is usually the block
already open at the top of the file. Use `section` when a run shares only binders, and
`namespace` when it also shares a name prefix. The two are not interchangeable for names: a
`section NormalLine` scopes variables and qualifies nothing, so `def setStatus` inside it is
`setStatus`, not `NormalLine.setStatus`, however much the section header suggests otherwise.
That is a live failure mode, because an unqualified sibling of `NormalLine.author` compiles
fine and is only noticed at the first call site. Pick one style per file, either
`namespace NormalLine` with bare names or dotted names written out, and never let a named
section imply a prefix it does not give.

A declaration that re-binds a type parameter explicitly - `abbrev Document (Position
Content Peer : Type)`, which needs explicit arguments at its use sites - shadows the
section variable, so the hoisted instances never reach it. It keeps its own copy.

## Align the field column

Inside a `structure`, `class`, `where`, or record body, pad each field name so that the
operator of every field in a run sits one column past the longest name in that run.
Declaration fields align on `:`:

```
class PositionSpec (α : Type) where
  ltPos     : α → α → Prop
  bottom    : α
  top       : α
  irrefl    : ∀ x, ¬ ltPos x x
  trans     : ∀ {a b c}, ltPos a b → ltPos b c → ltPos a c
  total     : ∀ a b, a ≠ b → ltPos a b ∨ ltPos b a
  bottom_lt : ∀ {x}, x ≠ bottom → ltPos bottom x
  lt_top    : ∀ {x}, x ≠ top → ltPos x top
  dense     : ∀ {a b}, ltPos a b → ∃ c, ltPos a c ∧ ltPos c b
```

Record fields align the same way on `:=`:

```
{ id          := line.fixed.id
  position    := p
  parentLeft  := l
  parentRight := r }
```

This is the one rule here that is not diff-minimizing, and it is a deliberate exception.
A new field whose name is longer than the current widest re-pads the whole run: N modified
lines to buy one insert. What it buys back is a column, so the fields can be read down the
page against each other, which is the whole point of a field block. The aesthetics win.
Five limits keep the cost bounded:

- **A run is a maximal block of consecutive field lines at the same indent, and it is
  homogeneous.** A blank line, a comment line, a differently indented line, or a line of
  the other kind all end the run, and the next run aligns independently. Breaking a wide
  block with a blank line is how you stop one long name from re-padding everything below
  it.
- **A field whose value is a `by` block or spans several lines is not a column entry.** It
  is left unpadded, as are the fields after it until a new run starts. In a `where` body
  that mixes single-line values with tactic proofs, the tactic fields fall outside the
  aligned run rather than terminating it half-padded.
- **One operator moves per line, and it is the leftmost one.** A field carrying a default
  (`retries : Nat := 3`) aligns on its `:`, never on its `:=`. Continuation lines of a
  wrapped type or value stay where they are, and the colons inside `inductive` constructor
  binders are left alone - those are not a column.
- **Never align inside a proof.** `obtain ⟨a, b⟩ := p`, `have h := _` and `let x := _` are
  tactic steps, not record fields. Tactic blocks keep their own indentation, as below.
- **Do not align a run whose padding would push any of its lines past 100 columns.** Leave
  that run single-spaced.

Field blocks are aligned whether or not the declaration carries instance binders. The
"convert only what pays" scope below governs signatures; it does not govern field columns.

Alignment is still pure whitespace, so both verification checks in the procedure hold: the
token streams match, and an alignment hunk adds exactly as many lines as it removes, which
the joined-lines check accepts.

## Scope: convert only what pays

Reformatting raises today's diff to lower tomorrow's, so it only pays on declarations
whose binder lists actually churn. Default to converting **only declarations that carry
instance binders**, since those are the ones that grow: in the project this came from,
`Ord Peer` became `LT Peer`, then gained `DecidableEq Peer`, then `DecidableLT Peer`,
rewriting a wrapped block each time.

Leave stable declarations alone even when they wrap. If the user names a wider scope in
$ARGUMENTS, follow it, but say how many declarations that touches before starting.

## Leave alone

- Declarations whose whole signature and body **already sit on one line**. `def
  Path.toList (p : Path) : List Segment := p.head :: p.tail` is worse as four lines. This
  is permission to leave a one-liner alone; it is never permission to collapse a
  multi-line declaration into one.
- Comment text, `namespace`/`end`, `import`, blank-line structure between declarations.
- Anything inside a proof body: tactic blocks keep their own indentation.

## Procedure

1. `lake build` first. If it is already red, stop and say so - you cannot tell a
   formatting break from a pre-existing one otherwise.
2. Pick the baseline for each file you will edit. Tracked and unmodified: use
   `git show HEAD:<file>`. Tracked but dirty, or untracked: copy the file to a scratch path
   first and compare against that, since `git show HEAD:<file>` fails on an untracked file
   and `git diff` reports nothing for one, so both checks below would pass vacuously.
3. Reformat, one file at a time.
4. `lake build` again. It must pass.
5. Compare token streams, since reflowing moves tokens across line boundaries and
   `git diff --ignore-all-space` reports those as real changes (it is not a usable check
   here):

   ```bash
   before=$(git show HEAD:<file> | tr -d '[:space:]' | shasum)   # or: < <baseline copy>
   after=$(tr -d '[:space:]' < <file> | shasum)
   ```

   The two hashes must match. If they differ you changed something you should not have -
   revert and try again. This shows the non-whitespace character stream is identical; it
   cannot see a token crossing into or out of a `--` comment's scope, which is why it is
   paired with step 6 rather than trusted alone.
6. Check that nothing was joined. Every hunk must add at least as many lines as it
   removes:

   ```bash
   git diff -U0 -- <file> |
     awk '/^@@/ { if (add<del && h!="") print h" JOINED"; h=$0; add=0; del=0; next }
          /^\+/ { add++ } /^-/ { del++ }
          END { if (add<del) print h" JOINED" }'
   ```

   Output here is a bug in the pass, with one exception: re-inlining a binder group under
   the short-group rule above does remove a line on purpose. Check each flagged hunk
   against that rule, and treat anything else it reports as a bug.
7. Report which declarations were reformatted and confirm all three checks.

Do not commit unless asked.
