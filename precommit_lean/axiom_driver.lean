import Lean

open Lean Elab Command

def nameFromString (value : String) : Name :=
  value.splitOn "." |>.foldl (fun parent part => Name.mkStr parent part) .anonymous

def allowedAxiom (declaration axiomName : Name) (native : Array String) : Bool :=
  axiomName == `propext || axiomName == `Classical.choice || axiomName == `Quot.sound ||
    native.any fun name =>
      name == declaration.toString &&
        (axiomName == `Lean.ofReduceBool || axiomName == `Lean.trustCompiler ||
          (name ++ "._native.native_decide.ax").isPrefixOf axiomName.toString)

run_cmd do
  let env ← getEnv
  let namespaceName ← liftIO <| IO.getEnv "PRECOMMIT_LEAN_NAMESPACE"
  let native ← liftIO <| IO.getEnv "PRECOMMIT_LEAN_NATIVE"
  let some namespaceName := namespaceName | throwError "missing PRECOMMIT_LEAN_NAMESPACE"
  let native := native.getD "" |>.splitOn "\n" |>.filter (· != "") |>.toArray
  let namespaceName := nameFromString namespaceName
  let modulePrefixes :=
    (← liftIO <| IO.getEnv "PRECOMMIT_LEAN_MODULES").getD "" |>.splitOn "\n"
      |>.filter (· != "") |>.map nameFromString |>.toArray
  let moduleIndices := env.allImportedModuleNames.foldl (fun indices module =>
    if modulePrefixes.any (·.isPrefixOf module) then
      match env.getModuleIdx? module with
      | some index => indices.push index
      | none => indices
    else indices) #[]
  let declarations := env.constants.fold (fun names name _ =>
    let inTarget := match env.getModuleIdxFor? name with
      | some index => moduleIndices.any (· == index)
      | none => false
    if namespaceName.isPrefixOf name && inTarget &&
        !name.toString.contains "._native.native_decide.ax_"
    then names.push name else names) #[]
  if declarations.isEmpty then
    throwError "no declarations matched the configured namespace and module"
  let mut failures := #[]
  for declaration in declarations do
    let axiomNames ← liftCoreM <| Lean.collectAxioms declaration
    let unexpected := axiomNames.filter fun axiomName =>
      !allowedAxiom declaration axiomName native
    unless unexpected.isEmpty do
      failures := failures.push (declaration, unexpected)
  IO.println s!"precommit-lean: checked {declarations.size} declarations"
  for (declaration, axiomNames) in failures do
    logError m!"unexpected axioms in {declaration}: {axiomNames}"
