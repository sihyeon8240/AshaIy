/-
Copyright (c) 2018 Kenny Lau. All rights reserved.
Released under Apache 2.0 license; see LICENSE-Mathlib in this directory.
Authors: Kenny Lau, Chris Hughes, Anne Baanen

Proofs adapted from Mathlib.LinearAlgebra.Matrix.Determinant.Basic.
-/
import Mathlib.LinearAlgebra.Matrix.Determinant.Basic

namespace LinearAlgebra.Determinants

open Matrix Equiv Equiv.Perm Finset Function
open scoped BigOperators

variable {n : Type*} [DecidableEq n] [Fintype n]
variable {K : Type*} [Field K]

local notation "ε " σ:arg => ((sign σ : ℤ) : K)

/-- Theorem: the determinant is the signed permutation sum. -/
theorem det_apply (M : Matrix n n K) : M.det = ∑ σ : Perm n, Equiv.Perm.sign σ • ∏ i, M (σ i) i :=
  MultilinearMap.alternatization_apply _ M

/-- Theorem: the Leibniz formula uses the integer sign cast into the coefficient field. -/
theorem det_apply' (M : Matrix n n K) : M.det = ∑ σ : Perm n, ε σ * ∏ i, M (σ i) i := by
  simp [det_apply, Units.smul_def]

/-- Theorem: the determinant of a diagonal matrix is the product of its diagonal entries. -/
theorem det_diagonal {d : n → K} : det (diagonal d) = ∏ i, d i := by
  rw [det_apply']

  refine (Finset.sum_eq_single 1 ?_ ?_).trans ?_
  · rintro σ - h2
    obtain ⟨x, h3⟩ := not_forall.1 (mt Equiv.ext h2)

    convert! mul_zero (ε σ)
    apply Finset.prod_eq_zero (mem_univ x)
    exact ite_eq_right h3

  · simp

  · simp

/-- Theorem: the identity matrix has determinant one. -/
theorem det_one : det (1 : Matrix n n K) = 1 := by
  rw [← diagonal_one, det_diagonal]
  exact Finset.prod_const_one

/-- Theorem: transposing a matrix preserves its determinant. -/
theorem det_transpose (M : Matrix n n K) : Mᵀ.det = M.det := by
  rw [det_apply', det_apply']

  refine Fintype.sum_bijective _ inv_involutive.bijective _ _ ?_
  intro σ
  rw [sign_inv]

  congr 1
  apply Fintype.prod_equiv σ
  simp

/-- Theorem: permuting rows multiplies the determinant by the permutation sign. -/
theorem det_permute (σ : Perm n) (M : Matrix n n K) :
    (M.submatrix σ id).det = Perm.sign σ * M.det :=
  ((detRowAlternating : (n → K) [⋀^n]→ₗ[K] K).map_perm M σ).trans (by simp [Units.smul_def, det])

/-- Theorem: permuting columns multiplies the determinant by the permutation sign. -/
theorem det_permute' (σ : Perm n) (M : Matrix n n K) :
    (M.submatrix id σ).det = Perm.sign σ * M.det := by
  rw [← det_transpose, transpose_submatrix, det_permute, det_transpose]

/-- Theorem: a matrix with two equal rows has determinant zero. -/
theorem det_zero_of_row_eq {M : Matrix n n K} {i j : n}
    (i_ne_j : i ≠ j) (hij : M i = M j) : M.det = 0 :=
  (detRowAlternating : (n → K) [⋀^n]→ₗ[K] K).map_eq_zero_of_eq M hij i_ne_j

/-- Theorem: a matrix with two equal columns has determinant zero. -/
theorem det_zero_of_column_eq {M : Matrix n n K} {i j : n}
    (i_ne_j : i ≠ j) (hij : ∀ k, M k i = M k j) : M.det = 0 := by
  rw [← det_transpose, det_zero_of_row_eq i_ne_j]
  exact funext hij

/-- Theorem: the determinant is additive in each row. -/
theorem det_updateRow_add (M : Matrix n n K) (j : n) (u v : n → K) :
    det (updateRow M j <| u + v) = det (updateRow M j u) + det (updateRow M j v) :=
  (detRowAlternating : (n → K) [⋀^n]→ₗ[K] K).map_update_add M j u v

/-- Theorem: the determinant is additive in each column. -/
theorem det_updateCol_add (M : Matrix n n K) (j : n) (u v : n → K) :
    det (updateCol M j <| u + v) = det (updateCol M j u) + det (updateCol M j v) := by
  rw [← det_transpose, ← updateRow_transpose, det_updateRow_add]
  simp only [updateRow_transpose, det_transpose]

/-- Theorem: scaling one row scales the determinant by the same scalar. -/
theorem det_updateRow_smul (M : Matrix n n K) (j : n) (s : K) (u : n → K) :
    det (updateRow M j <| s • u) = s * det (updateRow M j u) :=
  (detRowAlternating : (n → K) [⋀^n]→ₗ[K] K).map_update_smul M j s u

/-- Theorem: scaling one column scales the determinant by the same scalar. -/
theorem det_updateCol_smul (M : Matrix n n K) (j : n) (s : K) (u : n → K) :
    det (updateCol M j <| s • u) = s * det (updateCol M j u) := by
  rw [← det_transpose, ← updateRow_transpose, det_updateRow_smul]
  simp only [updateRow_transpose, det_transpose]

/-- Theorem: replacing a row by a different row gives determinant zero. -/
theorem det_updateRow_eq_zero {M : Matrix n n K} {i j : n} (h : i ≠ j) :
    (M.updateRow j (M i)).det = 0 := det_zero_of_row_eq h (by simp [h])

/-- Theorem: replacing a column by a different column gives determinant zero. -/
theorem det_updateCol_eq_zero {M : Matrix n n K} {i j : n} (h : i ≠ j) :
    (M.updateCol j (fun k ↦ M k i)).det = 0 := det_zero_of_column_eq h (by simp [h])

/-- Theorem: adding a multiple of a different row preserves the determinant. -/
theorem det_updateRow_add_smul_self (A : Matrix n n K) {i j : n} (hij : i ≠ j) (c : K) :
    det (updateRow A i (A i + c • A j)) = det A := by
  simp [det_updateRow_add, det_updateRow_smul,
    det_zero_of_row_eq hij (updateRow_self.trans (updateRow_ne hij.symm).symm)]

/-- Theorem: adding a multiple of a different column preserves the determinant. -/
theorem det_updateCol_add_smul_self (A : Matrix n n K) {i j : n} (hij : i ≠ j) (c : K) :
    det (updateCol A i fun k => A k i + c • A k j) = det A := by
  rw [← det_transpose, ← updateRow_transpose, ← det_transpose A]
  exact det_updateRow_add_smul_self Aᵀ hij c

/-- Lemma: adding a combination of other rows preserves the scaled determinant. -/
theorem det_updateRow_sum_off_diagonal (M : Matrix n n K) {j : n}
    (s : Finset n) (hj : j ∉ s) (c : n → K) (a : K) :
    (M.updateRow j (a • M j + ∑ k ∈ s, (c k) • M k)).det = a • M.det := by
  induction s using Finset.induction_on with
  | empty => rw [Finset.sum_empty, add_zero, smul_eq_mul, det_updateRow_smul, updateRow_eq_self]

  | insert k _ hk h_ind =>
    have h : k ≠ j := fun h ↦ (h ▸ hj) (Finset.mem_insert_self _ _)

    rw [Finset.sum_insert hk, add_comm ((c k) • M k), ← add_assoc, det_updateRow_add,
      det_updateRow_smul, det_updateRow_eq_zero h, mul_zero, add_zero, h_ind]
    exact fun h ↦ hj (Finset.mem_insert_of_mem h)

/-- Theorem: a row combination contributes only the coefficient of the replaced row. -/
theorem det_updateRow_sum (A : Matrix n n K) (j : n) (c : n → K) :
    (A.updateRow j (∑ k, (c k) • A k)).det = (c j) • A.det := by
  convert! det_updateRow_sum_off_diagonal A (Finset.univ.erase j)
    (Finset.univ.notMem_erase j) c (c j)
  rw [← Finset.univ.add_sum_erase _ (Finset.mem_univ j)]

/-- Theorem: a column combination contributes only the coefficient of the replaced column. -/
theorem det_updateCol_sum (A : Matrix n n K) (j : n) (c : n → K) :
    (A.updateCol j (fun k ↦ ∑ i, (c i) • A k i)).det = (c j) • A.det := by
  rw [← det_transpose, ← updateRow_transpose, ← det_transpose A]
  convert! det_updateRow_sum A.transpose j c
  simp only [smul_eq_mul, Finset.sum_apply, Pi.smul_apply, transpose_apply]

end LinearAlgebra.Determinants
