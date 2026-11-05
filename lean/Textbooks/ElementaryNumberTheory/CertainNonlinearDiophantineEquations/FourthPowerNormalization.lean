import Textbooks.ElementaryNumberTheory.CertainNonlinearDiophantineEquations.Parametrization

namespace ElementaryNumberTheory.CertainNonlinearDiophantineEquations

open DivisibilityTheoryInTheIntegers

/-- Lemma: dividing two fourth-power bases by their gcd divides the square root
by its square, and leaves coprime positive bases. -/
theorem normalize_fourth_powers {x y z ε : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (heq : x ^ 4 + ε * y ^ 4 = z ^ 2) :
    ∃ d a b c : ℤ, 0 < d ∧ 0 < a ∧ 0 < b ∧ 0 < c ∧ IsCoprime a b ∧
      x = d * a ∧ y = d * b ∧ z = d ^ 2 * c ∧ a ^ 4 + ε * b ^ 4 = c ^ 2 := by
  let d : ℤ := DivisibilityTheoryInTheIntegers.gcd x y
  obtain ⟨hd, hdx, hdy, _, _⟩ := gcd_spec x y (Or.inl hx.ne')
  have hdpos : 0 < d := by
    dsimp only [d]
    exact_mod_cast hd
  change d ∣ x at hdx
  change d ∣ y at hdy
  obtain ⟨a, ha⟩ := hdx
  obtain ⟨b, hb⟩ := hdy
  have hapos : 0 < a := by nlinarith
  have hbpos : 0 < b := by nlinarith
  have hdz : d ^ 2 ∣ z := by
    apply (sq_dvd_sq_iff (sq_pos_of_pos hdpos) hz).mp
    refine ⟨a ^ 4 + ε * b ^ 4, ?_⟩
    rw [ha, hb] at heq
    nlinarith [heq]
  obtain ⟨c, hc⟩ := hdz
  have hcpos : 0 < c := by nlinarith [sq_pos_of_pos hdpos]
  have hcop : IsCoprime a b := by
    apply (isCoprime_iff_gcd_eq_one (Or.inl hapos.ne')).mpr
    have hg := gcd_div_gcd_eq_one x y (Or.inl hx.ne')
    change DivisibilityTheoryInTheIntegers.gcd (x / d) (y / d) = 1 at hg
    rwa [ha, hb, Int.mul_ediv_cancel_left _ hdpos.ne',
      Int.mul_ediv_cancel_left _ hdpos.ne'] at hg
  have hnew : a ^ 4 + ε * b ^ 4 = c ^ 2 := by
    apply mul_left_cancel₀ (pow_ne_zero 4 hdpos.ne')
    rw [ha, hb, hc] at heq
    nlinarith [heq]
  exact ⟨d, a, b, c, hdpos, hapos, hbpos, hcpos, hcop, ha, hb, hc, hnew⟩

end ElementaryNumberTheory.CertainNonlinearDiophantineEquations
