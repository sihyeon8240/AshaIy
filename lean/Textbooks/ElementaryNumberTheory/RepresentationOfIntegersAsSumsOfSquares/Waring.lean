module

public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.FourSquares
public import Mathlib.Algebra.BigOperators.Fin
public import Mathlib.LinearAlgebra.QuadraticForm.Basic

public section

namespace ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares

/-- Definition: a representation by exactly r nonnegative kth powers;
zero summands allow fewer than r nonzero terms when k is positive. -/
@[expose]
def IsSumOfPowers (k r n : ℕ) : Prop :=
  ∃ a : Fin r → ℕ, n = ∑ i, a i ^ k

/-- Definition: r is a uniform bound for representing positive integers by kth powers. -/
@[expose]
def IsWaringBound (k r : ℕ) : Prop :=
  ∀ n : ℕ, 0 < n → IsSumOfPowers k r n

/-- Definition: r suffices for all sufficiently large positive integers. -/
@[expose]
def IsAsymptoticWaringBound (k r : ℕ) : Prop :=
  ∃ N : ℕ, ∀ n : ℕ, N ≤ n → 0 < n → IsSumOfPowers k r n

/-- Definition: g(k) is the least uniform bound, with existence supplied explicitly. -/
noncomputable def waringNumber (k : ℕ) (h : ∃ r, IsWaringBound k r) : ℕ := by
  classical
  exact Nat.find h

/-- Lemma: g(k) is a uniform bound whenever such a bound exists. -/
theorem waringNumber_spec (k : ℕ) (h : ∃ r, IsWaringBound k r) :
    IsWaringBound k (waringNumber k h) := by
  classical
  exact Nat.find_spec h

/-- Lemma: g(k) is no larger than any uniform bound. -/
theorem waringNumber_le {k r : ℕ} (h : ∃ s, IsWaringBound k s) (hr : IsWaringBound k r) :
    waringNumber k h ≤ r := by
  classical
  exact Nat.find_min' h hr

/-- Definition: G(k) is the least eventual bound, with existence supplied explicitly. -/
noncomputable def asymptoticWaringNumber (k : ℕ)
    (h : ∃ r, IsAsymptoticWaringBound k r) : ℕ := by
  classical
  exact Nat.find h

/-- Lemma: G(k) is an eventual bound whenever such a bound exists. -/
theorem asymptoticWaringNumber_spec (k : ℕ) (h : ∃ r, IsAsymptoticWaringBound k r) :
    IsAsymptoticWaringBound k (asymptoticWaringNumber k h) := by
  classical
  exact Nat.find_spec h

/-- Lemma: G(k) is no larger than any eventual bound. -/
theorem asymptoticWaringNumber_le_bound {k r : ℕ}
    (h : ∃ s, IsAsymptoticWaringBound k s) (hr : IsAsymptoticWaringBound k r) :
    asymptoticWaringNumber k h ≤ r := by
  classical
  exact Nat.find_min' h hr

/-- Lemma: the four-square theorem gives a four-term nonnegative power representation. -/
theorem isSumOfPowers_two_four (n : ℕ) : IsSumOfPowers 2 4 n := by
  obtain ⟨a, b, c, d, h⟩ := four_sq_nat n
  refine ⟨![a, b, c, d], ?_⟩
  simpa [Fin.sum_univ_four] using h

/-- Lemma: an excluded three-square integer has no representation with at most three terms. -/
theorem not_isSumOfPowers_two_of_lt_four (r s : ℕ) {t : ℕ} (ht : t < 4) :
    ¬IsSumOfPowers 2 t (4 ^ r * (8 * s + 7)) := by
  rintro ⟨a, ha⟩
  apply not_three_sq r s
  interval_cases t
  · refine ⟨0, 0, 0, ?_⟩
    simp only [Finset.univ_eq_empty, Finset.sum_empty] at ha
    norm_num only [zero_pow two_ne_zero, add_zero]
    exact_mod_cast ha

  · refine ⟨a 0, 0, 0, ?_⟩
    simp only [Fin.sum_univ_one] at ha
    norm_num only [zero_pow two_ne_zero, add_zero]
    exact_mod_cast ha

  · refine ⟨a 0, a 1, 0, ?_⟩
    simp only [Fin.sum_univ_two] at ha
    norm_num only [zero_pow two_ne_zero, add_zero]
    exact_mod_cast ha

  · refine ⟨a 0, a 1, a 2, ?_⟩
    simp only [Fin.sum_univ_three] at ha
    exact_mod_cast ha

/-- Proposition: a uniform Waring bound is also an eventual bound. -/
theorem isAsymptoticWaringBound_of_isWaringBound {k r : ℕ} (h : IsWaringBound k r) :
    IsAsymptoticWaringBound k r := by
  exact ⟨1, fun n _ hn => h n hn⟩

/-- Theorem: whenever g(k) exists, G(k) exists and is at most g(k). -/
theorem asymptoticWaringNumber_le (k : ℕ) (h : ∃ r, IsWaringBound k r) :
    ∃ hG : ∃ r, IsAsymptoticWaringBound k r,
      asymptoticWaringNumber k hG ≤ waringNumber k h := by
  have hg := isAsymptoticWaringBound_of_isWaringBound (waringNumber_spec k h)
  have hG : ∃ r, IsAsymptoticWaringBound k r := ⟨waringNumber k h, hg⟩
  exact ⟨hG, asymptoticWaringNumber_le_bound hG hg⟩

/-- Lemma: four is a uniform Waring bound for squares. -/
theorem exists_waringBound_two : ∃ r, IsWaringBound 2 r := by
  exact ⟨4, fun n _ => isSumOfPowers_two_four n⟩

/-- Theorem: four squares are necessary and sufficient as a uniform bound, so g(2)=4. -/
theorem waringNumber_two (h : ∃ r, IsWaringBound 2 r) : waringNumber 2 h = 4 := by
  apply Nat.le_antisymm
  · exact waringNumber_le h (fun n _ => isSumOfPowers_two_four n)

  · by_contra hlt
    have hg := waringNumber_spec 2 h 7 (by decide)
    exact not_isSumOfPowers_two_of_lt_four 0 0 (t := waringNumber 2 h) (by omega)
      (by simpa only [pow_zero, one_mul, mul_zero, zero_add] using hg)

/-- Lemma: four is an eventual Waring bound for squares. -/
theorem exists_asymptoticWaringBound_two : ∃ r, IsAsymptoticWaringBound 2 r := by
  exact ⟨4, isAsymptoticWaringBound_of_isWaringBound (fun n _ => isSumOfPowers_two_four n)⟩

/-- Theorem: arbitrarily large integers seven modulo eight require four squares, so G(2)=4. -/
theorem asymptoticWaringNumber_two (h : ∃ r, IsAsymptoticWaringBound 2 r) :
    asymptoticWaringNumber 2 h = 4 := by
  apply Nat.le_antisymm
  · exact asymptoticWaringNumber_le_bound h
      (isAsymptoticWaringBound_of_isWaringBound (fun n _ => isSumOfPowers_two_four n))

  · by_contra hlt
    obtain ⟨N, hN⟩ := asymptoticWaringNumber_spec 2 h
    have hg := hN (8 * N + 7) (by omega) (by omega)
    exact not_isSumOfPowers_two_of_lt_four 0 N (t := asymptoticWaringNumber 2 h) (by omega)
      (by simpa only [pow_zero, one_mul] using hg)

/-- Definition: an integral quadratic form is universal when it represents every positive integer. -/
@[expose]
def IsUniversal {r : ℕ} (Q : QuadraticForm ℤ (Fin r → ℤ)) : Prop :=
  ∀ n : ℕ, 0 < n → ∃ x : Fin r → ℤ, Q x = n

/-- Corollary: the form x₁²+x₂²+x₃²+x₄² is universal. -/
theorem four_square_form_universal :
    IsUniversal (QuadraticMap.weightedSumSquares ℤ (fun _ : Fin 4 => (1 : ℤ))) := by
  intro n hn
  obtain ⟨a, b, c, d, h⟩ := four_sq n hn
  refine ⟨![a, b, c, d], ?_⟩
  simpa [QuadraticMap.weightedSumSquares_apply, Fin.sum_univ_four, pow_two] using h.symm

end ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares
