import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.CompositeRoots

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

open scoped Classical
open NumberTheoreticFunctions EulersGeneralizationOfFermatsTheorem

/-- Lemma: separating one coordinate of the book's prime-exponent vector splits off
a coprime prime power, including a zero exponent. -/
theorem prime_power_split (n : ℕ) (hn : 0 < n) (p : ℕ) (hp : p.Prime) :
    ∃ k c : ℕ, 0 < c ∧ n = p ^ k * c ∧ p.Coprime c := by
  let e := primeExponents n
  let f := e.erase p
  have hsplit : Finsupp.single p (e p) + f = e := by
    ext q
    by_cases hq : q = p
    · subst q
      simp only [f, Finsupp.add_apply, Finsupp.single_eq_same, Finsupp.erase_same, add_zero]
    · simp only [f, Finsupp.add_apply, Finsupp.single_eq_of_ne hq, Finsupp.erase_ne hq, zero_add]
  have hf : ∀ q ∈ f.support, PrimesAndTheirDistribution.isPrime q := by
    intro q hq
    exact (primeExponents_spec n hn).1 q (Finset.mem_of_mem_erase
      (by simpa only [f, Finsupp.support_erase] using hq))
  have hneq : ∀ q ∈ f.support, q ≠ p := by
    intro q hq he
    subst q
    have hnonzero := Finsupp.mem_support_iff.mp hq
    exact hnonzero Finsupp.erase_same
  have heq : n = p ^ e p * factorValue f := by
    have he := congrArg factorValue hsplit
    rw [factorValue_add, factorValue, Finsupp.prod_single_index (pow_zero p)] at he
    exact (primeExponents_spec n hn).2.symm.trans he.symm

  refine ⟨e p, factorValue f, factorValue_pos f hf, heq, ?_⟩
  apply Nat.Coprime.prod_right
  intro q hq
  apply Nat.Coprime.pow_right
  have hqprime := hf q hq
  apply Nat.coprime_of_dvd
  intro d hd hdp hdq
  rcases (isPrime_of_prime p hp).2 d hdp with h | h
  · exact hd.ne_one h
  · subst d
    rcases hqprime.2 p hdq with h | h
    · exact hp.ne_one h
    · exact hneq q hq h.symm

/-- Lemma: an odd modulus greater than one admitting a primitive root is a prime power. -/
theorem prime_pow_of_odd_primitiveRoot (n : ℕ) (hn : 1 < n) (hodd : Odd n)
    (r : (ZMod n)ˣ) (hr : IsPrimitiveRoot r (Nat.totient n)) :
    ∃ p k : ℕ, p.Prime ∧ Odd p ∧ 0 < k ∧ n = p ^ k := by
  have : NeZero n := ⟨by omega⟩
  obtain ⟨l, hl, hprod⟩ := PrimesAndTheirDistribution.exists_prime_factors n (by omega)
  have hlne : l ≠ [] := by
    intro h
    rw [h] at hprod
    simp only [List.prod_nil] at hprod
    omega
  obtain ⟨p, hp⟩ := List.exists_mem_of_ne_nil l hlne
  have hplocal := hl p hp
  have hpstd : p.Prime := Nat.prime_def.mpr ⟨hplocal.1, hplocal.2⟩
  have hpd : p ∣ n := hprod ▸ List.dvd_prod hp
  have hpodd := hodd.of_dvd_nat hpd
  obtain ⟨k, c, hcpos, heq, hc⟩ := prime_power_split n (by omega) p hpstd
  have hk : 0 < k := by
    by_contra hk
    have hkzero : k = 0 := by omega
    rw [hkzero, pow_zero, one_mul] at heq
    have hd := Nat.dvd_gcd (heq ▸ hpd) (dvd_refl p)
    rw [hc.symm] at hd
    exact hpstd.ne_one (Nat.eq_one_of_dvd_one hd)
  have hppos := pow_pos hpstd.pos k
  have hpgt : 2 < p ^ k := by
    have hpowodd := hpodd.pow (n := k)
    have hpowgt : 1 < p ^ k := one_lt_pow₀ hpstd.one_lt hk.ne'
    have := Nat.odd_iff.mp hpowodd
    omega

  have hc1 : c = 1 := by
    by_contra hc1
    have hcodd : Odd c := hodd.of_dvd_nat ⟨p ^ k, by rw [heq, mul_comm]⟩
    have hcgt : 2 < c := by
      have := Nat.odd_iff.mp hcodd
      omega
    have hcop := hc.pow_left k
    apply not_exists_primitiveRoot_mul (p ^ k) c hpgt hcgt hcop
    have hh : ∃ s : (ZMod n)ˣ, IsPrimitiveRoot s (Nat.totient n) := ⟨r, hr⟩
    rwa [heq] at hh

  exact ⟨p, k, hpstd, hpodd, hk, by simpa only [hc1, mul_one] using heq⟩

/-- Theorem: among moduli greater than one, precisely 2, 4, odd prime powers,
and twice odd prime powers admit primitive roots. -/
theorem exists_primitiveRoot_iff (n : ℕ) (hn : 1 < n) :
    (∃ r : (ZMod n)ˣ, IsPrimitiveRoot r (Nat.totient n)) ↔
      n = 2 ∨ n = 4 ∨ ∃ p k : ℕ,
        p.Prime ∧ Odd p ∧ 0 < k ∧ (n = p ^ k ∨ n = 2 * p ^ k) := by
  have : NeZero n := ⟨by omega⟩
  constructor
  · rintro ⟨r, hr⟩
    obtain ⟨k, c, hcpos, heq, hc⟩ := prime_power_split n (by omega) 2 Nat.prime_two
    have hcodd : Odd c := Nat.coprime_two_left.mp hc
    have hk : k ≤ 2 := by
      by_contra hk
      have : NeZero (2 ^ k) := ⟨pow_ne_zero _ (by decide)⟩
      apply not_exists_primitiveRoot_two_pow k (by omega)
      exact ⟨ZMod.unitsMap ⟨c, heq⟩ r, primitiveRoot_of_dvd n (2 ^ k) ⟨c, heq⟩ r hr⟩

    interval_cases k
    · have hnc : n = c := by simpa only [pow_zero, one_mul] using heq
      have hodd : Odd n := hnc ▸ hcodd
      obtain ⟨p, j, hp, hpodd, hj, hnj⟩ := prime_pow_of_odd_primitiveRoot n hn hodd r hr
      exact Or.inr (Or.inr ⟨p, j, hp, hpodd, hj, Or.inl hnj⟩)

    · by_cases hc1 : c = 1
      · exact Or.inl (by simpa only [hc1, pow_one, mul_one] using heq)
      · have hcgt : 1 < c := by omega
        have : NeZero c := ⟨by omega⟩
        have hcd : c ∣ n := ⟨2, by simpa only [pow_one, mul_comm] using heq⟩
        obtain ⟨p, j, hp, hpodd, hj, hcj⟩ := prime_pow_of_odd_primitiveRoot c hcgt hcodd
          (ZMod.unitsMap hcd r) (primitiveRoot_of_dvd n c hcd r hr)
        exact Or.inr (Or.inr ⟨p, j, hp, hpodd, hj, Or.inr (by simpa only [pow_one, hcj] using heq)⟩)

    · have hc1 : c = 1 := by
        by_contra hc1
        have hcgt : 2 < c := by
          have := Nat.odd_iff.mp hcodd
          omega
        apply not_exists_primitiveRoot_mul 4 c (by decide) hcgt (hc.pow_left 2)
        have he : n = 4 * c := by simpa only [show 2 ^ 2 = 4 from rfl] using heq
        have hh : ∃ s : (ZMod n)ˣ, IsPrimitiveRoot s (Nat.totient n) := ⟨r, hr⟩
        rwa [he] at hh
      exact Or.inr (Or.inl (by simpa only [hc1, mul_one, show 2 ^ 2 = 4 from rfl] using heq))

  · rintro (rfl | rfl | ⟨p, k, hp, hpodd, hk, h⟩)
    · exact ⟨1, by
        have ht : Nat.totient 2 = 1 := by decide
        rw [ht]
        exact ⟨one_pow 1, fun i _ => one_dvd i⟩⟩

    · refine ⟨ZMod.unitOfCoprime 3 (by decide), (isPrimitiveRoot_iff_orderOf _ _).mpr ?_⟩
      have ht : Nat.totient 4 = 2 := by decide
      rw [ht]
      apply (orderOf_eq_iff (by decide : 0 < 2)).mpr
      refine ⟨by decide, ?_⟩
      intro i hi hipos
      have hei : i = 1 := by omega
      subst i
      decide

    · obtain ⟨j, rfl⟩ := Nat.exists_eq_succ_of_ne_zero hk.ne'
      obtain ⟨r, hr⟩ := exists_primitiveRoot_prime_pow p hp
        (hpodd.ne_two_of_dvd_nat dvd_rfl) j
      rcases h with rfl | rfl
      · exact ⟨r, hr⟩
      · have : NeZero (p ^ (j + 1)) := ⟨pow_ne_zero _ hp.ne_zero⟩
        exact exists_primitiveRoot_two_mul (p ^ (j + 1)) (hpodd.pow (n := j + 1)) r hr

end ElementaryNumberTheory.PrimitiveRootsAndIndices
