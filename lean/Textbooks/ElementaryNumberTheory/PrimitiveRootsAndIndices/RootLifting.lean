import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.CompositeRoots

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

open scoped Classical
open EulersGeneralizationOfFermatsTheorem

/-- Lemma: a nontrivial first lift has a coefficient not divisible by the prime. -/
theorem exists_lifting_coefficient (p : ℕ) (_hp : p.Prime) (r : ℤ)
    (hr : IsPrimitiveRoot (r : ZMod p) (p - 1))
    (hnot : (r : ZMod (p ^ 2)) ^ (p - 1) ≠ 1) :
    ∃ a : ℤ, r ^ (p - 1) = 1 + p * a ∧ ¬(p : ℤ) ∣ a := by
  have hcong : r ^ (p - 1) ≡ 1 [ZMOD (p : ℤ)] := by
    apply (ZMod.intCast_eq_intCast_iff _ _ p).mp
    simpa only [Int.cast_pow, Int.cast_one] using hr.pow_eq_one
  obtain ⟨a, ha⟩ := (TheTheoryOfCongruences.modEq_iff_dvd_sub _ _ _).mp hcong
  have he : r ^ (p - 1) = 1 + p * a := by linarith

  refine ⟨a, he, ?_⟩
  rintro ⟨b, hb⟩
  apply hnot
  have hcast := congrArg (fun z : ℤ => (z : ZMod (p ^ 2))) he
  rw [hb] at hcast
  simp only [Int.cast_pow, Int.cast_add, Int.cast_one, Int.cast_mul, Int.cast_natCast] at hcast
  have hz : (p : ZMod (p ^ 2)) * p = 0 := by
    rw [← pow_two, ← Nat.cast_pow, ZMod.natCast_self]
  simpa only [← mul_assoc, hz, zero_mul, add_zero] using hcast

/-- Lemma: a first nonzero p-adic coefficient remains nonzero at every higher lift. -/
theorem lifting_noncongruence (p : ℕ) (hp : p.Prime) (hpodd : p ≠ 2)
    (r a : ℤ) (hr : r ^ (p - 1) = 1 + p * a) (ha : ¬(p : ℤ) ∣ a) (j : ℕ) :
    (r : ZMod (p ^ (j + 2))) ^ (p ^ j * (p - 1)) ≠ 1 := by
  obtain ⟨y, hy⟩ := exists_prime_power_expansion p hp hpodd a j
  have he : r ^ (p ^ j * (p - 1)) = 1 + (p : ℤ) ^ (j + 1) * (a + p * y) := by
    rw [mul_comm, pow_mul, hr]
    exact hy
  have hcast := congrArg (fun z : ℤ => (z : ZMod (p ^ (j + 2)))) he
  simp only [Int.cast_pow, Int.cast_add, Int.cast_one, Int.cast_mul, Int.cast_natCast] at hcast
  intro h
  have hz : (((p : ℤ) ^ (j + 1) * (a + p * y) : ℤ) : ZMod (p ^ (j + 2))) = 0 := by
    have hh : (p : ZMod (p ^ (j + 2))) ^ (j + 1) * (a + p * y) = 0 := by
      rw [h] at hcast
      exact add_eq_left.mp hcast.symm
    simpa only [Int.cast_mul, Int.cast_pow, Int.cast_add, Int.cast_natCast] using hh

  have hd := (ZMod.intCast_zmod_eq_zero_iff_dvd _ _).mp hz
  have hpz : (p : ℤ) ≠ 0 := by exact_mod_cast hp.ne_zero
  rw [Nat.cast_pow, show j + 2 = j + 1 + 1 by omega, pow_succ,
    Int.mul_dvd_mul_iff_left (pow_ne_zero _ hpz)] at hd
  have hdsub := dvd_sub hd (dvd_mul_right (p : ℤ) y)
  exact ha (by simpa only [add_sub_cancel_right] using hdsub)

/-- Theorem: a primitive root with a nontrivial first lift is primitive at every prime power. -/
theorem primitiveRoot_all_prime_powers (p : ℕ) (hp : p.Prime) (hpodd : p ≠ 2) (r : ℤ)
    (hr : IsPrimitiveRoot (r : ZMod p) (p - 1))
    (hnot : (r : ZMod (p ^ 2)) ^ (p - 1) ≠ 1) (k : ℕ) :
    IsPrimitiveRoot (r : ZMod (p ^ (k + 1))) (Nat.totient (p ^ (k + 1))) := by
  have hp1 : 0 < p - 1 := by
    have := hp.two_le
    omega
  obtain ⟨a, ha, hpa⟩ := exists_lifting_coefficient p hp r hr hnot
  have hperiod (j : ℕ) : (r : ZMod (p ^ (j + 1))) ^ (p ^ j * (p - 1)) = 1 := by
    obtain ⟨y, hy⟩ := exists_prime_power_expansion p hp hpodd a j
    have he : r ^ (p ^ j * (p - 1)) = 1 + (p : ℤ) ^ (j + 1) * (a + p * y) := by
      rw [mul_comm, pow_mul, ha]
      exact hy
    have hcast := congrArg (fun z : ℤ => (z : ZMod (p ^ (j + 1)))) he
    simp only [Int.cast_pow, Int.cast_add, Int.cast_one, Int.cast_mul, Int.cast_natCast] at hcast
    rwa [← Nat.cast_pow, ZMod.natCast_self, zero_mul, add_zero] at hcast

  cases k with
  | zero =>
    rw [show p ^ (0 + 1) = p by simp, totient_prime p (isPrime_of_prime p hp)]
    exact hr

  | succ n =>
    let x := (r : ZMod (p ^ (n + 1 + 1)))
    have hdiv := (pow_eq_one_iff_dvd_order x _).mp (hperiod (n + 1))
    have hd : p - 1 ∣ orderOf x := by
      let f := ZMod.castHom (dvd_pow_self p (by omega : n + 1 + 1 ≠ 0)) (ZMod p)
      have he := congrArg f (pow_orderOf_eq_one x)
      simp only [map_pow, map_one] at he
      have hfx : f x = (r : ZMod p) := by
        exact map_intCast f r
      rw [hfx] at he
      exact hr.dvd_of_pow_eq_one _ he
    obtain ⟨t, ht⟩ := hd
    have htd : t ∣ p ^ (n + 1) := by
      have h := hdiv
      rw [ht, mul_comm (p ^ (n + 1))] at h
      exact (Nat.mul_dvd_mul_iff_left hp1).mp h
    have hmem := Nat.mem_divisors.mpr ⟨htd, (pow_pos hp.pos (n + 1)).ne'⟩
    rw [NumberTheoreticFunctions.divisors_prime_pow p (n + 1) (isPrime_of_prime p hp)] at hmem
    obtain ⟨i, hi, hei⟩ := Finset.mem_image.mp hmem
    have hib := Finset.mem_range.mp hi

    have hiend : i = n + 1 := by
      by_contra hne
      have hin : i ≤ n := by omega
      have hdprev : orderOf x ∣ p ^ n * (p - 1) := by
        rw [ht, ← hei, mul_comm (p ^ n)]
        exact Nat.mul_dvd_mul_left (p - 1) (pow_dvd_pow p hin)
      exact lifting_noncongruence p hp hpodd r a ha hpa n
        ((pow_eq_one_iff_dvd_order x _).mpr hdprev)

    apply (isPrimitiveRoot_iff_orderOf _ _).mpr
    rw [totient_prime_pow_succ p (n + 1) (isPrime_of_prime p hp), ht, ← hei, hiend, mul_comm]

/-- Lemma: if s^2=0, only the constant and linear terms survive a binomial expansion. -/
theorem add_pow_of_sq_eq_zero {R : Type*} [CommRing R] (r s : R) (hs : s ^ 2 = 0) (k : ℕ) :
    (r + s) ^ (k + 1) = r ^ (k + 1) + (k + 1 : ℕ) * r ^ k * s := by
  induction k with
  | zero => simp only [Nat.zero_add, pow_one, pow_zero, Nat.cast_one, one_mul]
  | succ k ih =>
    rw [pow_succ (r + s), ih]
    calc
      (r ^ (k + 1) + (k + 1 : ℕ) * r ^ k * s) * (r + s) =
          r ^ (k + 1 + 1) + (k + 1 + 1 : ℕ) * r ^ (k + 1) * s +
            (k + 1 : ℕ) * r ^ k * s ^ 2 := by
        simp only [pow_succ, Nat.cast_add, Nat.cast_one]
        ring
      _ = r ^ (k + 1 + 1) + (k + 1 + 1 : ℕ) * r ^ (k + 1) * s := by
        rw [hs, mul_zero, add_zero]

/-- Lemma: either r or r+p has a nontrivial first lift. -/
theorem first_lift_or_add_prime (p : ℕ) (hp : p.Prime) (hpodd : p ≠ 2) (r : ℤ)
    (hr : IsPrimitiveRoot (r : ZMod p) (p - 1)) :
    (r : ZMod (p ^ 2)) ^ (p - 1) ≠ 1 ∨
      ((r + p : ℤ) : ZMod (p ^ 2)) ^ (p - 1) ≠ 1 := by
  have : Fact p.Prime := ⟨hp⟩
  have hp3 : 3 ≤ p := by
    have := hp.two_le
    omega
  have hs : (p : ZMod (p ^ 2)) ^ 2 = 0 := by rw [← Nat.cast_pow, ZMod.natCast_self]
  have hbin := add_pow_of_sq_eq_zero (r : ZMod (p ^ 2)) p hs (p - 2)
  rw [show p - 2 + 1 = p - 1 by omega] at hbin
  by_contra hboth
  push Not at hboth
  obtain ⟨h₁, h₂⟩ := hboth
  simp only [Int.cast_add, Int.cast_natCast] at h₂
  have he : ((p - 1 : ℕ) : ZMod (p ^ 2)) * (r : ZMod (p ^ 2)) ^ (p - 2) * p = 0 := by
    rw [h₂, h₁] at hbin
    exact add_eq_left.mp hbin.symm
  have hz : ((((p - 1 : ℕ) : ℤ) * r ^ (p - 2) * p : ℤ) : ZMod (p ^ 2)) = 0 := by
    simpa only [Int.cast_mul, Int.cast_pow, Int.cast_natCast] using he
  have hd := (ZMod.intCast_zmod_eq_zero_iff_dvd _ _).mp hz
  have hpz : (p : ℤ) ≠ 0 := by exact_mod_cast hp.ne_zero
  rw [Nat.cast_pow, pow_two, Int.mul_dvd_mul_iff_right hpz] at hd
  have hzero := (ZMod.intCast_zmod_eq_zero_iff_dvd _ _).mpr hd
  simp only [Int.cast_mul, Int.cast_pow, Int.cast_natCast] at hzero

  have hrne : (r : ZMod p) ≠ 0 := by
    intro hz
    have h := hr.pow_eq_one
    rw [hz, zero_pow (by omega : p - 1 ≠ 0)] at h
    exact zero_ne_one h
  have hmne : ((p - 1 : ℕ) : ZMod p) ≠ 0 := by
    intro hz
    have hd := (ZMod.natCast_eq_zero_iff _ _).mp hz
    have := Nat.le_of_dvd (by omega : 0 < p - 1) hd
    omega
  exact (mul_ne_zero hmne (pow_ne_zero _ hrne)) hzero

/-- Corollary: either r or r+p is primitive modulo p^2 when r is primitive modulo p. -/
theorem primitiveRoot_or_add_prime (p : ℕ) (hp : p.Prime) (hpodd : p ≠ 2) (r : ℤ)
    (hr : IsPrimitiveRoot (r : ZMod p) (p - 1)) :
    IsPrimitiveRoot (r : ZMod (p ^ 2)) (Nat.totient (p ^ 2)) ∨
      IsPrimitiveRoot ((r + p : ℤ) : ZMod (p ^ 2)) (Nat.totient (p ^ 2)) := by
  rcases first_lift_or_add_prime p hp hpodd r hr with h | h
  · exact Or.inl (primitiveRoot_all_prime_powers p hp hpodd r hr h 1)
  · have hr' : IsPrimitiveRoot ((r + p : ℤ) : ZMod p) (p - 1) := by
      simpa only [Int.cast_add, Int.cast_natCast, ZMod.natCast_self, add_zero] using hr
    exact Or.inr (primitiveRoot_all_prime_powers p hp hpodd (r + p) hr' h 1)

end ElementaryNumberTheory.PrimitiveRootsAndIndices
