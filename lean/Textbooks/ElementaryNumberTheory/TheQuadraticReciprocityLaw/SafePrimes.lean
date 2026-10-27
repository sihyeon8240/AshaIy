import Textbooks.ElementaryNumberTheory.TheQuadraticReciprocityLaw.SupplementaryLaws

namespace ElementaryNumberTheory.TheQuadraticReciprocityLaw

open PrimitiveRootsAndIndices

/-- Theorem: if p and q=2p+1 are odd primes, the signed integer two has full order modulo q. -/
theorem primitiveRoot_safe_prime (p q : ℕ) [Fact p.Prime] [Fact q.Prime]
    (hp : p ≠ 2) (hq : q = 2 * p + 1) :
    IsPrimitiveRoot (((-1 : ℤ) ^ (p / 2) * 2 : ℤ) : ZMod q) (q - 1) := by
  let a : ℤ := (-1) ^ (p / 2) * 2
  have hpodd := Nat.odd_iff.mp ((Fact.out : p.Prime).odd_of_ne_two hp)
  have hpgt := (Fact.out : p.Prime).two_le
  have hqodd : q ≠ 2 := by omega
  have hqhalf : q / 2 = p := by omega
  have hchar : legendreSym q a = -1 := by
    rcases (by omega : p % 4 = 1 ∨ p % 4 = 3) with h | h
    · have he : Even (p / 2) := Nat.even_iff.mpr (by omega)
      rw [show a = 2 by simp only [a, he.neg_one_pow, one_mul], legendreSym_two hqodd,
        ite_eq_right (by omega)]

    · have he : Odd (p / 2) := Nat.odd_iff.mpr (by omega)
      rw [show a = -1 * 2 by simp only [a, he.neg_one_pow], legendreSym_mul hqodd,
        legendreSym_neg_one hqodd, hqhalf,
        ((Fact.out : p.Prime).odd_of_ne_two hp).neg_one_pow,
        legendreSym_two hqodd, ite_eq_left (by omega), mul_one]
  have hane : (a : ZMod q) ≠ 0 := by
    dsimp only [a]
    rw [Int.cast_mul, Int.cast_pow, Int.cast_neg, Int.cast_one, Int.cast_ofNat]
    exact mul_ne_zero (pow_ne_zero _ (neg_ne_zero.mpr one_ne_zero)) (two_ne_zero hqodd)
  let u : (ZMod q)ˣ := Units.mk0 (a : ZMod q) hane
  have hhalf : (u : ZMod q) ^ p = -1 := by
    have h := legendreSym_eq_pow hqodd a
    rw [hchar, Int.cast_neg, Int.cast_one, hqhalf] at h
    exact h.symm
  have hsquare : u ^ 2 ≠ 1 := by
    intro h
    have hh := congrArg (fun v : (ZMod q)ˣ => (v : ZMod q)) h
    have hasq : a ^ 2 = 4 := by
      dsimp only [a]
      rw [mul_pow, pow_right_comm, neg_one_sq, one_pow, one_mul]
      norm_num
    have hh' : ((a ^ 2 : ℤ) : ZMod q) = 1 := by
      simpa only [u, Units.val_pow_eq_pow_val, Units.val_mk0, Units.val_one,
        Int.cast_pow] using hh
    rw [hasq] at hh'
    have hzero : ((3 : ℕ) : ZMod q) = 0 := by
      have : (4 : ZMod q) = 1 := by simpa only [Int.cast_ofNat] using hh'
      linear_combination this
    have hd := (ZMod.natCast_eq_zero_iff 3 q).mp hzero
    have := Nat.le_of_dvd (by decide : 0 < 3) hd
    omega
  have hperiod := unit_orderOf_dvd_totient q u
  have hqe : q - 1 = 2 * p := by omega
  rw [EulersGeneralizationOfFermatsTheorem.totient_prime q
    (isPrime_of_prime q Fact.out), hqe] at hperiod
  have hnotp : ¬orderOf u ∣ p := by
    intro hd
    have hh := (pow_eq_one_iff_dvd_order u p).mpr hd
    have hv := congrArg (fun v : (ZMod q)ˣ => (v : ZMod q)) hh
    exact neg_one_ne_one hqodd (hhalf.symm.trans hv)
  have hnot2 : ¬orderOf u ∣ 2 := fun hd => hsquare ((pow_eq_one_iff_dvd_order u 2).mpr hd)
  have hord : orderOf u = 2 * p := by
    obtain ⟨s, t, hs, ht, hst⟩ := NumberTheoreticFunctions.exists_divisor_split 2 p
      (orderOf u) (unit_orderOf_pos q u) hperiod
    rcases (Nat.dvd_prime Nat.prime_two).mp hs with rfl | rfl <;>
      rcases (Nat.dvd_prime (Fact.out : p.Prime)).mp ht with rfl | rfl
    · exact (hnot2 (by rw [← hst]; simp only [one_mul, one_dvd])).elim
    · exact (hnotp (by rw [← hst, one_mul])).elim
    · exact (hnot2 (by rw [← hst, mul_one])).elim
    · exact hst.symm
  apply (isPrimitiveRoot_iff_orderOf _ _).mpr
  change orderOf (u : ZMod q) = q - 1
  rw [orderOf_units, hord, hqe]

end ElementaryNumberTheory.TheQuadraticReciprocityLaw
