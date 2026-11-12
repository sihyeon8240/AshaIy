module

public import Textbooks.ElementaryNumberTheory.CertainNonlinearDiophantineEquations.CoprimePowers
public import Mathlib.NumberTheory.PythagoreanTriples

import Mathlib.Tactic.IntervalCases
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum

public section

namespace ElementaryNumberTheory.CertainNonlinearDiophantineEquations

open DivisibilityTheoryInTheIntegers

/-- Definition: a primitive Pythagorean triple has coprime legs, using the book's gcd. -/
@[expose]
def IsPrimitivePythagoreanTriple (x y z : ℤ) : Prop :=
  PythagoreanTriple x y z ∧ DivisibilityTheoryInTheIntegers.gcd x y = 1

/-- Lemma: the standard Pythagorean predicate is the equation in squares. -/
theorem pythagoreanTriple_iff_sq {x y z : ℤ} :
    PythagoreanTriple x y z ↔ x ^ 2 + y ^ 2 = z ^ 2 := by
  simp only [PythagoreanTriple, pow_two]

/-- Lemma: the DivisibilityTheoryInTheIntegers.gcd of the legs divides a positive hypotenuse. -/
theorem gcd_legs_dvd_hypotenuse {x y z : ℤ} (hx : 0 < x) (hz : 0 < z)
    (h : PythagoreanTriple x y z) : (DivisibilityTheoryInTheIntegers.gcd x y : ℤ) ∣ z := by
  obtain ⟨hd, hdx, hdy, _, _⟩ := gcd_spec x y (Or.inl hx.ne')
  let d : ℤ := DivisibilityTheoryInTheIntegers.gcd x y
  have hdz : 0 < d := by
    dsimp only [d]
    exact_mod_cast hd
  change d ∣ x at hdx
  change d ∣ y at hdy
  apply (sq_dvd_sq_iff hdz hz).mp
  obtain ⟨a, ha⟩ := hdx
  obtain ⟨b, hb⟩ := hdy
  refine ⟨a ^ 2 + b ^ 2, ?_⟩
  have heq := pythagoreanTriple_iff_sq.mp h
  rw [ha, hb] at heq
  nlinarith [heq]

/-- Theorem: for positive triples, coprime legs are equivalent to gcd(x,y,z)=1. -/
theorem primitive_iff_gcd_three_eq_one {x y z : ℤ}
    (hx : 0 < x) (hz : 0 < z) (h : PythagoreanTriple x y z) :
    IsPrimitivePythagoreanTriple x y z ↔
      DivisibilityTheoryInTheIntegers.gcd (DivisibilityTheoryInTheIntegers.gcd x y) z = 1 := by
  obtain ⟨_, hdx, hdy, _, hcommon⟩ := gcd_spec x y (Or.inl hx.ne')
  have hdz := gcd_legs_dvd_hypotenuse hx hz h
  have heq : DivisibilityTheoryInTheIntegers.gcd x y =
      DivisibilityTheoryInTheIntegers.gcd (DivisibilityTheoryInTheIntegers.gcd x y) z := by
    apply gcd_eq_of_common_divisors
    intro c
    constructor
    · rintro ⟨hcx, hcy⟩
      have hcd := hcommon c hcx hcy
      exact ⟨hcd, hcd.trans hdz⟩
    · rintro ⟨hcd, _⟩
      exact ⟨hcd.trans hdx, hcd.trans hdy⟩
  rw [← heq]
  exact ⟨fun hp => hp.2, fun hg => ⟨h, hg⟩⟩

/-- Theorem: a primitive Pythagorean triple is pairwise coprime. -/
theorem primitive_pairwise_coprime {x y z : ℤ} (hx : 0 < x)
    (h : IsPrimitivePythagoreanTriple x y z) :
    IsCoprime x y ∧ IsCoprime x z ∧ IsCoprime y z := by
  have hxy := (isCoprime_iff_gcd_eq_one (Or.inl hx.ne')).mpr h.2
  have heq := pythagoreanTriple_iff_sq.mp h.1
  have hxz : IsCoprime x (z ^ 2) := by
    rw [← heq, pow_two x]
    exact hxy.pow_right.mul_add_left_right x
  have hyz : IsCoprime y (z ^ 2) := by
    rw [← heq, add_comm, pow_two y]
    exact hxy.symm.pow_right.mul_add_left_right y
  exact ⟨hxy, (IsCoprime.pow_right_iff (by decide : 0 < 2)).mp hxz,
    (IsCoprime.pow_right_iff (by decide : 0 < 2)).mp hyz⟩

/-- Theorem: exactly one leg of a positive primitive triple is even, and z is odd. -/
theorem primitive_parity {x y z : ℤ} (hx : 0 < x)
    (h : IsPrimitivePythagoreanTriple x y z) :
    ((Even x ∧ Odd y) ∨ (Odd x ∧ Even y)) ∧ Odd z := by
  have hxy := (primitive_pairwise_coprime hx h).1
  have heq := congrArg (fun n : ℤ => n % 4) (pythagoreanTriple_iff_sq.mp h.1)
  have hnot : ¬(x % 2 = 0 ∧ y % 2 = 0) := by
    rintro ⟨hxe, hye⟩
    obtain ⟨a, b, hab⟩ := hxy
    have hm := congrArg (fun n : ℤ => n % 2) hab
    norm_num [Int.add_emod, Int.mul_emod, hxe, hye] at hm
  have hxb := Int.emod_nonneg x (by decide : (4 : ℤ) ≠ 0)
  have hxu := Int.emod_lt_of_pos x (by decide : (0 : ℤ) < 4)
  have hyb := Int.emod_nonneg y (by decide : (4 : ℤ) ≠ 0)
  have hyu := Int.emod_lt_of_pos y (by decide : (0 : ℤ) < 4)
  have hzb := Int.emod_nonneg z (by decide : (4 : ℤ) ≠ 0)
  have hzu := Int.emod_lt_of_pos z (by decide : (0 : ℤ) < 4)
  have hmodx : x % 2 = (x % 4) % 2 := by omega
  have hmody : y % 2 = (y % 4) % 2 := by omega
  have hmodz : z % 2 = (z % 4) % 2 := by omega
  rw [Int.even_iff, Int.even_iff, Int.odd_iff, Int.odd_iff, Int.odd_iff]
  interval_cases hxm : x % 4 <;> interval_cases hym : y % 4 <;>
    interval_cases hzm : z % 4 <;>
    norm_num [pow_two, Int.add_emod, Int.mul_emod, hxm, hym, hzm] at heq <;> omega

/-- Theorem: every positive triple is a positive multiple of a primitive triple;
the multiplier is the DivisibilityTheoryInTheIntegers.gcd of its three entries. -/
theorem exists_primitive_factor {x y z : ℤ}
    (hx : 0 < x) (hy : 0 < y) (hz : 0 < z) (h : PythagoreanTriple x y z) :
    ∃ d a b c : ℤ, 0 < d ∧ 0 < a ∧ 0 < b ∧ 0 < c ∧
      IsPrimitivePythagoreanTriple a b c ∧ x = d * a ∧ y = d * b ∧ z = d * c ∧
      d = DivisibilityTheoryInTheIntegers.gcd (DivisibilityTheoryInTheIntegers.gcd x y) z := by
  obtain ⟨hd, hdx, hdy, _, _⟩ := gcd_spec x y (Or.inl hx.ne')
  let d : ℤ := DivisibilityTheoryInTheIntegers.gcd x y
  have hdpos : 0 < d := by
    dsimp only [d]
    exact_mod_cast hd
  change d ∣ x at hdx
  change d ∣ y at hdy
  obtain ⟨a, ha⟩ := hdx
  obtain ⟨b, hb⟩ := hdy
  have hdz : d ∣ z := gcd_legs_dvd_hypotenuse hx hz h
  obtain ⟨c, hc⟩ := hdz
  have hapos : 0 < a := by nlinarith
  have hbpos : 0 < b := by nlinarith
  have hcpos : 0 < c := by nlinarith
  have hab : DivisibilityTheoryInTheIntegers.gcd a b = 1 := by
    have hg := gcd_div_gcd_eq_one x y (Or.inl hx.ne')
    change DivisibilityTheoryInTheIntegers.gcd (x / d) (y / d) = 1 at hg
    rw [ha, hb, Int.mul_ediv_cancel_left _ hdpos.ne',
      Int.mul_ediv_cancel_left _ hdpos.ne'] at hg
    exact hg
  have heq := pythagoreanTriple_iff_sq.mp h
  rw [ha, hb, hc] at heq
  have hp : PythagoreanTriple a b c := by
    apply pythagoreanTriple_iff_sq.mpr
    apply mul_left_cancel₀ (pow_ne_zero 2 hdpos.ne')
    nlinarith [heq]
  have hg : DivisibilityTheoryInTheIntegers.gcd (DivisibilityTheoryInTheIntegers.gcd x y) z =
      DivisibilityTheoryInTheIntegers.gcd x y := by
    apply gcd_eq_of_common_divisors
    intro e
    constructor
    · rintro ⟨hed, _⟩
      exact ⟨hed.trans ⟨a, ha⟩, hed.trans ⟨b, hb⟩⟩
    · rintro ⟨hex, hey⟩
      have hed := (gcd_spec x y (Or.inl hx.ne')).2.2.2.2 e hex hey
      exact ⟨hed, hed.trans ⟨c, hc⟩⟩
  exact ⟨d, a, b, c, hdpos, hapos, hbpos, hcpos, ⟨hp, hab⟩, ha, hb, hc,
    by
      change (DivisibilityTheoryInTheIntegers.gcd x y : ℤ) = _
      exact_mod_cast hg.symm⟩

end ElementaryNumberTheory.CertainNonlinearDiophantineEquations
