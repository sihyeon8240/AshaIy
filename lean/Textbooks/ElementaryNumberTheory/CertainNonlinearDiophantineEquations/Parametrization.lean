import Textbooks.ElementaryNumberTheory.CertainNonlinearDiophantineEquations.PythagoreanTriples

namespace ElementaryNumberTheory.CertainNonlinearDiophantineEquations

/-- Theorem: a positive primitive triple with its even leg first has Euclid's parameters. -/
theorem exists_parameters_of_primitive {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z)
    (h : IsPrimitivePythagoreanTriple x y z) (hxeven : Even x) :
    ∃ s t : ℤ, 0 < t ∧ t < s ∧ IsCoprime s t ∧ s % 2 ≠ t % 2 ∧
      x = 2 * s * t ∧ y = s ^ 2 - t ^ 2 ∧ z = s ^ 2 + t ^ 2 := by
  have heq := pythagoreanTriple_iff_sq.mp h.1
  have hpar := primitive_parity hx h
  have hxm := Int.even_iff.mp hxeven
  have hym : y % 2 = 1 := by
    rcases hpar.1 with hp | hp
    · exact Int.odd_iff.mp hp.2
    · have := Int.odd_iff.mp hp.1
      omega
  have hzm := Int.odd_iff.mp hpar.2
  have hyz : y < z := by nlinarith [sq_pos_of_pos hx]
  let u := (z - y) / 2
  let v := (z + y) / 2
  have hu : 2 * u = z - y := by dsimp only [u]; omega
  have hv : 2 * v = z + y := by dsimp only [v]; omega
  have hupos : 0 < u := by omega
  have hvpos : 0 < v := by omega
  have hhalf : 2 * (x / 2) = x := by omega
  have hhalfpos : 0 < x / 2 := by omega
  have huv : u * v = (x / 2) ^ 2 := by nlinarith [heq]
  have hcop : IsCoprime u v := by
    obtain ⟨a, b, hab⟩ := (primitive_pairwise_coprime hx h).2.2
    refine ⟨b - a, a + b, ?_⟩
    have hys : y = v - u := by omega
    have hzs : z = u + v := by omega
    rw [hys, hzs] at hab
    nlinarith only [hab]

  obtain ⟨t, s, ht, hs, hut, hvs⟩ :=
    coprime_factors_of_power_int hupos hvpos hhalfpos (by decide) hcop huv
  have hst : t < s := by nlinarith
  have hstcop : IsCoprime s t := by
    rw [hut, hvs] at hcop
    exact ((IsCoprime.pow_left_iff (by decide : 0 < 2)).mp
      ((IsCoprime.pow_right_iff (by decide : 0 < 2)).mp hcop)).symm
  have hyform : y = s ^ 2 - t ^ 2 := by omega
  have hzform : z = s ^ 2 + t ^ 2 := by omega
  have hxform : x = 2 * s * t := by
    apply (sq_eq_sq₀ hx.le (by positivity)).mp
    rw [hyform, hzform] at heq
    nlinarith only [heq]
  have hparity : s % 2 ≠ t % 2 := by
    intro hsame
    have hm := congrArg (fun n : ℤ => n % 2) hyform
    norm_num [pow_two, Int.sub_emod, Int.mul_emod, hsame, hym] at hm
  exact ⟨s, t, ht, hst, hstcop, hparity, hxform, hyform, hzform⟩

/-- Theorem: coprime positive parameters of opposite parity give a positive primitive triple. -/
theorem primitive_of_parameters {s t : ℤ} (ht : 0 < t) (hst : t < s)
    (hcop : IsCoprime s t) (hpar : s % 2 ≠ t % 2) :
    0 < 2 * s * t ∧ 0 < s ^ 2 - t ^ 2 ∧ 0 < s ^ 2 + t ^ 2 ∧
      IsPrimitivePythagoreanTriple (2 * s * t) (s ^ 2 - t ^ 2) (s ^ 2 + t ^ 2) := by
  have hs : 0 < s := lt_trans ht hst
  have hx : 0 < 2 * s * t := by positivity
  have hy : 0 < s ^ 2 - t ^ 2 := by nlinarith
  have hz : 0 < s ^ 2 + t ^ 2 := by positivity
  have hodd : (s ^ 2 - t ^ 2) % 2 = 1 := by
    have hsmod := Int.emod_two_eq_zero_or_one s
    have htmod := Int.emod_two_eq_zero_or_one t
    rcases hsmod with hm | hm <;> rcases htmod with hn | hn <;>
      norm_num [pow_two, Int.sub_emod, Int.mul_emod, hm, hn] <;> omega
  have htwo : IsCoprime (2 : ℤ) (s ^ 2 - t ^ 2) := by
    refine ⟨-((s ^ 2 - t ^ 2) / 2), 1, ?_⟩
    omega
  have hsy : IsCoprime s (s ^ 2 - t ^ 2) := by
    have hbase : IsCoprime s (-(t ^ 2)) := hcop.pow_right.neg_right
    convert hbase.mul_add_left_right s using 1
    ring
  have hty : IsCoprime t (s ^ 2 - t ^ 2) := by
    have hbase : IsCoprime t (s ^ 2) := hcop.symm.pow_right
    convert hbase.add_mul_left_right (-t) using 1
    ring
  have hxy := (htwo.mul_left hsy).mul_left hty
  refine ⟨hx, hy, hz, pythagoreanTriple_iff_sq.mpr (by ring), ?_⟩
  exact (isCoprime_iff_gcd_eq_one (Or.inl hx.ne')).mp hxy

/-- Theorem: Euclid's parametrization characterizes positive primitive triples
whose first leg is even. -/
theorem primitive_iff_parameters {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) :
    IsPrimitivePythagoreanTriple x y z ∧ Even x ↔
      ∃ s t : ℤ, 0 < t ∧ t < s ∧ IsCoprime s t ∧ s % 2 ≠ t % 2 ∧
        x = 2 * s * t ∧ y = s ^ 2 - t ^ 2 ∧ z = s ^ 2 + t ^ 2 := by
  constructor
  · rintro ⟨h, he⟩
    exact exists_parameters_of_primitive hx hy hz h he
  · rintro ⟨s, t, ht, hst, hcop, hpar, rfl, rfl, rfl⟩
    exact ⟨(primitive_of_parameters ht hst hcop hpar).2.2.2,
      ⟨s * t, by ring⟩⟩

/-- Corollary: ordered positive parameters are uniquely recovered from the odd leg
and the hypotenuse. -/
theorem parameters_unique {s t u v y z : ℤ}
    (hs : 0 < s) (ht : 0 < t) (hu : 0 < u) (hv : 0 < v)
    (hy : y = s ^ 2 - t ^ 2) (hz : z = s ^ 2 + t ^ 2)
    (hy' : y = u ^ 2 - v ^ 2) (hz' : z = u ^ 2 + v ^ 2) :
    s = u ∧ t = v := by
  constructor
  · apply (sq_eq_sq₀ hs.le hu.le).mp
    omega
  · apply (sq_eq_sq₀ ht.le hv.le).mp
    omega

/-- Corollary: all positive triples arise by scaling Euclid's primitive triples,
up to interchanging the legs. -/
theorem exists_parameters {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (h : PythagoreanTriple x y z) :
    ∃ d s t : ℤ, 0 < d ∧ 0 < t ∧ t < s ∧ IsCoprime s t ∧ s % 2 ≠ t % 2 ∧
      ((x = d * (2 * s * t) ∧ y = d * (s ^ 2 - t ^ 2)) ∨
        (y = d * (2 * s * t) ∧ x = d * (s ^ 2 - t ^ 2))) ∧
      z = d * (s ^ 2 + t ^ 2) ∧ d = DivisibilityTheoryInTheIntegers.gcd
        (DivisibilityTheoryInTheIntegers.gcd x y) z := by
  obtain ⟨d, a, b, c, hd, ha, hb, hc, hp, hxa, hyb, hzc, hgd⟩ :=
    exists_primitive_factor hx hy hz h
  rcases (primitive_parity ha hp).1 with hpar | hpar
  · obtain ⟨s, t, ht, hst, hcop, hpar, has, hbs, hcs⟩ :=
      exists_parameters_of_primitive ha hb hc hp hpar.1
    exact ⟨d, s, t, hd, ht, hst, hcop, hpar,
      Or.inl ⟨by rwa [← has], by rwa [← hbs]⟩, by rwa [← hcs], hgd⟩
  · have hp' : IsPrimitivePythagoreanTriple b a c := by
      refine ⟨hp.1.symm, ?_⟩
      exact (isCoprime_iff_gcd_eq_one (Or.inl hb.ne')).mp
        ((primitive_pairwise_coprime ha hp).1.symm)
    obtain ⟨s, t, ht, hst, hcop, hpar, hbs, has, hcs⟩ :=
      exists_parameters_of_primitive hb ha hc hp' hpar.2
    exact ⟨d, s, t, hd, ht, hst, hcop, hpar,
      Or.inr ⟨by rwa [← hbs], by rwa [← has]⟩, by rwa [← hcs], hgd⟩

end ElementaryNumberTheory.CertainNonlinearDiophantineEquations
