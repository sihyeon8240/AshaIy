import Textbooks.LinearAlgebra.Determinants.Multiplicativity
import Textbooks.LinearAlgebra.LinearMapsAndMatrices.MatrixMaps

namespace LinearAlgebra.Determinants

open Matrix Equiv Finset Function
open scoped BigOperators

variable {K : Type*} [Field K] {n : ℕ}

/-- Theorem: the standard alternating form evaluated on columns is the determinant. -/
theorem det_cols (A : Matrix (Fin n) (Fin n) K) :
    Matrix.detRowAlternating A.col = A.det := by
  change A.transpose.det = A.det
  exact det_transpose A

/-- Theorem: the determinant of a one by one matrix is its sole entry. -/
theorem det_fin_one (A : Matrix (Fin 1) (Fin 1) K) : A.det = A 0 0 := by
  rw [det_apply]
  simp only [Finset.univ_unique, Finset.sum_singleton, Finset.prod_singleton]

  have hσ : (default : Equiv.Perm (Fin 1)) = 1 := Subsingleton.elim _ _
  rw [hσ, map_one, one_smul]
  rfl

/-- Theorem: a column combination replaces its own determinant by its coefficient. -/
theorem det_updateCol_mulVec (A : Matrix (Fin n) (Fin n) K) (x : Fin n → K)
    (j : Fin n) : (A.updateCol j (A *ᵥ x)).det = x j * A.det := by
  change (A.updateCol j (fun i => ∑ k, A i k * x k)).det = _
  have h := det_updateCol_sum A j x
  simpa only [Matrix.mulVec, dotProduct, mul_comm, smul_eq_mul] using h

/-- Theorem: Cramer's rule determines every coordinate of a solution. -/
theorem cramer_rule (A : Matrix (Fin n) (Fin n) K) (hA : A.det ≠ 0)
    (x b : Fin n → K) (hx : A *ᵥ x = b) (j : Fin n) :
    x j = (A.updateCol j b).det / A.det := by
  rw [← hx, det_updateCol_mulVec]
  exact (mul_div_cancel_right₀ (x j) hA).symm

/-- Lemma: a zero column forces the determinant to vanish. -/
theorem det_eq_zero_of_column_zero (A : Matrix (Fin n) (Fin n) K) (j : Fin n)
    (h : A.col j = 0) : A.det = 0 := by
  rw [← det_transpose]
  exact Matrix.detRowAlternating.map_coord_zero j h

/-- Theorem: nonzero determinant implies column independence. -/
theorem linearIndependent_cols_of_det_ne_zero (A : Matrix (Fin n) (Fin n) K)
    (hA : A.det ≠ 0) : LinearIndependent K (Matrices.column A) := by
  apply Fintype.linearIndependent_iff.mpr
  intro x hx j

  have hz : A *ᵥ x = 0 := by
    rw [Matrices.mulVec_eq_combination]
    exact hx

  have hd := det_updateCol_mulVec A x j
  rw [hz, det_eq_zero_of_column_zero _ j (by ext i; simp)] at hd
  exact (mul_eq_zero.mp hd.symm).resolve_right hA

/-- Theorem: a dependent column family has determinant zero. -/
theorem det_eq_zero_of_not_linearIndependent_cols (A : Matrix (Fin n) (Fin n) K)
    (h : ¬LinearIndependent K (Matrices.column A)) : A.det = 0 := by
  by_contra hn
  exact h (linearIndependent_cols_of_det_ne_zero A hn)

/-- Theorem: invertibility is equivalent to a nonzero determinant. -/
theorem isNonsingular_iff_det_ne_zero (A : Matrix (Fin n) (Fin n) K) :
    Matrices.IsNonsingular A ↔ A.det ≠ 0 := by
  constructor

  · rintro ⟨B, hAB, _⟩ hz
    have h := congrArg Matrix.det hAB
    rw [det_mul, det_one, hz, zero_mul] at h
    exact zero_ne_one h

  · intro hA
    exact (LinearMapsAndMatrices.isNonsingular_iff_linearIndependent A).mpr
      (linearIndependent_cols_of_det_ne_zero A hA)

/-- Theorem: column independence is equivalent to a nonzero determinant. -/
theorem linearIndependent_cols_iff_det_ne_zero (A : Matrix (Fin n) (Fin n) K) :
    LinearIndependent K (Matrices.column A) ↔ A.det ≠ 0 :=
  (LinearMapsAndMatrices.isNonsingular_iff_linearIndependent A).symm.trans
    (isNonsingular_iff_det_ne_zero A)

/-- Theorem: determinant zero is equivalent to column dependence. -/
theorem det_eq_zero_iff_dependent (A : Matrix (Fin n) (Fin n) K) :
    A.det = 0 ↔ ¬LinearIndependent K (Matrices.column A) := by
  simpa only [not_not] using (not_congr (linearIndependent_cols_iff_det_ne_zero A)).symm

/-- Theorem: a two-sided inverse has reciprocal determinant. -/
theorem det_inverse (A B : Matrix (Fin n) (Fin n) K) (hAB : A * B = 1)
    (hBA : B * A = 1) : B.det = A.det⁻¹ := by
  have hA := (isNonsingular_iff_det_ne_zero A).mp ⟨B, hAB, hBA⟩

  have hd := congrArg Matrix.det hAB
  rw [det_mul, det_one] at hd

  apply (mul_left_cancel₀ hA)
  rw [hd, mul_inv_cancel₀ hA]

/-- Theorem: a normalized alternating multilinear form is uniquely the determinant.
The arguments are rows; transposition supplies the column formulation. -/
theorem alternating_eq_det (F : (Fin n → K) [⋀^Fin n]→ₗ[K] K)
    (hF : F (fun i => Pi.single i 1) = 1) : F = Matrix.detRowAlternating := by
  apply (Pi.basisFun K (Fin n)).ext_alternating
  intro v hv

  let σ : Equiv.Perm (Fin n) := Equiv.ofBijective v
    ((Finite.injective_iff_bijective).mp hv)
  have he : (fun i => (Pi.basisFun K (Fin n)) (v i)) =
      (fun i => Pi.single i (1 : K)) ∘ σ := by
    simp only [Pi.basisFun_apply]
    rfl

  rw [he, F.map_perm, (Matrix.detRowAlternating :
    (Fin n → K) [⋀^Fin n]→ₗ[K] K).map_perm, hF]

  have hd : Matrix.detRowAlternating (fun i : Fin n => Pi.single i (1 : K)) = 1 := by
    convert (det_one (n := Fin n) (K := K)) using 1
    congr 1
    ext i j
    exact Matrix.one_eq_pi_single.symm

  rw [hd]

/-- Theorem: there exists exactly one normalized alternating multilinear form. -/
theorem exists_unique_determinant :
    ∃! F : (Fin n → K) [⋀^Fin n]→ₗ[K] K,
      F (fun i => Pi.single i 1) = 1 := by
  refine ⟨Matrix.detRowAlternating, ?_, ?_⟩

  · convert (det_one (n := Fin n) (K := K)) using 1
    congr 1
    ext i j
    exact Matrix.one_eq_pi_single.symm

  · intro F hF
    exact alternating_eq_det F hF

end LinearAlgebra.Determinants
