module

public import Textbooks.LinearAlgebra.SymmetricHermitianAndUnitaryOperators.Adjoint
public import Mathlib.LinearAlgebra.Matrix.Hermitian

import Mathlib.Tactic.LinearCombination
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring
import Mathlib.Tactic.NormNum

public section

namespace LinearAlgebra.SymmetricHermitianAndUnitaryOperators

variable {E : Type*} [NormedAddCommGroup E] [InnerProductSpace ℂ E]

local notation "⟪" x ", " y "⟫" => inner ℂ x y

/-- Definition: a complex Hermitian matrix equals its conjugate transpose. -/
abbrev IsHermitianMatrix {n : Type*} (A : Matrix n n ℂ) : Prop := A.IsHermitian

/-- Proposition: the Hermitian matrix condition is conjugate symmetry of its entries. -/
theorem isHermitianMatrix_iff {n : Type*} (A : Matrix n n ℂ) :
    IsHermitianMatrix A ↔ ∀ i j, star (A j i) = A i j := by
  change A.conjTranspose = A ↔ _
  exact Matrix.ext_iff.symm

/-- Lemma: expanding the difference of diagonal values isolates the mixed terms. -/
theorem polarization (A : Module.End ℂ E) (v w : E) :
    ⟪A (v + w), v + w⟫ - ⟪A (v - w), v - w⟫ =
      2 * (⟪A w, v⟫ + ⟪A v, w⟫) := by
  simp only [map_add, map_sub, inner_add_left, inner_add_right,
    inner_sub_left, inner_sub_right]
  ring

/-- Theorem: over the complex numbers, an operator with zero diagonal is zero. -/
theorem eq_zero_of_inner_map_self_eq_zero (A : Module.End ℂ E)
    (h : ∀ v, ⟪A v, v⟫ = 0) : A = 0 := by
  have mixed (v w : E) : ⟪A v, w⟫ = 0 := by
    have hp := polarization A v w
    rw [h, h, sub_self] at hp

    have hi := polarization A v (Complex.I • w)
    simp only [h, sub_self, map_smul, inner_smul_left, inner_smul_right,
      Complex.conj_I] at hi
    have hs : ⟪A w, v⟫ + ⟪A v, w⟫ = 0 := by
      linear_combination -hp / 2
    have ht : -Complex.I * ⟪A w, v⟫ + Complex.I * ⟪A v, w⟫ = 0 := by
      linear_combination -hi / 2
    have hz : (2 * Complex.I) * ⟪A v, w⟫ = 0 := by
      linear_combination Complex.I * hs + ht
    exact (mul_eq_zero.mp hz).resolve_left
      (mul_ne_zero (by norm_num) Complex.I_ne_zero)

  ext v
  apply (inner_self_eq_zero (𝕜 := ℂ)).mp
  exact mixed v (A v)

variable [Module.Finite ℂ E]

/-- Theorem: an operator is Hermitian exactly when all its diagonal values are real. -/
theorem isHermitian_iff_inner_map_self_real (A : Module.End ℂ E) :
    IsHermitian A ↔ ∀ v, (⟪A v, v⟫).im = 0 := by
  constructor

  · intro h v
    have he : star ⟪A v, v⟫ = ⟪A v, v⟫ := by
      calc
        star ⟪A v, v⟫ = ⟪v, A v⟫ := inner_conj_symm _ _
        _ = ⟪A v, v⟫ := (h v v).symm
    have hi := congrArg Complex.im he
    change -(⟪A v, v⟫).im = (⟪A v, v⟫).im at hi
    linarith

  · intro h
    have hz : A - adjoint A = 0 := by
      apply eq_zero_of_inner_map_self_eq_zero
      intro v
      rw [LinearMap.sub_apply, inner_sub_left, adjoint_inner_left,
        ← inner_conj_symm v (A v)]
      apply sub_eq_zero.mpr
      apply Complex.ext

      · rfl

      · simp only [Complex.conj_im, h, neg_zero]

    exact (isSymmetric_iff_adjoint_eq A).mpr (sub_eq_zero.mp hz).symm

end LinearAlgebra.SymmetricHermitianAndUnitaryOperators
