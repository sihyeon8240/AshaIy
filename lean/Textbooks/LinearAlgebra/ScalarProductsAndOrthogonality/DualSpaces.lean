import Textbooks.LinearAlgebra.LinearMappings.RankNullity
import Textbooks.LinearAlgebra.ScalarProductsAndOrthogonality.ScalarProducts
import Mathlib.LinearAlgebra.Dual.Basis
import Mathlib.LinearAlgebra.Projection

namespace LinearAlgebra.ScalarProductsAndOrthogonality

open Module Submodule
open scoped BigOperators

variable {K V : Type*} [Field K] [AddCommGroup V] [Module K V]

/-- Theorem: a functional is the sum of its basis values times the coordinate functionals. -/
theorem sum_smul_dualBasis {ι : Type*} [Fintype ι] [DecidableEq ι]
    (b : Basis ι K V) (φ : Module.Dual K V) :
    ∑ i, φ (b i) • b.dualBasis i = φ := by
  apply b.ext
  intro j
  simp only [LinearMap.sum_apply, LinearMap.smul_apply, b.dualBasis_apply_self,
    smul_eq_mul, mul_ite, mul_one, mul_zero, Finset.sum_ite_eq,
    Finset.mem_univ, ite_true]

/-- Theorem: the coordinate functionals form an independent generating family of the dual. -/
theorem dual_is_basis {ι : Type*} [Fintype ι] [DecidableEq ι] (b : Basis ι K V) :
    VectorSpaces.IsFiniteBasis (K := K) (fun i => b.dualBasis i) := by
  refine ⟨Fintype.linearIndependent_iff.mpr ?_, fun φ => ?_⟩

  · intro a ha j
    have hj := congrArg (fun φ : Module.Dual K V => φ (b j)) ha
    simpa only [LinearMap.sum_apply, LinearMap.smul_apply, b.dualBasis_apply_self,
      smul_eq_mul, mul_ite, mul_one, mul_zero, Finset.sum_ite_eq,
      Finset.mem_univ, ite_true, LinearMap.zero_apply] using hj

  · exact ⟨fun i => φ (b i), sum_smul_dualBasis b φ⟩

/-- Theorem: a finite-dimensional space and its dual have equal dimension. -/
theorem dual_finrank_eq [Module.Finite K V] :
    finrank K (Module.Dual K V) = finrank K V := by
  classical
  let b := VectorSpaces.finiteBasis (K := K) (V := V)
  obtain ⟨d, _⟩ := (VectorSpaces.finiteBasis_iff _).mp (dual_is_basis b)
  exact (finrank_eq_card_basis d).trans (finrank_eq_card_basis b).symm

/-- Theorem: a nondegenerate scalar product identifies the space with its dual. -/
theorem scalarProduct_bijective [Module.Finite K V] (B : LinearMap.BilinForm K V)
    (hB : B.SeparatingLeft) : Function.Bijective B := by
  apply LinearMappings.bijective_of_injective_of_finrank_eq B dual_finrank_eq.symm
  intro x y hxy
  apply sub_eq_zero.mp
  apply hB
  intro w
  rw [map_sub, LinearMap.sub_apply]
  exact sub_eq_zero.mpr (congrArg (fun φ : Module.Dual K V => φ w) hxy)

/-- Definition: the scalar-product representation isomorphism sends `v` to `B v`. -/
noncomputable def scalarProductEquiv [Module.Finite K V] (B : LinearMap.BilinForm K V)
    (hB : B.SeparatingLeft) : V ≃ₗ[K] Module.Dual K V :=
  LinearEquiv.ofBijective B (scalarProduct_bijective B hB)

/-- Corollary: every functional has a unique representing vector. -/
theorem exists_unique_representative [Module.Finite K V] (B : LinearMap.BilinForm K V)
    (hB : B.SeparatingLeft) (φ : Module.Dual K V) : ∃! v, B v = φ := by
  obtain ⟨v, hv⟩ := (scalarProduct_bijective B hB).2 φ
  exact ⟨v, hv, fun w hw => (scalarProduct_bijective B hB).1 (hw.trans hv.symm)⟩

/-- Lemma: a functional on a subspace extends by zero on a chosen complement. -/
theorem dualRestrict_surjective [Module.Finite K V] (W : Submodule K V) :
    Function.Surjective W.dualRestrict := by
  obtain ⟨U, hU⟩ := VectorSpaces.exists_complement W
  obtain ⟨hs, hz⟩ := VectorSpaces.directSum_sup_inf hU
  have hc : IsCompl W U := ⟨disjoint_iff.mpr hz, codisjoint_iff.mpr hs⟩

  intro φ
  refine ⟨φ.comp (W.projectionOnto U hc), ?_⟩
  ext w
  change φ (W.projectionOnto U hc (w : V)) = φ w
  rw [Submodule.projectionOnto_apply_left]

/-- Theorem: a subspace and its annihilator have complementary dimensions. -/
theorem finrank_add_finrank_dualAnnihilator_eq [Module.Finite K V]
    (W : Submodule K V) :
    finrank K W + finrank K W.dualAnnihilator = finrank K V := by
  have hr : LinearMap.range W.dualRestrict = ⊤ :=
    (LinearMap.range_eq_top).mpr (dualRestrict_surjective W)
  have hd := LinearMappings.rank_nullity W.dualRestrict
  rw [hr, LinearMappings.finrank_top, dual_finrank_eq, dual_finrank_eq] at hd
  change finrank K V = finrank K W.dualAnnihilator + finrank K W at hd
  omega

/-- Proposition: perpendicular vectors correspond exactly to annihilating functionals. -/
theorem mem_orthogonalBilin_iff_mem_dualAnnihilator (B : LinearMap.BilinForm K V)
    (hB : B.IsSymm) (W : Submodule K V) (v : V) :
    v ∈ W.orthogonalBilin B ↔ B v ∈ W.dualAnnihilator := by
  rw [Submodule.mem_dualAnnihilator]
  change (∀ w ∈ W, B w v = 0) ↔ ∀ w ∈ W, B v w = 0
  simp only [hB.eq v]

/-- Definition: scalar-product representation restricts to perpendicular and annihilator spaces. -/
noncomputable def orthogonalAnnihilatorEquiv [Module.Finite K V]
    (B : LinearMap.BilinForm K V) (hB : B.IsSymm) (hn : B.SeparatingLeft)
    (W : Submodule K V) : W.orthogonalBilin B ≃ₗ[K] W.dualAnnihilator := by
  let e := scalarProductEquiv B hn
  refine LinearEquiv.ofBijective
    (B.domRestrict (W.orthogonalBilin B) |>.codRestrict W.dualAnnihilator
      (fun v => (mem_orthogonalBilin_iff_mem_dualAnnihilator B hB W v).mp v.property)) ?_
  constructor

  · intro x y h
    apply Subtype.ext
    apply (scalarProduct_bijective B hn).1
    exact congrArg (fun z : W.dualAnnihilator => (z : Module.Dual K V)) h

  · intro φ
    have hv : e.symm φ ∈ W.orthogonalBilin B := by
      apply (mem_orthogonalBilin_iff_mem_dualAnnihilator B hB W _).mpr
      change e (e.symm (φ : Module.Dual K V)) ∈ W.dualAnnihilator
      rw [e.apply_symm_apply]
      exact φ.property
    exact ⟨⟨e.symm φ, hv⟩, Subtype.ext (e.apply_symm_apply φ)⟩

/-- Theorem: nondegenerate symmetric forms give complementary perpendicular dimensions. -/
theorem finrank_add_finrank_orthogonalBilin [Module.Finite K V]
    (B : LinearMap.BilinForm K V) (hB : B.IsSymm) (hn : B.SeparatingLeft)
    (W : Submodule K V) :
    finrank K W + finrank K (W.orthogonalBilin B) = finrank K V := by
  let e := orthogonalAnnihilatorEquiv B hB hn W
  have he := LinearMappings.finrank_eq_of_bijective (K := K)
    (V := W.orthogonalBilin B) (W := W.dualAnnihilator) e.toLinearMap e.bijective
  rw [he]
  exact finrank_add_finrank_dualAnnihilator_eq W

end LinearAlgebra.ScalarProductsAndOrthogonality
