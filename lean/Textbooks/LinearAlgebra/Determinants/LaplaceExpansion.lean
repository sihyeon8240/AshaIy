/-
Copyright (c) 2018 Kenny Lau. All rights reserved.
Released under Apache 2.0 license; see LICENSE-Mathlib in this directory.
Authors: Kenny Lau, Chris Hughes, Anne Baanen

Proofs adapted from Mathlib.LinearAlgebra.Matrix.Determinant.Basic.
-/
import Textbooks.LinearAlgebra.Determinants.Determinant

namespace LinearAlgebra.Determinants

open Matrix Equiv Equiv.Perm Finset Function
open scoped BigOperators

variable {n : Type*} [DecidableEq n] [Fintype n]
variable {K : Type*} [Field K]

local notation "ε " σ:arg => ((sign σ : ℤ) : K)

/-- Theorem: Laplace expansion along the first column. -/
theorem det_succ_column_zero {n : ℕ} (A : Matrix (Fin n.succ) (Fin n.succ) K) :
    det A = ∑ i : Fin n.succ, (-1) ^ (i : ℕ) * A i 0 * det (A.submatrix i.succAbove Fin.succ) := by
  rw [Matrix.det_apply, Finset.univ_perm_fin_succ, ← Finset.univ_product_univ]
  simp only [Finset.sum_map, Equiv.toEmbedding_apply, Finset.sum_product, Matrix.submatrix]

  refine Finset.sum_congr rfl fun i _ => Fin.cases ?_ (fun i => ?_) i
  · simp only [Fin.prod_univ_succ, Matrix.det_apply, Finset.mul_sum,
      Equiv.Perm.decomposeFin_symm_apply_zero, Fin.val_zero, one_mul,
      Equiv.Perm.decomposeFin.symm_sign, Equiv.swap_self, ite_true, id,
      Equiv.Perm.decomposeFin_symm_apply_succ, Fin.succAbove_zero, Equiv.coe_refl, pow_zero,
      mul_smul_comm, of_apply]

  -- Align the permutation decomposition with the increasing minor indices.
  have : (-1 : K) ^ (i : ℕ) = (Perm.sign i.cycleRange) := by simp [Fin.sign_cycleRange]
  rw [Fin.val_succ, pow_succ', this, mul_assoc, mul_assoc, mul_left_comm (ε _),
    ← det_permute, Matrix.det_apply, Finset.mul_sum, Finset.mul_sum]

  refine Finset.sum_congr rfl fun σ _ => ?_
  rw [Equiv.Perm.decomposeFin.symm_sign, ite_eq_right (Fin.succ_ne_zero i)]
  calc
    ((-1 * Perm.sign σ : ℤ) • ∏ i', A (Perm.decomposeFin.symm (Fin.succ i, σ) i') i') =
        (-1 * Perm.sign σ : ℤ) • (A (Fin.succ i) 0 *
          ∏ i', A ((Fin.succ i).succAbove (Fin.cycleRange i (σ i'))) i'.succ) := by
      simp only [Fin.prod_univ_succ, Fin.succAbove_cycleRange,
        Equiv.Perm.decomposeFin_symm_apply_zero, Equiv.Perm.decomposeFin_symm_apply_succ]
    _ = -1 * (A (Fin.succ i) 0 * (Perm.sign σ : ℤ) •
        ∏ i', A ((Fin.succ i).succAbove (Fin.cycleRange i (σ i'))) i'.succ) := by
      simp [_root_.neg_mul, one_mul, zsmul_eq_mul, neg_smul,
        Fin.succAbove_cycleRange, mul_left_comm]

/-- Theorem: Laplace expansion along the first row. -/
theorem det_succ_row_zero {n : ℕ} (A : Matrix (Fin n.succ) (Fin n.succ) K) :
    det A = ∑ j : Fin n.succ, (-1) ^ (j : ℕ) * A 0 j * det (A.submatrix Fin.succ j.succAbove) := by
  rw [← det_transpose A, det_succ_column_zero]
  refine Finset.sum_congr rfl fun i _ => ?_
  rw [← det_transpose]
  simp only [transpose_apply, transpose_submatrix, transpose_transpose]

/-- Theorem: Laplace expansion along any row, with zero-based cofactor signs. -/
theorem det_succ_row {n : ℕ} (A : Matrix (Fin n.succ) (Fin n.succ) K) (i : Fin n.succ) :
    det A =
      ∑ j : Fin n.succ, (-1) ^ (i + j : ℕ) * A i j * det (A.submatrix i.succAbove j.succAbove) := by
  simp_rw [pow_add, mul_assoc, ← mul_sum]

  have : det A = (-1 : K) ^ (i : ℕ) * (Perm.sign i.cycleRange⁻¹) * det A := by
    calc
      det A = ↑((-1 : ℤˣ) ^ (i : ℕ) * (-1 : ℤˣ) ^ (i : ℕ) : ℤˣ) * det A := by simp
      _ = (-1 : K) ^ (i : ℕ) * (Perm.sign i.cycleRange⁻¹) * det A := by simp [-Int.units_mul_self]

  rw [this, mul_assoc]
  congr

  rw [← det_permute, det_succ_row_zero]
  refine Finset.sum_congr rfl fun j _ => ?_
  rw [mul_assoc, Matrix.submatrix_apply, submatrix_submatrix, id_comp, Function.comp_def, id]
  simp

/-- Theorem: Laplace expansion along any column, with zero-based cofactor signs. -/
theorem det_succ_column {n : ℕ} (A : Matrix (Fin n.succ) (Fin n.succ) K) (j : Fin n.succ) :
    det A =
      ∑ i : Fin n.succ, (-1) ^ (i + j : ℕ) * A i j * det (A.submatrix i.succAbove j.succAbove) := by
  rw [← det_transpose, det_succ_row _ j]
  refine Finset.sum_congr rfl fun i _ => ?_
  rw [add_comm, ← det_transpose, transpose_apply, transpose_submatrix, transpose_transpose]

end LinearAlgebra.Determinants
