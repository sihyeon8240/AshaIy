module

public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.DifferenceSquares

public section

namespace ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares

/-- Lemma: an integer square is zero, one, or four modulo eight. -/
theorem sq_mod_eight (a : ℤ) : a ^ 2 % 8 = 0 ∨ a ^ 2 % 8 = 1 ∨ a ^ 2 % 8 = 4 := by
  have h0 := Int.emod_nonneg a (by decide : (8 : ℤ) ≠ 0)
  have h8 := Int.emod_lt_of_pos a (by decide : (0 : ℤ) < 8)
  interval_cases ha : a % 8 <;> norm_num [pow_two, Int.mul_emod, ha]

/-- Lemma: four divides an integer square exactly when two divides its coordinate. -/
theorem four_dvd_sq_iff (a : ℤ) : (4 : ℤ) ∣ a ^ 2 ↔ (2 : ℤ) ∣ a := by
  rw [Int.dvd_iff_emod_eq_zero, Int.dvd_iff_emod_eq_zero]
  have h0 := Int.emod_nonneg a (by decide : (4 : ℤ) ≠ 0)
  have h4 := Int.emod_lt_of_pos a (by decide : (0 : ℤ) < 4)
  have ha2 : a % 2 = (a % 4) % 2 := by omega
  interval_cases ha : a % 4 <;> norm_num [pow_two, Int.mul_emod, ha, ha2]

/-- Lemma: if four divides a sum of three squares, all three coordinates are even. -/
theorem two_dvd_of_four_dvd_three_sq {a b c : ℤ}
    (h : (4 : ℤ) ∣ a ^ 2 + b ^ 2 + c ^ 2) :
    (2 : ℤ) ∣ a ∧ (2 : ℤ) ∣ b ∧ (2 : ℤ) ∣ c := by
  have ha := sq_mod_four a
  have hb := sq_mod_four b
  have hc := sq_mod_four c
  have hm := Int.emod_eq_zero_of_dvd h
  have hsq : a ^ 2 % 4 = 0 ∧ b ^ 2 % 4 = 0 ∧ c ^ 2 % 4 = 0 := by omega
  exact ⟨(four_dvd_sq_iff a).mp (Int.dvd_of_emod_eq_zero hsq.1),
    (four_dvd_sq_iff b).mp (Int.dvd_of_emod_eq_zero hsq.2.1),
    (four_dvd_sq_iff c).mp (Int.dvd_of_emod_eq_zero hsq.2.2)⟩

/-- Theorem: an integer of the form 4^r(8s+7), for nonnegative r and s,
cannot be a sum of three integer squares. -/
theorem not_three_sq (r s : ℕ) :
    ¬∃ a b c : ℤ, (4 : ℤ) ^ r * (8 * s + 7) = a ^ 2 + b ^ 2 + c ^ 2 := by
  induction r with
  | zero =>
    rintro ⟨a, b, c, h⟩
    have ha := sq_mod_eight a
    have hb := sq_mod_eight b
    have hc := sq_mod_eight c
    norm_num only [pow_zero, one_mul] at h
    omega

  | succ r ih =>
    rintro ⟨a, b, c, h⟩
    have hdiv : (4 : ℤ) ∣ a ^ 2 + b ^ 2 + c ^ 2 := by
      rw [← h, pow_succ]
      exact ⟨4 ^ r * (8 * s + 7), by ring⟩
    obtain ⟨⟨x, hx⟩, ⟨y, hy⟩, ⟨z, hz⟩⟩ := two_dvd_of_four_dvd_three_sq hdiv
    apply ih
    refine ⟨x, y, z, ?_⟩
    rw [hx, hy, hz, pow_succ] at h
    nlinarith only [h]

end ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares
