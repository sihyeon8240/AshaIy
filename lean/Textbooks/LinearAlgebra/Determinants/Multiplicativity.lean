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

/-- Lemma: nonbijective choices of intermediate indices cancel in the signed sum. -/
theorem signed_sum_eq_zero_of_nonbijective {M N : Matrix n n K} {p : n → n} (H : ¬Bijective p) :
    (∑ σ : Perm n, ε σ * ∏ x, M (σ x) (p x) * N (p x) x) = 0 := by
  obtain ⟨i, j, hpij, hij⟩ : ∃ i j, p i = p j ∧ i ≠ j := by
    rw [← Finite.injective_iff_bijective, Injective] at H
    push Not at H
    exact H

  exact
    sum_involution (fun σ _ => σ * Equiv.swap i j)
      (fun σ _ => by
        have : (∏ x, M (σ x) (p x)) = ∏ x, M ((σ * Equiv.swap i j) x) (p x) :=
          Fintype.prod_equiv (swap i j) _ _ (by simp [apply_swap_eq_self hpij])

        simp [this, sign_swap hij, -sign_swap', prod_mul_distrib])
      (fun σ _ _ => (not_congr mul_swap_eq_iff).mpr hij) (fun _ _ => mem_univ _) fun σ _ =>
      mul_swap_involutive i j σ

/-- Theorem: the determinant of a product is the product of the determinants. -/
theorem det_mul (M N : Matrix n n K) : det (M * N) = det M * det N :=
  calc
    det (M * N) = ∑ p : n → n, ∑ σ : Perm n, ε σ * ∏ i, M (σ i) (p i) * N (p i) i := by
      simp only [det_apply', Matrix.mul_apply, prod_univ_sum, mul_sum, Fintype.piFinset_univ]
      rw [Finset.sum_comm]

    _ = ∑ p : n → n with Bijective p, ∑ σ : Perm n, ε σ * ∏ i, M (σ i) (p i) * N (p i) i := by
      refine (sum_subset (filter_subset _ _)
        fun f _ hbij ↦ signed_sum_eq_zero_of_nonbijective ?_).symm
      simpa only [mem_filter_univ] using hbij

    _ = ∑ τ : Perm n, ∑ σ : Perm n, ε σ * ∏ i, M (σ i) (τ i) * N (τ i) i :=
      sum_bij (fun p h ↦ Equiv.ofBijective p (mem_filter.1 h).2) (fun _ _ ↦ mem_univ _)
        (fun _ _ _ _ h ↦ by injection h)
        (fun b _ ↦ ⟨b, mem_filter.2 ⟨mem_univ _, b.bijective⟩, coe_fn_injective rfl⟩) fun _ _ ↦ rfl

    _ = ∑ σ : Perm n, ∑ τ : Perm n, (∏ i, N (σ i) i) * ε τ * ∏ j, M (τ j) (σ j) := by
      simp only [mul_comm, mul_left_comm, prod_mul_distrib, mul_assoc]

    _ = ∑ σ : Perm n, ∑ τ : Perm n, (∏ i, N (σ i) i) * (ε σ * ε τ) * ∏ i, M (τ i) i :=
      (sum_congr rfl fun σ _ =>
        Fintype.sum_equiv (Equiv.mulRight σ⁻¹) _ _ fun τ => by
          have : (∏ j, M (τ j) (σ j)) = ∏ j, M ((τ * σ⁻¹) j) j := by
            rw [← (σ⁻¹ : _ ≃ _).prod_comp]
            simp

          have h : ε σ * ε (τ * σ⁻¹) = ε τ :=
            calc
              ε σ * ε (τ * σ⁻¹) = ε (τ * σ⁻¹ * σ) := by
                rw [mul_comm, sign_mul (τ * σ⁻¹)]
                simp only [Int.cast_mul, Units.val_mul]
              _ = ε τ := by simp only [inv_mul_cancel_right]

          simp_rw [Equiv.coe_mulRight, h]
          simp only [this])

    _ = det M * det N := by
      simp only [det_apply', Finset.mul_sum, mul_comm, mul_left_comm, mul_assoc]

end LinearAlgebra.Determinants
