module

public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.Waring
public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.TwoSquareFactorization

public section

namespace ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares

/-- Definition: the least number of nonnegative squares representing n;
for positive n, a minimal representation has no zero summands. -/
noncomputable def squareLength (n : ℕ) : ℕ := by
  classical
  exact Nat.find (show ∃ r, IsSumOfPowers 2 r n from ⟨4, isSumOfPowers_two_four n⟩)

/-- Lemma: the least square length has a representation. -/
theorem squareLength_spec (n : ℕ) : IsSumOfPowers 2 (squareLength n) n := by
  classical
  exact Nat.find_spec (show ∃ r, IsSumOfPowers 2 r n from ⟨4, isSumOfPowers_two_four n⟩)

/-- Lemma: any representation bounds the least square length. -/
theorem squareLength_le {n r : ℕ} (h : IsSumOfPowers 2 r n) : squareLength n ≤ r := by
  classical
  exact Nat.find_min' ⟨4, isSumOfPowers_two_four n⟩ h

/-- Proposition: a positive integer needs between one and four nonzero squares. -/
theorem squareLength_bounds (n : ℕ) (hn : 0 < n) : 1 ≤ squareLength n ∧ squareLength n ≤ 4 := by
  refine ⟨?_, squareLength_le (isSumOfPowers_two_four n)⟩
  by_contra h
  have hz : squareLength n = 0 := by omega
  obtain ⟨a, ha⟩ := hz ▸ squareLength_spec n
  simp only [Finset.univ_eq_empty, Finset.sum_empty] at ha
  omega

/-- Lemma: a one-term square representation is precisely a perfect square. -/
theorem isSumOfPowers_two_one_iff (n : ℕ) : IsSumOfPowers 2 1 n ↔ IsSquare n := by
  constructor
  · rintro ⟨a, ha⟩
    exact ⟨a 0, by simpa only [Fin.sum_univ_one, pow_two] using ha⟩

  · rintro ⟨a, ha⟩
    exact ⟨fun _ => a, by simpa only [Fin.sum_univ_one, pow_two] using ha⟩

/-- Proposition: a positive integer has least square length one exactly when it is a square. -/
theorem squareLength_eq_one_iff (n : ℕ) (hn : 0 < n) : squareLength n = 1 ↔ IsSquare n := by
  constructor
  · intro h
    exact (isSumOfPowers_two_one_iff n).mp (h ▸ squareLength_spec n)

  · intro h
    have hle := squareLength_le ((isSumOfPowers_two_one_iff n).mpr h)
    have hpos := (squareLength_bounds n hn).1
    omega

/-- Lemma: two nonnegative square coordinates are equivalent to two integer square coordinates. -/
theorem isSumOfPowers_two_two_iff (n : ℕ) :
    IsSumOfPowers 2 2 n ↔ ∃ a b : ℤ, (n : ℤ) = a ^ 2 + b ^ 2 := by
  constructor
  · rintro ⟨a, ha⟩
    refine ⟨a 0, a 1, ?_⟩
    simp only [Fin.sum_univ_two] at ha
    exact_mod_cast ha

  · rintro ⟨a, b, hab⟩
    have hnat : n = a.natAbs ^ 2 + b.natAbs ^ 2 := by
      have heq : (n : ℤ) = (a.natAbs : ℤ) ^ 2 + (b.natAbs : ℤ) ^ 2 := by
        simpa only [Int.natCast_natAbs, sq_abs] using hab
      exact_mod_cast heq
    exact ⟨![a.natAbs, b.natAbs], by simpa [Fin.sum_univ_two] using hnat⟩

/-- Proposition: least length two means that n is not a square and its obstructing
prime exponents are all even. -/
theorem squareLength_eq_two_iff (n : ℕ) (hn : 0 < n) :
    squareLength n = 2 ↔ ¬IsSquare n ∧
      ∀ p : ℕ, p.Prime → p % 4 = 3 → Even (NumberTheoreticFunctions.primeExponents n p) := by
  constructor
  · intro h
    refine ⟨?_, (sq_add_sq_iff_even_primeExponents n hn).mp
      ((isSumOfPowers_two_two_iff n).mp (h ▸ squareLength_spec n))⟩
    intro hs
    have := (squareLength_eq_one_iff n hn).mpr hs
    omega

  · rintro ⟨hs, he⟩
    have hle := squareLength_le ((isSumOfPowers_two_two_iff n).mpr
      ((sq_add_sq_iff_even_primeExponents n hn).mpr he))
    have hpos := (squareLength_bounds n hn).1
    have hne : squareLength n ≠ 1 := fun h => hs ((squareLength_eq_one_iff n hn).mp h)
    omega

/-- Proposition: integers excluded by the three-square obstruction need exactly four squares. -/
theorem squareLength_eq_four_of_excluded (r s : ℕ) :
    squareLength (4 ^ r * (8 * s + 7)) = 4 := by
  have hle := squareLength_le (isSumOfPowers_two_four (4 ^ r * (8 * s + 7)))
  by_contra hne
  exact not_isSumOfPowers_two_of_lt_four r s (by omega) (squareLength_spec _)

end ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares
