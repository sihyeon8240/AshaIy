module

public import Textbooks.LinearAlgebra.SymmetricHermitianAndUnitaryOperators.Adjoint
public import Textbooks.LinearAlgebra.LinearMappings.RankNullity

import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

public section

namespace LinearAlgebra.SymmetricHermitianAndUnitaryOperators

variable {𝕜 E : Type*} [RCLike 𝕜] [NormedAddCommGroup E] [InnerProductSpace 𝕜 E]

local notation "⟪" x ", " y "⟫" => inner 𝕜 x y

/-- Definition: a real or complex unitary operator preserves the fixed inner product. -/
def IsUnitary (A : Module.End 𝕜 E) : Prop := ∀ v w, ⟪A v, A w⟫ = ⟪v, w⟫

/-- Lemma: expansion of the squared norm of a sum recovers the real mixed term. -/
theorem norm_add_sq (v w : E) :
    ‖v + w‖ ^ 2 = ‖v‖ ^ 2 + 2 * RCLike.re ⟪v, w⟫ + ‖w‖ ^ 2 := by
  rw [norm_sq_eq_re_inner (𝕜 := 𝕜)]
  simp only [inner_add_left, inner_add_right, map_add, ← norm_sq_eq_re_inner,
    inner_re_symm w v]
  ring

/-- Lemma: preservation of norms forces preservation of the real part of the inner product. -/
theorem re_inner_map_eq_of_norm_map (A : Module.End 𝕜 E)
    (h : ∀ v, ‖A v‖ = ‖v‖) (v w : E) :
    RCLike.re ⟪A v, A w⟫ = RCLike.re ⟪v, w⟫ := by
  have hA := norm_add_sq (𝕜 := 𝕜) (A v) (A w)
  have hV := norm_add_sq (𝕜 := 𝕜) v w
  rw [← map_add, h, h, h] at hA
  linarith

/-- Theorem: an operator is unitary exactly when it preserves every norm. -/
theorem isUnitary_iff_norm_map (A : Module.End 𝕜 E) :
    IsUnitary A ↔ ∀ v, ‖A v‖ = ‖v‖ := by
  constructor

  · intro h v
    have he := congrArg RCLike.re (h v v)
    rw [← norm_sq_eq_re_inner, ← norm_sq_eq_re_inner] at he
    nlinarith [norm_nonneg (A v), norm_nonneg v]

  · intro h v w
    apply RCLike.ext

    · exact re_inner_map_eq_of_norm_map A h v w

    · have hi := re_inner_map_eq_of_norm_map A h v ((RCLike.I : 𝕜) • w)
      simpa only [map_smul, inner_smul_right, RCLike.I_mul_re, neg_inj] using hi

/-- Theorem: preserving unit vectors is equivalent to preserving every norm, including zero. -/
theorem norm_map_iff_unit_vectors (A : Module.End 𝕜 E) :
    (∀ v, ‖A v‖ = ‖v‖) ↔ ∀ v, ‖v‖ = 1 → ‖A v‖ = 1 := by
  constructor

  · intro h v hv
    rw [h, hv]

  · intro h v
    by_cases hv : v = 0

    · rw [hv, map_zero]

    have hn : ‖v‖ ≠ 0 := norm_ne_zero_iff.mpr hv
    have hu : ‖(‖v‖ : 𝕜)⁻¹ • v‖ = 1 := by
      rw [ScalarProductsAndOrthogonality.norm_smul, norm_inv, RCLike.norm_ofReal,
        abs_of_nonneg (norm_nonneg v), inv_mul_cancel₀ hn]

    have he := h _ hu
    rw [map_smul, ScalarProductsAndOrthogonality.norm_smul, norm_inv,
      RCLike.norm_ofReal, abs_of_nonneg (norm_nonneg v)] at he
    calc
      ‖A v‖ = ‖v‖ * (‖v‖⁻¹ * ‖A v‖) := by rw [← mul_assoc, mul_inv_cancel₀ hn, one_mul]
      _ = ‖v‖ := by rw [he, mul_one]

/-- Corollary: an operator is unitary exactly when it takes unit vectors to unit vectors. -/
theorem isUnitary_iff_unit_vectors (A : Module.End 𝕜 E) :
    IsUnitary A ↔ ∀ v, ‖v‖ = 1 → ‖A v‖ = 1 :=
  (isUnitary_iff_norm_map A).trans (norm_map_iff_unit_vectors A)

/-- Corollary: a unitary operator preserves perpendicularity. -/
theorem IsUnitary.inner_eq_zero {A : Module.End 𝕜 E} (hA : IsUnitary A)
    {v w : E} (h : ⟪v, w⟫ = 0) : ⟪A v, A w⟫ = 0 := by
  rw [hA, h]

/-- Lemma: a norm-preserving operator is injective. -/
theorem IsUnitary.injective {A : Module.End 𝕜 E} (hA : IsUnitary A) :
    Function.Injective A := by
  intro v w he
  apply sub_eq_zero.mp
  apply norm_eq_zero.mp
  rw [← (isUnitary_iff_norm_map A).mp hA, map_sub, he, sub_self, norm_zero]

variable [Module.Finite 𝕜 E]

/-- Theorem: unitarity is equivalent to the adjoint being a left inverse.
Over the reals this is the transpose criterion. -/
theorem isUnitary_iff_adjoint_mul_self (A : Module.End 𝕜 E) :
    IsUnitary A ↔ adjoint A * A = 1 := by
  constructor

  · intro h
    ext w
    apply eq_of_inner_left_eq (𝕜 := 𝕜)
    intro v
    change ⟪adjoint A (A w), v⟫ = ⟪w, v⟫
    rw [adjoint_inner_left, h]

  · intro h v w
    rw [inner_adjoint_right]
    have hw := congrArg (fun C : Module.End 𝕜 E => C w) h
    change adjoint A (A w) = w at hw
    rw [hw]

/-- Corollary: a unitary operator on a finite-dimensional space is invertible. -/
theorem IsUnitary.bijective {A : Module.End 𝕜 E} (hA : IsUnitary A) :
    Function.Bijective A :=
  LinearMappings.bijective_of_injective_of_finrank_eq A rfl hA.injective

/-- Definition: the linear equivalence supplied by a unitary operator. -/
noncomputable def unitaryEquiv (A : Module.End 𝕜 E) (hA : IsUnitary A) : E ≃ₗ[𝕜] E :=
  LinearEquiv.ofBijective A hA.bijective

/-- Theorem: a unitary operator takes an orthonormal basis to an orthonormal basis. -/
theorem IsUnitary.map_basis {ι : Type*} [Fintype ι] {A : Module.End 𝕜 E}
    (hA : IsUnitary A) (b : Module.Basis ι 𝕜 E) (hb : Orthonormal 𝕜 b) :
    ∃ c : Module.Basis ι 𝕜 E, (∀ i, c i = A (b i)) ∧ Orthonormal 𝕜 c := by
  let c := b.map (unitaryEquiv A hA)
  have hc (i : ι) : c i = A (b i) := rfl
  refine ⟨c, hc, ?_⟩
  classical
  rw [orthonormal_iff_ite]
  intro i j
  rw [hc, hc, hA, orthonormal_iff_ite.mp hb]

omit [Module.Finite 𝕜 E] in
/-- Theorem: taking one orthonormal basis to another forces unitarity. -/
theorem isUnitary_of_map_basis {ι : Type*} [Fintype ι] (A : Module.End 𝕜 E)
    (b c : Module.Basis ι 𝕜 E) (hb : Orthonormal 𝕜 b) (hc : Orthonormal 𝕜 c)
    (h : ∀ i, A (b i) = c i) : IsUnitary A := by
  classical
  intro v w
  rw [← b.sum_repr v, ← b.sum_repr w]
  simp only [map_sum, map_smul, sum_inner, inner_sum, inner_smul_left,
    inner_smul_right, h, orthonormal_iff_ite.mp hb, orthonormal_iff_ite.mp hc]

end LinearAlgebra.SymmetricHermitianAndUnitaryOperators
