module

public import Textbooks.LinearAlgebra.ScalarProductsAndOrthogonality.GramSchmidt
public import Mathlib.Analysis.InnerProductSpace.Symmetric

public section

namespace LinearAlgebra.SymmetricHermitianAndUnitaryOperators

open scoped BigOperators

variable {𝕜 E : Type*} [RCLike 𝕜] [NormedAddCommGroup E] [InnerProductSpace 𝕜 E]
variable [Module.Finite 𝕜 E]

local notation "⟪" x ", " y "⟫" => inner 𝕜 x y

/-- Theorem: each functional on a finite-dimensional positive inner-product space
has exactly one representing vector. -/
theorem exists_unique_inner_representative (L : Module.Dual 𝕜 E) :
    ∃! w : E, ∀ v, L v = ⟪w, v⟫ := by
  classical
  obtain ⟨b, hb⟩ := ScalarProductsAndOrthogonality.exists_orthonormal_basis (𝕜 := 𝕜) (E := E)
  let w := ∑ i, star (L (b i)) • b i

  have hw : innerₛₗ 𝕜 w = L := by
    apply b.ext
    intro j
    change ⟪w, b j⟫ = L (b j)
    simp only [w, sum_inner, inner_smul_left, starRingEnd_apply, star_star,
      orthonormal_iff_ite.mp hb, mul_ite, mul_one, mul_zero,
      Finset.sum_ite_eq', Finset.mem_univ, ite_true]

  refine ⟨w, fun v => (congrArg (fun f : Module.Dual 𝕜 E => f v) hw).symm, ?_⟩
  intro u hu
  apply sub_eq_zero.mp
  apply (inner_self_eq_zero (𝕜 := 𝕜)).mp
  rw [inner_sub_left, ← hu, ← congrArg (fun f : Module.Dual 𝕜 E => f (u - w)) hw,
    innerₛₗ_apply_apply, sub_self]

/-- Definition: the representing vector of a functional, constructed by finite-dimensional
orthonormal coordinates. -/
noncomputable def innerRepresentative (L : Module.Dual 𝕜 E) : E :=
  (exists_unique_inner_representative L).exists.choose

/-- Lemma: evaluation of the represented functional. -/
theorem innerRepresentative_apply (L : Module.Dual 𝕜 E) (v : E) :
    ⟪innerRepresentative L, v⟫ = L v :=
  ((exists_unique_inner_representative L).exists.choose_spec v).symm

omit [Module.Finite 𝕜 E] in
/-- Lemma: two vectors agreeing against every second argument are equal. -/
theorem eq_of_inner_left_eq {u v : E} (h : ∀ w, ⟪u, w⟫ = ⟪v, w⟫) : u = v := by
  apply sub_eq_zero.mp
  apply (inner_self_eq_zero (𝕜 := 𝕜)).mp
  rw [inner_sub_left, h, sub_self]

/-- Definition: the adjoint sends `w` to the representative of `v ↦ inner w (A v)`. -/
noncomputable def adjoint (A : Module.End 𝕜 E) : Module.End 𝕜 E where
  toFun w := innerRepresentative ((innerₛₗ 𝕜 w).comp A)
  map_add' x y := by
    apply eq_of_inner_left_eq (𝕜 := 𝕜)
    intro v
    simp only [innerRepresentative_apply, LinearMap.comp_apply, innerₛₗ_apply_apply,
      inner_add_left]
  map_smul' c w := by
    apply eq_of_inner_left_eq (𝕜 := 𝕜)
    intro v
    simp only [innerRepresentative_apply, LinearMap.comp_apply, innerₛₗ_apply_apply,
      inner_smul_left, RingHom.id_apply]

/-- Lemma: the constructed adjoint satisfies the defining inner-product identity. -/
theorem adjoint_inner_left (A : Module.End 𝕜 E) (w v : E) :
    ⟪adjoint A w, v⟫ = ⟪w, A v⟫ :=
  innerRepresentative_apply _ v

/-- Lemma: the adjoint identity with the operator in the first argument. -/
theorem inner_adjoint_right (A : Module.End 𝕜 E) (v w : E) :
    ⟪A v, w⟫ = ⟪v, adjoint A w⟫ := by
  rw [← inner_conj_symm v (adjoint A w), adjoint_inner_left, inner_conj_symm]

/-- Lemma: the inner-product identity determines the adjoint uniquely. -/
theorem adjoint_unique (A C : Module.End 𝕜 E)
    (hC : ∀ v w, ⟪A v, w⟫ = ⟪v, C w⟫) : C = adjoint A := by
  ext w
  apply eq_of_inner_left_eq (𝕜 := 𝕜)
  intro v
  rw [adjoint_inner_left, ← inner_conj_symm (C w), ← hC, inner_conj_symm]

/-- Lemma: every operator has a unique linear adjoint. -/
theorem exists_unique_adjoint (A : Module.End 𝕜 E) :
    ∃! C : Module.End 𝕜 E, ∀ v w, ⟪A v, w⟫ = ⟪v, C w⟫ :=
  ⟨adjoint A, inner_adjoint_right A, adjoint_unique A⟩

/-- Definition: a Hermitian operator uses Mathlib's symmetric inner-product predicate. -/
abbrev IsHermitian {V : Type*} [NormedAddCommGroup V] [InnerProductSpace ℂ V]
    (A : Module.End ℂ V) : Prop := A.IsSymmetric

/-- Proposition: an operator is symmetric or Hermitian exactly when its adjoint equals itself. -/
theorem isSymmetric_iff_adjoint_eq (A : Module.End 𝕜 E) :
    A.IsSymmetric ↔ adjoint A = A := by
  constructor

  · intro h
    exact (adjoint_unique A A h).symm

  · intro h v w
    rw [inner_adjoint_right, h]

/-- Theorem: taking adjoints preserves sums. -/
theorem adjoint_add (A B : Module.End 𝕜 E) : adjoint (A + B) = adjoint A + adjoint B := by
  symm
  apply adjoint_unique
  intro v w
  simp only [LinearMap.add_apply, inner_add_left, inner_add_right, inner_adjoint_right]

/-- Theorem: taking adjoints reverses composition. -/
theorem adjoint_mul (A B : Module.End 𝕜 E) : adjoint (A * B) = adjoint B * adjoint A := by
  symm
  apply adjoint_unique
  intro v w
  change ⟪A (B v), w⟫ = ⟪v, adjoint B (adjoint A w)⟫
  rw [inner_adjoint_right, inner_adjoint_right]

/-- Theorem: taking adjoints conjugates scalar coefficients. -/
theorem adjoint_smul (c : 𝕜) (A : Module.End 𝕜 E) :
    adjoint (c • A) = star c • adjoint A := by
  symm
  apply adjoint_unique
  intro v w
  simp only [LinearMap.smul_apply, inner_smul_left, inner_smul_right,
    starRingEnd_apply, inner_adjoint_right]

/-- Theorem: taking the adjoint twice recovers the operator. -/
theorem adjoint_adjoint (A : Module.End 𝕜 E) : adjoint (adjoint A) = A := by
  symm
  apply adjoint_unique
  exact adjoint_inner_left A

end LinearAlgebra.SymmetricHermitianAndUnitaryOperators
