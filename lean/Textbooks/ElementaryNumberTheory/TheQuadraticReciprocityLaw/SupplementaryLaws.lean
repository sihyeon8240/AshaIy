import Textbooks.ElementaryNumberTheory.TheQuadraticReciprocityLaw.QuadraticReciprocity
import Mathlib.Tactic.IntervalCases

namespace ElementaryNumberTheory.TheQuadraticReciprocityLaw

private instance : Fact (Nat.Prime 3) := ⟨by decide⟩

variable {p : ℕ} [Fact p.Prime]

/-- Lemma: multiplication by two has p/2-p/4 upper remainders in the half-system. -/
theorem gaussCount_two (hp : p ≠ 2) : gaussCount p 2 = p / 2 - p / 4 := by
  have hodd := Nat.odd_iff.mp ((Fact.out : p.Prime).odd_of_ne_two hp)
  have hv (k : ℕ) (hk : k ∈ halfResidues p) : ((2 : ZMod p) * k).val = 2 * k := by
    have hk := Finset.mem_Ico.mp hk
    rw [← Nat.cast_ofNat, ← Nat.cast_mul, ZMod.val_natCast, Nat.mod_eq_of_lt (by omega)]
  have he : ((halfResidues p).filter fun k : ℕ => p / 2 < ((2 : ZMod p) * k).val) =
      Finset.Ico (p / 4 + 1) (p / 2 + 1) := by
    ext k
    constructor
    · intro hk
      obtain ⟨hk, hu⟩ := Finset.mem_filter.mp hk
      rw [hv k hk] at hu
      have hk := Finset.mem_Ico.mp hk
      apply Finset.mem_Ico.mpr
      omega

    · intro hk
      have hk := Finset.mem_Ico.mp hk
      have hm : k ∈ halfResidues p := Finset.mem_Ico.mpr (by omega)
      apply Finset.mem_filter.mpr ⟨hm, ?_⟩
      rw [hv k hm]
      omega
  unfold gaussCount
  simp only [Int.cast_ofNat, he, Nat.card_Ico, Nat.add_sub_add_right]

/-- Theorem: the quadratic character of two is determined by the prime modulo eight. -/
theorem legendreSym_two (hp : p ≠ 2) :
    legendreSym p 2 = if p % 8 = 1 ∨ p % 8 = 7 then 1 else -1 := by
  rw [gauss_lemma hp 2 (by simpa only [Int.cast_ofNat] using two_ne_zero hp), gaussCount_two hp,
    neg_one_pow_eq_pow_mod_two]
  have ho := Nat.odd_iff.mp ((Fact.out : p.Prime).odd_of_ne_two hp)
  by_cases h : p % 8 = 1 ∨ p % 8 = 7
  · rw [ite_eq_left h, show (p / 2 - p / 4) % 2 = 0 by omega, pow_zero]

  · rw [ite_eq_right h, show (p / 2 - p / 4) % 2 = 1 by omega, pow_one]

/-- Corollary: the exponent form of the second supplementary law. -/
theorem legendreSym_two_eq_pow (hp : p ≠ 2) :
    legendreSym p 2 = (-1 : ℤ) ^ ((p ^ 2 - 1) / 8) := by
  have ho := Nat.odd_iff.mp ((Fact.out : p.Prime).odd_of_ne_two hp)
  have hs := Nat.pow_mod p 2 16
  have hb := Nat.mod_lt p (by decide : 0 < 16)
  have he : (p / 2 - p / 4) % 2 = ((p ^ 2 - 1) / 8) % 2 := by
    interval_cases h : p % 16 <;> norm_num [h] at hs <;> omega
  rw [gauss_lemma hp 2 (by simpa only [Int.cast_ofNat] using two_ne_zero hp), gaussCount_two hp]
  conv_lhs => rw [neg_one_pow_eq_pow_mod_two]
  conv_rhs => rw [neg_one_pow_eq_pow_mod_two]
  rw [he]

/-- Corollary: two is a square exactly at primes congruent to one or seven modulo eight. -/
theorem isSquare_two_iff (hp : p ≠ 2) :
    IsSquare (2 : ZMod p) ↔ p % 8 = 1 ∨ p % 8 = 7 := by
  have ha : ((2 : ℤ) : ZMod p) ≠ 0 := by simpa only [Int.cast_ofNat] using two_ne_zero hp
  have he := legendreSym_eq_one_iff ha
  rw [Int.cast_ofNat] at he
  rw [← he, legendreSym_two hp]
  split_ifs <;> simp_all only [iff_self]

/-- Theorem: the quadratic character of three is determined by the prime modulo twelve. -/
theorem legendreSym_three (hp : p ≠ 2) (hthree : p ≠ 3) :
    legendreSym p 3 = if p % 12 = 1 ∨ p % 12 = 11 then 1 else -1 := by
  have hrec := quadratic_reciprocity p 3 hp (by decide) hthree
  have hchar : legendreSym 3 (p : ℤ) = if p % 3 = 1 then 1 else -1 := by
    rw [legendreSym_def]
    have hn : p % 3 ≠ 0 := by
      intro h
      have hd := Nat.dvd_of_mod_eq_zero h
      have he := (Fact.out : p.Prime).eq_one_or_self_of_dvd 3 hd
      omega
    have hv : (p : ZMod 3) = (p % 3 : ℕ) :=
      (ZMod.natCast_eq_natCast_iff _ _ 3).mpr (Nat.mod_modEq p 3).symm
    have hb := Nat.mod_lt p (by decide : 0 < 3)
    rcases (by omega : p % 3 = 1 ∨ p % 3 = 2) with h | h
    · simp only [Int.cast_natCast, hv, h, Nat.cast_one, one_ne_zero, IsSquare.one,
        ite_true, ite_false]

    · have htwo : ¬IsSquare (2 : ZMod 3) := by decide
      have hne : (2 : ZMod 3) ≠ 0 := by decide
      simp only [Int.cast_natCast, hv, h, Nat.cast_ofNat, hne, htwo, ite_false,
        show (2 : ℕ) ≠ 1 by decide]
  rw [hchar, show 3 / 2 = 1 by decide, mul_one, neg_one_pow_eq_pow_mod_two] at hrec
  have ho := Nat.odd_iff.mp ((Fact.out : p.Prime).odd_of_ne_two hp)
  have hn : p % 3 ≠ 0 := by
    intro h
    have hd := Nat.dvd_of_mod_eq_zero h
    have he := (Fact.out : p.Prime).eq_one_or_self_of_dvd 3 hd
    omega
  rcases (by omega : p % 12 = 1 ∨ p % 12 = 5 ∨ p % 12 = 7 ∨ p % 12 = 11) with h | h | h | h
  · norm_num [show p % 3 = 1 by omega, show p / 2 % 2 = 0 by omega] at hrec
    rw [ite_eq_left (Or.inl h)]
    exact hrec

  · norm_num [show p % 3 = 2 by omega, show p / 2 % 2 = 0 by omega] at hrec
    rw [ite_eq_right (by omega)]
    omega

  · norm_num [show p % 3 = 1 by omega, show p / 2 % 2 = 1 by omega] at hrec
    rw [ite_eq_right (by omega)]
    exact hrec

  · norm_num [show p % 3 = 2 by omega, show p / 2 % 2 = 1 by omega] at hrec
    rw [ite_eq_left (Or.inr h)]
    omega

end ElementaryNumberTheory.TheQuadraticReciprocityLaw
