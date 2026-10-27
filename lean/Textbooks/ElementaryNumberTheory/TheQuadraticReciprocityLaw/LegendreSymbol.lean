import Textbooks.ElementaryNumberTheory.TheQuadraticReciprocityLaw.EulerCriterion

namespace ElementaryNumberTheory.TheQuadraticReciprocityLaw

open PrimitiveRootsAndIndices

variable {p : ℕ} [Fact p.Prime]

/-- Lemma: the standard Legendre symbol extends the residue/nonresidue definition by zero. -/
theorem legendreSym_def (a : ℤ) :
    legendreSym p a = if (a : ZMod p) = 0 then 0 else
      if IsSquare (a : ZMod p) then 1 else -1 := rfl

/-- Proposition: congruent integers have the same quadratic character. -/
theorem legendreSym_congr {a b : ℤ} (h : a ≡ b [ZMOD (p : ℤ)]) :
    legendreSym p a = legendreSym p b := by
  have he := (ZMod.intCast_eq_intCast_iff a b p).mpr h
  rw [legendreSym_def, legendreSym_def, he]

/-- Proposition: the Legendre symbol is zero exactly on multiples of the prime. -/
theorem legendreSym_eq_zero_iff (a : ℤ) : legendreSym p a = 0 ↔ (p : ℤ) ∣ a := by
  rw [← ZMod.intCast_zmod_eq_zero_iff_dvd, legendreSym_def]
  split_ifs <;> simp_all only [one_ne_zero, iff_self]

/-- Proposition: the Legendre symbol of a nonzero class is one or minus one. -/
theorem legendreSym_eq_one_or_neg_one {a : ℤ} (ha : (a : ZMod p) ≠ 0) :
    legendreSym p a = 1 ∨ legendreSym p a = -1 := by
  rw [legendreSym_def, ite_eq_right ha]
  split_ifs <;> simp only [true_or, or_true]

/-- Proposition: symbol one means that the nonzero class is a square. -/
theorem legendreSym_eq_one_iff {a : ℤ} (ha : (a : ZMod p) ≠ 0) :
    legendreSym p a = 1 ↔ IsSquare (a : ZMod p) := by
  rw [legendreSym_def, ite_eq_right ha]
  by_cases hs : IsSquare (a : ZMod p)
  · rw [ite_eq_left hs]
    exact iff_of_true rfl hs

  · rw [ite_eq_right hs]
    exact iff_of_false (by decide) hs

/-- Lemma: reduction modulo an odd prime distinguishes the two integer signs. -/
theorem sign_eq_of_cast_eq (hp : p ≠ 2) {a b : ℤ}
    (ha : a = 1 ∨ a = -1) (hb : b = 1 ∨ b = -1) (h : (a : ZMod p) = b) : a = b := by
  rcases ha with rfl | rfl <;> rcases hb with rfl | rfl
  · rfl
  · exact (neg_one_ne_one hp (by simpa only [Int.cast_one, Int.cast_neg] using h.symm)).elim
  · exact (neg_one_ne_one hp (by simpa only [Int.cast_one, Int.cast_neg] using h)).elim
  · rfl

/-- Theorem: Euler's criterion expresses the Legendre symbol as a half power modulo p. -/
theorem legendreSym_eq_pow (hp : p ≠ 2) (a : ℤ) :
    (legendreSym p a : ZMod p) = (a : ZMod p) ^ (p / 2) := by
  by_cases ha : (a : ZMod p) = 0
  · have hh : 0 < p / 2 := Nat.div_pos (Fact.out : p.Prime).two_le (by decide)
    simp only [legendreSym_def, ha, ite_true, Int.cast_zero, zero_pow hh.ne']

  · by_cases hs : IsSquare (a : ZMod p)
    · rw [legendreSym_def, ite_eq_right ha, ite_eq_left hs, Int.cast_one,
        (euler_criterion hp ha).mp hs]

    · rw [legendreSym_def, ite_eq_right ha, ite_eq_right hs, Int.cast_neg, Int.cast_one,
        (euler_criterion_nonresidue hp ha).mp hs]

/-- Theorem: the Legendre symbol is multiplicative. -/
theorem legendreSym_mul (hp : p ≠ 2) (a b : ℤ) :
    legendreSym p (a * b) = legendreSym p a * legendreSym p b := by
  by_cases ha : (a : ZMod p) = 0
  · simp only [legendreSym_def, Int.cast_mul, ha, zero_mul, ite_true]

  by_cases hb : (b : ZMod p) = 0
  · simp only [legendreSym_def, Int.cast_mul, hb, mul_zero, ite_true]

  have hab : ((a * b : ℤ) : ZMod p) ≠ 0 := by
    rw [Int.cast_mul]
    exact mul_ne_zero ha hb
  have hsign : legendreSym p a * legendreSym p b = 1 ∨
      legendreSym p a * legendreSym p b = -1 := by
    rcases legendreSym_eq_one_or_neg_one ha with h | h <;>
      rcases legendreSym_eq_one_or_neg_one hb with h' | h' <;> rw [h, h'] <;> norm_num

  apply sign_eq_of_cast_eq hp (legendreSym_eq_one_or_neg_one hab) hsign
  rw [Int.cast_mul, legendreSym_eq_pow hp, legendreSym_eq_pow hp,
    legendreSym_eq_pow hp, Int.cast_mul, mul_pow]

/-- Proposition: the Legendre symbol of one is one. -/
theorem legendreSym_one : legendreSym p 1 = 1 := by
  rw [legendreSym_def, Int.cast_one, ite_eq_right one_ne_zero, ite_eq_left IsSquare.one]

/-- Proposition: every square coprime to p has Legendre symbol one. -/
theorem legendreSym_sq {a : ℤ} (ha : (a : ZMod p) ≠ 0) : legendreSym p (a ^ 2) = 1 := by
  apply (legendreSym_eq_one_iff (by simpa only [Int.cast_pow] using pow_ne_zero 2 ha)).mpr
  rw [Int.cast_pow]
  exact IsSquare.sq _

/-- Corollary: a nonzero square factor may be deleted from the numerator. -/
theorem legendreSym_mul_sq (hp : p ≠ 2) (a b : ℤ) (hb : (b : ZMod p) ≠ 0) :
    legendreSym p (a * b ^ 2) = legendreSym p a := by
  rw [legendreSym_mul hp, legendreSym_sq hb, mul_one]

/-- Theorem: the Legendre symbol of minus one is the sign of the half exponent. -/
theorem legendreSym_neg_one (hp : p ≠ 2) : legendreSym p (-1) = (-1 : ℤ) ^ (p / 2) := by
  have ha : ((-1 : ℤ) : ZMod p) ≠ 0 := by
    simpa only [Int.cast_neg, Int.cast_one] using (neg_ne_zero.mpr (one_ne_zero : (1 : ZMod p) ≠ 0))
  apply sign_eq_of_cast_eq hp
    (legendreSym_eq_one_or_neg_one ha) (neg_one_pow_eq_or ℤ _)
  rw [legendreSym_eq_pow hp, Int.cast_pow, Int.cast_neg, Int.cast_one]

/-- Corollary: minus one is a quadratic residue exactly at primes one modulo four. -/
theorem legendreSym_neg_one_eq_one_iff (hp : p ≠ 2) :
    legendreSym p (-1) = 1 ↔ p % 4 = 1 := by
  have ha : ((-1 : ℤ) : ZMod p) ≠ 0 := by
    simpa only [Int.cast_neg, Int.cast_one] using (neg_ne_zero.mpr (one_ne_zero : (1 : ZMod p) ≠ 0))
  rw [legendreSym_eq_one_iff ha, Int.cast_neg, Int.cast_one]
  have he := FermatsTheorem.exists_square_eq_neg_one_iff p
    (isPrime_of_prime p Fact.out) ((Fact.out : p.Prime).odd_of_ne_two hp)
  have hs : IsSquare (-1 : ZMod p) ↔ ∃ x : ℤ, x ^ 2 ≡ -1 [ZMOD (p : ℤ)] := by
    constructor
    · rintro ⟨x, hx⟩
      refine ⟨x.val, (ZMod.intCast_eq_intCast_iff _ _ p).mp ?_⟩
      simpa only [Int.cast_pow, Int.cast_natCast, ZMod.natCast_zmod_val,
        Int.cast_neg, Int.cast_one, pow_two, Int.cast_mul] using hx.symm

    · rintro ⟨x, hx⟩
      refine ⟨(x : ZMod p), ?_⟩
      have h := (ZMod.intCast_eq_intCast_iff _ _ p).mpr hx
      simpa only [Int.cast_pow, Int.cast_neg, Int.cast_one, pow_two, Int.cast_mul] using h.symm
  exact hs.trans he

end ElementaryNumberTheory.TheQuadraticReciprocityLaw
