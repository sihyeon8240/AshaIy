module

public import Textbooks.ElementaryNumberTheory.CertainNonlinearDiophantineEquations.FourthPowerDifferences
public import Mathlib.Data.Rat.Lemmas

import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

public section

namespace ElementaryNumberTheory.CertainNonlinearDiophantineEquations

/-- Lemma: the legs of a positive integer right triangle have different lengths. -/
theorem legs_ne {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (h : PythagoreanTriple x y z) : x ≠ y := by
  intro hsame
  obtain ⟨d, a, b, c, hd, ha, _, _, hp, hxa, hyb, _, _⟩ :=
    exists_primitive_factor hx hy hz h
  have hab : a = b := by nlinarith only [hd, hxa, hyb, hsame]
  rcases (primitive_parity ha hp).1 with hpar | hpar
  · exact Int.not_even_iff_odd.mpr hpar.2 (hab ▸ hpar.1)
  · exact Int.not_even_iff_odd.mpr hpar.1 (hab.symm ▸ hpar.2)

/-- Theorem: a positive integer right triangle cannot have square area. -/
theorem area_ne_square {x y z u : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (hu : 0 < u)
    (h : PythagoreanTriple x y z) : x * y ≠ 2 * u ^ 2 := by
  intro harea
  have hlegs := legs_ne hx hy hz h
  have hdiff : x ^ 2 - y ^ 2 ≠ 0 := by
    intro heq
    apply hlegs
    exact (sq_eq_sq₀ hx.le hy.le).mp (by omega)
  have heq := pythagoreanTriple_iff_sq.mp h
  have hnew : z ^ 4 - (2 * u) ^ 4 = |x ^ 2 - y ^ 2| ^ 2 := by
    rw [sq_abs]
    calc
      z ^ 4 - (2 * u) ^ 4 = (x ^ 2 + y ^ 2) ^ 2 - 4 * (2 * u ^ 2) ^ 2 := by
        rw [heq]
        ring
      _ = (x ^ 2 - y ^ 2) ^ 2 := by rw [← harea]; ring
  exact difference_fourth_powers_ne_square hz (by omega) (abs_pos.mpr hdiff) hnew

/-- Lemma: a common positive denominator clears finitely many rational coordinates. -/
private theorem clear_four_denominators (x y z u : ℚ) :
    ∃ D : ℕ, 0 < D ∧ ∃ a b c v : ℤ,
      (a : ℚ) = D * x ∧ (b : ℚ) = D * y ∧ (c : ℚ) = D * z ∧ (v : ℚ) = D * u := by
  let D := x.den * y.den * z.den * u.den
  have hD : 0 < D := by
    dsimp only [D]
    exact mul_pos (mul_pos (mul_pos x.den_pos y.den_pos) z.den_pos) u.den_pos
  have integral (q : ℚ) (hd : q.den ∣ D) : ∃ a : ℤ, (a : ℚ) = D * q := by
    obtain ⟨k, hk⟩ := hd
    refine ⟨(k : ℤ) * q.num, ?_⟩
    rw [hk]
    push_cast
    rw [mul_right_comm, Rat.den_mul_eq_num]
    ring
  obtain ⟨a, ha⟩ := integral x ⟨y.den * z.den * u.den, by dsimp only [D]; ring⟩
  obtain ⟨b, hb⟩ := integral y ⟨x.den * z.den * u.den, by dsimp only [D]; ring⟩
  obtain ⟨c, hc⟩ := integral z ⟨x.den * y.den * u.den, by dsimp only [D]; ring⟩
  obtain ⟨v, hv⟩ := integral u ⟨x.den * y.den * z.den, by dsimp only [D]; ring⟩
  exact ⟨D, hD, a, b, c, v, ha, hb, hc, hv⟩

/-- Corollary: a positive rational right triangle cannot have rational square area. -/
theorem rational_area_ne_square {x y z u : ℚ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (hu : 0 < u)
    (h : x ^ 2 + y ^ 2 = z ^ 2) : x * y ≠ 2 * u ^ 2 := by
  intro harea
  obtain ⟨D, hD, a, b, c, v, ha, hb, hc, hv⟩ := clear_four_denominators x y z u
  have hDq : (0 : ℚ) < D := by exact_mod_cast hD
  have hapos : 0 < a := by exact_mod_cast (ha.symm ▸ mul_pos hDq hx)
  have hbpos : 0 < b := by exact_mod_cast (hb.symm ▸ mul_pos hDq hy)
  have hcpos : 0 < c := by exact_mod_cast (hc.symm ▸ mul_pos hDq hz)
  have hvpos : 0 < v := by exact_mod_cast (hv.symm ▸ mul_pos hDq hu)
  have htriangle : PythagoreanTriple a b c := by
    apply pythagoreanTriple_iff_sq.mpr
    have heq : (a : ℚ) ^ 2 + (b : ℚ) ^ 2 = (c : ℚ) ^ 2 := by
      rw [ha, hb, hc]
      calc
        ((D : ℚ) * x) ^ 2 + (D * y) ^ 2 = D ^ 2 * (x ^ 2 + y ^ 2) := by ring
        _ = D ^ 2 * z ^ 2 := by rw [h]
        _ = (D * z) ^ 2 := by ring
    exact_mod_cast heq
  have hareaint : a * b = 2 * v ^ 2 := by
    have heq : (a : ℚ) * b = 2 * (v : ℚ) ^ 2 := by
      rw [ha, hb, hv]
      calc
        (D : ℚ) * x * (D * y) = D ^ 2 * (x * y) := by ring
        _ = D ^ 2 * (2 * u ^ 2) := by rw [harea]
        _ = 2 * (D * u) ^ 2 := by ring
    exact_mod_cast heq
  exact area_ne_square hapos hbpos hcpos hvpos htriangle hareaint

/-- Corollary: three distinct integer squares in arithmetic progression cannot
have a positive square common difference. -/
theorem arithmetic_progression_difference_ne_square {a b c u : ℤ}
    (hu : 0 < u) (hab : b ^ 2 - a ^ 2 = u ^ 2) : c ^ 2 - b ^ 2 ≠ u ^ 2 := by
  intro hbc
  have hca : |a| < |c| := by
    nlinarith only [hab, hbc, sq_pos_of_pos hu, abs_nonneg a, abs_nonneg c, sq_abs a, sq_abs c]
  have hbpos : 0 < |b| := by
    nlinarith only [hab, sq_pos_of_pos hu, sq_nonneg a, abs_nonneg b, sq_abs b]
  have hx : 0 < |c| + |a| := by
    have := abs_nonneg a
    omega
  have hy : 0 < |c| - |a| := sub_pos.mpr hca
  have hz : 0 < 2 * |b| := by omega
  have hp : PythagoreanTriple (|c| + |a|) (|c| - |a|) (2 * |b|) := by
    apply pythagoreanTriple_iff_sq.mpr
    nlinarith only [hab, hbc, sq_abs a, sq_abs b, sq_abs c]
  apply area_ne_square hx hy hz hu hp
  nlinarith only [hab, hbc, sq_abs a, sq_abs c]

/-- Lemma: a positive integer square has a positive integer square root. -/
private theorem positive_square_root {x : ℤ} (hx : 0 < x) (hs : IsSquare x) :
    ∃ a : ℤ, 0 < a ∧ x = a ^ 2 := by
  obtain ⟨a, ha⟩ := hs
  have hane : a ≠ 0 := by intro heq; rw [heq] at ha; nlinarith only [hx, ha]
  exact ⟨|a|, abs_pos.mpr hane, by nlinarith only [ha, sq_abs a]⟩

/-- Corollary: at most one side of a positive integer right triangle is a square. -/
theorem at_most_one_square_side {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (h : PythagoreanTriple x y z) :
    ¬(IsSquare x ∧ IsSquare y) ∧ ¬(IsSquare x ∧ IsSquare z) ∧
      ¬(IsSquare y ∧ IsSquare z) := by
  have heq := pythagoreanTriple_iff_sq.mp h
  refine ⟨?_, ?_, ?_⟩
  · rintro ⟨hxs, hys⟩
    obtain ⟨a, ha, hxa⟩ := positive_square_root hx hxs
    obtain ⟨b, hb, hyb⟩ := positive_square_root hy hys
    rw [hxa, hyb] at heq
    exact sum_fourth_powers_ne_square ha hb hz (by nlinarith only [heq])
  · rintro ⟨hxs, hzs⟩
    obtain ⟨a, ha, hxa⟩ := positive_square_root hx hxs
    obtain ⟨c, hc, hzc⟩ := positive_square_root hz hzs
    rw [hxa, hzc] at heq
    exact difference_fourth_powers_ne_square hc ha hy (by nlinarith only [heq])
  · rintro ⟨hys, hzs⟩
    obtain ⟨b, hb, hyb⟩ := positive_square_root hy hys
    obtain ⟨c, hc, hzc⟩ := positive_square_root hz hzs
    rw [hyb, hzc] at heq
    exact difference_fourth_powers_ne_square hc hb hx (by nlinarith only [heq])

end ElementaryNumberTheory.CertainNonlinearDiophantineEquations
