module

public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.Thue

import Mathlib.Tactic.Ring

public section

namespace ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares

open PrimitiveRootsAndIndices

/-- Lemma: the two-square product identity, with integer coordinates. -/
theorem two_square_identity (a b c d : ℤ) :
    (a ^ 2 + b ^ 2) * (c ^ 2 + d ^ 2) =
      (a * c + b * d) ^ 2 + (a * d - b * c) ^ 2 := by
  ring

/-- Lemma: products of sums of two integer squares are sums of two integer squares. -/
theorem sq_add_sq_mul {m n : ℤ} (hm : ∃ a b : ℤ, m = a ^ 2 + b ^ 2)
    (hn : ∃ c d : ℤ, n = c ^ 2 + d ^ 2) :
    ∃ x y : ℤ, m * n = x ^ 2 + y ^ 2 := by
  obtain ⟨a, b, rfl⟩ := hm
  obtain ⟨c, d, rfl⟩ := hn
  exact ⟨a * c + b * d, a * d - b * c, two_square_identity a b c d⟩

/-- Lemma: a prime congruent to three modulo four dividing a sum of two squares
divides both coordinates. -/
theorem prime_dvd_sq_add_sq {p : ℕ} (hp : p.Prime) (hp4 : p % 4 = 3)
    {a b : ℤ} (h : (p : ℤ) ∣ a ^ 2 + b ^ 2) : (p : ℤ) ∣ a ∧ (p : ℤ) ∣ b := by
  let : Fact p.Prime := ⟨hp⟩
  have hsum : (a : ZMod p) ^ 2 + (b : ZMod p) ^ 2 = 0 := by
    have := (ZMod.intCast_zmod_eq_zero_iff_dvd _ p).mpr h
    simpa only [Int.cast_add, Int.cast_pow] using this

  have ha0 : (a : ZMod p) = 0 := by
    by_contra ha
    have hs : IsSquare (-1 : ZMod p) := by
      refine ⟨(b : ZMod p) / a, ?_⟩
      apply (mul_right_injective₀ (pow_ne_zero 2 ha))
      field_simp
      linear_combination -hsum
    have hleg := (TheQuadraticReciprocityLaw.legendreSym_eq_one_iff
      (p := p) (a := -1) (by
        simpa only [Int.cast_neg, Int.cast_one] using
          (neg_ne_zero.mpr (one_ne_zero : (1 : ZMod p) ≠ 0)))).mpr
            (by simpa only [Int.cast_neg, Int.cast_one] using hs)
    have hfour := (TheQuadraticReciprocityLaw.legendreSym_neg_one_eq_one_iff
      (p := p) (by omega)).mp hleg
    omega

  have hb0 : (b : ZMod p) = 0 := by
    rw [ha0, zero_pow two_ne_zero, zero_add] at hsum
    exact (sq_eq_zero_iff.mp hsum)

  exact ⟨(ZMod.intCast_zmod_eq_zero_iff_dvd a p).mp ha0,
    (ZMod.intCast_zmod_eq_zero_iff_dvd b p).mp hb0⟩

/-- Theorem: no prime congruent to three modulo four is a sum of two integer squares. -/
theorem not_sq_add_sq_of_mod_four_eq_three {p : ℕ} (hp : p.Prime) (hp4 : p % 4 = 3) :
    ¬∃ a b : ℤ, (p : ℤ) = a ^ 2 + b ^ 2 := by
  rintro ⟨a, b, hab⟩
  have hd : (p : ℤ) ∣ a ^ 2 + b ^ 2 := ⟨1, by linarith⟩
  obtain ⟨⟨c, hc⟩, ⟨d, hd⟩⟩ := prime_dvd_sq_add_sq hp hp4 hd
  have hp' : (1 : ℤ) < p := by exact_mod_cast hp.one_lt
  have hsum : (p : ℤ) * (c ^ 2 + d ^ 2) = 1 := by
    apply mul_left_cancel₀ (by omega : (p : ℤ) ≠ 0)
    rw [hc, hd] at hab
    nlinarith only [hab]
  have hpos : 1 ≤ c ^ 2 + d ^ 2 := by
    have := sq_nonneg c
    have := sq_nonneg d
    nlinarith
  nlinarith

/-- Proposition: at a prime one modulo four, the half-factorial is a square root of minus one. -/
theorem half_factorial_sq_modEq_neg_one {p : ℕ} (hp : p.Prime) (hp4 : p % 4 = 1) :
    (((p - 1) / 2).factorial : ℤ) ^ 2 ≡ -1 [ZMOD (p : ℤ)] := by
  have hpbook := isPrime_of_prime p hp
  have hpm : p = 2 * ((p - 1) / 2) + 1 := by omega
  have heven : Even ((p - 1) / 2) := Nat.even_iff.mpr (by omega)
  have hhalf := FermatsTheorem.half_factorial p ((p - 1) / 2) hpm
  rw [heven.neg_one_pow, one_mul] at hhalf
  have hw := (ZMod.intCast_eq_intCast_iff _ _ p).mpr (FermatsTheorem.wilson p hpbook)
  simp only [Int.cast_natCast, Int.cast_neg, Int.cast_one] at hw
  apply (ZMod.intCast_eq_intCast_iff _ _ p).mp
  simpa only [Int.cast_pow, Int.cast_natCast, Int.cast_neg, Int.cast_one] using hhalf.symm.trans hw

/-- Theorem: an odd prime is a sum of two integer squares exactly when it is one modulo four. -/
theorem prime_sq_add_sq_iff {p : ℕ} (hp : p.Prime) (hp2 : p ≠ 2) :
    (∃ a b : ℤ, (p : ℤ) = a ^ 2 + b ^ 2) ↔ p % 4 = 1 := by
  let : Fact p.Prime := ⟨hp⟩
  constructor
  · intro h
    have ho := Nat.odd_iff.mp (hp.odd_of_ne_two hp2)
    have hn : p % 4 ≠ 3 := fun h3 => not_sq_add_sq_of_mod_four_eq_three hp h3 h
    omega

  · intro hp4
    obtain ⟨a, ha⟩ := (FermatsTheorem.exists_square_eq_neg_one_iff p
      (isPrime_of_prime p hp) (hp.odd_of_ne_two hp2)).mpr hp4
    have ha0 : ¬(p : ℤ) ∣ a := by
      intro hd
      have hc := (ZMod.intCast_eq_intCast_iff _ _ p).mpr ha
      push_cast at hc
      rw [(ZMod.intCast_zmod_eq_zero_iff_dvd a p).mpr hd] at hc
      norm_num at hc

    obtain ⟨x, y, hx0, hy0, hx, hy, hxy⟩ := thue p hp a ha0
    have hd : (p : ℤ) ∣ x ^ 2 + y ^ 2 := by
      apply (ZMod.intCast_zmod_eq_zero_iff_dvd _ p).mp
      have hc := (ZMod.intCast_eq_intCast_iff _ _ p).mpr ha
      have hxyc := (ZMod.intCast_eq_intCast_iff _ _ p).mpr hxy
      push_cast at hc hxyc ⊢
      rw [← hxyc, mul_pow, hc]
      ring

    obtain ⟨k, hk⟩ := hd
    have hp' : (0 : ℤ) < p := by exact_mod_cast hp.pos
    have hpos : 0 < x ^ 2 + y ^ 2 := by
      nlinarith [sq_pos_of_ne_zero hx0, sq_nonneg y]
    have hk1 : k = 1 := by nlinarith
    exact ⟨x, y, by nlinarith [hk]⟩

end ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares
