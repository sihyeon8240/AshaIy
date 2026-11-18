module

public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.TwoSquarePrimes

import Mathlib.Tactic.IntervalCases

public section

namespace ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares

/-- Lemma: an integer square is zero or one modulo four. -/
theorem sq_mod_four (a : ℤ) : a ^ 2 % 4 = 0 ∨ a ^ 2 % 4 = 1 := by
  have h0 := Int.emod_nonneg a (by decide : (4 : ℤ) ≠ 0)
  have h4 := Int.emod_lt_of_pos a (by decide : (0 : ℤ) < 4)
  interval_cases ha : a % 4 <;> norm_num [pow_two, Int.mul_emod, ha]

/-- Theorem: a positive integer is a difference of two integer squares exactly when
it is not congruent to two modulo four. -/
theorem sq_sub_sq_iff (n : ℤ) (_hn : 0 < n) :
    (∃ a b : ℤ, n = a ^ 2 - b ^ 2) ↔ n % 4 ≠ 2 := by
  constructor
  · rintro ⟨a, b, rfl⟩
    have ha := sq_mod_four a
    have hb := sq_mod_four b
    omega

  · intro hn
    have h0 := Int.emod_nonneg n (by decide : (4 : ℤ) ≠ 0)
    have h4 := Int.emod_lt_of_pos n (by decide : (0 : ℤ) < 4)
    have heq := Int.emod_add_mul_ediv n 4
    rcases (by omega : n % 4 = 0 ∨ n % 4 = 1 ∨ n % 4 = 3) with h | h | h
    · refine ⟨n / 4 + 1, n / 4 - 1, ?_⟩
      rw [h] at heq
      nlinarith

    · refine ⟨2 * (n / 4) + 1, 2 * (n / 4), ?_⟩
      rw [h] at heq
      nlinarith

    · refine ⟨2 * (n / 4) + 2, 2 * (n / 4) + 1, ?_⟩
      rw [h] at heq
      nlinarith

/-- Proposition: nonnegative difference representations correspond to positive factor
pairs of equal parity, with the smaller factor first. -/
theorem sq_sub_sq_iff_factor_pair {n a b : ℤ} :
    (n = a ^ 2 - b ^ 2 ∧ 0 ≤ b ∧ b < a) ↔
      ∃ u v : ℤ, 0 < u ∧ u ≤ v ∧ u % 2 = v % 2 ∧ n = u * v ∧
        a = (v + u) / 2 ∧ b = (v - u) / 2 := by
  constructor
  · rintro ⟨hn, hb, hab⟩
    refine ⟨a - b, a + b, by omega, by omega, by omega, ?_, ?_, ?_⟩
    · nlinarith [hn]
    · omega
    · omega

  · rintro ⟨u, v, hu, huv, hpar, hn, ha, hb⟩
    have ha2 : 2 * a = v + u := by omega
    have hb2 : 2 * b = v - u := by omega
    refine ⟨?_, by omega, by omega⟩
    nlinarith [hn]

/-- Lemma: the coordinates in an odd prime's nonnegative difference representation
are consecutive. -/
theorem prime_sq_sub_sq_consecutive {p : ℕ} (hp : p.Prime) {a b : ℤ}
    (h : (p : ℤ) = a ^ 2 - b ^ 2) (hb : 0 ≤ b) (hab : b < a) : a = b + 1 := by
  let u := a - b
  let v := a + b
  have hu : 0 < u := by
    dsimp only [u]
    omega
  have huv : u ≤ v := by
    dsimp only [u, v]
    omega
  have hn : (p : ℤ) = u * v := by
    dsimp only [u, v]
    nlinarith [h]
  have huabs : (u.natAbs : ℤ) = u := by rw [Int.natCast_natAbs, abs_of_pos hu]
  have hd : u.natAbs ∣ p := by
    apply Int.natCast_dvd_natCast.mp
    exact ⟨v, by
      rw [huabs]
      exact hn⟩

  rcases hp.eq_one_or_self_of_dvd _ hd with he | he
  · rw [he, Nat.cast_one] at huabs
    dsimp only [u] at huabs
    omega

  · rw [he] at huabs
    have hv : v = 1 := by
      apply mul_left_cancel₀ (by exact_mod_cast hp.ne_zero : (p : ℤ) ≠ 0)
      rw [← huabs] at hn
      simpa only [mul_one] using hn.symm
    have hp' : (1 : ℤ) < p := by exact_mod_cast hp.one_lt
    omega

/-- Corollary: an odd prime has a unique difference representation with a>b≥0. -/
theorem prime_sq_sub_sq_unique {p : ℕ} (hp : p.Prime) (hp2 : p ≠ 2) :
    ∃! ab : ℤ × ℤ, (p : ℤ) = ab.1 ^ 2 - ab.2 ^ 2 ∧
      0 ≤ ab.2 ∧ ab.2 < ab.1 := by
  have ho := Nat.odd_iff.mp (hp.odd_of_ne_two hp2)
  have hp' : (1 : ℤ) < p := by exact_mod_cast hp.one_lt
  refine ⟨((p + 1) / 2, (p - 1) / 2), ?_, ?_⟩
  · have hpodd : (p : ℤ) % 2 = 1 := by exact_mod_cast ho
    have ha : 2 * (((p : ℤ) + 1) / 2) = p + 1 := by omega
    have hb : 2 * (((p : ℤ) - 1) / 2) = p - 1 := by omega
    exact ⟨by nlinarith, by omega, by omega⟩

  · rintro ⟨a, b⟩ ⟨heq, hb, hab⟩
    change (p : ℤ) = a ^ 2 - b ^ 2 at heq
    have hcon := prime_sq_sub_sq_consecutive hp heq hb hab
    have hb2 : 2 * b = p - 1 := by
      rw [hcon] at heq
      nlinarith only [heq]
    apply Prod.ext <;> dsimp <;> omega

end ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares
