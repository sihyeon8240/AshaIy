module

public import Textbooks.ElementaryNumberTheory.CertainNonlinearDiophantineEquations.FourthPowerSums
public import Textbooks.ElementaryNumberTheory.PrimesAndTheirDistribution.SieveOfEratosthenes

public section

namespace ElementaryNumberTheory.CertainNonlinearDiophantineEquations

/-- Lemma: an exponent greater than two has either four or an odd prime as a divisor. -/
theorem four_dvd_or_odd_prime_dvd {n : ℕ} (hn : 2 < n) :
    4 ∣ n ∨ ∃ p : ℕ, p.Prime ∧ Odd p ∧ p ∣ n := by
  by_cases hfour : 4 ∣ n
  · exact Or.inl hfour
  · have find_odd_prime (m : ℕ) (hm : 1 < m) (hmod : m % 2 = 1) (hd : m ∣ n) :
        ∃ p : ℕ, p.Prime ∧ Odd p ∧ p ∣ n := by
      obtain ⟨p, hp, hpm, _⟩ := PrimesAndTheirDistribution.exists_prime_divisor m hm
      have hpstd : p.Prime := Nat.prime_def.mpr hp
      have hpne : p ≠ 2 := by
        intro heq
        subst p
        have := Nat.mod_eq_zero_of_dvd hpm
        omega
      exact ⟨p, hpstd, hpstd.odd_of_ne_two hpne, hpm.trans hd⟩
    rcases Nat.mod_two_eq_zero_or_one n with hmod | hmod
    · have hd : 2 ∣ n := Nat.dvd_of_mod_eq_zero hmod
      obtain ⟨m, hm⟩ := hd
      have hmgt : 1 < m := by omega
      have hmodm : m % 2 = 1 := by
        by_contra hnot
        have hdm : 2 ∣ m := Nat.dvd_of_mod_eq_zero (by omega)
        obtain ⟨k, hk⟩ := hdm
        exact hfour ⟨k, by omega⟩
      exact Or.inr (find_odd_prime m hmgt hmodm ⟨2, by omega⟩)
    · exact Or.inr (find_odd_prime n (by omega) hmod dvd_rfl)

/-- Theorem: any hypothetical Fermat solution with exponent greater than two
would yield a positive solution with an odd prime exponent. -/
theorem exists_odd_prime_exponent_solution {x y z : ℤ} {n : ℕ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (hn : 2 < n)
    (heq : x ^ n + y ^ n = z ^ n) :
    ∃ p : ℕ, p.Prime ∧ Odd p ∧ ∃ a b c : ℤ,
      0 < a ∧ 0 < b ∧ 0 < c ∧ a ^ p + b ^ p = c ^ p := by
  rcases four_dvd_or_odd_prime_dvd hn with hfour | ⟨p, hp, hpodd, k, hk⟩
  · exact (powers_ne_power_of_four_dvd hx hy hz (by omega) hfour heq).elim
  · refine ⟨p, hp, hpodd, x ^ k, y ^ k, z ^ k,
      pow_pos hx k, pow_pos hy k, pow_pos hz k, ?_⟩
    simpa only [← pow_mul, Nat.mul_comm k p, ← hk] using heq

end ElementaryNumberTheory.CertainNonlinearDiophantineEquations
