import Textbooks.ElementaryNumberTheory.EulersGeneralizationOfFermatsTheorem.Euler
import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.PrimeExponentSplitting
import Mathlib.RingTheory.RootsOfUnity.PrimitiveRoots

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

open EulersGeneralizationOfFermatsTheorem

/-- Lemma: division by the least positive period characterizes all periods. -/
theorem pow_eq_one_iff_dvd_order {M : Type*} [Monoid M] (a : M) (h : ℕ) :
    a ^ h = 1 ↔ orderOf a ∣ h := by
  constructor
  · intro hh
    have hr : a ^ (h % orderOf a) = 1 := by
      have he : a ^ h = a ^ (h % orderOf a) := by
        conv_lhs => rw [← Nat.mod_add_div h (orderOf a)]
        rw [pow_add, pow_mul, pow_orderOf_eq_one, one_pow, mul_one]
      exact he.symm.trans hh

    by_cases hz : orderOf a = 0
    · have : h = 0 := by
        by_contra hn
        exact (orderOf_eq_zero_iff.mp hz)
          (isOfFinOrder_iff_pow_eq_one.mpr ⟨h, Nat.pos_of_ne_zero hn, hh⟩)
      rw [this]
      exact dvd_zero _

    · apply Nat.dvd_of_mod_eq_zero
      by_contra hn
      exact pow_ne_one_of_lt_orderOf hn (Nat.mod_lt _ (Nat.pos_of_ne_zero hz)) hr

  · rintro ⟨t, rfl⟩
    rw [pow_mul, pow_orderOf_eq_one, one_pow]

/-- Lemma: a multiplicative map sends an element's order to a divisor of its order. -/
theorem orderOf_map_dvd {G H : Type*} [Monoid G] [Monoid H] (f : G →* H) (a : G) :
    orderOf (f a) ∣ orderOf a := by
  apply (pow_eq_one_iff_dvd_order (f a) _).mp
  rw [← map_pow, pow_orderOf_eq_one, map_one]

/-- Lemma: an injective multiplicative map preserves all periods, and hence the order. -/
theorem orderOf_injective {G H : Type*} [Monoid G] [Monoid H]
    (f : G →* H) (hf : Function.Injective f) (a : G) : orderOf (f a) = orderOf a := by
  apply Nat.dvd_antisymm (orderOf_map_dvd f a)
  apply (pow_eq_one_iff_dvd_order a _).mp
  apply hf
  rw [map_pow, pow_orderOf_eq_one, map_one]

/-- Lemma: the standard primitive-root predicate is exactly the least-positive-period order. -/
theorem isPrimitiveRoot_iff_orderOf {M : Type*} [CommMonoid M] (a : M) (k : ℕ) :
    IsPrimitiveRoot a k ↔ orderOf a = k := by
  constructor
  · intro h
    exact Nat.dvd_antisymm ((pow_eq_one_iff_dvd_order a k).mp h.pow_eq_one)
      (h.dvd_of_pow_eq_one (orderOf a) (pow_orderOf_eq_one a))

  · intro h
    refine ⟨h ▸ pow_orderOf_eq_one a, ?_⟩
    intro j hj
    exact h ▸ (pow_eq_one_iff_dvd_order a j).mp hj

/-- Lemma: extracting the order from the primitive-root characterization. -/
theorem orderOf_eq_of_primitiveRoot {M : Type*} [CommMonoid M] {a : M} {k : ℕ}
    (h : IsPrimitiveRoot a k) : orderOf a = k := by
  exact (isPrimitiveRoot_iff_orderOf a k).mp h

/-- Lemma: a power equality is equality of exponents modulo the order. -/
theorem pow_eq_pow_iff_modEq {G : Type*} [Group G] (a : G)
    (ha : 0 < orderOf a) (i j : ℕ) :
    a ^ i = a ^ j ↔ i ≡ j [MOD orderOf a] := by
  have hreduce (t : ℕ) : a ^ t = a ^ (t % orderOf a) := by
    conv_lhs => rw [← Nat.mod_add_div t (orderOf a)]
    rw [pow_add, pow_mul, pow_orderOf_eq_one, one_pow, mul_one]

  have hinj : ∀ u v : ℕ, u < orderOf a → v < orderOf a → a ^ u = a ^ v → u = v := by
    intro u v hu hv he
    wlog huv : v ≤ u generalizing u v
    · exact (this v u hv hu he.symm (by omega)).symm

    have hdiff : a ^ (u - v) = 1 := by
      apply mul_right_cancel (b := a ^ v)
      rw [one_mul, ← pow_add, Nat.sub_add_cancel huv, he]
    have hd := (pow_eq_one_iff_dvd_order a (u - v)).mp hdiff

    have hzero : u - v = 0 := by
      by_contra hn
      have := Nat.le_of_dvd (Nat.pos_of_ne_zero hn) hd
      omega
    omega

  constructor
  · intro he
    change i % orderOf a = j % orderOf a
    exact hinj _ _ (Nat.mod_lt _ ha) (Nat.mod_lt _ ha)
      ((hreduce i).symm.trans (he.trans (hreduce j)))

  · intro he
    exact (hreduce i).trans (he ▸ (hreduce j).symm)

/-- Lemma: reducing an integer's Euler congruence gives a positive period. -/
theorem orderOf_pos (n : ℕ) (hn : 0 < n) (a : ℤ)
    (ha : DivisibilityTheoryInTheIntegers.gcd a n = 1) :
    0 < orderOf (a : ZMod n) := by
  have he := (ZMod.intCast_eq_intCast_iff _ _ n).mpr (euler n hn a ha)
  have ht : 0 < Nat.totient n := totient_pos _ hn

  apply IsOfFinOrder.orderOf_pos
  exact isOfFinOrder_iff_pow_eq_one.mpr ⟨Nat.totient n, ht,
    by simpa only [Int.cast_pow, Int.cast_one] using he⟩

/-- Theorem: precisely the multiples of the order give the identity congruence. -/
theorem pow_modEq_one_iff (n : ℕ) (a : ℤ) (h : ℕ) :
    a ^ h ≡ 1 [ZMOD (n : ℤ)] ↔ orderOf (a : ZMod n) ∣ h := by
  rw [← ZMod.intCast_eq_intCast_iff]
  simpa only [Int.cast_pow, Int.cast_one] using pow_eq_one_iff_dvd_order (a : ZMod n) h

/-- Corollary: the order of a coprime integer divides phi of the modulus. -/
theorem orderOf_dvd_totient (n : ℕ) (hn : 0 < n) (a : ℤ)
    (ha : DivisibilityTheoryInTheIntegers.gcd a n = 1) :
    orderOf (a : ZMod n) ∣ Nat.totient n := by
  exact (pow_modEq_one_iff n a _).mp (euler n hn a ha)

/-- Theorem: equal powers correspond to congruent exponents modulo the order. -/
theorem pow_modEq_pow_iff (n : ℕ) (hn : 0 < n) (a : ℤ)
    (ha : DivisibilityTheoryInTheIntegers.gcd a n = 1) (i j : ℕ) :
    a ^ i ≡ a ^ j [ZMOD (n : ℤ)] ↔ i ≡ j [MOD orderOf (a : ZMod n)] := by
  let u := unitOfGcdEqOne n hn a ha
  have hu : orderOf u = orderOf (a : ZMod n) :=
    (orderOf_injective (Units.coeHom (ZMod n)) Units.coeHom_injective u).symm

  rw [← ZMod.intCast_eq_intCast_iff]
  simp only [Int.cast_pow]
  have he : (a : ZMod n) ^ i = (a : ZMod n) ^ j ↔ u ^ i = u ^ j := by
    constructor
    · intro h
      apply Units.ext
      exact h

    · intro h
      exact congrArg (fun v : (ZMod n)ˣ => (v : ZMod n)) h

  rw [he, pow_eq_pow_iff_modEq u (hu ▸ orderOf_pos n hn a ha), hu]

/-- Theorem: taking a positive power divides the order by the gcd of the exponent and order. -/
theorem orderOf_pow {G : Type*} [Monoid G] (a : G) (ha : 0 < orderOf a) (h : ℕ) :
    orderOf (a ^ h) = orderOf a / Nat.gcd (orderOf a) h := by
  let k := orderOf a
  let d := Nat.gcd k h
  have hd : 0 < d := Nat.gcd_pos_of_pos_left h ha
  have hk : 0 < k / d := Nat.div_pos (Nat.le_of_dvd ha (Nat.gcd_dvd_left k h)) hd

  have hdiv (t : ℕ) : k ∣ h * t ↔ k / d ∣ t := by
    have hcop := DivisibilityTheoryInTheIntegers.gcd_div_gcd_eq_one k h
      (Or.inl (by exact_mod_cast ha.ne'))
    rw [gcd_natCast_of_pos_left k h ha] at hcop
    have hc : (k / d).Coprime (h / d) :=
      (coprime_iff_gcd_eq_one (k / d) (h / d) hk).mpr (by
        simpa only [Int.natCast_ediv] using hcop)

    have he : k ∣ h * t ↔ k / d ∣ h / d * t := by
      have hk' : d * (k / d) = k := Nat.mul_div_cancel' (Nat.gcd_dvd_left k h)
      have hh' : d * (h / d) = h := Nat.mul_div_cancel' (Nat.gcd_dvd_right k h)
      calc
        k ∣ h * t ↔ d * (k / d) ∣ d * (h / d * t) := by
          rw [← mul_assoc, hk', hh']
        _ ↔ k / d ∣ h / d * t := Nat.mul_dvd_mul_iff_left hd

    rw [he]
    exact ⟨fun ht => nat_dvd_of_dvd_mul_of_coprime _ _ t hk hc ht,
      fun ht => dvd_mul_of_dvd_right ht _⟩

  have hp : (a ^ h) ^ (k / d) = 1 := by
    rw [← pow_mul, pow_eq_one_iff_dvd_order]
    exact (hdiv _).mpr dvd_rfl

  apply (orderOf_eq_iff hk).mpr
  refine ⟨hp, ?_⟩
  intro t ht htpos he
  rw [← pow_mul, pow_eq_one_iff_dvd_order] at he
  have := Nat.le_of_dvd htpos ((hdiv t).mp he)
  omega

/-- Corollary: taking a power preserves the order exactly for coprime exponents. -/
theorem orderOf_pow_eq_iff {G : Type*} [Monoid G] (a : G)
    (ha : 0 < orderOf a) (h : ℕ) :
    orderOf (a ^ h) = orderOf a ↔ h.Coprime (orderOf a) := by
  rw [orderOf_pow a ha, Nat.coprime_iff_gcd_eq_one, Nat.gcd_comm h]
  constructor
  · intro he
    have hd := Nat.mul_div_cancel' (Nat.gcd_dvd_left (orderOf a) h)
    rw [he] at hd
    exact Nat.eq_of_mul_eq_mul_right ha (hd.trans (one_mul _).symm)

  · intro he
    rw [he, Nat.div_one]

/-- Theorem: a power of a primitive root is primitive exactly for coprime exponents. -/
theorem isPrimitiveRoot_pow_iff (n : ℕ) (hn : 0 < n) (r : ZMod n)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (h : ℕ) :
    IsPrimitiveRoot (r ^ h) (Nat.totient n) ↔ h.Coprime (Nat.totient n) := by
  have ho := orderOf_eq_of_primitiveRoot hr
  have hp : 0 < orderOf r := ho ▸ (totient_pos _ hn)
  rw [isPrimitiveRoot_iff_orderOf _ _, ← ho, orderOf_pow_eq_iff r hp]

/-- Lemma: the book's Euler theorem applies to units represented by their least residues. -/
theorem unit_pow_totient (n : ℕ) [NeZero n] (a : (ZMod n)ˣ) :
    a ^ Nat.totient n = 1 := by
  have hn := NeZero.pos n
  have hc := ZMod.val_coe_unit_coprime a
  have hg := (coprime_iff_gcd_eq_one n (a : ZMod n).val hn).mp hc.symm
  have he := euler n hn (a : ZMod n).val
    (by
      rw [DivisibilityTheoryInTheIntegers.gcd_eq_of_common_divisors
        (a : ZMod n).val n n (a : ZMod n).val (fun _ => and_comm)]
      exact hg)

  apply Units.ext
  have hv := (ZMod.intCast_eq_intCast_iff _ _ n).mpr he
  simpa only [Int.cast_pow, Int.cast_natCast, ZMod.natCast_zmod_val, Int.cast_one,
    Units.val_pow_eq_pow_val, Units.val_one] using hv

/-- Lemma: Euler's positive exponent proves finiteness of every unit's order. -/
theorem unit_orderOf_pos (n : ℕ) [NeZero n] (a : (ZMod n)ˣ) : 0 < orderOf a := by
  exact (isOfFinOrder_iff_pow_eq_one.mpr
    ⟨Nat.totient n, totient_pos _ (NeZero.pos n), unit_pow_totient n a⟩).orderOf_pos

/-- Corollary: the order of every unit divides the totient. -/
theorem unit_orderOf_dvd_totient (n : ℕ) [NeZero n] (a : (ZMod n)ˣ) :
    orderOf a ∣ Nat.totient n := by
  exact (pow_eq_one_iff_dvd_order a _).mp (unit_pow_totient n a)

/-- Proposition: the order of a product divides the product of its factors' orders. -/
theorem orderOf_mul_dvd {G : Type*} [CommMonoid G] (a b : G) :
    orderOf (a * b) ∣ orderOf a * orderOf b := by
  apply (pow_eq_one_iff_dvd_order (a * b) _).mp
  rw [mul_pow, pow_mul, pow_orderOf_eq_one, one_pow, mul_comm (orderOf a),
    pow_mul, pow_orderOf_eq_one, one_pow, mul_one]

/-- Proposition: coprime orders multiply under multiplication of commuting units. -/
theorem orderOf_mul_of_coprime {G : Type*} [CommGroup G] (a b : G)
    (ha : 0 < orderOf a) (hb : 0 < orderOf b)
    (hc : (orderOf a).Coprime (orderOf b)) :
    orderOf (a * b) = orderOf a * orderOf b := by
  apply Nat.dvd_antisymm (orderOf_mul_dvd a b)
  have hm := pow_orderOf_eq_one (a * b)

  have hleft : orderOf a ∣ orderOf (a * b) * orderOf b := by
    apply (pow_eq_one_iff_dvd_order a _).mp
    have hh := congrArg (fun x : G => x ^ orderOf b) hm
    rw [mul_pow, mul_pow, ← pow_mul, pow_right_comm b, pow_orderOf_eq_one,
      one_pow, mul_one, one_pow] at hh
    exact hh

  have hright : orderOf b ∣ orderOf (a * b) * orderOf a := by
    apply (pow_eq_one_iff_dvd_order b _).mp
    have hh := congrArg (fun x : G => x ^ orderOf a) hm
    rw [mul_pow, mul_pow, pow_right_comm a, pow_orderOf_eq_one,
      one_pow, one_mul, ← pow_mul, one_pow] at hh
    exact hh

  have hda := nat_dvd_of_dvd_mul_of_coprime (orderOf a) (orderOf b) (orderOf (a * b))
    ha hc (by simpa only [mul_comm] using hleft)
  have hdb := nat_dvd_of_dvd_mul_of_coprime (orderOf b) (orderOf a) (orderOf (a * b))
    hb hc.symm (by simpa only [mul_comm] using hright)
  exact nat_mul_dvd_of_coprime _ _ _ ha hc hda hdb

/-- Lemma: selecting coprime prime-power parts of two orders realizes their local lcm. -/
theorem exists_orderOf_eq_lcm {G : Type*} [CommGroup G] (a b : G)
    (ha : 0 < orderOf a) (hb : 0 < orderOf b) :
    ∃ c : G, orderOf c = DivisibilityTheoryInTheIntegers.lcm (orderOf a) (orderOf b) := by
  obtain ⟨u, v, hupos, hvpos, hu, hv, hcop, huv⟩ :=
    exists_coprime_lcm_factors (orderOf a) (orderOf b) ha hb

  have hpow (x : G) (hx : 0 < orderOf x) (d : ℕ) (hd : d ∣ orderOf x)
      (hdpos : 0 < d) : orderOf (x ^ (orderOf x / d)) = d := by
    rw [orderOf_pow x hx, Nat.gcd_eq_right (Nat.div_dvd_of_dvd hd),
      Nat.div_div_self hd hx.ne']

  refine ⟨a ^ (orderOf a / u) * b ^ (orderOf b / v), ?_⟩
  have hau := hpow a ha u hu hupos
  have hbv := hpow b hb v hv hvpos
  have haupos : 0 < orderOf (a ^ (orderOf a / u)) := by
    rw [hau]
    exact hupos
  have hbvpos : 0 < orderOf (b ^ (orderOf b / v)) := by
    rw [hbv]
    exact hvpos
  have hcop' : (orderOf (a ^ (orderOf a / u))).Coprime (orderOf (b ^ (orderOf b / v))) := by
    rw [hau, hbv]
    exact hcop

  rw [orderOf_mul_of_coprime _ _ haupos hbvpos hcop', hau, hbv]
  exact huv

end ElementaryNumberTheory.PrimitiveRootsAndIndices
