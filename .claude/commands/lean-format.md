---
name: lean-format
description: Reformat Lean 4 declarations to a diff-minimizing layout - name alone on the keyword line, one binder group per line, leading colon, aligned columns. Whitespace only, never changes meaning. Use in projects that already follow this layout, and when writing new declarations there.
allowed-tools: Read, Edit, Bash, Grep, Glob
---

# Lean 4 diff-minimizing format

A layout for Lean 4 declarations that optimizes for the size of the *next* diff rather
than for the size of the file. It is not Mathlib style, and every difference is
deliberate. The operational rules come first; the cost model, what the layout costs, and
the case against it are at the end. Rationale appears inline where a rule would otherwise
look arbitrary.

Every Lean snippet below is copied from a formalization that builds under this layout.
Some are cut short after the part being discussed, but nothing is retyped, with two
exceptions: the elided record literal, and the hand-packed "Compact" signature in the cost
model.

## When to use, when not

Use it when the target project has already adopted this layout. It is the better trade
while a formalization is under construction and its typeclass discipline is still moving,
because every review there is a diff review.

Do not use it when:

- The project follows Mathlib style, even if asked. Mathlib's conventions win inside
  Mathlib and in anything that upstreams to it. Say so and stop, rather than converting.
- The project has stabilized and is now read far more than it is patched. Packed
  signatures cost less to read; see "The case against".
- There is no cheap way to typecheck the result (Procedure step 1). A formatting pass you
  cannot verify is a refactor you cannot verify.

## The layout

```
<docstring>
<attributes>
<modifier>
<keyword> <Name>
    [instance binder]
    [instance binder]
    {implicit binder}
    (explicit binder)
    (hypothesis)
    : ∀ <bound>,
      <premise> →
      <premise> →
      <conclusion>
    :=
  <body>
```

- The keyword and the name share the first line, with nothing else on it. Attributes and
  docstrings go above it. The point is that the line carrying the name is not rewritten by
  a binder change, so `git blame` on the name keeps pointing at the commit that introduced
  the declaration.
- Each modifier gets its own line above the keyword, in the order written:
  `private`, `protected`, `noncomputable`, `partial`, `unsafe`, `scoped`, `local`. So

  ```lean
  noncomputable
  def localHistory
  ```

  not `noncomputable def localHistory`. Marking an existing declaration `noncomputable` or
  `private` is then an inserted line, and the keyword line it sits above, the one carrying
  the name, is untouched. It also keeps the first column readable top to bottom: attribute,
  modifier, keyword and name, binders, type. A declaration that fits entirely on one line
  keeps its modifier there, under the same permission that leaves any one-liner alone.
- Signature continuation lines indent by 4, the body by 2. Two different indents, so the
  eye finds where the type ends without counting. This one is legibility, not diff size. A
  `variable` block has no name to align under, so it indents by 2 instead.
- One binder group per line. A group is one pair of brackets: `[DecidableEq Peer]`,
  `{a b : α}`, `(doc : RawDocument Position Content Peer)`. Adding a group is then an
  inserted line rather than a rewritten one. A defining type parameter list is the
  exception: it splits one *name* per line. See "Binder groups".
- One operand per line in the ascribed type. Every top-level `→`, `∧`, `∨`, `↔` and every
  comma closing a top-level `∀`/`∃` binder ends its line, and the continuations sit flat at
  indent 6, under the first operand. This holds whether or not the packed form would have
  fitted in 100 columns, for the same reason binders are one per line: the type is read
  down the left margin, one argument or premise or conjunct per row, instead of parsed
  left to right out of a chain, and a new one is an inserted line. Unlike a binder, the
  operator trails rather than leads, because an operand is inserted above an existing
  operator and the line that gains the operator is the line being inserted anyway. See
  "Reading a signature vertically".
- The colon leads its own line, and so does the assignment: `:=` and `:= by` sit below the
  type at indent 4, never trailing the last operand. The same goes for `=>`, `|`,
  `extends`, `deriving` and `where`. An operator that begins a line does not have to be
  split off the previous one when something is inserted before it, and appending a premise
  to a type must not rewrite the line that carries the body's introduction.
- A declaration with no ascribed type puts that bare `:=` where the colon line would go, at
  the same indent 4, which is now the same shape typed declarations use. See
  `abbrev Document` under "Binder groups".
- `where` joins the header only when everything before it already sits on one line: the
  keyword, the name, and the ascribed type if there is one. `inductive Status where`,
  `structure ObjectId where` and `instance : Ord Segment where` qualify; those gain a
  binder rarely enough that splitting them now would be churn. The moment any piece moves
  to its own line, whether a binder, an `extends` clause, a type, or a name split off a
  keyword, `where` follows it down. So `structure Transaction (Controller : Type) where`
  becomes the keyword and name, the parameter list, then `where`, and a `structure` whose
  parameters come from a `variable` block still splits, because its name already sits alone
  on the keyword line. Never join a `where` that is already on its own line.
- Order: instance binders, implicits, explicits, hypotheses. Within each group keep the
  order that is already there. Dependency wins over category: when a binder mentions a name
  that a later category introduces in this same declaration, it stays after it, which is
  why `abbrev Document` below writes `(Position Content Peer : Type)` before
  `[PositionSpec Position]`. Writing that one in category order does not compile.
- Wrap at 100 columns. Nothing derives this number; it is a convention, and it is the rule
  most likely to force a reflow that costs extra diff lines. When a wrap is forced, break
  at a syntactic boundary (a binder, an arrow, a conjunct, or a relation such as `=` or
  `<`), never at whatever token crosses column 100.
- `namespace`, `section` and their matching `end` never indent their contents, at any
  nesting depth.
- Never join lines. This pass splits and re-indents. A declaration already spread over
  several lines stays spread; its line count never goes down. One exception, under "Binder
  groups": re-inlining a short local binder group.

## Scope: what to convert

Reformatting raises today's diff to lower tomorrow's, so a bulk pass converts only what
churns. Convert a declaration when either test passes, judged on the source text, not on
what Lean elaborates:

1. Its written signature contains at least one instance binder `[...]`. Those are the
   binder lists that grow.
2. It is the defining occurrence of a type parameter family: a `variable` block, or the
   `structure`/`inductive`/`class` that introduces the parameters.

A declaration whose binders are all local values, or that picks up section variables
without naming them, is out of scope for a bulk pass even when it wraps.
`instance (a b : Segment) : Decidable (a < b) := ...` stays exactly as it is.

Three things this gate does not govern:

- Wrapping, and the vertical split. A signature too long for 100 columns has to break
  whether or not it passes either test, and any ascribed type splits at its top-level
  operators whether or not the declaration passes either test, including one currently
  packed onto the keyword line. This is the one place the pass touches a declaration that
  does not churn, and it is deliberate: a file where one `A → B → Prop` is split and its
  neighbour is not reads worse than either convention applied consistently. The single
  exception is the whole-declaration one-liner under "Leave alone in every case". Both
  break according to "The layout", so many out-of-scope declarations are already in this
  shape and stay that way: the rule against joining lines applies to them too.
- New code. Write new declarations in this layout throughout; the gate exists to limit
  what an existing file's reformatting pass touches.
- Field, constructor and match columns. Those are aligned wherever they occur. Alignment
  is about reading a block, not about binder churn.

Leave alone in every case:

- A declaration whose signature and body already fit on one line, such as
  `def Segment.least : Segment := { digit := 0, peer := 1 }` or
  `instance : Max Status := maxOfLe`. This is permission to leave a one-liner alone, never
  permission to collapse a multi-line declaration into one.
- Comment and docstring text, `namespace`/`end`, `import`, `#guard`/`#check`/`#eval`
  lines, `open X in`, and the blank-line structure between declarations.
- Proof bodies. Tactic blocks keep their own indentation, including `calc` steps,
  `refine ⟨...⟩` argument lists, and `obtain`/`have`/`let` steps. Reindenting a signature
  can break a proof body it never touches: a `let`/`have` chain and a multi-line `{ ... }`
  or `⟨...⟩` literal are parsed relative to the column of the line that opens them. The
  token-hash and joined-lines checks in the procedure are whitespace-blind by construction
  and see nothing; only the re-typecheck catches it, and it has caught it, with
  `unexpected token 'have'` and `unsolved goals`. Leave such a region alone rather than
  flatten it, and never skip step 4.

If a wider scope is requested, follow it, but count the declarations first and say how
many will be touched.

The examples further down show the target layout for each syntax shape. Several of those
sample declarations would not pass the gate above; they are there for the shape.

## Procedure

1. Typecheck before touching anything, by the cheapest route that covers the files you
   will edit: `lake build <Module>` for each module you are about to edit; whole-project
   `lake build` only when the edited modules cannot be identified; `lean <file>` with
   `LEAN_PATH` pointing at the project's build output (`.lake/build/lib/lean` in a Lake
   project) when there is no Lake target at all. If it is already red, stop and say so:
   you cannot distinguish a formatting break from a pre-existing one otherwise.
2. For each target file, decide what to compare against:
   - Tracked and unmodified (`git ls-files --error-unmatch <file>` succeeds and
     `git diff --quiet -- <file>` succeeds): the baseline is `git show HEAD:<file>`.
   - Tracked but dirty, or untracked: copy the file to a scratch path first and use that
     copy as the baseline. `git show HEAD:<file>` fails on an untracked file and
     `git diff` reports nothing for one, so both checks below would pass vacuously.
3. Reformat, one file at a time.
4. Typecheck again, the same way as step 1. It must pass.
5. Compare token streams. Reflowing moves tokens across line boundaries, and
   `git diff --ignore-all-space` reports those as real changes, so it is not a usable
   check here.

   ```bash
   before=$(git show HEAD:<file> | tr -d '[:space:]' | shasum)   # or: < <baseline copy>
   after=$(tr -d '[:space:]' < <file> | shasum)
   ```

   The hashes must match. If they differ, revert and try again. This shows the
   non-whitespace character stream is identical; it cannot see a token crossing into or
   out of a `--` comment's scope, which is why it is paired with step 6 rather than
   trusted alone.
6. Check that nothing was joined. Every hunk must add at least as many lines as it
   removes:

   ```bash
   git diff -U0 -- <file> | awk '
     /^@@/ { if (add < del && h != "") print h" JOINED"; h = $0; add = 0; del = 0; next }
     /^\+/ { add++ } /^-/ { del++ }
     END   { if (add < del) print h" JOINED" }'
   ```

   For an untracked or dirty file, diff against the scratch baseline instead:
   `git diff --no-index -U0 <baseline> <file> | awk ...`. Output means a bug in the pass,
   with one exception: re-inlining a short binder group removes a line on purpose. Check
   each flagged hunk against that rule.
7. Report which declarations were reformatted and confirm all three checks.

Do not commit unless asked.

## Binder groups

A binder group stays on one line when its names are local to this one declaration:

```lean
    {a b c : Status}
    (a b : Line Position Content Peer)
```

It splits one name per line when it is the defining occurrence of a type parameter family,
because the family can gain a parameter without the block's own lines being rewritten:

```lean
variable
  (
    Position
    Content
    Peer
    : Type
  )
```

A `variable` line that only changes the visibility of an existing family, rather than
introducing one, is never split, however many names it carries:

```lean
variable {Position Content Peer}
```

A declaration that re-binds an existing family's parameters keeps them inline too:

```lean
abbrev Document
    (Position Content Peer : Type)
    [PositionSpec Position]
    [LT Peer]
    [DecidableEq Peer]
    :=
  { doc : RawDocument Position Content Peer // RawDocument.WellFormed doc }
```

Adding a fourth parameter there is never an isolated insert: every use site of `Document`
takes explicit arguments and changes too, so the line saved in the header is noise beside
the edit you were already making. The same reasoning covers `{a b c : Status}` in a
transitivity lemma, where a fourth variable makes it a different theorem.

The test: split one name per line if the group introduces parameters that other
declarations refer to. Keep it inline if the names appear only inside this declaration's
own statement, or if they re-bind a family defined elsewhere. Re-inlining such a group is
the one place this pass may remove a line.

## Instance binders

Write instance binders in one canonical order, so that `@`-applications and explicit
instance arguments line up across a family of declarations. Order by the type parameter
they constrain, following the parameter list itself, and within one parameter put the
structural class before its decidability companions:

```lean
instance instDecidableLTLine
    [PositionSpec Position]
    [DecidableEq Position]
    [DecidableLT Position]
    [LT Peer]
    [DecidableEq Peer]
    [DecidableLT Peer]
    (a b : Line Position Content Peer)
    : Decidable (a < b)
    :=
  inferInstanceAs (Decidable (_ ∨ _))
```

Bringing a legacy signature into this order is a block rewrite, N removed and N added, not
an insertion. It is worth doing once per family, and it is the largest single cost in this
guide; do it in its own commit so the reordering is reviewable on its own.

An anonymous instance puts the keyword alone on the first line, exactly as a named one
puts keyword and name there:

```lean
instance
    [spec : PositionSpec α]
    : LT α
    where
  lt := spec.ltPos
```

A `variable` block carrying instances uses the same one-per-line layout at indent 2:

```lean
variable
  [PositionSpec Position]
  [LT Peer]
  [DecidableEq Peer]
```

Hoisting a shared instance set into a `variable` block pays when a contiguous run of
declarations needs exactly that set: a fourth class is then one inserted line instead of
one per declaration. It is not a blanket win, because Lean includes section variables
differently for definitions and for theorems:

- `def`, `abbrev`, `instance`, `structure` and `inductive` pick up an instance variable
  only when the declaration actually uses it.
- A `theorem` picks up every in-scope instance variable whose type mentions an included
  variable, used or not. `linter.unusedSectionVars` then reports "automatically included
  section variable(s) unused in theorem" and suggests `omit [C α] in`.

So a hoist spanning a theorem that needs fewer instances silently over-generalizes that
theorem's statement. Scope the hoist with a named `section` around the run that genuinely
shares the set, and leave declarations with a different set outside it with their binders
written locally. Reach for `omit ... in` only when moving the declaration would break the
file's reading order.

`namespace` scopes `variable` exactly as `section` does, and it is usually the block
already open at the top of the file. Use `section` when a run shares only binders, and
`namespace` when it also shares a name prefix. The two are not interchangeable for names:
a `section NormalLine` scopes variables and qualifies nothing, so `def setStatus` inside
it is `setStatus`, not `NormalLine.setStatus`, however much the section header suggests
otherwise. That is a live failure mode, because an unqualified sibling of
`NormalLine.author` compiles fine and is only noticed at the first call site. Pick one
style per file, either `namespace NormalLine` with bare names or dotted names written out,
and never let a named section imply a prefix it does not give.

A declaration that re-binds a type parameter explicitly, such as
`abbrev Document (Position Content Peer : Type)` above, shadows the section variable, so
hoisted instances never reach it. It keeps its own copy.

## Reading a signature vertically

Binder lists split by the rules above. The ascribed type splits the same way: it breaks
after every top-level `→`, `∧`, `∨`, `↔`, and after the comma that closes a top-level
`∀`/`∃` binder. One operand per line, operator trailing, conclusion last, everything flat at indent
6. Length does not enter into it, and a chain that would have fitted on the colon line
splits anyway, so that the whole type is read down the margin the way binders are:

```lean
def Path.compareList
    : List Segment →
      List Segment →
      Ordering
  | [], [] => .eq
```

A constructor's type in an `inductive` is a signature too, with the colon at 6 and its
continuations at 8. Splitting it puts one premise per line and the conclusion last, which
is the inference-rule reading the premise rule lines are for:

```lean
inductive FlagUpdate
    : SendRecord Controller →
      SendRecord Controller →
      Prop
  | cutMe
      {before after}
      : before.WellFormed →
        (∀ dep ∈ before.dependencies, dep.cutYou = false) →
        after = { before with cutMe := true } →
        FlagUpdate before after
```

A theorem's statement is an ascribed type, so it splits too, quantifiers included:

```lean
theorem labels_phase_mono
    : ∀ a ∈ evidence,
      ∀ b ∈ evidence,
      a.snapshot.owner = b.snapshot.owner →
      a.snapshot.history.IsPrefix b.snapshot.history →
      ConcreteTime.le (phaseOfLabel (labels a.snapshot)) (phaseOfLabel (labels b.snapshot))
    := by
```

The nesting is flat on purpose. A `∀` under a `∀` is indented no further than the premise
under it, because the column, not the indentation, is what is being read; stepping each
quantifier in by 2 would push the conclusion of a five-premise statement off to the right
for nothing.

Only top-level operators split. An operator nested inside parentheses or brackets, or
inside a binder's type, belongs to its operand and stays with it, so
`(∀ dep ∈ before.dependencies, dep.cutYou = false) →` is one line, not three, and
`(application : Transaction Controller → Prop)` is one binder.

The rule stops at two borders. A `structure`, `class` or `where` field whose type fits on
one line stays packed, `ltPos : α → α → Prop` and `msgId : Msg → MsgId` included, because
that column is aligned for reading a block and splitting it would destroy the alignment.
And an implication in a body, rather than in an ascribed type, follows the body rule below.

A single operand too long for the line breaks under the wrap rule, at a syntactic boundary,
with its continuation indented 2 further.

A hypothesis whose own type wraps indents its continuation 2 past the binder:

```lean
theorem storedPayload_congr
    {left right : StoredSignatures Peer Key Tag}
    (line : NormalLine Position Content Peer)
    (parentLeft :
      left.storedSignature line.parentLeft =
        right.storedSignature line.parentLeft)
    (parentRight :
      left.storedSignature line.parentRight =
        right.storedSignature line.parentRight)
    : left.storedPayload line = right.storedPayload line
    := by
  simp [storedPayload, parentLeft, parentRight]
```

In a body, each nested quantifier or implication steps in by 2, and the second operand of
a trailing `∧`/`∨` steps in 2 past the first:

```lean
def RawDocument.HasParentIntervals
    [PositionSpec Position]
    [DecidableEq Peer]
    (doc : RawDocument Position Content Peer)
    : Prop
    :=
  ∀ line ∈ doc.normalLines,
    ∀ left right,
      doc.line? line.parentLeft = some left →
      doc.line? line.parentRight = some right →
      left.position < line.position ∧
        line.position < right.position
```

## Alignment

Inside a `structure`, `class`, `where` body, record literal, or match block, pad each name
so the operator of every line in the run sits one column past the longest name in that
run. Fields align on `:`, record and `where` fields on `:=`, match alternatives on `=>`.

This rule does not minimize diffs; it buys reading a block down the page. The cost is
asymmetric and usually zero: inserting a field whose name is no longer than the current
widest is a plain 1-added, 0-removed insert. Inserting a longer one re-pads the whole run:
N modified lines to buy one insert.

What counts as a column entry:

- A `structure` or `class` field, `name : Type`, always.
- A `where` field in an `instance` or `example` implementation, including one that takes
  its own binders, when its value is a single-line term: `ltPos a b := PathId.lt a.val
  b.val` aligns with its neighbours.
- Not a field whose value is a `by` block or spans several lines. That field ends the run,
  and it is left unpadded, as are the fields after it until a new run starts.

Five limits keep the cost bounded:

- A run is a maximal block of consecutive column entries at the same indent. A blank line,
  a comment or docstring line, a differently indented line, or a line of another kind ends
  the run, and the next run aligns independently. Breaking a wide block with a blank line
  is how you stop one long name from re-padding everything below it.
- Continuation lines of a wrapped type or value keep their own indentation and are never
  padded.
- One operator moves per line, and it is the leftmost. A field with a default
  (`retries : Nat := 3`) aligns on its `:`, never on its `:=`.
- Do not align a run whose padding would push any line past 100 columns; leave it
  single-spaced. If a later insertion would push an already-aligned run past 100 columns,
  de-align the whole run in that same edit. That is the accepted worst case.
- Never align inside a proof. `obtain ⟨a, b⟩ := p`, `have h := _` and `let x := _` are
  tactic steps, not fields.

## Examples across the syntax

### def with a pattern match

```lean
def RawDocument.line?
    [DecidableEq Peer]
    (doc : RawDocument Position Content Peer)
    : LineId Peer →
      Option (Line Position Content Peer)
  | .bottom       => some .bottom
  | .top          => some .top
  | .operation id => (doc.normalLine? id).map .normal
```

### theorem with an attribute, and with hypotheses

```lean
@[simp]
theorem RawDocument.line?_bottom
    [DecidableEq Peer]
    (doc : RawDocument Position Content Peer)
    : doc.line? .bottom = some .bottom
    :=
  rfl

theorem Status.canBecome_trans
    {a b c : Status}
    (hab : a.canBecome b)
    (hbc : b.canBecome c)
    : a.canBecome c
    := by
  exact Nat.le_trans hab hbc
```

Hypotheses are binders: one per line, conclusion behind the leading colon.

### structure, with parameters in a variable block

```lean
variable
  (
    Position
    Content
    Peer
    : Type
  )

structure RawDocument
    where
  normalLines : List (NormalLine Position Content Peer)
```

### structure with a return type

```lean
structure RawDocument.WellFormed
    (doc : RawDocument Position Content Peer)
    : Prop
    where
  uniqueIds       : RawDocument.HasUniqueIds doc
  presentParents  : RawDocument.HasPresentParents doc
  parentIntervals : RawDocument.HasParentIntervals doc
  parentRanked    : RawDocument.ParentRanked doc
  sortedLines     : RawDocument.HasSortedLines doc
```

The signature is already split, so `where` gets its own line. A one-line header would
keep it joined; compare `inductive Status where` further down.

### structure with extends, docstrings, and premise rule lines

```lean
structure Network
    extends System (Event Msg)
    where
  msgId : Msg → MsgId
  /-- Every delivered message was broadcast by some node. -/
  deliveryHasCause :
    ∀ {i : Nat} {m : Msg},
      Event.deliver m ∈ history i →
      ----------------------------------
      ∃ j,
      Event.broadcast m ∈ history j

  /-- A node delivers its own broadcasts, and does so after broadcasting them. -/
  deliverLocally :
    ∀ {i : Nat} {m : Msg},
      Event.broadcast m ∈ history i →
      --------------------------------------------------------------
      Event.broadcast m ⊏[toSystem, i] Event.deliver m
```

Two things to read off this one. `msgId` is not padded to align with `deliveryHasCause`,
because the docstring between them ends the run. And an implication-shaped field may
separate its premises from its conclusion with a rule line of hyphens, read as an
inference rule. That is a comment, so it costs nothing at elaboration time, and it is
legibility rather than diff economy: use it where premises actually stack, not on a
single-premise implication.

### class with an aligned field column

```lean
class PositionSpec
    (α : Type)
    where
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

### instance implementing that class

```lean
instance : PositionSpec { x : PathId // x.WellFormed } where
  ltPos a b     := PathId.lt a.val b.val
  bottom        := ⟨.infimum, trivial⟩
  top           := ⟨.supremum, trivial⟩
  irrefl x      := PathId.lt_irrefl x.val
  trans hab hbc := PathId.lt_trans hab hbc
  total a b h   := PathId.lt_total a.val b.val fun hv => h (Subtype.ext hv)
  bottom_lt := by
    intro x hx
    exact PathId.infimum_lt fun hv => hx (Subtype.ext hv)
  lt_top := by
    intro x hx
    exact PathId.lt_supremum fun hv => hx (Subtype.ext hv)
```

The first six fields carry their own binders and single-line values, so they form one
aligned run. `bottom_lt` has a `by` block, so it falls outside the run and is unpadded, as
is `lt_top` after it.

### inductive, one-line constructors

```lean
inductive Event
    (Msg : Type)
    where
  | broadcast (msg : Msg)
  | deliver   (msg : Msg)
deriving DecidableEq, Repr
```

`deriving` returns to column 0: it is a clause of the declaration, not of the last
constructor, so adding a constructor never re-indents it.

A parameterless inductive whose header fits stays on one line:

```lean
inductive Status where
  | aura      -- inserted, not yet acknowledged by every trusted peer
  | settled   -- acknowledged by the whole network (response checklist complete)
  | tombstone -- deleted, still in the document (signatures chain through it), absorbing
deriving DecidableEq, Repr, Ord
```

### inductive, constructors with their own binders

```lean
inductive Operation
    where
  | insert
      (id : OpId Peer)
      (rank : Nat)
      (position : Position)
      (parentLeft parentRight : LineId Peer)
      (supersedes : Option (LineId Peer))
      (content : Content)
      (wireTag : Tag)

  | delete
      (id : OpId Peer)
      (target : LineId Peer)
      (wireTag : Tag)

  -- Acknowledgements are idempotent response updates, so they have no `OpId`.
  | acknowledge
      (target : LineId Peer)
      (peer : Peer)
      (wireTag : Tag)

deriving DecidableEq, Repr
```

Constructor binders indent 6, one group per line. Once any constructor is multi-line, put
a blank line between all of them, which also makes each constructor its own alignment run.

### instance, short forms

```lean
instance : Ord Segment where
  compare a b :=
    (compare a.digit b.digit).then
      (compare a.peer b.peer)

instance : Max Status := maxOfLe

instance (a b : Segment) : Decidable (a < b) :=
  decidable_of_iff _ Segment.lt_def.symm
```

The last two are out of scope for a bulk pass: one fits on a line, and neither carries an
instance binder.

### structure instance update

```lean
def NormalLine.setStatus
    (line : NormalLine Position Content Peer)
    (next : Status)
    (_ : line.state.status.canBecome next)
    : NormalLine Position Content Peer
    :=
  { line with state := { line.state with status := next } }
```

A `{ x with ... }` update that fits on one line stays on one line, nesting included. Split
it one field per line, aligned on `:=`, only when it does not fit.

### record literal spanning lines

```lean
  { id          := line.fixed.id
    position    := p
    parentLeft  := l
    parentRight := r }
```

Illustrative, with the remaining fields elided. The opening brace carries the first field,
so a new field is an insertion and the closing brace never moves alone.

### example with a where body

```lean
example
    : Network Unit Unit
    where
  history i := if i = 0 then [.broadcast (), .deliver ()] else []

  wdhistory i := by by_cases h : i = 0 <;> simp [h] <;> decide

  msgId _ := ()

  deliveryHasCause _ := ⟨0, by simp⟩

  deliverLocally {i _} h := by
    by_cases hi : i = 0
    · exact ⟨[], [], [], by simp [hi]⟩
    · simp [hi] at h

  msgIdUnique {i j _ _} h₁ h₂ _ := by
    by_cases hi : i = 0 <;> by_cases hj : j = 0 <;> simp_all
```

Nothing is padded here: the blank lines between fields put each one in its own run, and
most of them carry `by` blocks anyway. Separating implementation fields with blank lines
is the cheap way to keep one long name from re-padding its neighbours.

### notation

```lean
@[inherit_doc System.before]
scoped
notation:50
  x:51 " ⊏[" S ", " i "] " y:51
  => System.before S i x y
```

Modifier, keyword with its precedence, the syntax pattern, then the expansion behind a
leading `=>`. The pattern stays on one line even though it can grow: a notation is read as
a single shape, and splitting it into atoms to save one diff line would make it
unreadable.

## Forms this guide does not cover

`mutual` blocks, `termination_by`/`decreasing_by` clauses, `where` clauses attached to a
def body, explicit universe parameters, `deriving instance C for T`, `do` notation in a
term body, a header carrying `extends` and binders and `deriving` at once, and the
`macro`/`syntax`/`elab` family do not occur in the codebase this guide was extracted from,
so there is no tested rule for them. Apply the same three principles and say what you
chose: keyword and name alone on the first line, one binder group per line at indent 4,
and any operator that could be pushed down by an insertion starts its own line. Do not
invent a column where the guide does not define one.

## Why: the cost model

Almost every signature edit has the same shape: a binder is added. Under a compact layout
that edit rewrites lines that had nothing to do with it; under this layout it is an
inserted line. Take a real signature and add `[DecidableLT Peer]`.

Compact, before the insert:

```lean
def RawDocument.normalLine? [DecidableEq Peer] (doc : RawDocument Position Content Peer)
    (id : OpId Peer) : Option (NormalLine Position Content Peer) :=
```

The new binder does not fit on the first line, so the signature reflows. What that costs
depends on the wrapper, not on the code: 1 removed and 2 added if it keeps the second line
untouched, 2 removed and 3 added if it repacks from scratch, 1 removed and 1 added if it
is willing to run to 107 columns and break the wrap rule.

This layout, before the insert:

```lean
def RawDocument.normalLine?
    [DecidableEq Peer]
    (doc : RawDocument Position Content Peer)
    (id : OpId Peer)
    : Option (NormalLine Position Content Peer)
    :=
```

Inserting `[DecidableLT Peer]` under `[DecidableEq Peer]` is 1 added, 0 removed, with no
dependence on a wrapping algorithm, and the added line is the change. Nothing else in the
declaration moves, so `git blame` still attributes the name, the other binders and the
body to the commits that wrote them.

Two smaller measurements, stated honestly:

- The leading colon pays for binders appended at the end of the list. With a trailing
  colon on the last binder, appending costs 2 added and 1 removed, because that line must
  be split first; with a leading colon it is 1 added, 0 removed. For a binder inserted in
  the middle of the list, both layouts cost 1 added, 0 removed, and the leading colon buys
  nothing.
- One-per-line shrinks the surface of a conflict but does not prevent one: two branches
  each adding an instance binder for the same type parameter land at the same insertion
  point under the canonical order and still conflict.

## What it costs

- Vertical space. A two-line signature becomes five to seven. A declaration with a dozen
  binders is a dozen lines before the body starts.
- One-time blame churn. Converting a stable declaration resets `git blame` on every
  signature line it touches. That is what the scope gate is for.
- Reordering existing instance binders into the canonical order, which is a block rewrite
  rather than an insertion.
- Review overhead on the pass itself: a bulk reformat needs the token-hash and
  joined-lines checks before anyone can trust that it changed nothing.
- Four departures from the thesis, kept for legibility and listed here once: column
  alignment, the 4-versus-2 indent contrast, the single-line notation pattern, and the
  premise rule lines. Everywhere else, a rule that costs diff lines is a bug in the rule.

## The case against

Mathlib packs signatures to a column budget, and inside Mathlib that is correct. The
strongest form of the argument: a formalization is read for mathematical content far more
often than it is patched, and a packed line carries information that splitting destroys.
`[DecidableEq Position] [DecidableLT Position]` on one line says "these travel together";
on separate lines they look like two unrelated constraints. A packed signature also fits
on a screen, so a reader takes it in at a glance instead of scrolling.

That argument wins whenever a codebase is stable and read-heavy. This layout is the better
trade in the opposite case: a formalization still under construction, where the typeclass
discipline is still moving, and where every review is a diff review. Adopt it for that, or
not at all.
