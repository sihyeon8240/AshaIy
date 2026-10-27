import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.Applications
import Textbooks.ElementaryNumberTheory.FermatsTheorem.QuadraticCongruences
import Mathlib.NumberTheory.LegendreSymbol.Basic

namespace ElementaryNumberTheory.TheQuadraticReciprocityLaw

open PrimitiveRootsAndIndices

variable {p : ℕ} [Fact p.Prime]

/-- Lemma: for an odd prime, the two natural-number half exponents agree. -/
theorem half_prime (hp : p ≠ 2) : (p - 1) / 2 = p / 2 := by
  have := (Fact.out : p.Prime).odd_of_ne_two hp
  have := Nat.odd_iff.mp this
  omega

/-- Lemma: two is nonzero modulo an odd prime. -/
theorem two_ne_zero (hp : p ≠ 2) : (2 : ZMod p) ≠ 0 := by
  intro h
  have hd := (ZMod.natCast_eq_zero_iff 2 p).mp h
  have := (Nat.dvd_prime Nat.prime_two).mp hd
  have := (Fact.out : p.Prime).two_le
  omega

/-- Lemma: minus one and one remain distinct modulo an odd prime. -/
theorem neg_one_ne_one (hp : p ≠ 2) : (-1 : ZMod p) ≠ 1 := by
  intro h
  have he := (ZMod.neg_one_eq_one_iff (n := p)).mp h
  have := (Fact.out : p.Prime).two_le
  omega

/-- Proposition: completing the square preserves a quadratic equation modulo an odd prime. -/
theorem quadratic_eq_zero_iff (hp : p ≠ 2) (A B C x : ZMod p) (hA : A ≠ 0) :
    A * x ^ 2 + B * x + C = 0 ↔ (2 * A * x + B) ^ 2 = B ^ 2 - 4 * A * C := by
  have hid : (2 * A * x + B) ^ 2 - (B ^ 2 - 4 * A * C) =
      (2 * 2 * A) * (A * x ^ 2 + B * x + C) := by ring
  have hne := mul_ne_zero (mul_ne_zero (two_ne_zero hp) (two_ne_zero hp)) hA
  constructor
  · intro h
    apply sub_eq_zero.mp
    rw [hid, h, mul_zero]

  · intro h
    apply (mul_eq_zero.mp ?_).resolve_left hne
    rw [← hid, h, sub_self]

/-- Theorem: Euler's criterion characterizes the nonzero quadratic residues. -/
theorem euler_criterion (hp : p ≠ 2) {a : ZMod p} (ha : a ≠ 0) :
    IsSquare a ↔ a ^ (p / 2) = 1 := by
  obtain ⟨r, hr⟩ := exists_primitiveRoot_prime p Fact.out
  have he := exists_pow_eq_zmod_iff p r hr (Units.mk0 a ha) 2 (by decide)
  have heven : 2 ∣ p - 1 := by
    have := Nat.odd_iff.mp ((Fact.out : p.Prime).odd_of_ne_two hp)
    omega
  rw [EulersGeneralizationOfFermatsTheorem.totient_prime p
    (isPrime_of_prime p Fact.out), Nat.gcd_eq_left heven, half_prime hp] at he
  simpa only [Units.val_mk0, isSquare_iff_exists_sq, eq_comm] using he

/-- Lemma: the half power of a nonzero class is one or minus one. -/
theorem pow_half_eq_one_or_neg_one (hp : p ≠ 2) {a : ZMod p} (ha : a ≠ 0) :
    a ^ (p / 2) = 1 ∨ a ^ (p / 2) = -1 := by
  have hperiod := unit_pow_totient p (Units.mk0 a ha)
  have hv := congrArg (fun u : (ZMod p)ˣ => (u : ZMod p)) hperiod
  rw [EulersGeneralizationOfFermatsTheorem.totient_prime p
    (isPrime_of_prime p Fact.out)] at hv
  simp only [Units.val_pow_eq_pow_val, Units.val_mk0, Units.val_one] at hv
  have hhalf : p / 2 * 2 = p - 1 := by
    have := Nat.odd_iff.mp ((Fact.out : p.Prime).odd_of_ne_two hp)
    omega
  apply (sq_eq_one_iff).mp
  rw [← pow_mul, hhalf, hv]

/-- Corollary: Euler's minus-one alternative characterizes quadratic nonresidues. -/
theorem euler_criterion_nonresidue (hp : p ≠ 2) {a : ZMod p} (ha : a ≠ 0) :
    ¬IsSquare a ↔ a ^ (p / 2) = -1 := by
  rw [euler_criterion hp ha]
  exact ⟨fun h => (pow_half_eq_one_or_neg_one hp ha).resolve_left h,
    fun h hn => neg_one_ne_one hp (h.symm.trans hn)⟩

/-- Proposition: a square has only the two opposite candidate roots. -/
theorem square_eq_iff {a x y : ZMod p} (hy : y ^ 2 = a) :
    x ^ 2 = a ↔ x = y ∨ x = -y := by
  rw [← hy, sq_eq_sq_iff_eq_or_eq_neg]

/-- Proposition: the two roots of a nonzero square are distinct at an odd prime. -/
theorem square_roots_distinct (hp : p ≠ 2) {a y : ZMod p} (ha : a ≠ 0) (hy : y ^ 2 = a) :
    y ≠ -y := by
  have hne : y ≠ 0 := by
    intro h
    rw [h, zero_pow (by decide : 2 ≠ 0)] at hy
    exact ha hy.symm
  intro h
  have hz : 2 * y = 0 := by linear_combination h
  exact mul_ne_zero (two_ne_zero hp) hne hz

end ElementaryNumberTheory.TheQuadraticReciprocityLaw
