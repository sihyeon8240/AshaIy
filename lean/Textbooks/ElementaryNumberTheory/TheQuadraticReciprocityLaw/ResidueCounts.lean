import Textbooks.ElementaryNumberTheory.TheQuadraticReciprocityLaw.LegendreSymbol

namespace ElementaryNumberTheory.TheQuadraticReciprocityLaw

open PrimitiveRootsAndIndices
open scoped BigOperators

variable {p : ℕ} [Fact p.Prime]

/-- Lemma: multiplication of residue classes induces multiplication of their symbols. -/
theorem legendreSym_val_mul (hp : p ≠ 2) (a b : ZMod p) :
    legendreSym p (a * b).val = legendreSym p a.val * legendreSym p b.val := by
  have hc : ((a * b).val : ℤ) ≡ (a.val : ℤ) * b.val [ZMOD (p : ℤ)] := by
    apply (ZMod.intCast_eq_intCast_iff _ _ p).mp
    simp only [Int.cast_natCast, Int.cast_mul, ZMod.natCast_zmod_val]
  rw [legendreSym_congr hc, legendreSym_mul hp]

/-- Theorem: a primitive root modulo an odd prime is a quadratic nonresidue. -/
theorem legendreSym_primitiveRoot (hp : p ≠ 2) (r : (ZMod p)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient p)) : legendreSym p (r : ZMod p).val = -1 := by
  have ha : (((r : ZMod p).val : ℤ) : ZMod p) ≠ 0 := by
    simpa only [Int.cast_natCast, ZMod.natCast_zmod_val] using Units.ne_zero r
  have hor : orderOf r = 2 * (p / 2) := by
    rw [orderOf_eq_of_primitiveRoot hr, EulersGeneralizationOfFermatsTheorem.totient_prime p
      (isPrime_of_prime p Fact.out)]
    have := Nat.odd_iff.mp ((Fact.out : p.Prime).odd_of_ne_two hp)
    omega
  have hh := half_order_eq_neg_one p r (p / 2) hor
  apply sign_eq_of_cast_eq hp (legendreSym_eq_one_or_neg_one ha) (Or.inr rfl)
  rw [legendreSym_eq_pow hp, Int.cast_natCast, ZMod.natCast_zmod_val,
    Int.cast_neg, Int.cast_one]
  exact hh

/-- Corollary: even powers of a primitive root are residues and odd powers are nonresidues. -/
theorem legendreSym_pow_primitiveRoot (hp : p ≠ 2) (r : (ZMod p)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient p)) (n : ℕ) :
    legendreSym p ((r : ZMod p) ^ n).val = (-1 : ℤ) ^ n := by
  induction n with
  | zero => simpa only [pow_zero, ZMod.val_one, Nat.cast_one] using (legendreSym_one (p := p))
  | succ n ih =>
    rw [pow_succ, legendreSym_val_mul hp, ih, legendreSym_primitiveRoot hp r hr, pow_succ]

/-- Theorem: the Legendre symbols of the nonzero residue classes sum to zero. -/
theorem sum_legendreSym_units (hp : p ≠ 2) :
    (∑ a : (ZMod p)ˣ, legendreSym p (a : ZMod p).val) = 0 := by
  obtain ⟨r, hr⟩ := exists_primitiveRoot_prime p Fact.out
  have hterm (a : (ZMod p)ˣ) : legendreSym p ((r * a : (ZMod p)ˣ) : ZMod p).val =
      -legendreSym p (a : ZMod p).val := by
    rw [Units.val_mul, legendreSym_val_mul hp, legendreSym_primitiveRoot hp r hr, neg_one_mul]
  have hs := Equiv.sum_comp (Equiv.mulLeft r)
    (fun a : (ZMod p)ˣ => legendreSym p (a : ZMod p).val)
  change (∑ a : (ZMod p)ˣ, legendreSym p ((r * a : (ZMod p)ˣ) : ZMod p).val) =
    ∑ a : (ZMod p)ˣ, legendreSym p (a : ZMod p).val at hs
  simp only [hterm, Finset.sum_neg_distrib] at hs
  omega

/-- Lemma: a square root of a unit is itself a unit. -/
private theorem unit_square_iff (a : (ZMod p)ˣ) :
    IsSquare (a : ZMod p) ↔ ∃ x : (ZMod p)ˣ, x ^ 2 = a := by
  constructor
  · rintro ⟨x, hx⟩
    have hne : x ≠ 0 := by
      intro h
      rw [h, mul_zero] at hx
      exact Units.ne_zero a hx
    exact ⟨Units.mk0 x hne, Units.ext (by simpa only [Units.val_pow_eq_pow_val,
      Units.val_mk0, pow_two, Units.val_mul] using hx.symm)⟩

  · rintro ⟨x, hx⟩
    refine ⟨(x : ZMod p), ?_⟩
    have h := congrArg (fun u : (ZMod p)ˣ => (u : ZMod p)) hx
    simpa only [Units.val_pow_eq_pow_val, pow_two, Units.val_mul] using h.symm

/-- Theorem: exactly half of the nonzero classes have Legendre symbol one. -/
theorem card_quadratic_residues (hp : p ≠ 2) :
    Fintype.card {a : (ZMod p)ˣ // legendreSym p (a : ZMod p).val = 1} = p / 2 := by
  have he (a : (ZMod p)ˣ) : legendreSym p (a : ZMod p).val = 1 ↔
      ∃ x : (ZMod p)ˣ, x ^ 2 = a := by
    have ha : (((a : ZMod p).val : ℤ) : ZMod p) ≠ 0 := by
      simpa only [Int.cast_natCast, ZMod.natCast_zmod_val] using Units.ne_zero a
    rw [legendreSym_eq_one_iff ha, Int.cast_natCast, ZMod.natCast_zmod_val]
    exact unit_square_iff a
  rw [Fintype.card_congr (Equiv.subtypeEquivRight he),
    card_square_residues p ((Fact.out : p.Prime).odd_of_ne_two hp), half_prime hp]

/-- Theorem: exactly half of the nonzero classes have Legendre symbol minus one. -/
theorem card_quadratic_nonresidues (hp : p ≠ 2) :
    Fintype.card {a : (ZMod p)ˣ // legendreSym p (a : ZMod p).val = -1} = p / 2 := by
  have he (a : (ZMod p)ˣ) : legendreSym p (a : ZMod p).val = -1 ↔
      ¬legendreSym p (a : ZMod p).val = 1 := by
    have ha : (((a : ZMod p).val : ℤ) : ZMod p) ≠ 0 := by
      simpa only [Int.cast_natCast, ZMod.natCast_zmod_val] using Units.ne_zero a
    have hd := legendreSym_eq_one_or_neg_one ha
    omega
  rw [Fintype.card_congr (Equiv.subtypeEquivRight he), Fintype.card_subtype_compl,
    card_quadratic_residues hp, ZMod.card_units_eq_totient,
    EulersGeneralizationOfFermatsTheorem.totient_prime p (isPrime_of_prime p Fact.out)]
  have := Nat.odd_iff.mp ((Fact.out : p.Prime).odd_of_ne_two hp)
  omega

end ElementaryNumberTheory.TheQuadraticReciprocityLaw
