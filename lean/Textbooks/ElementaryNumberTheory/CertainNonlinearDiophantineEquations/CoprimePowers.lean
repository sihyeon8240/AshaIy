module

public import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.PrimeExponentSplitting
public import Textbooks.ElementaryNumberTheory.NumberTheoreticFunctions.Mobius
public import Mathlib.RingTheory.Coprime.Lemmas

import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum

public section

namespace ElementaryNumberTheory.CertainNonlinearDiophantineEquations

open NumberTheoreticFunctions

/-- Lemma: Bezout coefficients identify coprimality with the book's constructed gcd. -/
theorem isCoprime_iff_gcd_eq_one {a b : ℤ} (hab : a ≠ 0 ∨ b ≠ 0) :
    IsCoprime a b ↔ DivisibilityTheoryInTheIntegers.gcd a b = 1 := by
  simpa only [IsCoprime, mul_comm, eq_comm] using
    (DivisibilityTheoryInTheIntegers.gcd_eq_one_iff_exists_mul_add_mul a b hab).symm

/-- Lemma: multiplying every exponent by k raises its value to the kth power. -/
theorem factorValue_smul (e : ℕ →₀ ℕ) (k : ℕ) :
    factorValue (k • e) = factorValue e ^ k := by
  induction k with
  | zero => simp only [zero_smul, factorValue, Finsupp.prod_zero_index, pow_zero]
  | succ k ih =>
    rw [succ_nsmul, factorValue_add, ih, pow_succ]

/-- Lemma: raising a positive integer to a power multiplies its prime exponents. -/
theorem primeExponents_pow (a k : ℕ) (ha : 0 < a) :
    primeExponents (a ^ k) = k • primeExponents a := by
  induction k with
  | zero => rw [pow_zero, primeExponents_one, zero_smul]
  | succ k ih =>
    rw [pow_succ, primeExponents_mul _ _ (pow_pos ha k) ha, ih, succ_nsmul]

/-- Lemma: divisibility between equal positive powers cancels their exponent. -/
theorem pow_dvd_pow_iff {a b k : ℕ} (ha : 0 < a) (hb : 0 < b) (hk : 0 < k) :
    a ^ k ∣ b ^ k ↔ a ∣ b := by
  rw [dvd_iff_primeExponents_le _ _ (pow_pos ha k) (pow_pos hb k),
    primeExponents_pow a k ha, primeExponents_pow b k hb,
    dvd_iff_primeExponents_le a b ha hb]
  constructor
  · intro h p
    have hp := h p
    simp only [Finsupp.smul_apply, smul_eq_mul] at hp
    exact (mul_le_mul_iff_right₀ hk).mp hp
  · intro h p
    exact Nat.mul_le_mul_left k (h p)

/-- Theorem: coprime positive factors of a kth power are themselves positive kth powers. -/
theorem coprime_factors_of_power {a b c k : ℕ} (ha : 0 < a) (hb : 0 < b)
    (hc : 0 < c) (_hk : 2 ≤ k) (hab : a.Coprime b) (heq : a * b = c ^ k) :
    ∃ s t : ℕ, 0 < s ∧ 0 < t ∧ a = s ^ k ∧ b = t ^ k := by
  classical
  have hlocal := (EulersGeneralizationOfFermatsTheorem.coprime_iff_gcd_eq_one a b ha).mp hab
  have hdis := prime_support_disjoint a b ha hb hlocal
  have hexp : primeExponents a + primeExponents b = k • primeExponents c := by
    rw [← primeExponents_mul a b ha hb, heq, primeExponents_pow c k hc]

  have extract (d : ℕ) (hd : 0 < d)
      (hdiv : ∀ p, k ∣ primeExponents d p) : ∃ s : ℕ, 0 < s ∧ d = s ^ k := by
    let e := (primeExponents d).mapRange (fun n => n / k) (Nat.zero_div k)
    have he : k • e = primeExponents d := by
      ext p
      simp only [e, Finsupp.smul_apply, Finsupp.mapRange_apply, smul_eq_mul]
      exact Nat.mul_div_cancel' (hdiv p)
    have hprime : ∀ p ∈ e.support, PrimesAndTheirDistribution.isPrime p := by
      intro p hp
      apply (primeExponents_spec d hd).1
      exact Finsupp.support_mapRange hp
    refine ⟨factorValue e, factorValue_pos e hprime, ?_⟩
    rw [← factorValue_smul, he, (primeExponents_spec d hd).2]

  have hdiv (p : ℕ) : k ∣ primeExponents a p ∧ k ∣ primeExponents b p := by
    have hp := DFunLike.congr_fun hexp p
    simp only [Finsupp.add_apply, Finsupp.smul_apply, smul_eq_mul] at hp
    have hz : primeExponents a p = 0 ∨ primeExponents b p = 0 := by
      by_contra h
      push Not at h
      exact Finset.disjoint_left.mp hdis
        (Finsupp.mem_support_iff.mpr h.1) (Finsupp.mem_support_iff.mpr h.2)
    rcases hz with hz | hz
    · rw [hz, zero_add] at hp
      exact ⟨hz ▸ dvd_zero k, ⟨primeExponents c p, hp⟩⟩
    · rw [hz, add_zero] at hp
      exact ⟨⟨primeExponents c p, hp⟩, hz ▸ dvd_zero k⟩

  obtain ⟨s, hs, has⟩ := extract a ha (fun p => (hdiv p).1)
  obtain ⟨t, ht, hbt⟩ := extract b hb (fun p => (hdiv p).2)
  exact ⟨s, t, hs, ht, has, hbt⟩

/-- Lemma: the coprime-power factorization for positive integer inputs. -/
theorem coprime_factors_of_power_int {a b c : ℤ} {k : ℕ}
    (ha : 0 < a) (hb : 0 < b) (hc : 0 < c) (hk : 2 ≤ k)
    (hab : IsCoprime a b) (heq : a * b = c ^ k) :
    ∃ s t : ℤ, 0 < s ∧ 0 < t ∧ a = s ^ k ∧ b = t ^ k := by
  have hae : (a.toNat : ℤ) = a := Int.toNat_of_nonneg ha.le
  have hbe : (b.toNat : ℤ) = b := Int.toNat_of_nonneg hb.le
  have hce : (c.toNat : ℤ) = c := Int.toNat_of_nonneg hc.le
  have habn : a.toNat.Coprime b.toNat := by
    apply Nat.isCoprime_iff_coprime.mp
    rwa [hae, hbe]
  have heqn : a.toNat * b.toNat = c.toNat ^ k := by
    exact_mod_cast (show (a.toNat : ℤ) * b.toNat = (c.toNat : ℤ) ^ k by
      rwa [hae, hbe, hce])
  obtain ⟨s, t, hs, ht, has, hbt⟩ := coprime_factors_of_power
    (by omega) (by omega) (by omega) hk habn heqn
  refine ⟨s, t, by exact_mod_cast hs, by exact_mod_cast ht, ?_, ?_⟩
  · rw [← hae]
    exact_mod_cast has
  · rw [← hbe]
    exact_mod_cast hbt

/-- Lemma: a positive integer square divisible by another square has a divisible root. -/
theorem sq_dvd_sq_iff {a b : ℤ} (ha : 0 < a) (hb : 0 < b) :
    a ^ 2 ∣ b ^ 2 ↔ a ∣ b := by
  have hae : (a.toNat : ℤ) = a := Int.toNat_of_nonneg ha.le
  have hbe : (b.toNat : ℤ) = b := Int.toNat_of_nonneg hb.le
  rw [← hae, ← hbe, ← Nat.cast_pow, ← Nat.cast_pow,
    Int.natCast_dvd_natCast, Int.natCast_dvd_natCast]
  exact pow_dvd_pow_iff (by omega) (by omega) (by decide)

/-- Lemma: in a coprime product twice a square, the odd factor is a square
and the even factor is twice a square. -/
theorem coprime_factors_of_twice_square {a b w : ℤ}
    (ha : 0 < a) (hb : 0 < b) (hw : 0 < w) (hab : IsCoprime a b)
    (_haodd : Odd a) (hbeven : Even b) (heq : 2 * a * b = w ^ 2) :
    ∃ u v : ℤ, 0 < u ∧ 0 < v ∧ a = u ^ 2 ∧ b = 2 * v ^ 2 := by
  obtain ⟨r, hr⟩ := hbeven
  have hrpos : 0 < r := by omega
  have hwr : Even w := by
    have hm := congrArg (fun n : ℤ => n % 2) heq
    rcases Int.emod_two_eq_zero_or_one w with hwb | hwb
    · exact Int.even_iff.mpr hwb
    · norm_num [pow_two, Int.mul_emod, hwb] at hm
  obtain ⟨q, hq⟩ := hwr
  have hqpos : 0 < q := by omega
  have har : IsCoprime a r := hab.of_isCoprime_of_dvd_right ⟨2, by omega⟩
  have hprod : a * r = q ^ 2 := by nlinarith [heq]
  obtain ⟨u, v, hu, hv, hau, hrv⟩ :=
    coprime_factors_of_power_int ha hrpos hqpos (by decide) har hprod
  exact ⟨u, v, hu, hv, hau, by nlinarith⟩

end ElementaryNumberTheory.CertainNonlinearDiophantineEquations
