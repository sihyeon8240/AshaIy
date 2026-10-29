import Textbooks.LinearAlgebra.Determinants.Multiplicativity

namespace LinearAlgebra.Determinants

open Equiv Equiv.Perm Matrix
open scoped BigOperators

variable {n : ℕ}

/-- Theorem: every finite permutation is a product of transpositions. -/
theorem exists_list_transpositions (σ : Equiv.Perm (Fin n)) :
    ∃ l : List (Equiv.Perm (Fin n)), l.prod = σ ∧ ∀ τ ∈ l, IsSwap τ := by
  induction σ using Equiv.Perm.swap_induction_on with
  | one => exact ⟨[], rfl, by simp only [List.not_mem_nil, false_implies, forall_const]⟩

  | swap_mul σ i j hij ih =>
    obtain ⟨l, hl, hs⟩ := ih

    refine ⟨Equiv.swap i j :: l, ?_, ?_⟩
    · rw [List.prod_cons, hl]

    · intro τ hτ
      rcases List.mem_cons.mp hτ with rfl | hτ
      · exact ⟨i, j, hij, rfl⟩
      · exact hs τ hτ

/-- Proposition: a transposition is its own inverse. -/
theorem swap_inv (i j : Fin n) : (Equiv.swap i j)⁻¹ = Equiv.swap i j := by
  exact Equiv.symm_swap i j

/-- Proposition: the sign of a transposition is negative.
This is the elementary permutation-sign fact used as finite-counting background. -/
theorem sign_swap (i j : Fin n) (hij : i ≠ j) :
    Equiv.Perm.sign (Equiv.swap i j) = -1 := by
  exact Equiv.Perm.sign_swap hij

/-- Proposition: sign is multiplicative under composition. -/
theorem sign_mul (σ τ : Equiv.Perm (Fin n)) :
    Equiv.Perm.sign (σ * τ) = Equiv.Perm.sign σ * Equiv.Perm.sign τ := by
  exact map_mul Equiv.Perm.sign σ τ

/-- Corollary: the sign of a transposition product is minus one to its length. -/
theorem sign_prod_transpositions (l : List (Equiv.Perm (Fin n)))
    (hl : ∀ τ ∈ l, IsSwap τ) : Equiv.Perm.sign l.prod = (-1) ^ l.length := by
  induction l with
  | nil => exact map_one Equiv.Perm.sign

  | cons τ l ih =>
    have hτ := hl τ (List.mem_cons_self ..)
    obtain ⟨i, j, hij, rfl⟩ := hτ

    rw [List.prod_cons, sign_mul, sign_swap _ _ hij,
      ih (fun τ hτ => hl τ (List.mem_cons_of_mem _ hτ)), List.length_cons, pow_succ']

/-- Corollary: even permutations have transposition decompositions of even length. -/
theorem sign_prod_eq_one_iff_even (l : List (Equiv.Perm (Fin n)))
    (hl : ∀ τ ∈ l, IsSwap τ) : Equiv.Perm.sign l.prod = 1 ↔ Even l.length := by
  have h := sign_prod_transpositions l hl
  have hc : ((Equiv.Perm.sign l.prod : ℤˣ) : ℤ) = (-1 : ℤ) ^ l.length := by
    rw [h, Units.val_pow_eq_pow_val]
    rfl

  rw [← Units.val_inj, hc]
  exact neg_one_pow_eq_one_iff_even (by decide : (-1 : ℤ) ≠ 1)

/-- Corollary: odd permutations have transposition decompositions of odd length. -/
theorem sign_prod_eq_neg_one_iff_odd (l : List (Equiv.Perm (Fin n)))
    (hl : ∀ τ ∈ l, IsSwap τ) : Equiv.Perm.sign l.prod = -1 ↔ Odd l.length := by
  have h := sign_prod_transpositions l hl
  have hc : ((Equiv.Perm.sign l.prod : ℤˣ) : ℤ) = (-1 : ℤ) ^ l.length := by
    rw [h, Units.val_pow_eq_pow_val]
    rfl

  rw [← Units.val_inj, hc]
  exact neg_one_pow_eq_neg_one_iff_odd (by decide : (-1 : ℤ) ≠ 1)

/-- Corollary: the sign of the inverse permutation equals the original sign. -/
theorem sign_inv (σ : Equiv.Perm (Fin n)) :
    Equiv.Perm.sign σ⁻¹ = Equiv.Perm.sign σ := by
  rw [map_inv, Int.units_inv_eq_self]

/-- Theorem: a column permutation of the identity has determinant equal to its sign. -/
theorem det_permutationMatrix {K : Type*} [Field K] (σ : Equiv.Perm (Fin n)) :
    ((1 : Matrix (Fin n) (Fin n) K).submatrix id σ).det =
      (Equiv.Perm.sign σ : ℤ) := by
  rw [det_permute', det_one, mul_one]

/-- Theorem: interchanging two columns negates the determinant. -/
theorem det_swap_cols {K : Type*} [Field K] (A : Matrix (Fin n) (Fin n) K)
    (i j : Fin n) (hij : i ≠ j) :
    (A.submatrix id (Equiv.swap i j)).det = -A.det := by
  rw [det_permute', Equiv.Perm.sign_swap hij]
  simp only [Int.cast_neg, Int.cast_one, Int.reduceNeg, Units.val_neg,
    Units.val_one, neg_mul, one_mul]

/-- Theorem: interchanging two rows negates the determinant. -/
theorem det_swap_rows {K : Type*} [Field K] (A : Matrix (Fin n) (Fin n) K)
    (i j : Fin n) (hij : i ≠ j) :
    (A.submatrix (Equiv.swap i j) id).det = -A.det := by
  rw [det_permute, Equiv.Perm.sign_swap hij]
  simp only [Int.cast_neg, Int.cast_one, Int.reduceNeg, Units.val_neg,
    Units.val_one, neg_mul, one_mul]

/-- Lemma: simultaneous linear combinations expand as a signed permutation sum. -/
theorem det_column_combinations {K : Type*} [Field K]
    (X B : Matrix (Fin n) (Fin n) K) :
    (X * B).det = ∑ σ : Equiv.Perm (Fin n),
      (((Equiv.Perm.sign σ : ℤ) : K) * ∏ i, B (σ i) i) * X.det := by
  rw [det_mul, det_apply' B, mul_comm X.det, Finset.sum_mul]

end LinearAlgebra.Determinants
