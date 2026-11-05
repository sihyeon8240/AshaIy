import Textbooks.ElementaryNumberTheory.CertainNonlinearDiophantineEquations.Parametrization
import Textbooks.ElementaryNumberTheory.TheQuadraticReciprocityLaw.LegendreSymbol
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.LinearCombination

namespace ElementaryNumberTheory.CertainNonlinearDiophantineEquations

/-- Theorem: every integer at least three occurs as a leg of a positive Pythagorean triple. -/
theorem exists_triple_with_leg {n : ℤ} (hn : 3 ≤ n) :
    ∃ y z : ℤ, 0 < y ∧ 0 < z ∧ PythagoreanTriple n y z := by
  rcases Int.emod_two_eq_zero_or_one n with hm | hm
  · let k := n / 2
    have hk : 2 * k = n := by dsimp only [k]; omega
    have hkpos : 2 ≤ k := by omega
    refine ⟨k ^ 2 - 1, k ^ 2 + 1, by nlinarith only [hkpos], by positivity, ?_⟩
    apply pythagoreanTriple_iff_sq.mpr
    rw [← hk]
    ring
  · have hsq : n ^ 2 % 2 = 1 := by norm_num [pow_two, Int.mul_emod, hm]
    let y := (n ^ 2 - 1) / 2
    have hy : 2 * y = n ^ 2 - 1 := by dsimp only [y]; omega
    have hypos : 0 < y := by nlinarith only [hy, hn]
    exact ⟨y, y + 1, hypos, by omega,
      pythagoreanTriple_iff_sq.mpr (by nlinarith only [hy])⟩

/-- Theorem: the even leg of a positive primitive triple is divisible by four. -/
theorem four_dvd_even_leg {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z)
    (h : IsPrimitivePythagoreanTriple x y z) (heven : Even x) : (4 : ℤ) ∣ x := by
  obtain ⟨s, t, _, _, _, hpar, hxform, _, _⟩ :=
    exists_parameters_of_primitive hx hy hz h heven
  have he : Even s ∨ Even t := by
    rcases Int.emod_two_eq_zero_or_one s with hs | hs
    · exact Or.inl (Int.even_iff.mpr hs)
    · exact Or.inr (Int.even_iff.mpr (by
        have := Int.emod_two_eq_zero_or_one t
        omega))
  rcases he with ⟨a, ha⟩ | ⟨a, ha⟩
  · refine ⟨a * t, ?_⟩
    rw [hxform, ha]
    ring
  · refine ⟨s * a, ?_⟩
    rw [hxform, ha]
    ring

/-- Lemma: coprime integers have no common positive divisor greater than one. -/
private theorem not_common_divisor {p x y : ℤ} (hp : 1 < p) (h : IsCoprime x y) :
    ¬(p ∣ x ∧ p ∣ y) := by
  rintro ⟨hpx, hpy⟩
  have hu := h.isUnit_of_dvd' hpx hpy
  rcases Int.isUnit_iff.mp hu with heq | heq <;> omega

/-- Theorem: exactly one leg of a positive primitive triple is divisible by three. -/
theorem three_dvd_exactly_one_leg {x y z : ℤ}
    (hx : 0 < x) (h : IsPrimitivePythagoreanTriple x y z) :
    ((3 : ℤ) ∣ x ∧ ¬(3 : ℤ) ∣ y) ∨ ((3 : ℤ) ∣ y ∧ ¬(3 : ℤ) ∣ x) := by
  have finite_check : ∀ a b c : ZMod 3,
      a ^ 2 + b ^ 2 = c ^ 2 → a = 0 ∨ b = 0 := by decide
  have heq := congrArg (fun n : ℤ => (n : ZMod 3)) (pythagoreanTriple_iff_sq.mp h.1)
  simp only [Int.cast_add, Int.cast_pow] at heq
  have hex := finite_check _ _ _ heq
  rw [ZMod.intCast_zmod_eq_zero_iff_dvd, ZMod.intCast_zmod_eq_zero_iff_dvd] at hex
  have hnot := not_common_divisor (by decide : (1 : ℤ) < 3)
    (primitive_pairwise_coprime hx h).1
  rcases hex with hd | hd
  · exact Or.inl ⟨hd, fun hd' => hnot ⟨hd, hd'⟩⟩
  · exact Or.inr ⟨hd, fun hd' => hnot ⟨hd', hd⟩⟩

/-- Theorem: exactly one entry of a positive primitive triple is divisible by five. -/
theorem five_dvd_exactly_one_entry {x y z : ℤ}
    (hx : 0 < x) (h : IsPrimitivePythagoreanTriple x y z) :
    ((5 : ℤ) ∣ x ∧ ¬(5 : ℤ) ∣ y ∧ ¬(5 : ℤ) ∣ z) ∨
      ((5 : ℤ) ∣ y ∧ ¬(5 : ℤ) ∣ x ∧ ¬(5 : ℤ) ∣ z) ∨
      ((5 : ℤ) ∣ z ∧ ¬(5 : ℤ) ∣ x ∧ ¬(5 : ℤ) ∣ y) := by
  have finite_check : ∀ a b c : ZMod 5,
      a ^ 2 + b ^ 2 = c ^ 2 → a = 0 ∨ b = 0 ∨ c = 0 := by decide
  have heq := congrArg (fun n : ℤ => (n : ZMod 5)) (pythagoreanTriple_iff_sq.mp h.1)
  simp only [Int.cast_add, Int.cast_pow] at heq
  have hex := finite_check _ _ _ heq
  simp only [ZMod.intCast_zmod_eq_zero_iff_dvd] at hex
  obtain ⟨hxy, hxz, hyz⟩ := primitive_pairwise_coprime hx h
  have hnotxy := not_common_divisor (by decide : (1 : ℤ) < 5) hxy
  have hnotxz := not_common_divisor (by decide : (1 : ℤ) < 5) hxz
  have hnotyz := not_common_divisor (by decide : (1 : ℤ) < 5) hyz
  rcases hex with hd | hd | hd
  · exact Or.inl ⟨hd, fun hd' => hnotxy ⟨hd, hd'⟩, fun hd' => hnotxz ⟨hd, hd'⟩⟩
  · exact Or.inr (Or.inl ⟨hd, fun hd' => hnotxy ⟨hd', hd⟩,
      fun hd' => hnotyz ⟨hd, hd'⟩⟩)
  · exact Or.inr (Or.inr ⟨hd, fun hd' => hnotxz ⟨hd', hd⟩,
      fun hd' => hnotyz ⟨hd', hd⟩⟩)

/-- Theorem: sixty divides the product of the entries of a positive primitive triple. -/
theorem sixty_dvd_product {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z)
    (h : IsPrimitivePythagoreanTriple x y z) : (60 : ℤ) ∣ x * y * z := by
  have hfour : (4 : ℤ) ∣ x * y * z := by
    rcases (primitive_parity hx h).1 with hp | hp
    · exact dvd_mul_of_dvd_left (dvd_mul_of_dvd_left
        (four_dvd_even_leg hx hy hz h hp.1) y) z
    · have hp' : IsPrimitivePythagoreanTriple y x z := by
        refine ⟨h.1.symm, ?_⟩
        exact (isCoprime_iff_gcd_eq_one (Or.inl hy.ne')).mp
          (primitive_pairwise_coprime hx h).1.symm
      have hd := four_dvd_even_leg hy hx hz hp' hp.2
      exact dvd_mul_of_dvd_left (dvd_mul_of_dvd_right hd x) z
  have hthree : (3 : ℤ) ∣ x * y * z := by
    rcases three_dvd_exactly_one_leg hx h with hp | hp
    · exact dvd_mul_of_dvd_left (dvd_mul_of_dvd_left hp.1 y) z
    · exact dvd_mul_of_dvd_left (dvd_mul_of_dvd_right hp.1 x) z
  have hfive : (5 : ℤ) ∣ x * y * z := by
    rcases five_dvd_exactly_one_entry hx h with hp | hp | hp
    · exact dvd_mul_of_dvd_left (dvd_mul_of_dvd_left hp.1 y) z
    · exact dvd_mul_of_dvd_left (dvd_mul_of_dvd_right hp.1 x) z
    · exact dvd_mul_of_dvd_right hp.1 (x * y)
  have htwelve : (12 : ℤ) ∣ x * y * z :=
    (by decide : IsCoprime (4 : ℤ) 3).mul_dvd hfour hthree
  exact (by decide : IsCoprime (12 : ℤ) 5).mul_dvd htwelve hfive

/-- Theorem: every prime divisor of a positive primitive hypotenuse is one modulo four. -/
theorem prime_dvd_hypotenuse_mod_four {x y z : ℤ} {p : ℕ}
    (hx : 0 < x) (h : IsPrimitivePythagoreanTriple x y z)
    (hp : p.Prime) (hpd : (p : ℤ) ∣ z) : p % 4 = 1 := by
  let : Fact p.Prime := ⟨hp⟩
  have hpgt : (1 : ℤ) < p := by exact_mod_cast hp.one_lt
  have htwo : p ≠ 2 := by
    intro heq
    subst p
    have hzodd := Int.odd_iff.mp (primitive_parity hx h).2
    have hzeven := Int.emod_eq_zero_of_dvd hpd
    omega
  have hyne : (y : ZMod p) ≠ 0 := by
    intro heq
    exact not_common_divisor hpgt (primitive_pairwise_coprime hx h).2.2
      ⟨(ZMod.intCast_zmod_eq_zero_iff_dvd y p).mp heq, hpd⟩
  have hzeq : (z : ZMod p) = 0 := (ZMod.intCast_zmod_eq_zero_iff_dvd z p).mpr hpd
  have heq := congrArg (fun n : ℤ => (n : ZMod p)) (pythagoreanTriple_iff_sq.mp h.1)
  simp only [Int.cast_add, Int.cast_pow, hzeq, zero_pow (by decide : (2 : ℕ) ≠ 0)] at heq
  have hsquare : IsSquare (-1 : ZMod p) := by
    refine ⟨(x : ZMod p) / y, ?_⟩
    field_simp [hyne]
    linear_combination -heq
  apply (TheQuadraticReciprocityLaw.legendreSym_neg_one_eq_one_iff htwo).mp
  apply (TheQuadraticReciprocityLaw.legendreSym_eq_one_iff
    (by simpa only [Int.cast_neg, Int.cast_one] using
      (neg_ne_zero.mpr (one_ne_zero : (1 : ZMod p) ≠ 0)))).mpr
  simpa only [Int.cast_neg, Int.cast_one] using hsquare

/-- Theorem: the inradius of a positive integer right triangle is a positive integer,
characterized by both the semiperimeter and the area formulas. -/
theorem exists_integer_inradius {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (h : PythagoreanTriple x y z) :
    ∃ r : ℤ, 0 < r ∧ 2 * r = x + y - z ∧ r * (x + y + z) = x * y := by
  obtain ⟨d, s, t, hd, ht, hts, _, _, hlegs, hzform, _⟩ :=
    exists_parameters hx hy hz h
  refine ⟨d * t * (s - t), mul_pos (mul_pos hd ht) (sub_pos.mpr hts), ?_, ?_⟩ <;>
    rcases hlegs with ⟨hxform, hyform⟩ | ⟨hyform, hxform⟩ <;>
    rw [hxform, hyform, hzform] <;> ring

/-- Corollary: the inradius of a scaled parametrized triple is d t (s-t). -/
theorem inradius_parameters (d s t : ℤ) :
    (d * (2 * s * t) + d * (s ^ 2 - t ^ 2) - d * (s ^ 2 + t ^ 2)) / 2 =
      d * t * (s - t) := by
  have heq : d * (2 * s * t) + d * (s ^ 2 - t ^ 2) - d * (s ^ 2 + t ^ 2) =
      2 * (d * t * (s - t)) := by ring
  rw [heq, Int.mul_ediv_cancel_left _ (by decide : (2 : ℤ) ≠ 0)]

end ElementaryNumberTheory.CertainNonlinearDiophantineEquations
