import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.PowerCongruences
import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.Classification

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

open scoped Classical
open EulersGeneralizationOfFermatsTheorem

/-- Theorem: a positive power congruent to one forces the base to be coprime to the modulus. -/
theorem gcd_eq_one_of_pow_modEq_one (n a : ℤ) (h : ℕ) (hh : 0 < h)
    (ha : a ^ h ≡ 1 [ZMOD n]) : DivisibilityTheoryInTheIntegers.gcd a n = 1 := by
  have hinv : a * a ^ (h - 1) ≡ 1 [ZMOD n] := by
    rw [← pow_succ', Nat.sub_add_cancel hh]
    exact ha
  have hd := (TheTheoryOfCongruences.exists_linear_modEq_iff n a 1).mp ⟨a ^ (h - 1), hinv⟩
  exact Nat.eq_one_of_dvd_one (Int.natCast_dvd_natCast.mp hd)

/-- Lemma: an odd integer's square is one modulo eight. -/
theorem odd_square_modEq_one (a : ℤ) (ha : Odd a) : a ^ 2 ≡ 1 [ZMOD 8] := by
  obtain ⟨t, ht⟩ := ha
  apply (TheTheoryOfCongruences.modEq_iff_dvd_sub _ _ _).mpr
  rcases Int.even_or_odd t with ⟨s, hs⟩ | ⟨s, hs⟩
  · refine ⟨s * (2 * s + 1), ?_⟩
    rw [ht, hs]
    ring

  · refine ⟨(2 * s + 1) * (s + 1), ?_⟩
    rw [ht, hs]
    ring

/-- Theorem: every odd integer has a period 2^(k-2) modulo 2^k for k at least three. -/
theorem odd_pow_two_pow_modEq_one (a : ℤ) (ha : Odd a) (j : ℕ) :
    a ^ (2 ^ (j + 1)) ≡ 1 [ZMOD ((2 : ℤ) ^ (j + 3))] := by
  induction j with
  | zero => exact odd_square_modEq_one a ha
  | succ j ih =>
    obtain ⟨t, ht⟩ := (TheTheoryOfCongruences.modEq_iff_dvd_sub _ _ _).mp ih
    have he : a ^ (2 ^ (j + 1)) = 1 + (2 : ℤ) ^ (j + 3) * t := by linarith
    apply (TheTheoryOfCongruences.modEq_iff_dvd_sub _ _ _).mpr
    refine ⟨t + (2 : ℤ) ^ (j + 2) * t ^ 2, ?_⟩
    rw [pow_succ (2 : ℕ) (j + 1), pow_mul, he]
    simp only [pow_succ]
    ring

/-- Lemma: an element of even order reaches minus one halfway through its period. -/
theorem half_order_eq_neg_one (p : ℕ) [Fact p.Prime] (a : (ZMod p)ˣ)
    (k : ℕ) (hk : orderOf a = 2 * k) : (a : ZMod p) ^ k = -1 := by
  have hkpos : 0 < k := by
    have := unit_orderOf_pos p a
    omega
  have hs : (a ^ k) ^ 2 = 1 := by
    rw [← pow_mul, mul_comm k, ← hk, pow_orderOf_eq_one]
  have hne : a ^ k ≠ 1 := by
    intro h
    have hd := (pow_eq_one_iff_dvd_order a k).mp h
    have hle := Nat.le_of_dvd hkpos hd
    omega
  have hval : (a : ZMod p) ^ k ≠ 1 := by
    intro h
    exact hne (Units.ext h)

  have hsval := congrArg (fun u : (ZMod p)ˣ => (u : ZMod p)) hs
  simp only [Units.val_pow_eq_pow_val, Units.val_one] at hsval
  have hprod : ((a : ZMod p) ^ k - 1) * ((a : ZMod p) ^ k + 1) = 0 := by
    calc
      _ = ((a : ZMod p) ^ k) ^ 2 - 1 := by ring
      _ = 0 := by rw [hsval, sub_self]
  have he := (mul_eq_zero.mp hprod).resolve_left (sub_ne_zero.mpr hval)
  exact eq_neg_of_add_eq_zero_left he

/-- Corollary: the product of two primitive roots at an odd prime is not primitive. -/
theorem not_primitiveRoot_mul_prime (p : ℕ) [Fact p.Prime] (hpodd : Odd p)
    (r s : (ZMod p)ˣ) (hr : IsPrimitiveRoot r (Nat.totient p))
    (hs : IsPrimitiveRoot s (Nat.totient p)) :
    ¬IsPrimitiveRoot (r * s) (Nat.totient p) := by
  have hp : p.Prime := Fact.out
  have hpgt : 2 < p := by
    have := hp.two_le
    have := Nat.odd_iff.mp hpodd
    omega
  obtain ⟨k, hk⟩ := totient_even p hpgt
  have hm : Nat.totient p = 2 * k := by omega
  have hkpos : 0 < k := by
    have := Nat.totient_pos.mpr hp.pos
    omega
  have hrhalf := half_order_eq_neg_one p r k ((orderOf_eq_of_primitiveRoot hr).trans hm)
  have hshalf := half_order_eq_neg_one p s k ((orderOf_eq_of_primitiveRoot hs).trans hm)
  have hhalf : (r * s) ^ k = 1 := by
    apply Units.ext
    simp only [Units.val_pow_eq_pow_val, Units.val_mul, Units.val_one, mul_pow,
      hrhalf, hshalf, neg_one_mul, neg_neg]

  intro h
  have hd := h.dvd_of_pow_eq_one k hhalf
  have hle := Nat.le_of_dvd hkpos hd
  omega

/-- Corollary: at an odd prime, a nonzero class is a square precisely when its index is even. -/
theorem exists_square_iff_even_index (p : ℕ) [Fact p.Prime] (hpodd : Odd p)
    (r : (ZMod p)ˣ) (hr : IsPrimitiveRoot r (Nat.totient p)) (a : (ZMod p)ˣ) :
    (∃ x : (ZMod p)ˣ, x ^ 2 = a) ↔ Even (index p r hr a) := by
  have hpgt : 2 < p := by
    have := (Fact.out : p.Prime).two_le
    have := Nat.odd_iff.mp hpodd
    omega
  have heven := totient_even p hpgt
  rw [exists_pow_eq_iff_dvd_index p r hr, Nat.gcd_eq_left (even_iff_two_dvd.mp heven),
    ← even_iff_two_dvd]

/-- Corollary: a solvable nonzero quadratic equation at an odd prime has exactly two roots. -/
theorem card_square_solutions (p : ℕ) [Fact p.Prime] (hpodd : Odd p)
    (a x₀ : (ZMod p)ˣ) (h₀ : x₀ ^ 2 = a) :
    Fintype.card {x : (ZMod p)ˣ // x ^ 2 = a} = 2 := by
  have heven : Even (p - 1) := by
    have := Nat.odd_iff.mp hpodd
    exact Nat.even_iff.mpr (by omega)
  rw [card_pow_solutions_prime p a x₀ 2 h₀, Nat.gcd_eq_left (even_iff_two_dvd.mp heven)]

/-- Theorem: exactly (p-1)/2 nonzero classes at an odd prime are quadratic residues. -/
theorem card_square_residues (p : ℕ) [Fact p.Prime] (hpodd : Odd p) :
    Fintype.card {a : (ZMod p)ˣ // ∃ x : (ZMod p)ˣ, x ^ 2 = a} = (p - 1) / 2 := by
  obtain ⟨r, hr⟩ := exists_primitiveRoot_prime p Fact.out
  let s := r ^ 2
  have hspos := unit_orderOf_pos p s
  let f : Fin (orderOf s) → {a : (ZMod p)ˣ // ∃ x : (ZMod p)ˣ, x ^ 2 = a} :=
    fun i => ⟨s ^ i.val, ⟨r ^ i.val, pow_right_comm r i.val 2⟩⟩
  have hinj : Function.Injective f := by
    intro i j hij
    exact pow_injective_fin s hspos (congrArg Subtype.val hij)
  have hsurj : Function.Surjective f := by
    intro a
    obtain ⟨x, hx⟩ := a.property
    obtain ⟨i, hi, _⟩ := exists_unique_pow p r hr x
    refine ⟨⟨i.val % orderOf s, Nat.mod_lt _ hspos⟩, ?_⟩
    apply Subtype.ext
    have hmod := (pow_eq_pow_iff_modEq s hspos _ _).mpr (Nat.mod_modEq i.val (orderOf s))
    change s ^ (i.val % orderOf s) = a.val
    rw [hmod]
    change (r ^ 2) ^ i.val = a.val
    rw [pow_right_comm, hi, hx]

  have hcard := Fintype.card_of_bijective ⟨hinj, hsurj⟩
  rw [Fintype.card_fin] at hcard
  rw [← hcard, orderOf_pow r (unit_orderOf_pos p r), (orderOf_eq_of_primitiveRoot hr),
    totient_prime p (isPrime_of_prime p Fact.out)]
  have heven : Even (p - 1) := by
    have := Nat.odd_iff.mp hpodd
    exact Nat.even_iff.mpr (by omega)
  rw [Nat.gcd_eq_right (even_iff_two_dvd.mp heven)]

/-- Proposition: any positive universal period supplies inverses for linear congruences. -/
theorem inverse_from_period (n a b : ℤ) (h : ℕ) (hh : 0 < h)
    (ha : a ^ h ≡ 1 [ZMOD n]) : a * (b * a ^ (h - 1)) ≡ b [ZMOD n] := by
  have he : a * (b * a ^ (h - 1)) = a ^ h * b := by
    calc
      a * (b * a ^ (h - 1)) = (a ^ (h - 1) * a) * b := by ring
      _ = a ^ h * b := by rw [← pow_succ, Nat.sub_add_cancel hh]

  rw [he]
  have h := TheTheoryOfCongruences.modEq_mul ha (TheTheoryOfCongruences.modEq_refl n b)
  simpa only [one_mul] using h

end ElementaryNumberTheory.PrimitiveRootsAndIndices
