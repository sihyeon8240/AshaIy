module

public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.TwoSquarePrimes

public section

namespace ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares

/-- Lemma: Euler's four-square identity with the coordinates used in the descent. -/
theorem four_square_identity (a b c d x y z w : ℤ) :
    (a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2) * (x ^ 2 + y ^ 2 + z ^ 2 + w ^ 2) =
      (a * x + b * y + c * z + d * w) ^ 2 +
      (a * y - b * x + c * w - d * z) ^ 2 +
      (a * z - b * w - c * x + d * y) ^ 2 +
      (a * w + b * z - c * y - d * x) ^ 2 := by
  ring

/-- Lemma: products of sums of four integer squares are sums of four integer squares. -/
theorem four_sq_mul {m n : ℤ} (hm : ∃ a b c d : ℤ, m = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2)
    (hn : ∃ x y z w : ℤ, n = x ^ 2 + y ^ 2 + z ^ 2 + w ^ 2) :
    ∃ a b c d : ℤ, m * n = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2 := by
  obtain ⟨a, b, c, d, rfl⟩ := hm
  obtain ⟨x, y, z, w, rfl⟩ := hn
  exact ⟨a * x + b * y + c * z + d * w, a * y - b * x + c * w - d * z,
    a * z - b * w - c * x + d * y, a * w + b * z - c * y - d * x,
    four_square_identity a b c d x y z w⟩

/-- Lemma: an odd prime admits x²+y²+1≡0 with both coordinates between zero and (p-1)/2. -/
theorem exists_sq_add_sq_add_one_modEq (p : ℕ) (hp : p.Prime) (hp2 : p ≠ 2) :
    ∃ x y : ℕ, x ≤ (p - 1) / 2 ∧ y ≤ (p - 1) / 2 ∧
      (x : ℤ) ^ 2 + y ^ 2 + 1 ≡ 0 [ZMOD (p : ℤ)] := by
  let : Fact p.Prime := ⟨hp⟩
  have hodd := Nat.odd_iff.mp (hp.odd_of_ne_two hp2)
  have hinj : Function.Injective (fun i : Fin (p / 2 + 1) => (i.val : ZMod p) ^ 2) := by
    intro i j hij
    have hi : i.val ≤ p / 2 := Nat.le_of_lt_succ i.isLt
    have hj : j.val ≤ p / 2 := Nat.le_of_lt_succ j.isLt
    have hip : i.val < p := by omega
    have hjp : j.val < p := by omega
    rcases (sq_eq_sq_iff_eq_or_eq_neg).mp hij with he | he
    · have := congrArg ZMod.val he
      simp only [ZMod.val_natCast, Nat.mod_eq_of_lt hip, Nat.mod_eq_of_lt hjp] at this
      exact Fin.ext this

    · have hzero : ((i.val + j.val : ℕ) : ZMod p) = 0 := by
        push_cast
        rw [he]
        ring
      have hd := (ZMod.natCast_eq_zero_iff _ _).mp hzero
      have hz : i.val + j.val = 0 := Nat.eq_zero_of_dvd_of_lt hd (by omega)
      apply Fin.ext
      omega

  let f : Fin (p / 2 + 1) ⊕ Fin (p / 2 + 1) → ZMod p :=
    Sum.elim (fun i => (i.val : ZMod p) ^ 2) (fun j => -1 - (j.val : ZMod p) ^ 2)
  obtain ⟨u, v, huv, heq⟩ := Fintype.exists_ne_map_eq_of_card_lt f (by
    simp only [ZMod.card, Fintype.card_sum, Fintype.card_fin]
    omega)

  have hcross (i j : Fin (p / 2 + 1))
      (h : (i.val : ZMod p) ^ 2 = -1 - (j.val : ZMod p) ^ 2) :
      (i.val : ℤ) ^ 2 + j.val ^ 2 + 1 ≡ 0 [ZMOD (p : ℤ)] := by
    apply (ZMod.intCast_eq_intCast_iff _ _ p).mp
    push_cast
    linear_combination h

  cases u with
  | inl i =>
    cases v with
    | inl j => exact (huv (congrArg Sum.inl (hinj heq))).elim
    | inr j => exact ⟨i.val, j.val, by omega, by omega, hcross i j heq⟩

  | inr i =>
    cases v with
    | inl j => exact ⟨j.val, i.val, by omega, by omega, hcross j i heq.symm⟩
    | inr j =>
      have he : (i.val : ZMod p) ^ 2 = (j.val : ZMod p) ^ 2 := by
        change -1 - (i.val : ZMod p) ^ 2 = -1 - (j.val : ZMod p) ^ 2 at heq
        linear_combination -heq
      exact (huv (congrArg Sum.inr (hinj he))).elim

/-- Corollary: some positive multiple kp, with k<p, is a sum of four squares. -/
theorem exists_small_four_sq_multiple (p : ℕ) (hp : p.Prime) :
    ∃ k : ℕ, 0 < k ∧ k < p ∧
      ∃ a b c d : ℤ, (k * p : ℕ) = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2 := by
  by_cases hp2 : p = 2
  · subst p
    exact ⟨1, by decide, by decide, 1, 1, 0, 0, by norm_num⟩

  · obtain ⟨x, y, hx, hy, hxy⟩ := exists_sq_add_sq_add_one_modEq p hp hp2
    have hd : p ∣ x ^ 2 + y ^ 2 + 1 := by
      have := (TheTheoryOfCongruences.modEq_zero_iff _ _).mp hxy
      exact_mod_cast this
    obtain ⟨k, hk⟩ := hd
    have ho := Nat.odd_iff.mp (hp.odd_of_ne_two hp2)
    have hkp : k < p := by
      have hxp : 2 * x < p := by omega
      have hyp : 2 * y < p := by omega
      have hp3 : 3 ≤ p := by
        have := hp.two_le
        omega
      have hxx : (2 * x) ^ 2 ≤ (p - 1) ^ 2 := Nat.pow_le_pow_left (by omega) 2
      have hyy : (2 * y) ^ 2 ≤ (p - 1) ^ 2 := Nat.pow_le_pow_left (by omega) 2
      nlinarith

    refine ⟨k, by nlinarith, hkp, x, y, 1, 0, ?_⟩
    have hk' : (x : ℤ) ^ 2 + y ^ 2 + 1 = p * k := by exact_mod_cast hk
    push_cast
    nlinarith [hk']

end ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares
