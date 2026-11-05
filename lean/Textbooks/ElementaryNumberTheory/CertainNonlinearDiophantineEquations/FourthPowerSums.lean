import Textbooks.ElementaryNumberTheory.CertainNonlinearDiophantineEquations.FourthPowerNormalization

namespace ElementaryNumberTheory.CertainNonlinearDiophantineEquations

/-- Lemma: two primitive parametrizations turn a coprime solution with even first leg
into a solution with a smaller square root. -/
private theorem sum_fourth_descent_even {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (hcop : IsCoprime x y)
    (heq : x ^ 4 + y ^ 4 = z ^ 2) (heven : Even (x ^ 2)) :
    ∃ a b c : ℤ, 0 < a ∧ 0 < b ∧ 0 < c ∧ a ^ 4 + b ^ 4 = c ^ 2 ∧ c < z := by
  have hp : IsPrimitivePythagoreanTriple (x ^ 2) (y ^ 2) z := by
    refine ⟨pythagoreanTriple_iff_sq.mpr (by nlinarith only [heq]), ?_⟩
    exact (isCoprime_iff_gcd_eq_one (Or.inl (pow_ne_zero 2 hx.ne'))).mp hcop.pow
  obtain ⟨s, t, ht, hts, hstcop, _, hxform, hyform, hzform⟩ :=
    exists_parameters_of_primitive (sq_pos_of_pos hx) (sq_pos_of_pos hy) hz hp heven
  have hs : 0 < s := lt_trans ht hts
  have hyodd : Odd y := by
    have hpar := primitive_parity (sq_pos_of_pos hx) hp
    have hy2odd : Odd (y ^ 2) := by
      rcases hpar.1 with hpar | hpar
      · exact hpar.2
      · exact (Int.not_even_iff_odd.mpr hpar.1 heven).elim
    apply Int.odd_iff.mpr
    have hm := Int.odd_iff.mp hy2odd
    rcases Int.emod_two_eq_zero_or_one y with hm' | hm'
    · norm_num [pow_two, Int.mul_emod, hm'] at hm
    · exact hm'
  have hyt : IsCoprime y t := by
    have hsq : IsCoprime (y ^ 2) t := by
      rw [hyform]
      have hbase : IsCoprime (s ^ 2) t := hstcop.pow_left
      convert hbase.add_mul_left_left (-t) using 1
      ring
    exact (IsCoprime.pow_left_iff (by decide : 0 < 2)).mp hsq
  have hp' : IsPrimitivePythagoreanTriple t y s := by
    refine ⟨pythagoreanTriple_iff_sq.mpr (by nlinarith only [hyform]), ?_⟩
    exact (isCoprime_iff_gcd_eq_one (Or.inl ht.ne')).mp hyt.symm
  have hpar' := primitive_parity ht hp'
  have hteven : Even t := by
    rcases hpar'.1 with hpar | hpar
    · exact hpar.1
    · exact (Int.not_even_iff_odd.mpr hyodd hpar.2).elim
  obtain ⟨c, w, hc, hw, hsc, htw⟩ := coprime_factors_of_twice_square
    hs ht hx hstcop hpar'.2 hteven hxform.symm

  obtain ⟨u, v, hv, hvu, huv, _, htform, _, hsform⟩ :=
    exists_parameters_of_primitive ht hy hs hp' hteven
  have hu : 0 < u := lt_trans hv hvu
  have hprod : u * v = w ^ 2 := by nlinarith only [htform, htw]
  obtain ⟨a, b, ha, hb, hua, hvb⟩ :=
    coprime_factors_of_power_int hu hv hw (by decide) huv hprod
  have hnew : a ^ 4 + b ^ 4 = c ^ 2 := by
    rw [hua, hvb] at hsform
    nlinarith only [hsform, hsc]
  have hsmaller : c < z := by
    have hcs : c ≤ s := by
      rw [hsc]
      exact Int.le_self_sq c
    have hsz : s < z := by
      rw [hzform]
      nlinarith only [Int.le_self_sq s, sq_pos_of_pos ht]
    omega
  exact ⟨a, b, c, ha, hb, hc, hnew, hsmaller⟩

/-- Lemma: every positive solution to a sum of fourth powers being a square
would produce another one with a smaller square root. -/
theorem sum_fourth_descent {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (heq : x ^ 4 + y ^ 4 = z ^ 2) :
    ∃ a b c : ℤ, 0 < a ∧ 0 < b ∧ 0 < c ∧ a ^ 4 + b ^ 4 = c ^ 2 ∧ c < z := by
  obtain ⟨d, a, b, c, hd, ha, hb, hc, hab, _, _, hzc, heq'⟩ :=
    normalize_fourth_powers hx hy hz (ε := 1) (by simpa only [one_mul] using heq)
  simp only [one_mul] at heq'
  have hp : IsPrimitivePythagoreanTriple (a ^ 2) (b ^ 2) c := by
    refine ⟨pythagoreanTriple_iff_sq.mpr (by nlinarith only [heq']), ?_⟩
    exact (isCoprime_iff_gcd_eq_one (Or.inl (pow_ne_zero 2 ha.ne'))).mp hab.pow
  have hcle : c ≤ z := by
    rw [hzc]
    nlinarith only [hc, sq_pos_of_pos hd]
  rcases (primitive_parity (sq_pos_of_pos ha) hp).1 with hpar | hpar
  · obtain ⟨u, v, w, hu, hv, hw, heq'', hlt⟩ :=
      sum_fourth_descent_even ha hb hc hab heq' hpar.1
    exact ⟨u, v, w, hu, hv, hw, heq'', lt_of_lt_of_le hlt hcle⟩
  · obtain ⟨u, v, w, hu, hv, hw, heq'', hlt⟩ :=
      sum_fourth_descent_even hb ha hc hab.symm (by omega) hpar.2
    exact ⟨u, v, w, hu, hv, hw, heq'', lt_of_lt_of_le hlt hcle⟩

/-- Theorem: the sum of two positive fourth powers is never a square. -/
theorem sum_fourth_powers_ne_square {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) : x ^ 4 + y ^ 4 ≠ z ^ 2 := by
  have descent (n : ℕ) : ∀ x y z : ℤ, 0 < x → 0 < y → 0 < z → z.toNat = n →
      x ^ 4 + y ^ 4 ≠ z ^ 2 := by
    induction n using Nat.strong_induction_on with
    | h n ih =>
      intro x y z hx hy hz hn heq
      obtain ⟨a, b, c, ha, hb, hc, hnew, hlt⟩ := sum_fourth_descent hx hy hz heq
      have hcn : c.toNat < n := by
        rw [← hn]
        exact (Int.toNat_lt_toNat hz).mpr hlt
      exact ih c.toNat hcn a b c ha hb hc rfl hnew
  exact descent z.toNat x y z hx hy hz rfl

/-- Corollary: Fermat's equation for exponent four has no positive solution. -/
theorem fourth_powers_ne_fourth_power {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) : x ^ 4 + y ^ 4 ≠ z ^ 4 := by
  intro heq
  apply sum_fourth_powers_ne_square hx hy (sq_pos_of_pos hz) (z := z ^ 2)
  nlinarith only [heq]

/-- Corollary: the same impossibility holds for every positive multiple of four. -/
theorem powers_ne_power_of_four_dvd {x y z : ℤ} {n : ℕ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (_hn : 0 < n) (hfour : 4 ∣ n) :
    x ^ n + y ^ n ≠ z ^ n := by
  obtain ⟨k, rfl⟩ := hfour
  intro heq
  apply fourth_powers_ne_fourth_power (pow_pos hx k) (pow_pos hy k) (pow_pos hz k)
  simpa only [← pow_mul, Nat.mul_comm k 4] using heq

end ElementaryNumberTheory.CertainNonlinearDiophantineEquations
