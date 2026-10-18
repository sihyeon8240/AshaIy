import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.Indices
import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.PrimeRoots

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

open scoped Classical

/-- Lemma: a solvable linear equation in exponent residue classes has gcd(k,m) solutions. -/
theorem card_zmod_linear_solutions (m : ℕ) [NeZero m] (k b : ℕ) (x₀ : ZMod m)
    (h₀ : (k : ZMod m) * x₀ = b) :
    Fintype.card {x : ZMod m // (k : ZMod m) * x = b} = Nat.gcd k m := by
  have h₀int : (k : ℤ) * x₀.val ≡ b [ZMOD (m : ℤ)] := by
    apply (ZMod.intCast_eq_intCast_iff _ _ m).mp
    simpa only [Int.cast_mul, Int.cast_natCast, ZMod.natCast_zmod_val] using h₀
  let g := DivisibilityTheoryInTheIntegers.gcd k m
  let c := (m : ℤ) / (g : ℤ)
  have hclasses := TheTheoryOfCongruences.linear_solution_classes (m : ℤ) k b x₀.val
    (by exact_mod_cast NeZero.pos m) h₀int
  let f : Fin g → {x : ZMod m // (k : ZMod m) * x = b} := fun t =>
    ⟨((x₀.val : ℤ) + c * t.val : ℤ), by
      have hcast := (ZMod.intCast_eq_intCast_iff _ _ m).mpr (hclasses.1 t)
      simpa only [Int.cast_mul, Int.cast_natCast] using hcast⟩

  have hunique : ∀ y : {x : ZMod m // (k : ZMod m) * x = b}, ∃! t : Fin g, f t = y := by
    intro y
    have hy : (k : ℤ) * y.val.val ≡ b [ZMOD (m : ℤ)] := by
      apply (ZMod.intCast_eq_intCast_iff _ _ m).mp
      simpa only [Int.cast_mul, Int.cast_natCast, ZMod.natCast_zmod_val] using y.property
    obtain ⟨t, ht, huniq⟩ := hclasses.2 y.val.val hy
    refine ⟨t, ?_, ?_⟩
    · apply Subtype.ext
      have hcast := (ZMod.intCast_eq_intCast_iff _ _ m).mpr ht
      simpa only [Int.cast_natCast, ZMod.natCast_zmod_val] using hcast.symm

    · intro s hs
      apply huniq s
      apply (ZMod.intCast_eq_intCast_iff _ _ m).mp
      have hval := congrArg Subtype.val hs
      simpa only [Int.cast_natCast, ZMod.natCast_zmod_val] using hval.symm

  have hbij : Function.Bijective f := by
    constructor
    · intro i j hij
      obtain ⟨t, _, ht⟩ := hunique (f j)
      exact (ht i hij).trans (ht j rfl).symm
    · intro y
      obtain ⟨t, ht, _⟩ := hunique y
      exact ⟨t, ht⟩
  let e := Equiv.ofBijective f hbij
  rw [← Fintype.card_congr e, Fintype.card_fin]
  exact gcd_natCast k m (NeZero.pos m)

/-- Theorem: a solvable power equation has exactly gcd(k,phi(n)) unit solutions. -/
theorem card_pow_solutions (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a x₀ : (ZMod n)ˣ) (k : ℕ)
    (h₀ : x₀ ^ k = a) :
    Fintype.card {x : (ZMod n)ˣ // x ^ k = a} = Nat.gcd k (Nat.totient n) := by
  have : NeZero (Nat.totient n) := ⟨(Nat.totient_pos.mpr (NeZero.pos n)).ne'⟩
  let e := indexEquiv n r hr
  have he (x : (ZMod n)ˣ) :
      x ^ k = a ↔ (k : ZMod (Nat.totient n)) * e x = (index n r hr a : ℕ) := by
    rw [pow_eq_iff_index n r hr]
    change k * index n r hr x ≡ index n r hr a [MOD Nat.totient n] ↔
      (k : ZMod (Nat.totient n)) * (index n r hr x : ℕ) = (index n r hr a : ℕ)
    rw [← Nat.cast_mul, ZMod.natCast_eq_natCast_iff]

  rw [Fintype.card_congr (e.subtypeEquiv
    (q := fun y => (k : ZMod (Nat.totient n)) * y = (index n r hr a : ℕ)) he)]
  exact card_zmod_linear_solutions (Nat.totient n) k (index n r hr a) (e x₀) ((he x₀).mp h₀)

/-- Definition: a positive power equal to a unit gives an explicit inverse for its base. -/
def unitOfPowEq (n k : ℕ) (x : ZMod n) (a : (ZMod n)ˣ) (hk : 0 < k)
    (hx : x ^ k = (a : ZMod n)) : (ZMod n)ˣ := by
  let y := x ^ (k - 1) * (a⁻¹ : (ZMod n)ˣ)
  have hxy : x * y = 1 := by
    dsimp only [y]
    rw [← mul_assoc, ← pow_succ', Nat.sub_add_cancel hk, hx]
    exact a.val_inv
  have hyx : y * x = 1 := by
    rw [mul_comm]
    exact hxy

  exact ⟨x, y, hxy, hyx⟩

/-- Corollary: allowing all residue classes as candidate roots gives the same solvability test. -/
theorem exists_pow_eq_zmod_iff (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a : (ZMod n)ˣ) (k : ℕ) (hk : 0 < k) :
    (∃ x : ZMod n, x ^ k = (a : ZMod n)) ↔
      (a : ZMod n) ^ (Nat.totient n / Nat.gcd k (Nat.totient n)) = 1 := by
  have hex : (∃ x : ZMod n, x ^ k = (a : ZMod n)) ↔ ∃ x : (ZMod n)ˣ, x ^ k = a := by
    constructor
    · rintro ⟨x, hx⟩
      refine ⟨unitOfPowEq n k x a hk hx, ?_⟩
      exact Units.ext hx

    · rintro ⟨x, hx⟩
      refine ⟨x, ?_⟩
      exact congrArg (fun u : (ZMod n)ˣ => (u : ZMod n)) hx
  have hone : a ^ (Nat.totient n / Nat.gcd k (Nat.totient n)) = 1 ↔
      (a : ZMod n) ^ (Nat.totient n / Nat.gcd k (Nat.totient n)) = 1 := by
    constructor
    · intro h
      exact congrArg (fun u : (ZMod n)ˣ => (u : ZMod n)) h
    · intro h
      exact Units.ext h

  exact hex.trans ((exists_pow_eq_iff n r hr a k).trans hone)

/-- Corollary: every positive-power solution is a unit, so the full residue-class count is d. -/
theorem card_pow_solutions_zmod (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a : (ZMod n)ˣ) (k : ℕ) (hk : 0 < k)
    (x₀ : ZMod n) (h₀ : x₀ ^ k = (a : ZMod n)) :
    Fintype.card {x : ZMod n // x ^ k = (a : ZMod n)} = Nat.gcd k (Nat.totient n) := by
  let e : {x : (ZMod n)ˣ // x ^ k = a} ≃ {x : ZMod n // x ^ k = (a : ZMod n)} :=
    { toFun := fun x => ⟨x.val, congrArg (fun u : (ZMod n)ˣ => (u : ZMod n)) x.property⟩
      invFun := fun x => ⟨unitOfPowEq n k x.val a hk x.property, Units.ext x.property⟩
      left_inv := fun _ => Subtype.ext (Units.ext rfl)
      right_inv := fun _ => Subtype.ext rfl }
  have hc := card_pow_solutions n r hr a (unitOfPowEq n k x₀ a hk h₀) k (Units.ext h₀)

  have he : Nat.card {x : ZMod n // x ^ k = (a : ZMod n)} = Nat.gcd k (Nat.totient n) := by
    rw [← Nat.card_congr e]
    simpa only [← Nat.card_eq_fintype_card] using hc
  simpa only [Nat.card_eq_fintype_card] using he

/-- Corollary: a prime-modulus power equation satisfies the same criterion with phi(p)=p-1. -/
theorem exists_pow_eq_prime_iff (p : ℕ) [Fact p.Prime] (a : (ZMod p)ˣ) (k : ℕ) :
    (∃ x : (ZMod p)ˣ, x ^ k = a) ↔ a ^ ((p - 1) / Nat.gcd k (p - 1)) = 1 := by
  have hp : p.Prime := Fact.out
  obtain ⟨r, hr⟩ := exists_primitiveRoot_prime p hp
  have he := exists_pow_eq_iff p r hr a k
  rwa [EulersGeneralizationOfFermatsTheorem.totient_prime p (isPrime_of_prime p hp)] at he

/-- Corollary: a solvable prime-modulus power equation has exactly gcd(k,p-1) solutions. -/
theorem card_pow_solutions_prime (p : ℕ) [Fact p.Prime] (a x₀ : (ZMod p)ˣ) (k : ℕ)
    (h₀ : x₀ ^ k = a) :
    Fintype.card {x : (ZMod p)ˣ // x ^ k = a} = Nat.gcd k (p - 1) := by
  obtain ⟨r, hr⟩ := exists_primitiveRoot_prime p Fact.out
  have he := card_pow_solutions p r hr a x₀ k h₀
  rwa [EulersGeneralizationOfFermatsTheorem.totient_prime p (isPrime_of_prime p Fact.out)] at he

/-- Lemma: if d-th roots form a set of size d, a primitive d-th root parametrizes all of them. -/
theorem card_primitiveRoots_of_card_roots {G : Type*} [CommGroup G] [Fintype G]
    (d : ℕ) (hd : 0 < d) (r : G) (hr : IsPrimitiveRoot r d)
    (hcard : Fintype.card {a : G // a ^ d = 1} = d) :
    Fintype.card {a : G // IsPrimitiveRoot a d} = Nat.totient d := by
  have ho : orderOf r = d := (orderOf_eq_of_primitiveRoot hr)
  have hrpos : 0 < orderOf r := by
    rw [ho]
    exact hd
  let f : Fin (orderOf r) → {a : G // a ^ d = 1} := fun i =>
    ⟨r ^ i.val, by rw [pow_right_comm, hr.pow_eq_one, one_pow]⟩
  have hinj : Function.Injective f := by
    intro i j hij
    exact pow_injective_fin r hrpos (congrArg Subtype.val hij)
  have hbij := (Fintype.bijective_iff_injective_and_card f).mpr
    ⟨hinj, by rw [Fintype.card_fin, ho, hcard]⟩
  let e := Equiv.ofBijective f hbij
  have he (i : Fin (orderOf r)) :
      i.val.Coprime (orderOf r) ↔ IsPrimitiveRoot (e i).val d := by
    change i.val.Coprime (orderOf r) ↔ IsPrimitiveRoot (r ^ i.val) d
    rw [isPrimitiveRoot_iff_orderOf _ _, ← ho, orderOf_pow_eq_iff r hrpos]
  let q : {a : {x : G // x ^ d = 1} // IsPrimitiveRoot a.val d} ≃
      {a : G // IsPrimitiveRoot a d} :=
    { toFun := fun a => ⟨a.val.val, a.property⟩
      invFun := fun a => ⟨⟨a.val, a.property.pow_eq_one⟩, a.property⟩
      left_inv := fun _ => rfl
      right_inv := fun _ => rfl }

  rw [← Fintype.card_congr q, ← Fintype.card_congr (e.subtypeEquiv he), card_coprime_fin, ho]

/-- Theorem: for each divisor d of p-1, exactly phi(d) classes have order d. -/
theorem card_orderOf_eq_prime (p : ℕ) [Fact p.Prime] (d : ℕ) (hd : d ∣ p - 1) :
    Fintype.card {a : (ZMod p)ˣ // orderOf a = d} = Nat.totient d := by
  have hp : p.Prime := Fact.out
  have ht := EulersGeneralizationOfFermatsTheorem.totient_prime p (isPrime_of_prime p hp)
  have hdphi : d ∣ Nat.totient p := ht ▸ hd
  obtain ⟨r, hr⟩ := exists_orderOf_eq_divisor p hp d hdphi
  have hdpos := Nat.pos_of_dvd_of_pos hdphi (Nat.totient_pos.mpr hp.pos)
  have hc := card_primitiveRoots_of_card_roots (G := (ZMod p)ˣ) d hdpos r
    ((isPrimitiveRoot_iff_orderOf _ _).mpr hr) (by
      simpa only [← Nat.card_eq_fintype_card] using card_pow_eq_one_prime p d hdphi)

  have he : {a : (ZMod p)ˣ // orderOf a = d} ≃
      {a : (ZMod p)ˣ // IsPrimitiveRoot a d} :=
    Equiv.subtypeEquivRight (fun _ => (isPrimitiveRoot_iff_orderOf _ _).symm)
  have hcard : Nat.card {a : (ZMod p)ˣ // orderOf a = d} = Nat.totient d := by
    rw [Nat.card_congr he]
    simpa only [← Nat.card_eq_fintype_card] using hc
  simpa only [Nat.card_eq_fintype_card] using hcard

end ElementaryNumberTheory.PrimitiveRootsAndIndices
