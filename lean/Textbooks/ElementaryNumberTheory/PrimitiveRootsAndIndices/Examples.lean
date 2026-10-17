import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.Applications
import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.RootLifting
import Mathlib.Tactic.FinCases

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

/-- Lemma: testing the finitely many smaller positive exponents determines an order. -/
theorem orderOf_eq_of_fin_test {M : Type*} [Monoid M] (a : M) (k : ℕ) (hk : 0 < k)
    (hperiod : a ^ k = 1) (hsmall : ∀ i : Fin k, 0 < i.val → a ^ i.val ≠ 1) :
    orderOf a = k := by
  apply (orderOf_eq_iff hk).mpr
  exact ⟨hperiod, fun i hi hipos => hsmall ⟨i, hi⟩ hipos⟩

/-- Lemma: the finite form of the least-positive-period test for primitive roots. -/
theorem isPrimitiveRoot_iff_fin_test {M : Type*} [CommMonoid M] (a : M)
    (k : ℕ) (hk : 0 < k) :
    IsPrimitiveRoot a k ↔ a ^ k = 1 ∧ ∀ i : Fin k, 0 < i.val → a ^ i.val ≠ 1 := by
  rw [isPrimitiveRoot_iff_orderOf _ _, orderOf_eq_iff hk]
  exact and_congr_right fun _ =>
    ⟨fun h i hipos => h i.val i.isLt hipos, fun h i hi hipos => h ⟨i, hi⟩ hipos⟩

/-- Proposition: two has order three modulo seven. -/
theorem orderOf_two_mod_seven : orderOf (2 : ZMod 7) = 3 := by
  exact orderOf_eq_of_fin_test _ _ (by decide) (by decide) (by decide)

/-- Proposition: the orders of the twelve nonzero classes modulo thirteen. -/
theorem orders_mod_thirteen :
    (fun i : Fin 12 => orderOf ((i.val + 1 : ℕ) : ZMod 13)) =
      ![1, 12, 3, 6, 4, 12, 12, 4, 3, 6, 12, 2] := by
  funext i
  fin_cases i <;> exact orderOf_eq_of_fin_test _ _ (by decide) (by decide) (by decide)

/-- Proposition: every unit modulo twelve has period two. -/
theorem units_mod_twelve_pow_two : ∀ a : (ZMod 12)ˣ, a ^ 2 = 1 := by decide

/-- Proposition: twelve has no primitive root. -/
theorem not_exists_primitiveRoot_twelve :
    ¬∃ r : (ZMod 12)ˣ, IsPrimitiveRoot r (Nat.totient 12) := by
  exact not_exists_primitiveRoot_mul 3 4 (by decide) (by decide) (by decide)

/-- Proposition: the powers of three modulo seven run through all nonzero classes. -/
theorem powers_three_mod_seven :
    (fun i : Fin 6 => (3 : ZMod 7) ^ (i.val + 1)) = ![3, 2, 6, 4, 5, 1] := by decide

/-- Proposition: two and five are exactly the primitive residues modulo nine. -/
theorem primitive_residues_mod_nine :
    ∀ a : ZMod 9, IsPrimitiveRoot a 6 ↔ a = 2 ∨ a = 5 := by
  simp_rw [isPrimitiveRoot_iff_fin_test _ 6 (by decide)]
  decide

/-- Proposition: the primitive residues modulo thirteen are two, six, seven, and eleven. -/
theorem primitive_residues_mod_thirteen :
    ∀ a : ZMod 13, IsPrimitiveRoot a 12 ↔ a = 2 ∨ a = 6 ∨ a = 7 ∨ a = 11 := by
  simp_rw [isPrimitiveRoot_iff_fin_test _ 12 (by decide)]
  decide

/-- Proposition: three is a primitive root modulo thirty-one. -/
theorem primitiveRoot_three_mod_thirty_one : IsPrimitiveRoot (3 : ZMod 31) 30 := by
  rw [isPrimitiveRoot_iff_fin_test _ 30 (by decide)]
  decide

/-- Proposition: six and twenty-six are exactly the residues of order six modulo thirty-one. -/
theorem residues_order_six_mod_thirty_one :
    ∀ a : ZMod 31, orderOf a = 6 ↔ a = 6 ∨ a = 26 := by
  simp_rw [← isPrimitiveRoot_iff_orderOf _ _, isPrimitiveRoot_iff_fin_test _ 6 (by decide)]
  decide

/-- Proposition: three and ten are primitive modulo forty-nine. -/
theorem primitiveRoots_mod_forty_nine :
    IsPrimitiveRoot (3 : ZMod 49) 42 ∧ IsPrimitiveRoot (10 : ZMod 49) 42 := by
  simp_rw [isPrimitiveRoot_iff_fin_test _ 42 (by decide)]
  decide

/-- Proposition: two is primitive at every positive power of five. -/
theorem primitiveRoot_two_pow_five (k : ℕ) :
    IsPrimitiveRoot (2 : ZMod (5 ^ (k + 1))) (Nat.totient (5 ^ (k + 1))) := by
  simpa only [Int.cast_ofNat] using primitiveRoot_all_prime_powers 5 (by decide) (by decide) 2
    (by
      rw [isPrimitiveRoot_iff_fin_test _ 4 (by decide)]
      decide) (by decide) k

/-- Proposition: three is primitive at every positive power of five. -/
theorem primitiveRoot_three_pow_five (k : ℕ) :
    IsPrimitiveRoot (3 : ZMod (5 ^ (k + 1))) (Nat.totient (5 ^ (k + 1))) := by
  simpa only [Int.cast_ofNat] using primitiveRoot_all_prime_powers 5 (by decide) (by decide) 3
    (by
      rw [isPrimitiveRoot_iff_fin_test _ 4 (by decide)]
      decide) (by decide) k

/-- Proposition: 4x^9=7 modulo thirteen has exactly the residues two, five, and six. -/
theorem solutions_four_mul_pow_nine_mod_thirteen :
    ∀ x : ZMod 13, 4 * x ^ 9 = 7 ↔ x = 2 ∨ x = 5 ∨ x = 6 := by decide

/-- Proposition: x^3=4 modulo thirteen has no solution. -/
theorem no_cube_eq_four_mod_thirteen : ¬∃ x : ZMod 13, x ^ 3 = 4 := by decide

/-- Proposition: x^3=5 modulo thirteen has exactly the residues seven, eight, and eleven. -/
theorem solutions_cube_eq_five_mod_thirteen :
    ∀ x : ZMod 13, x ^ 3 = 5 ↔ x = 7 ∨ x = 8 ∨ x = 11 := by decide

/-- Definition: the positive nonzero representatives modulo thirteen as units. -/
private def unitThirteen (i : Fin 12) : (ZMod 13)ˣ :=
  ZMod.unitOfCoprime (i.val + 1) (by fin_cases i <;> decide)

/-- Definition: the unit represented by two modulo thirteen. -/
private def twoThirteen : (ZMod 13)ˣ := ZMod.unitOfCoprime 2 (by decide)

/-- Lemma: two is primitive modulo thirteen. -/
private theorem twoThirteen_primitive : IsPrimitiveRoot twoThirteen (Nat.totient 13) := by
  have ht : Nat.totient 13 = 12 := by decide
  rw [ht, isPrimitiveRoot_iff_fin_test _ 12 (by decide)]
  decide

/-- Proposition: the positive index table relative to two modulo thirteen. -/
theorem indices_mod_thirteen :
    (fun i : Fin 12 => index 13 twoThirteen twoThirteen_primitive (unitThirteen i)) =
      ![12, 1, 4, 2, 9, 5, 11, 3, 8, 10, 7, 6] := by
  funext i
  fin_cases i <;> exact index_eq_of_pow_eq _ _ _ _ _ (by decide) (by decide) (by decide)

/-- Definition: the positive nonzero representatives modulo five as units. -/
private def unitFive (i : Fin 4) : (ZMod 5)ˣ :=
  ZMod.unitOfCoprime (i.val + 1) (by fin_cases i <;> decide)

/-- Definition: the unit represented by two modulo five. -/
private def twoFive : (ZMod 5)ˣ := ZMod.unitOfCoprime 2 (by decide)

/-- Lemma: two is primitive modulo five. -/
private theorem twoFive_primitive : IsPrimitiveRoot twoFive (Nat.totient 5) := by
  have ht : Nat.totient 5 = 4 := by decide
  rw [ht, isPrimitiveRoot_iff_fin_test _ 4 (by decide)]
  decide

/-- Proposition: the identity has positive index four in the index table modulo five. -/
theorem indices_mod_five :
    (fun i : Fin 4 => index 5 twoFive twoFive_primitive (unitFive i)) = ![4, 1, 3, 2] := by
  funext i
  fin_cases i <;> exact index_eq_of_pow_eq _ _ _ _ _ (by decide) (by decide) (by decide)

/-- Proposition: two is not primitive at a prime Fermat number with index greater than one. -/
theorem not_primitiveRoot_two_fermat (n : ℕ) (hn : 1 < n)
    (hp : (2 ^ (2 ^ n) + 1).Prime) :
    ¬IsPrimitiveRoot (2 : ZMod (2 ^ (2 ^ n) + 1)) (Nat.totient (2 ^ (2 ^ n) + 1)) := by
  let p := 2 ^ (2 ^ n) + 1
  have hneg : (2 : ZMod p) ^ (2 ^ n) = -1 := by
    have hz := ZMod.natCast_self p
    simp only [p, Nat.cast_add, Nat.cast_pow, Nat.cast_ofNat, Nat.cast_one] at hz
    exact eq_neg_of_add_eq_zero_left hz
  have hperiod : (2 : ZMod p) ^ (2 ^ (n + 1)) = 1 := by
    rw [pow_succ (2 : ℕ), pow_mul, hneg, neg_one_sq]
  have hsmall : n + 1 < 2 ^ n := by
    have haux (j : ℕ) : j + 2 + 1 < 2 ^ (j + 2) := by
      induction j with
      | zero => decide
      | succ j ih =>
        rw [pow_succ]
        nlinarith
    obtain ⟨j, hj⟩ : ∃ j : ℕ, n = j + 2 := ⟨n - 2, by omega⟩
    rw [hj]
    exact haux j
  have hlt : 2 ^ (n + 1) < 2 ^ (2 ^ n) := pow_lt_pow_right₀ (by decide : 1 < (2 : ℕ)) hsmall

  intro hr
  have hd := hr.dvd_of_pow_eq_one _ hperiod
  have hle := Nat.le_of_dvd (by positivity : 0 < 2 ^ (n + 1)) hd
  rw [EulersGeneralizationOfFermatsTheorem.totient_prime _ (isPrime_of_prime _ hp),
    Nat.add_sub_cancel] at hle
  omega

end ElementaryNumberTheory.PrimitiveRootsAndIndices
