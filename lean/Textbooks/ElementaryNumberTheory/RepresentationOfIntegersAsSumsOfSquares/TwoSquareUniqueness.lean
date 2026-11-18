module

public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.TwoSquarePrimes

public section

namespace ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares

/-- Corollary: a prime's representation by two positive squares is unique up to order. -/
theorem prime_sq_add_sq_unique {p : ℕ} (hp : p.Prime) {a b c d : ℤ}
    (ha : 0 < a) (hb : 0 < b) (hc : 0 < c) (hd : 0 < d)
    (hab : (p : ℤ) = a ^ 2 + b ^ 2) (hcd : (p : ℤ) = c ^ 2 + d ^ 2) :
    (a = c ∧ b = d) ∨ (a = d ∧ b = c) := by
  have hp' : (0 : ℤ) < p := by exact_mod_cast hp.pos
  have hprod : (p : ℤ) ∣ (a * d - b * c) * (a * d + b * c) := by
    refine ⟨d ^ 2 - b ^ 2, ?_⟩
    calc
      (a * d - b * c) * (a * d + b * c) =
          (a ^ 2 + b ^ 2) * d ^ 2 - b ^ 2 * (c ^ 2 + d ^ 2) := by ring
      _ = (p : ℤ) * (d ^ 2 - b ^ 2) := by
        rw [← hab, ← hcd]
        ring

  rcases PrimesAndTheirDistribution.prime_dvd_mul p
      (PrimitiveRootsAndIndices.isPrime_of_prime p hp) _ _ hprod with hminus | hplus
  · have had : a * d < p := by
      nlinarith [sq_nonneg (a - d), sq_pos_of_pos hb, sq_pos_of_pos hc]
    have hbc : b * c < p := by
      nlinarith [sq_nonneg (b - c), sq_pos_of_pos ha, sq_pos_of_pos hd]
    have hdet : a * d - b * c = 0 := by
      rcases le_total 0 (a * d - b * c) with hnonneg | hnonpos
      · exact Int.eq_zero_of_dvd_of_nonneg_of_lt hnonneg
          (by nlinarith [mul_pos hb hc]) hminus
      · have hz := Int.eq_zero_of_dvd_of_nonneg_of_lt (by omega : 0 ≤ -(a * d - b * c))
          (by nlinarith [mul_pos ha hd] : -(a * d - b * c) < p) hminus.neg_right
        omega
    have hid := two_square_identity a b c d
    rw [← hab, ← hcd, hdet] at hid
    have hdot : a * c + b * d = p := by
      nlinarith [mul_pos ha hc, mul_pos hb hd]
    left
    have hdist : (a - c) ^ 2 + (b - d) ^ 2 = 0 := by nlinarith
    exact ⟨by nlinarith [sq_nonneg (b - d)], by nlinarith [sq_nonneg (a - c)]⟩

  · have hle : a * d + b * c ≤ p := by
      nlinarith [sq_nonneg (a - d), sq_nonneg (b - c)]
    obtain ⟨k, hk⟩ := hplus
    have hk1 : k = 1 := by
      have hkpos : 0 < k := by nlinarith [mul_pos ha hd, mul_pos hb hc]
      nlinarith
    have hcross : a * d + b * c = p := by nlinarith [hk]
    right
    have hdist : (a - d) ^ 2 + (b - c) ^ 2 = 0 := by nlinarith
    exact ⟨by nlinarith [sq_nonneg (b - c)], by nlinarith [sq_nonneg (a - d)]⟩

/-- Corollary: arbitrary integer representations of a prime are unique up to signs and order. -/
theorem prime_sq_add_sq_natAbs_unique {p : ℕ} (hp : p.Prime) (_hp4 : p % 4 = 1)
    {a b c d : ℤ} (hab : (p : ℤ) = a ^ 2 + b ^ 2)
    (hcd : (p : ℤ) = c ^ 2 + d ^ 2) :
    (a.natAbs = c.natAbs ∧ b.natAbs = d.natAbs) ∨
      (a.natAbs = d.natAbs ∧ b.natAbs = c.natAbs) := by
  have hnonzero {x y : ℤ} (hxy : (p : ℤ) = x ^ 2 + y ^ 2) : x ≠ 0 := by
    intro hx
    have hy : p = y.natAbs ^ 2 := by
      have : (p : ℤ) = (y.natAbs : ℤ) ^ 2 := by
        simpa only [hx, zero_pow two_ne_zero, zero_add, Int.natCast_natAbs, sq_abs] using hxy
      exact_mod_cast this
    have hdiv : y.natAbs ∣ p := ⟨y.natAbs, by nlinarith [hy]⟩
    rcases hp.eq_one_or_self_of_dvd _ hdiv with he | he
    · rw [he] at hy
      norm_num at hy
      exact hp.ne_one hy
    · rw [he] at hy
      nlinarith [hp.two_le]

  have hpos {x y : ℤ} (hxy : (p : ℤ) = x ^ 2 + y ^ 2) : 0 < |x| :=
    abs_pos.mpr (hnonzero hxy)
  have h := prime_sq_add_sq_unique hp (hpos hab) (hpos (x := b) (y := a) (by nlinarith [hab]))
    (hpos hcd) (hpos (x := d) (y := c) (by nlinarith [hcd]))
    (by simpa only [sq_abs] using hab) (by simpa only [sq_abs] using hcd)
  simpa only [← Int.natCast_natAbs, Int.natCast_inj] using h

end ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares
