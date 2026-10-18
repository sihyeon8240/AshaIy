import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.PrimeRoots
import Textbooks.ElementaryNumberTheory.NumberTheoreticFunctions.DivisorFormulas
import Mathlib.Data.Nat.Choose.Basic
import Mathlib.Data.ZMod.Units

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

open scoped Classical
open EulersGeneralizationOfFermatsTheorem

/-- Lemma: every interior binomial coefficient in a prime row is divisible by the prime. -/
theorem prime_dvd_choose (p : ℕ) (hp : p.Prime) (i : ℕ) (hi : 0 < i) (hip : i < p) :
    p ∣ p.choose i := by
  have hid : p ∣ p.choose i * i := by
    obtain ⟨j, rfl⟩ := Nat.exists_eq_succ_of_ne_zero hi.ne'
    have he := Nat.add_one_mul_choose_eq (p - 1) j
    rw [Nat.sub_add_cancel hp.one_lt.le] at he
    exact ⟨(p - 1).choose j, by nlinarith [he]⟩
  rcases PrimesAndTheirDistribution.prime_dvd_mul_nat p (p.choose i) i
      (isPrime_of_prime p hp) hid with h | h
  · exact h
  · have := Nat.le_of_dvd hi h
    omega

/-- Lemma: the terms beyond the linear term in the binomial expansion have an extra factor.
The expansion layout is adapted from Mathlib's Apache-2.0-licensed UnitsCyclic.lean
(Antoine Chambert-Loir and Junyan Xu); no lifting theorem is invoked. -/
theorem exists_binomial_remainder (p : ℕ) (hp : p.Prime) (u v x : ℤ)
    (hvu : v ∣ u) (hpuv : (p : ℤ) * u * v ∣ u ^ p) :
    ∃ y : ℤ, (1 + u * x) ^ p = 1 + p * u * (x + v * y) := by
  rw [add_comm, add_pow]
  rw [← Finset.add_sum_erase (a := 0) _ _ (by
    simp only [Finset.mem_range]
    omega)]
  simp only [one_pow, pow_zero, Nat.choose_zero_right, Nat.cast_one, mul_one]
  rw [← Finset.add_sum_erase (a := 1) _ _ (by
    simp only [Finset.mem_erase, Finset.mem_range]
    have := hp.two_le
    omega)]
  rw [← Finset.sum_erase_add (a := p) _ _ (by
    simp only [Finset.mem_erase, Finset.mem_range]
    have := hp.two_le
    omega)]
  obtain ⟨a, ha⟩ := hvu
  obtain ⟨b, hb⟩ := hpuv
  refine ⟨a * x ^ 2 * ∑ i ∈ (((Finset.range (p + 1)).erase 0).erase 1).erase p,
    (u * x) ^ (i - 2) * (p.choose i / p : ℕ) + b * x ^ p, ?_⟩
  rw [mul_add]
  congr 2
  · rw [Nat.choose_one_right]
    ring

  simp only [mul_add, Finset.mul_sum]
  congr 1
  · apply Finset.sum_congr rfl
    intro i hi
    simp only [Finset.mem_erase, Finset.mem_range] at hi
    have hi2 : 2 ≤ i := by omega
    have hid := prime_dvd_choose p hp i (by omega) (by omega)
    calc
      (u * x) ^ i * p.choose i =
          (u * x) ^ (2 + (i - 2)) * p.choose i := by rw [Nat.add_sub_of_le hi2]
      _ = u ^ 2 * x ^ 2 * (u * x) ^ (i - 2) * (p * (p.choose i / p) : ℕ) := by
        rw [Nat.mul_div_cancel' hid]
        ring
      _ = p * u * (v * (a * x ^ 2 * ((u * x) ^ (i - 2) * (p.choose i / p : ℕ)))) := by
        rw [Nat.cast_mul, ha]
        ring
  · rw [Nat.choose_self, Nat.cast_one, mul_one, mul_pow, hb]
    ring

/-- Lemma: powering 1+pa preserves its first nonzero p-adic coefficient. -/
theorem exists_prime_power_expansion (p : ℕ) (hp : p.Prime) (hpodd : p ≠ 2)
    (a : ℤ) (m : ℕ) :
    ∃ y : ℤ, (1 + p * a) ^ (p ^ m) = 1 + (p : ℤ) ^ (m + 1) * (a + p * y) := by
  have hp3 : 3 ≤ p := by
    have := hp.two_le
    omega
  induction m with
  | zero => exact ⟨0, by simp only [Nat.zero_add, pow_zero, pow_one, mul_zero, add_zero]⟩
  | succ m ih =>
    obtain ⟨y, hy⟩ := ih
    have hdiv : (p : ℤ) * (p : ℤ) ^ (m + 1) * p ∣ ((p : ℤ) ^ (m + 1)) ^ p := by
      rw [← pow_mul, ← pow_succ', ← pow_succ]
      exact pow_dvd_pow _ (by nlinarith)
    obtain ⟨z, hz⟩ := exists_binomial_remainder p hp ((p : ℤ) ^ (m + 1)) p
      (a + p * y) (dvd_pow_self _ (by omega)) hdiv

    refine ⟨y + z, ?_⟩
    rw [pow_succ, pow_mul, hy, hz, pow_succ']
    ring

/-- Lemma: a period p^(n+1), with the previous power excluded, is the exact order. -/
theorem orderOf_eq_prime_pow_succ {M : Type*} [Monoid M] (a : M)
    (p : ℕ) (hp : p.Prime) (n : ℕ)
    (hperiod : a ^ (p ^ (n + 1)) = 1) (hprevious : a ^ (p ^ n) ≠ 1) :
    orderOf a = p ^ (n + 1) := by
  have hpos := (isOfFinOrder_iff_pow_eq_one.mpr
    ⟨p ^ (n + 1), pow_pos hp.pos _, hperiod⟩).orderOf_pos
  have hd := (pow_eq_one_iff_dvd_order a _).mp hperiod
  have hmem := Nat.mem_divisors.mpr ⟨hd, (pow_pos hp.pos (n + 1)).ne'⟩
  rw [NumberTheoreticFunctions.divisors_prime_pow p (n + 1) (isPrime_of_prime p hp)] at hmem
  obtain ⟨i, hi, hei⟩ := Finset.mem_image.mp hmem
  have hib := Finset.mem_range.mp hi

  by_cases he : i = n + 1
  · exact (he ▸ hei).symm
  · have hin : i ≤ n := by omega
    have hdiv : orderOf a ∣ p ^ n := hei ▸ pow_dvd_pow p hin
    exact (hprevious ((pow_eq_one_iff_dvd_order a _).mpr hdiv)).elim

/-- Theorem: 1+pa has order p^n modulo p^(n+1) when p is odd and p does not divide a. -/
theorem orderOf_one_add_mul_prime (p : ℕ) (hp : p.Prime) (hpodd : p ≠ 2)
    (a : ℤ) (ha : ¬(p : ℤ) ∣ a) (n : ℕ) :
    orderOf (1 + p * a : ZMod (p ^ (n + 1))) = p ^ n := by
  have hpz : (p : ℤ) ≠ 0 := by exact_mod_cast hp.ne_zero
  cases n with
  | zero =>
    rw [pow_one, ZMod.natCast_self, zero_mul, add_zero, orderOf_one, pow_zero]
  | succ n =>
    have hcast (m : ℕ) : ∃ y : ℤ,
        (1 + p * a : ZMod (p ^ (n + 1 + 1))) ^ (p ^ m) =
          1 + (p : ZMod (p ^ (n + 1 + 1))) ^ (m + 1) * (a + p * y) := by
      obtain ⟨y, hy⟩ := exists_prime_power_expansion p hp hpodd a m
      refine ⟨y, ?_⟩
      have he := congrArg (fun x : ℤ => (x : ZMod (p ^ (n + 1 + 1)))) hy
      simpa only [Int.cast_pow, Int.cast_add, Int.cast_mul, Int.cast_one,
        Int.cast_natCast] using he

    apply orderOf_eq_prime_pow_succ _ p hp n
    · obtain ⟨y, hy⟩ := hcast (n + 1)
      rw [hy, ← Nat.cast_pow, ZMod.natCast_self, zero_mul, add_zero]

    · obtain ⟨y, hy⟩ := hcast n
      intro he
      rw [hy, add_eq_left] at he
      have hzero : (((p : ℤ) ^ (n + 1) * (a + p * y) : ℤ) :
          ZMod (p ^ (n + 1 + 1))) = 0 := by
        simpa only [Int.cast_mul, Int.cast_pow, Int.cast_add, Int.cast_natCast] using he
      have hdiv := (ZMod.intCast_zmod_eq_zero_iff_dvd _ _).mp hzero
      rw [Nat.cast_pow, pow_succ, Int.mul_dvd_mul_iff_left (pow_ne_zero _ hpz)] at hdiv
      exact ha (by
        have hsub := dvd_sub hdiv (dvd_mul_right (p : ℤ) y)
        simpa only [add_sub_cancel_right] using hsub)

end ElementaryNumberTheory.PrimitiveRootsAndIndices
