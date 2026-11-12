module

import Lean

/-! Validation tooling, copied into build/lean-links by proof_links.py.
This is not a mathematical textbook module. -/

open Lean Meta

set_option autoImplicit false

private def auditAxioms (name : Name) : MetaM Unit := do
  let permitted := #[``propext, ``Classical.choice, ``Quot.sound]

  for axiomName in (← collectAxioms name) do
    unless permitted.contains axiomName do
      throwError "{name} depends on forbidden axiom {axiomName}"

private def auditTextbookDeclarations : MetaM Unit := do
  let env ← getEnv

  -- Select modules before visiting declarations to avoid traversing all of Mathlib.
  for moduleName in env.header.moduleNames, moduleData in env.header.moduleData do
    unless (`Textbooks).isPrefixOf moduleName do
      continue

    for info in moduleData.constants do
      if info matches .axiomInfo _ then
        throwError "repository-defined axiom is forbidden: {info.name}"

      auditAxioms info.name

private def auditProof (name : Name) : MetaM Unit := do
  let some info := (← getEnv).find? name
    | throwError "registered proof declaration does not exist: {name}"

  if info.isUnsafe then
    throwError "registered proof is unsafe: {name}"

  unless (← isProp info.type) do
    throwError "registered declaration is not a proof of a proposition: {name}"

  auditAxioms name

public unsafe def main (_ : List String) : IO Unit := do
  let declarations := ((← (← IO.getStdin).readToEnd).splitOn "\n").filter (· != "")
  initSearchPath (← findSysroot)
  enableInitializersExecution

  -- Load private proofs and the cached axiom dependencies in a standalone process.
  let env ← importModules #[{ module := `Textbooks }] {} (loadExts := true) (level := .private)
  let audit : MetaM Unit := do
    auditTextbookDeclarations
    for declaration in declarations do
      auditProof declaration.toName

  discard <| audit.run' {} |>.toIO
    { fileName := "<proof audit>", fileMap := default } { env }
