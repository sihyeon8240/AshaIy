import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.PrimitiveRoots
import Mathlib.Algebra.Polynomial.Div
import Mathlib.Algebra.Polynomial.Degree.Operations
import Mathlib.Algebra.Field.ZMod

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

open scoped Classical
open Polynomial

/-- Lemma: the standard prime predicate supplies the book's divisor characterization. -/
theorem isPrime_of_prime (p : ℕ) (hp : p.Prime) : PrimesAndTheirDistribution.isPrime p := by
  exact ⟨hp.one_lt, fun d hd => (Nat.dvd_prime hp).mp hd⟩

/-- Theorem: a nonzero polynomial has at most its degree many distinct roots.
Removing a root removes a linear factor; induction counts the remaining roots. -/
theorem card_roots_le_natDegree {R : Type*} [CommRing R] [IsDomain R]
    (s : Finset R) (f : R[X]) (hf : f ≠ 0) (hs : ∀ x ∈ s, f.eval x = 0) :
    s.card ≤ f.natDegree := by
  induction s using Finset.induction_on generalizing f with
  | empty => exact Nat.zero_le _
  | @insert a s has ih =>
    have ha : f.IsRoot a := hs a (Finset.mem_insert_self a s)
    obtain ⟨g, hfg⟩ := (Polynomial.dvd_iff_isRoot).mpr ha
    have hg : g ≠ 0 := by
      intro h
      rw [h, mul_zero] at hfg
      exact hf hfg

    have hsg : ∀ x ∈ s, g.eval x = 0 := by
      intro x hx
      have hxne : x ≠ a := by
        intro h
        exact has (h ▸ hx)
      have he := hs x (Finset.mem_insert_of_mem hx)
      rw [hfg, Polynomial.eval_mul, Polynomial.eval_sub, Polynomial.eval_X,
        Polynomial.eval_C] at he
      exact (mul_eq_zero.mp he).resolve_left (sub_ne_zero.mpr hxne)

    have hcount := ih g hg hsg
    rw [Finset.card_insert_of_notMem has, hfg,
      Polynomial.natDegree_mul (Polynomial.X_sub_C_ne_zero a) hg,
      Polynomial.natDegree_X_sub_C]
    omega

/-- Theorem: the polynomial congruence bound over a prime modulus. -/
theorem card_polynomial_solutions (p : ℕ) [Fact p.Prime] (f : (ZMod p)[X])
    (hf : f ≠ 0) :
    ((Finset.univ : Finset (ZMod p)).filter (fun x => f.eval x = 0)).card ≤ f.natDegree := by
  exact card_roots_le_natDegree _ f hf (fun _ hx => (Finset.mem_filter.mp hx).2)

/-- Lemma: if all units are roots of x^m-1, then there are at most m units. -/
theorem card_units_le_of_pow_eq_one (p : ℕ) (hp : p.Prime) (m : ℕ) (hm : 0 < m)
    (h : ∀ a : (ZMod p)ˣ, a ^ m = 1) : Nat.totient p ≤ m := by
  have : Fact p.Prime := ⟨hp⟩
  let s := (Finset.univ : Finset (ZMod p)ˣ).image (fun a : (ZMod p)ˣ => (a : ZMod p))
  have hs : s.card = Nat.totient p := by
    rw [Finset.card_image_of_injective _ Units.val_injective, Finset.card_univ,
      ZMod.card_units_eq_totient]
  have hf : (X ^ m - C (1 : ZMod p) : (ZMod p)[X]) ≠ 0 := by
    intro he
    have hd := congrArg Polynomial.natDegree he
    rw [Polynomial.natDegree_X_pow_sub_C, Polynomial.natDegree_zero] at hd
    omega

  have hroots : ∀ x ∈ s, (X ^ m - C (1 : ZMod p)).eval x = 0 := by
    intro x hx
    obtain ⟨a, _, rfl⟩ := Finset.mem_image.mp hx
    have he := congrArg (fun u : (ZMod p)ˣ => (u : ZMod p)) (h a)
    simp only [Units.val_pow_eq_pow_val, Units.val_one] at he
    rw [Polynomial.eval_sub, Polynomial.eval_pow, Polynomial.eval_X,
      Polynomial.eval_C, he, sub_self]

  have hc := card_roots_le_natDegree s (X ^ m - C 1) hf hroots
  rwa [hs, Polynomial.natDegree_X_pow_sub_C] at hc

/-- Theorem: every prime modulus has a primitive root.
A maximal-order unit contains all other orders as divisors; the polynomial
root bound forces its order to be the number of units. -/
theorem exists_primitiveRoot_prime (p : ℕ) (hp : p.Prime) :
    ∃ r : (ZMod p)ˣ, IsPrimitiveRoot r (Nat.totient p) := by
  have : Fact p.Prime := ⟨hp⟩
  obtain ⟨r, _, hmax⟩ := (Finset.univ : Finset (ZMod p)ˣ).exists_max_image orderOf
    ⟨1, Finset.mem_univ 1⟩
  have hr := unit_orderOf_pos p r

  have hd : ∀ a : (ZMod p)ˣ, orderOf a ∣ orderOf r := by
    intro a
    obtain ⟨b, hb⟩ := exists_orderOf_eq_lcm r a hr (unit_orderOf_pos p a)
    have hle := hmax b (Finset.mem_univ b)
    rw [hb] at hle
    have hlcm := DivisibilityTheoryInTheIntegers.lcm_spec (orderOf r) (orderOf a)
      (by exact_mod_cast hr.ne') (by exact_mod_cast (unit_orderOf_pos p a).ne')
    have hge := Nat.le_of_dvd hlcm.1 (Int.natCast_dvd_natCast.mp hlcm.2.1)
    have he : DivisibilityTheoryInTheIntegers.lcm (orderOf r) (orderOf a) = orderOf r := by omega
    exact he ▸ Int.natCast_dvd_natCast.mp hlcm.2.2.1

  have hbound := card_units_le_of_pow_eq_one p hp (orderOf r) hr
    (fun a => (pow_eq_one_iff_dvd_order a _).mpr (hd a))
  have hle := Nat.le_of_dvd (Nat.totient_pos.mpr hp.pos) (unit_orderOf_dvd_totient p r)
  refine ⟨r, (isPrimitiveRoot_iff_orderOf _ _).mpr ?_⟩
  omega

/-- Lemma: a divisor of the prime's totient is realized as an order. -/
theorem exists_orderOf_eq_divisor (p : ℕ) (hp : p.Prime) (d : ℕ)
    (hd : d ∣ Nat.totient p) : ∃ r : (ZMod p)ˣ, orderOf r = d := by
  have : Fact p.Prime := ⟨hp⟩
  obtain ⟨r, hr⟩ := exists_primitiveRoot_prime p hp
  have ho : orderOf r = Nat.totient p := (orderOf_eq_of_primitiveRoot hr)
  have hrd : d ∣ orderOf r := ho ▸ hd

  refine ⟨r ^ (orderOf r / d), ?_⟩
  rw [orderOf_pow r (unit_orderOf_pos p r),
    Nat.gcd_eq_right (Nat.div_dvd_of_dvd hrd),
    Nat.div_div_self hrd (unit_orderOf_pos p r).ne']

/-- Theorem: x^d=1 has exactly d residue-class solutions for d dividing p-1. -/
theorem card_pow_eq_one_prime (p : ℕ) [Fact p.Prime] (d : ℕ)
    (hd : d ∣ Nat.totient p) :
    Fintype.card {a : (ZMod p)ˣ // a ^ d = 1} = d := by
  have hp : p.Prime := Fact.out
  have hdpos := Nat.pos_of_dvd_of_pos hd (Nat.totient_pos.mpr hp.pos)
  obtain ⟨r, hr⟩ := exists_orderOf_eq_divisor p hp d hd
  let f : Fin d → {a : (ZMod p)ˣ // a ^ d = 1} := fun i =>
    ⟨r ^ i.val, by
      have he : r ^ d = 1 := hr ▸ pow_orderOf_eq_one r
      rw [pow_right_comm, he, one_pow]⟩
  have hinj : Function.Injective f := by
    intro i j hij
    have hp := congrArg Subtype.val hij
    have he := (pow_eq_pow_iff_modEq r (unit_orderOf_pos p r) i.val j.val).mp hp
    rw [hr] at he
    apply Fin.ext
    simpa only [Nat.ModEq, Nat.mod_eq_of_lt i.isLt, Nat.mod_eq_of_lt j.isLt] using he
  have hlow : d ≤ Fintype.card {a : (ZMod p)ˣ // a ^ d = 1} := by
    simpa only [Fintype.card_fin] using Fintype.card_le_of_injective f hinj

  let s := ((Finset.univ : Finset (ZMod p)ˣ).filter (fun a => a ^ d = 1)).image
    (fun a : (ZMod p)ˣ => (a : ZMod p))
  have hs : s.card = Fintype.card {a : (ZMod p)ˣ // a ^ d = 1} := by
    rw [Finset.card_image_of_injective _ Units.val_injective, Fintype.card_subtype]
  have hf : (X ^ d - C (1 : ZMod p) : (ZMod p)[X]) ≠ 0 := by
    intro he
    have := congrArg Polynomial.natDegree he
    rw [Polynomial.natDegree_X_pow_sub_C, Polynomial.natDegree_zero] at this
    omega
  have hhigh := card_roots_le_natDegree s (X ^ d - C 1) hf (by
    intro x hx
    obtain ⟨a, ha, rfl⟩ := Finset.mem_image.mp hx
    have he := congrArg (fun u : (ZMod p)ˣ => (u : ZMod p)) (Finset.mem_filter.mp ha).2
    simpa only [Polynomial.eval_sub, Polynomial.eval_pow, Polynomial.eval_X,
      Polynomial.eval_C, Units.val_pow_eq_pow_val, Units.val_one, sub_eq_zero] using he)
  rw [hs, Polynomial.natDegree_X_pow_sub_C] at hhigh
  omega

end ElementaryNumberTheory.PrimitiveRootsAndIndices
