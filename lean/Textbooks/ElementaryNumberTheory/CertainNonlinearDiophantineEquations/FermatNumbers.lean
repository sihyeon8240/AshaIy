import Textbooks.ElementaryNumberTheory.CertainNonlinearDiophantineEquations.ExponentReduction
import Mathlib.Algebra.BigOperators.Ring.Nat

namespace ElementaryNumberTheory.CertainNonlinearDiophantineEquations

/-- Lemma: the only positive odd divisor of a power of two is one. -/
private theorem odd_divisor_two_pow_eq_one {d N : ℕ} (hd : 0 < d) (hodd : Odd d)
    (hdiv : d ∣ 2 ^ N) : d = 1 := by
  induction N with
  | zero => exact Nat.eq_one_of_dvd_one (by simpa only [pow_zero] using hdiv)
  | succ N ih =>
    have hcop : d.Coprime 2 := Nat.coprime_two_right.mpr hodd
    have hdiv' : d ∣ 2 * 2 ^ N := by simpa only [pow_succ, mul_comm] using hdiv
    exact ih (PrimitiveRootsAndIndices.nat_dvd_of_dvd_mul_of_coprime d 2 (2 ^ N) hd hcop hdiv')

/-- Theorem: a Fermat number is never a proper power of an integer greater than one. -/
theorem fermat_number_ne_proper_power {a m : ℕ} (n : ℕ) (ha : 1 < a) (hm : 1 < m) :
    2 ^ (2 ^ n) + 1 ≠ a ^ m := by
  intro heq
  obtain ⟨p, hp, hpm, _⟩ := PrimesAndTheirDistribution.exists_prime_divisor m hm
  have hpstd : p.Prime := Nat.prime_def.mpr hp
  obtain ⟨k, hk⟩ := hpm
  have hkpos : 0 < k := by nlinarith only [hm, hk]
  let b := a ^ k
  have hb : 1 < b := one_lt_pow₀ ha hkpos.ne'
  have hbpow : b ^ p = 2 ^ (2 ^ n) + 1 := by
    dsimp only [b]
    rw [← pow_mul, Nat.mul_comm k p, ← hk, ← heq]
  by_cases hp2 : p = 2
  · subst p
    cases n with
    | zero =>
      norm_num at hbpow
      nlinarith only [hb, hbpow]
    | succ n =>
      let c : ℕ := 2 ^ (2 ^ n)
      have hc : 0 < c := pow_pos (by decide : 0 < (2 : ℕ)) _
      have hpow : (2 : ℕ) ^ (2 ^ (n + 1)) = c ^ 2 := by
        dsimp only [c]
        rw [pow_succ (2 : ℕ) n, pow_mul]
      have heq' : b ^ 2 = c ^ 2 + 1 := by
        simpa only [hpow] using hbpow
      have hcb : c < b := by nlinarith only [heq', hb, hc]
      nlinarith only [hcb, heq', hc]
  · have hpodd := hpstd.odd_of_ne_two hp2
    have hFodd : Odd (2 ^ (2 ^ n) + 1 : ℕ) :=
      (even_two.pow_of_ne_zero (pow_ne_zero n (by decide : (2 : ℕ) ≠ 0))).add_one
    have hbodd : Odd b := (Nat.odd_pow_iff hpstd.ne_zero).mp (hbpow.symm ▸ hFodd)
    let S : ℕ := ∑ i ∈ Finset.range p, b ^ i
    have hSodd : Odd S := by
      dsimp only [S]
      rw [Finset.odd_sum_iff_odd_card_odd]
      simpa only [hbodd.pow, Finset.filter_true, Finset.card_range] using hpodd
    have hSge : b ≤ S := by
      simpa only [pow_one] using
        (Finset.single_le_sum (fun i (_ : i ∈ Finset.range p) => Nat.zero_le (b ^ i))
          (Finset.mem_range.mpr hpstd.one_lt))
    have hSdiv : S ∣ 2 ^ (2 ^ n) := by
      apply Int.natCast_dvd_natCast.mp
      refine ⟨(b : ℤ) - 1, ?_⟩
      have hgeom := geom_sum_mul (b : ℤ) p
      have hcast : (S : ℤ) = ∑ i ∈ Finset.range p, (b : ℤ) ^ i := by
        simp only [S, Nat.cast_sum, Nat.cast_pow]
      rw [← hcast] at hgeom
      have hbpow' : (b : ℤ) ^ p = (2 : ℤ) ^ (2 ^ n) + 1 := by exact_mod_cast hbpow
      push_cast
      nlinarith only [hgeom, hbpow']
    have hSone := odd_divisor_two_pow_eq_one (by omega : 0 < S) hSodd hSdiv
    omega

end ElementaryNumberTheory.CertainNonlinearDiophantineEquations
