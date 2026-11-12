module

public import Textbooks.ElementaryNumberTheory.CertainNonlinearDiophantineEquations.FourthPowerSums

import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Positivity

public section

namespace ElementaryNumberTheory.CertainNonlinearDiophantineEquations

/-- Lemma: splitting the even parameter twice produces a smaller first coordinate. -/
private theorem difference_descent_even_parameter {e o y x : ℤ}
    (he : 0 < e) (ho : 0 < o) (hy : 0 < y) (hx : 0 < x)
    (hcop : IsCoprime o e) (hodd : Odd o) (heven : Even e)
    (hprod : 2 * o * e = y ^ 2) (hsum : x ^ 2 = e ^ 2 + o ^ 2) :
    ∃ a b c : ℤ, 0 < a ∧ 0 < b ∧ 0 < c ∧ a ^ 4 - b ^ 4 = c ^ 2 ∧ a < x := by
  obtain ⟨v, u, hv, hu, hov, heu⟩ :=
    coprime_factors_of_twice_square ho he hy hcop hodd heven hprod
  have hp : IsPrimitivePythagoreanTriple (2 * u ^ 2) (v ^ 2) x := by
    refine ⟨pythagoreanTriple_iff_sq.mpr ?_, ?_⟩
    · rw [heu, hov] at hsum
      nlinarith only [hsum]
    · apply (isCoprime_iff_gcd_eq_one (Or.inr (pow_ne_zero 2 hv.ne'))).mp
      rw [← heu, ← hov]
      exact hcop.symm
  have hupos : 0 < 2 * u ^ 2 := by positivity
  obtain ⟨a, b, hb, hba, hab, _, huform, hvform, hxform⟩ :=
    exists_parameters_of_primitive hupos (sq_pos_of_pos hv) hx hp
      ⟨u ^ 2, by ring⟩
  have ha : 0 < a := lt_trans hb hba
  have habsq : a * b = u ^ 2 := by nlinarith only [huform]
  obtain ⟨c, d, hc, hd, hac, hbd⟩ :=
    coprime_factors_of_power_int ha hb hu (by decide) hab habsq
  have hnew : c ^ 4 - d ^ 4 = v ^ 2 := by
    rw [hac, hbd] at hvform
    nlinarith only [hvform]
  have hca : c ≤ a := by
    rw [hac]
    exact Int.le_self_sq c
  have hax : a < x := by
    rw [hxform]
    nlinarith only [Int.le_self_sq a, sq_pos_of_pos hb]
  exact ⟨c, d, v, hc, hd, hv, hnew, lt_of_le_of_lt hca hax⟩

/-- Lemma: a coprime positive solution of a difference of fourth powers being a square
would have a smaller positive solution. -/
private theorem difference_fourth_descent_coprime {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (hcop : IsCoprime x y)
    (heq : x ^ 4 - y ^ 4 = z ^ 2) :
    ∃ a b c : ℤ, 0 < a ∧ 0 < b ∧ 0 < c ∧ a ^ 4 - b ^ 4 = c ^ 2 ∧ a < x := by
  have hyz : IsCoprime y z := by
    have hbase : IsCoprime y (x ^ 4) := hcop.symm.pow_right
    have hsq : IsCoprime y (z ^ 2) := by
      convert hbase.add_mul_left_right (-(y ^ 3)) using 1
      nlinarith only [heq]
    exact (IsCoprime.pow_right_iff (by decide : 0 < 2)).mp hsq
  have hp : IsPrimitivePythagoreanTriple (y ^ 2) z (x ^ 2) := by
    refine ⟨pythagoreanTriple_iff_sq.mpr (by nlinarith only [heq]), ?_⟩
    exact (isCoprime_iff_gcd_eq_one (Or.inr hz.ne')).mp hyz.pow_left
  rcases (primitive_parity (sq_pos_of_pos hy) hp).1 with hpar | hpar
  · obtain ⟨s, t, ht, hts, hstcop, hstpar, hyform, _, hxform⟩ :=
      exists_parameters_of_primitive (sq_pos_of_pos hy) hz (sq_pos_of_pos hx) hp hpar.1
    have hs : 0 < s := lt_trans ht hts
    rcases Int.emod_two_eq_zero_or_one s with hsmod | hsmod
    · have htmod : t % 2 = 1 := by
        have := Int.emod_two_eq_zero_or_one t
        omega
      exact difference_descent_even_parameter hs ht hy hx hstcop.symm
        (Int.odd_iff.mpr htmod) (Int.even_iff.mpr hsmod)
        (by nlinarith only [hyform]) hxform
    · have htmod : t % 2 = 0 := by
        have := Int.emod_two_eq_zero_or_one t
        omega
      exact difference_descent_even_parameter ht hs hy hx hstcop
        (Int.odd_iff.mpr hsmod) (Int.even_iff.mpr htmod)
        hyform.symm (by omega)

  · have hp' : IsPrimitivePythagoreanTriple z (y ^ 2) (x ^ 2) := by
      refine ⟨hp.1.symm, ?_⟩
      exact (isCoprime_iff_gcd_eq_one (Or.inl hz.ne')).mp hyz.pow_left.symm
    obtain ⟨s, t, ht, hts, _, _, _, hyform, hxform⟩ :=
      exists_parameters_of_primitive hz (sq_pos_of_pos hy) (sq_pos_of_pos hx) hp' hpar.2
    have hs : 0 < s := lt_trans ht hts
    have hnew : s ^ 4 - t ^ 4 = (x * y) ^ 2 := by
      calc
        s ^ 4 - t ^ 4 = (s ^ 2 - t ^ 2) * (s ^ 2 + t ^ 2) := by ring
        _ = y ^ 2 * x ^ 2 := by rw [← hyform, ← hxform]
        _ = (x * y) ^ 2 := by ring
    have hsx : s < x := by
      nlinarith only [hx, hs, hxform, sq_pos_of_pos ht]
    exact ⟨s, t, x * y, hs, ht, mul_pos hx hy, hnew, hsx⟩

/-- Lemma: every positive solution of a difference of fourth powers being a square
would produce another with a smaller first coordinate. -/
theorem difference_fourth_descent {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (heq : x ^ 4 - y ^ 4 = z ^ 2) :
    ∃ a b c : ℤ, 0 < a ∧ 0 < b ∧ 0 < c ∧ a ^ 4 - b ^ 4 = c ^ 2 ∧ a < x := by
  obtain ⟨d, a, b, c, hd, ha, hb, hc, hab, hxa, _, _, heq'⟩ :=
    normalize_fourth_powers hx hy hz (ε := -1) (by nlinarith only [heq])
  have hnew : a ^ 4 - b ^ 4 = c ^ 2 := by nlinarith only [heq']
  obtain ⟨u, v, w, hu, hv, hw, heq'', hlt⟩ :=
    difference_fourth_descent_coprime ha hb hc hab hnew
  have hax : a ≤ x := by nlinarith only [hd, ha, hxa]
  exact ⟨u, v, w, hu, hv, hw, heq'', lt_of_lt_of_le hlt hax⟩

/-- Theorem: the difference of two positive fourth powers is never a positive square. -/
theorem difference_fourth_powers_ne_square {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) : x ^ 4 - y ^ 4 ≠ z ^ 2 := by
  have descent (n : ℕ) : ∀ x y z : ℤ, 0 < x → 0 < y → 0 < z → x.toNat = n →
      x ^ 4 - y ^ 4 ≠ z ^ 2 := by
    induction n using Nat.strong_induction_on with
    | h n ih =>
      intro x y z hx hy hz hn heq
      obtain ⟨a, b, c, ha, hb, hc, hnew, hlt⟩ := difference_fourth_descent hx hy hz heq
      have han : a.toNat < n := by
        rw [← hn]
        exact (Int.toNat_lt_toNat hx).mpr hlt
      exact ih a.toNat han a b c ha hb hc rfl hnew
  exact descent x.toNat x y z hx hy hz rfl

end ElementaryNumberTheory.CertainNonlinearDiophantineEquations
