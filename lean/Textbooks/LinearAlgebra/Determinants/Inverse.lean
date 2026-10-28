import Textbooks.LinearAlgebra.Determinants.Characterization
import Textbooks.LinearAlgebra.Determinants.LaplaceExpansion
import Mathlib.LinearAlgebra.Matrix.NonsingularInverse

namespace LinearAlgebra.Determinants

open Matrix
open scoped BigOperators

variable {K : Type*} [Field K] {n : ℕ}

/-- Theorem: replacing a column by a unit vector gives the corresponding cofactor. -/
theorem det_updateCol_single (A : Matrix (Fin (n + 1)) (Fin (n + 1)) K)
    (i j : Fin (n + 1)) :
    (A.updateCol i (Pi.single j 1)).det =
      (-1 : K) ^ (j.val + i.val) * (A.submatrix j.succAbove i.succAbove).det := by
  rw [det_succ_column _ i]

  have hm : (A.updateCol i (Pi.single j 1)).submatrix j.succAbove i.succAbove =
      A.submatrix j.succAbove i.succAbove := by
    ext a b
    simp only [Matrix.submatrix_apply, Matrix.updateCol_apply,
      Fin.succAbove_ne, ite_false]

  simp only [Matrix.updateCol_self, Pi.single_apply, mul_ite, mul_one, mul_zero,
    ite_mul, zero_mul, Finset.sum_ite_eq', Finset.mem_univ, ite_true, hm]

/-- Theorem: Cramer determinants give every entry of a two-sided inverse. -/
theorem inverse_apply (A B : Matrix (Fin n) (Fin n) K)
    (hA : A.det ≠ 0) (hAB : A * B = 1) (i j : Fin n) :
    B i j = (A.updateCol i (Pi.single j 1)).det / A.det := by
  apply cramer_rule A hA (fun k => B k j) (Pi.single j 1) _ i
  ext k

  have h := congrArg (fun M : Matrix (Fin n) (Fin n) K => M k j) hAB
  simpa only [Matrix.mulVec, dotProduct, Matrix.mul_apply, Matrix.one_apply,
    Pi.single_apply, eq_comm] using h

/-- Theorem: the matrix of Cramer quotients is a two-sided inverse. -/
theorem cramer_matrix_inverse (A : Matrix (Fin n) (Fin n) K) (hA : A.det ≠ 0) :
    let B : Matrix (Fin n) (Fin n) K :=
      Matrix.of fun i j => (A.updateCol i (Pi.single j 1)).det / A.det
    A * B = 1 ∧ B * A = 1 := by
  obtain ⟨C, hAC, hCA⟩ := (isNonsingular_iff_det_ne_zero A).mpr hA

  have he : C = Matrix.of (fun i j => (A.updateCol i (Pi.single j 1)).det / A.det) := by
    ext i j
    exact inverse_apply A C hA hAC i j

  simpa only [← he] using And.intro hAC hCA

/-- Theorem: the standard inverse has Cramer's entries. -/
theorem inv_apply (A : Matrix (Fin n) (Fin n) K) (hA : A.det ≠ 0) (i j : Fin n) :
    A⁻¹ i j = (A.updateCol i (Pi.single j 1)).det / A.det := by
  obtain ⟨B, hAB, hBA⟩ := (isNonsingular_iff_det_ne_zero A).mpr hA

  rw [Matrix.inv_eq_left_inv hBA]
  exact inverse_apply A B hA hAB i j

/-- Theorem: the inverse is the transpose of the cofactor matrix divided by the determinant. -/
theorem inv_apply_cofactor (A : Matrix (Fin (n + 1)) (Fin (n + 1)) K)
    (hA : A.det ≠ 0) (i j : Fin (n + 1)) :
    A⁻¹ i j = (-1 : K) ^ (j.val + i.val) *
      (A.submatrix j.succAbove i.succAbove).det / A.det := by
  rw [inv_apply A hA, det_updateCol_single]

/-- Corollary: the determinant of the standard inverse is the reciprocal determinant. -/
theorem det_inv (A : Matrix (Fin n) (Fin n) K) (hA : A.det ≠ 0) :
    A⁻¹.det = A.det⁻¹ := by
  obtain ⟨B, hAB, hBA⟩ := (isNonsingular_iff_det_ne_zero A).mpr hA

  rw [Matrix.inv_eq_left_inv hBA]
  exact det_inverse A B hAB hBA

end LinearAlgebra.Determinants
