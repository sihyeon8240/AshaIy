module

public import Textbooks.LinearAlgebra.ScalarProductsAndOrthogonality.DualSpaces

public section

namespace LinearAlgebra.SymmetricHermitianAndUnitaryOperators

variable {K V : Type*} [Field K] [AddCommGroup V] [Module K V]

/-- Definition: an operator is a linear endomorphism. -/
abbrev Operator (K V : Type*) [Field K] [AddCommGroup V] [Module K V] := Module.End K V

variable [Module.Finite K V]
variable (B : LinearMap.BilinForm K V) (hB : B.IsSymm) (hn : B.SeparatingLeft)

/-- Definition: transpose is constructed by transporting the dual map through the
scalar-product representation of the dual. -/
noncomputable def transpose (A : Module.End K V) : Module.End K V :=
  let e := ScalarProductsAndOrthogonality.scalarProductEquiv B hn
  e.symm.toLinearMap.comp (A.dualMap.comp e.toLinearMap)

include hB hn

/-- Lemma: the constructed transpose satisfies its defining identity. -/
theorem transpose_apply (A : Module.End K V) (v w : V) :
    B (A v) w = B v (transpose B hn A w) := by
  let e := ScalarProductsAndOrthogonality.scalarProductEquiv B hn
  have he := congrArg (fun f : Module.Dual K V => f v)
    (e.apply_symm_apply (A.dualMap (e w)))
  change B (transpose B hn A w) v = B w (A v) at he
  exact (hB.eq (A v) w).trans (he.symm.trans (hB.eq _ _))

/-- Lemma: the defining identity determines the transpose uniquely. -/
theorem transpose_unique (A C : Module.End K V)
    (hC : ∀ v w, B (A v) w = B v (C w)) : C = transpose B hn A := by
  ext w
  apply sub_eq_zero.mp
  apply hn
  intro v
  rw [map_sub, LinearMap.sub_apply, hB.eq (C w), hB.eq (transpose B hn A w),
    ← hC, ← transpose_apply B hB hn, sub_self]

/-- Lemma: every operator has a unique transpose for a nondegenerate scalar product. -/
theorem exists_unique_transpose (A : Module.End K V) :
    ∃! C : Module.End K V, ∀ v w, B (A v) w = B v (C w) :=
  ⟨transpose B hn A, transpose_apply B hB hn A, transpose_unique B hB hn A⟩

/-- Definition: symmetry uses the standard self-adjoint predicate for a bilinear form. -/
abbrev IsSymmetric (A : Module.End K V) : Prop := B.IsSelfAdjoint A

/-- Proposition: symmetry is equivalent to equality with the transpose. -/
theorem isSymmetric_iff_transpose_eq (A : Module.End K V) :
    IsSymmetric B A ↔ transpose B hn A = A := by
  constructor

  · intro h
    exact (transpose_unique B hB hn A A h).symm

  · intro h v w
    exact (transpose_apply B hB hn A v w).trans
      (congrArg (fun C : Module.End K V => B v (C w)) h)

/-- Theorem: transposition preserves sums. -/
theorem transpose_add (A C : Module.End K V) :
    transpose B hn (A + C) = transpose B hn A + transpose B hn C := by
  symm
  apply transpose_unique B hB hn
  intro v w
  simp only [LinearMap.add_apply, map_add, transpose_apply B hB hn]

/-- Theorem: transposition reverses composition. -/
theorem transpose_mul (A C : Module.End K V) :
    transpose B hn (A * C) = transpose B hn C * transpose B hn A := by
  symm
  apply transpose_unique B hB hn
  intro v w
  change B (A (C v)) w = B v (transpose B hn C (transpose B hn A w))
  rw [transpose_apply B hB hn, transpose_apply B hB hn]

/-- Theorem: transposition commutes with scalar multiplication. -/
theorem transpose_smul (c : K) (A : Module.End K V) :
    transpose B hn (c • A) = c • transpose B hn A := by
  symm
  apply transpose_unique B hB hn
  intro v w
  simp only [LinearMap.smul_apply, map_smul, transpose_apply B hB hn]

/-- Theorem: transposing twice recovers the operator. -/
theorem transpose_transpose (A : Module.End K V) :
    transpose B hn (transpose B hn A) = A := by
  symm
  apply transpose_unique B hB hn
  intro v w
  rw [hB.eq, ← transpose_apply B hB hn, hB.eq]

end LinearAlgebra.SymmetricHermitianAndUnitaryOperators
