import Textbooks.LinearAlgebra.LinearMappings.RankNullity
import Mathlib.LinearAlgebra.UnitaryGroup
import Mathlib.LinearAlgebra.Matrix.NonsingularInverse

namespace LinearAlgebra.SymmetricHermitianAndUnitaryOperators

variable {n : Type*} [Fintype n] [DecidableEq n]

/-- Definition: a real unitary matrix is a member of Mathlib's orthogonal group. -/
abbrev IsOrthogonalMatrix (A : Matrix n n ℝ) : Prop := A ∈ Matrix.orthogonalGroup n ℝ

/-- Lemma: a left inverse of a square real matrix is also a right inverse. -/
private theorem matrix_mul_eq_one_of_mul_eq_one (A B : Matrix n n ℝ) (h : B * A = 1) :
    A * B = 1 := by
  have hi : Function.Injective (Matrix.toLin' A) := by
    intro x y he
    have hx : Matrix.toLin' B (Matrix.toLin' A x) = x := by
      rw [← Matrix.toLin'_mul_apply, h, Matrix.toLin'_one, LinearMap.id_apply]
    have hy : Matrix.toLin' B (Matrix.toLin' A y) = y := by
      rw [← Matrix.toLin'_mul_apply, h, Matrix.toLin'_one, LinearMap.id_apply]
    rw [he, hy] at hx
    exact hx.symm

  have hs := (LinearMappings.bijective_of_injective_of_finrank_eq
    (Matrix.toLin' A) rfl hi).2
  apply Matrix.toLin'.injective
  apply LinearMap.ext
  intro x
  obtain ⟨y, rfl⟩ := hs x
  rw [Matrix.toLin'_mul_apply, Matrix.toLin'_one, LinearMap.id_apply,
    ← Matrix.toLin'_mul_apply B A, h, Matrix.toLin'_one, LinearMap.id_apply]

/-- Proposition: a real matrix is orthogonal exactly when its transpose is a left inverse. -/
theorem isOrthogonalMatrix_iff_transpose_mul (A : Matrix n n ℝ) :
    IsOrthogonalMatrix A ↔ A.transpose * A = 1 := by
  change (A.transpose * A = 1 ∧ A * A.transpose = 1) ↔ A.transpose * A = 1
  exact ⟨And.left, fun h => ⟨h, matrix_mul_eq_one_of_mul_eq_one A A.transpose h⟩⟩

/-- Proposition: a real matrix is orthogonal exactly when it is invertible and its
transpose is its inverse. -/
theorem isOrthogonalMatrix_iff_transpose_eq_inv (A : Matrix n n ℝ) :
    IsOrthogonalMatrix A ↔ IsUnit A ∧ A.transpose = A⁻¹ := by
  rw [isOrthogonalMatrix_iff_transpose_mul]
  constructor

  · intro h
    have hr := matrix_mul_eq_one_of_mul_eq_one A A.transpose h
    have hu : IsUnit A := ⟨⟨A, A.transpose, hr, h⟩, rfl⟩
    exact ⟨hu, (Matrix.inv_eq_left_inv h).symm⟩

  · rintro ⟨hu, he⟩
    rw [he, Matrix.nonsing_inv_mul A ((Matrix.isUnit_iff_isUnit_det A).mp hu)]

end LinearAlgebra.SymmetricHermitianAndUnitaryOperators
