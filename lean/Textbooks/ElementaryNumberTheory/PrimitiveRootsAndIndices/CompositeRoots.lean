import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.PrimePowerLifting
import Textbooks.ElementaryNumberTheory.EulersGeneralizationOfFermatsTheorem.ReducedResidues
import Mathlib.Algebra.Group.Equiv.Basic

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

open scoped Classical
open EulersGeneralizationOfFermatsTheorem

/-- Theorem: every positive power of an odd prime has a primitive root. -/
theorem exists_primitiveRoot_prime_pow (p : ℕ) (hp : p.Prime) (hpodd : p ≠ 2) (n : ℕ) :
    ∃ r : (ZMod (p ^ (n + 1)))ˣ, IsPrimitiveRoot r (Nat.totient (p ^ (n + 1))) := by
  have : Fact p.Prime := ⟨hp⟩
  have : NeZero (p ^ (n + 1)) := ⟨pow_ne_zero _ hp.ne_zero⟩
  let ha : IsUnit (1 + p : ZMod (p ^ (n + 1))) := by
    have he : (1 + p : ZMod (p ^ (n + 1))) = ((1 + p : ℕ) : ZMod (p ^ (n + 1))) := by
      rw [Nat.cast_add, Nat.cast_one]
    rw [he, ZMod.isUnit_iff_coprime]
    exact (Nat.coprime_add_self_left.mpr (Nat.coprime_one_left p)).pow_right _
  let a := ha.unit
  have hao : orderOf a = p ^ n := by
    rw [← orderOf_injective (Units.coeHom (ZMod (p ^ (n + 1)))) Units.coeHom_injective,
      Units.coeHom_apply, IsUnit.unit_spec]
    have h := orderOf_one_add_mul_prime p hp hpodd 1
      (by
        intro hd
        have := Int.natCast_dvd_natCast.mp hd
        exact hp.ne_one (Nat.eq_one_of_dvd_one this)) n
    simpa only [Int.cast_one, mul_one] using h

  obtain ⟨c, hc⟩ := exists_primitiveRoot_prime p hp
  let b := ZMod.unitOfCoprime (c : ZMod p).val (ZMod.val_coe_unit_coprime c |>.pow_right (n + 1))
  let f := ZMod.unitsMap (dvd_pow_self p (by omega : n + 1 ≠ 0))
  have hfb : f b = c := by
    apply Units.ext
    change (ZMod.castHom (dvd_pow_self p (by omega : n + 1 ≠ 0)) (ZMod p))
      (((c : ZMod p).val : ℕ) : ZMod (p ^ (n + 1))) = (c : ZMod p)
    rw [map_natCast, ZMod.natCast_zmod_val]
  have hd : p - 1 ∣ orderOf b := by
    have h := orderOf_map_dvd f b
    rw [hfb, (orderOf_eq_of_primitiveRoot hc), totient_prime p (isPrime_of_prime p hp)] at h
    exact h
  have hb := unit_orderOf_pos (p ^ (n + 1)) b
  let t := b ^ (orderOf b / (p - 1))
  have hto : orderOf t = p - 1 := by
    rw [orderOf_pow b hb, Nat.gcd_eq_right (Nat.div_dvd_of_dvd hd), Nat.div_div_self hd hb.ne']

  have hcop : (p ^ n).Coprime (p - 1) := by
    apply Nat.Coprime.pow_left
    exact (Nat.coprime_self_sub_right hp.one_lt.le).mpr (Nat.coprime_one_right p)
  have htpos : 0 < orderOf t := by
    rw [hto]
    have := hp.two_le
    omega
  have hcop' : (orderOf a).Coprime (orderOf t) := by
    rw [hao, hto]
    exact hcop

  refine ⟨a * t, (isPrimitiveRoot_iff_orderOf _ _).mpr ?_⟩
  rw [orderOf_mul_of_coprime a t (unit_orderOf_pos _ a) htpos hcop', hao, hto,
    totient_prime_pow_succ p n (isPrime_of_prime p hp)]

/-- Lemma: a surjective image of the powers of an element still consists of powers. -/
theorem orderOf_eq_card_of_pow_surjective {G : Type*} [Group G] [Fintype G]
    (r : G) (hr : 0 < orderOf r) (h : ∀ a : G, ∃ i : ℕ, r ^ i = a) :
    orderOf r = Fintype.card G := by
  let f : Fin (orderOf r) → G := fun i => r ^ i.val
  have hinj := pow_injective_fin r hr
  have hsurj : Function.Surjective f := by
    intro a
    obtain ⟨i, hi⟩ := h a
    refine ⟨⟨i % orderOf r, Nat.mod_lt i hr⟩, ?_⟩
    change r ^ (i % orderOf r) = a
    have he : r ^ i = r ^ (i % orderOf r) := by
      conv_lhs => rw [← Nat.mod_add_div i (orderOf r)]
      rw [pow_add, pow_mul, pow_orderOf_eq_one, one_pow, mul_one]
    exact he.symm.trans hi

  have he := Fintype.card_of_bijective ⟨hinj, hsurj⟩
  simpa only [Fintype.card_fin] using he

/-- Lemma: reduction on units is surjective for a divisor of a positive modulus.
The chosen correction avoids precisely the primes dividing the modulus. -/
theorem unitsMap_surjective (m n : ℕ) [NeZero m] (hd : n ∣ m) :
    Function.Surjective (ZMod.unitsMap hd) := by
  have : NeZero n := ⟨fun hn => NeZero.ne m (Nat.eq_zero_of_zero_dvd (hn ▸ hd))⟩
  intro u
  let x := (u : ZMod n).val
  let s := (NumberTheoreticFunctions.primeExponents m).support.filter (fun p => ¬p ∣ x)
  let k := s.prod id
  have hx := ZMod.val_coe_unit_coprime u
  have hcop : (x + k * n).Coprime m := by
    apply Nat.coprime_of_dvd
    intro p hp hpx hpm
    by_cases hpd : p ∣ x
    · have hprod : p ∣ k * n := by
        have h := Nat.dvd_sub hpx hpd
        simpa only [add_comm x, Nat.add_sub_cancel] using h
      rcases PrimesAndTheirDistribution.prime_dvd_mul_nat p k n
          (isPrime_of_prime p hp) hprod with hpk | hpn
      · obtain ⟨q, hq, hpq⟩ := prime_dvd_finset_prod p (isPrime_of_prime p hp) s id hpk
        obtain ⟨hqprime, hqx⟩ := Finset.mem_filter.mp hq
        have hq := (NumberTheoreticFunctions.primeExponents_spec m (NeZero.pos m)).1 q hqprime
        rcases hq.2 p hpq with hp1 | hpq
        · exact hp.ne_one hp1
        · exact hqx (hpq ▸ hpd)
      · have hdiv := Nat.dvd_gcd hpd hpn
        rw [hx] at hdiv
        exact hp.ne_one (Nat.eq_one_of_dvd_one hdiv)

    · have hps : p ∈ s := Finset.mem_filter.mpr
        ⟨prime_mem_primeExponents_support p m (isPrime_of_prime p hp) (NeZero.pos m) hpm, hpd⟩
      have hpk : p ∣ k := Finset.dvd_prod_of_mem id hps
      have h := Nat.dvd_sub hpx (dvd_mul_of_dvd_left hpk n)
      exact hpd (by simpa only [Nat.add_sub_cancel] using h)

  refine ⟨ZMod.unitOfCoprime (x + k * n) hcop, ?_⟩
  apply Units.ext
  change (ZMod.castHom hd (ZMod n)) ((x + k * n : ℕ) : ZMod m) = (u : ZMod n)
  rw [map_natCast, Nat.cast_add, Nat.cast_mul, ZMod.natCast_self, mul_zero,
    add_zero, show x = (u : ZMod n).val from rfl, ZMod.natCast_zmod_val]

/-- Theorem: a primitive root reduces to a primitive root at every positive divisor. -/
theorem primitiveRoot_of_dvd (m n : ℕ) [NeZero m] [NeZero n] (hd : n ∣ m)
    (r : (ZMod m)ˣ) (hr : IsPrimitiveRoot r (Nat.totient m)) :
    IsPrimitiveRoot (ZMod.unitsMap hd r) (Nat.totient n) := by
  let f := ZMod.unitsMap hd
  have hpow : ∀ a : (ZMod n)ˣ, ∃ i : ℕ, (f r) ^ i = a := by
    intro a
    obtain ⟨b, hb⟩ := unitsMap_surjective m n hd a
    obtain ⟨i, hi, _⟩ := exists_unique_pow m r hr b
    refine ⟨i.val, ?_⟩
    rw [← map_pow, hi]
    exact hb

  apply (isPrimitiveRoot_iff_orderOf _ _).mpr
  rw [← ZMod.card_units_eq_totient]
  exact orderOf_eq_card_of_pow_surjective (f r) (unit_orderOf_pos n (f r)) hpow

/-- Theorem: no power of two of exponent at least three has a primitive root. -/
theorem not_exists_primitiveRoot_two_pow (k : ℕ) (hk : 3 ≤ k) :
    ¬∃ r : (ZMod (2 ^ k))ˣ, IsPrimitiveRoot r (Nat.totient (2 ^ k)) := by
  have : NeZero (2 ^ k) := ⟨pow_ne_zero _ (by decide)⟩
  rintro ⟨r, hr⟩
  have h8 := primitiveRoot_of_dvd (2 ^ k) 8 (pow_dvd_pow 2 hk) r hr
  have hpow : ∀ a : (ZMod 8)ˣ, a ^ 2 = 1 := by decide
  have hd := h8.dvd_of_pow_eq_one 2 (hpow _)
  have ht8 : Nat.totient 8 = 4 := by decide
  rw [ht8] at hd
  norm_num at hd

/-- Theorem: a coprime product of two moduli exceeding two has no primitive root. -/
theorem not_exists_primitiveRoot_mul (m n : ℕ) (hm : 2 < m) (hn : 2 < n)
    (hc : m.Coprime n) :
    ¬∃ r : (ZMod (m * n))ˣ, IsPrimitiveRoot r (Nat.totient (m * n)) := by
  have : NeZero m := ⟨by omega⟩
  have : NeZero n := ⟨by omega⟩
  have : NeZero (m * n) := ⟨mul_ne_zero (by omega) (by omega)⟩
  obtain ⟨u, hu⟩ := totient_even m hm
  obtain ⟨v, hv⟩ := totient_even n hn
  have hu0 : 0 < u := by
    have := totient_pos _ (by omega : 0 < m)
    omega
  have hv0 : 0 < v := by
    have := totient_pos _ (by omega : 0 < n)
    omega
  have ht := totient_mul m n (by omega) (by omega) ((coprime_iff_gcd_eq_one m n (by omega)).mp hc)
  let e := (Units.mapEquiv (ZMod.chineseRemainder hc).toMulEquiv).trans MulEquiv.prodUnits

  rintro ⟨r, hr⟩
  have he : r ^ (2 * u * v) = 1 := by
    apply e.injective
    rw [map_pow, map_one]
    apply Prod.ext
    · change (e r).1 ^ (2 * u * v) = 1
      rw [show 2 * u * v = Nat.totient m * v by nlinarith [hu],
        pow_mul, unit_pow_totient, one_pow]
    · change (e r).2 ^ (2 * u * v) = 1
      rw [show 2 * u * v = Nat.totient n * u by nlinarith [hv],
        pow_mul, unit_pow_totient, one_pow]

  have hd := hr.dvd_of_pow_eq_one (2 * u * v) he
  have hle := Nat.le_of_dvd (by positivity : 0 < 2 * u * v) hd
  rw [ht, hu, hv] at hle
  nlinarith [mul_pos hu0 hv0]

/-- Theorem: twice an odd modulus has a primitive root whenever that modulus does. -/
theorem exists_primitiveRoot_two_mul (n : ℕ) (hn : Odd n) [NeZero n]
    (r : (ZMod n)ˣ) (hr : IsPrimitiveRoot r (Nat.totient n)) :
    ∃ s : (ZMod (2 * n))ˣ, IsPrimitiveRoot s (Nat.totient (2 * n)) := by
  have : NeZero (2 * n) := ⟨mul_ne_zero (by decide) (NeZero.ne n)⟩
  have hc := Nat.coprime_two_left.mpr hn
  let e := (Units.mapEquiv (ZMod.chineseRemainder hc).toMulEquiv).trans MulEquiv.prodUnits
  have ht : Nat.totient (2 * n) = Nat.totient n := by
    rw [totient_mul 2 n (by decide) (NeZero.pos n)
      ((coprime_iff_gcd_eq_one 2 n (by decide)).mp hc)]
    have htwo : Nat.totient 2 = 1 := by decide
    rw [htwo, one_mul]

  refine ⟨e.symm (1, r), ?_⟩
  rw [ht]
  constructor
  · apply e.injective
    rw [map_pow, e.apply_symm_apply, map_one]
    exact Prod.ext (one_pow _) hr.pow_eq_one

  · intro i hi
    have he := congrArg (fun x => (e x).2) hi
    simp only [map_pow, e.apply_symm_apply, Prod.pow_snd, map_one] at he
    exact hr.dvd_of_pow_eq_one i he

end ElementaryNumberTheory.PrimitiveRootsAndIndices
