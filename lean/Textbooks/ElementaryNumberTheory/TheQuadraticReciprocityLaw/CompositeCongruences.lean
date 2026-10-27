import Textbooks.ElementaryNumberTheory.TheQuadraticReciprocityLaw.PrimePowerCongruences

namespace ElementaryNumberTheory.TheQuadraticReciprocityLaw

open TheTheoryOfCongruences PrimitiveRootsAndIndices
open scoped BigOperators

/-- Theorem: a square congruence at pairwise coprime moduli is solvable exactly when all
of its component congruences are solvable. -/
theorem exists_square_prod_iff {ι : Type*} (s : Finset ι) (m : ι → ℤ) (a : ℤ)
    (hm : ∀ i ∈ s, m i ≠ 0)
    (hcop : ∀ i ∈ s, ∀ j ∈ s, i ≠ j → DivisibilityTheoryInTheIntegers.gcd (m i) (m j) = 1) :
    (∃ x : ℤ, x ^ 2 ≡ a [ZMOD ∏ i ∈ s, m i]) ↔
      ∀ i ∈ s, ∃ x : ℤ, x ^ 2 ≡ a [ZMOD m i] := by
  classical
  constructor
  · rintro ⟨x, hx⟩ i hi
    exact ⟨x, modEq_of_dvd (Finset.dvd_prod_of_mem m hi) hx⟩

  · intro h
    let roots (i : ι) := if hi : i ∈ s then (h i hi).choose else 0
    have hr (i : ι) (hi : i ∈ s) : (roots i) ^ 2 ≡ a [ZMOD m i] := by
      dsimp only [roots]
      rw [dite_eq_left hi]
      exact (h i hi).choose_spec
    obtain ⟨x, hx, _⟩ := chinese_remainder s m roots hm hcop
    refine ⟨x, (modEq_iff_dvd_sub _ _ _).mpr ?_⟩
    apply prod_dvd_of_pairwise s m hm hcop
    intro i hi
    apply (modEq_iff_dvd_sub _ _ _).mp
    exact (modEq_pow (hx i hi) 2).trans (hr i hi)

/-- Theorem: the prime-power factorization gives the complete solvability criterion.
At two the exponent-one condition is automatic, exponent two requires one modulo four,
and every larger exponent requires one modulo eight. -/
theorem complete_solvability_criterion (s : Finset ℕ) (e : ℕ → ℕ)
    (hp : ∀ p ∈ s, p.Prime) (he : ∀ p ∈ s, 0 < e p) (a : ℤ)
    (ha : DivisibilityTheoryInTheIntegers.gcd a (∏ p ∈ s, (p : ℤ) ^ e p) = 1) :
    (∃ x : ℤ, x ^ 2 ≡ a [ZMOD ∏ p ∈ s, (p : ℤ) ^ e p]) ↔
      ∀ p, ∀ hps : p ∈ s,
        if p = 2 then
          (e p = 2 → a ≡ 1 [ZMOD 4]) ∧ (3 ≤ e p → a ≡ 1 [ZMOD 8])
        else @legendreSym p ⟨hp p hps⟩ a = 1 := by
  have hm (p : ℕ) (hps : p ∈ s) : (p : ℤ) ^ e p ≠ 0 :=
    pow_ne_zero _ (by exact_mod_cast (hp p hps).ne_zero)
  have hn : (∏ p ∈ s, (p : ℤ) ^ e p) ≠ 0 := Finset.prod_ne_zero_iff.mpr hm
  have hcop (p : ℕ) (hps : p ∈ s) (q : ℕ) (hqs : q ∈ s) (hpq : p ≠ q) :
      DivisibilityTheoryInTheIntegers.gcd ((p : ℤ) ^ e p) ((q : ℤ) ^ e q) = 1 := by
    have hg := FermatsTheorem.gcd_distinct_primes p q
      (isPrime_of_prime p (hp p hps)) (isPrime_of_prime q (hp q hqs)) hpq
    have hc := (EulersGeneralizationOfFermatsTheorem.coprime_iff_gcd_eq_one p q
      (hp p hps).pos).mpr hg
    have hc' := (hc.pow_left (e p)).pow_right (e q)
    rw [← Nat.cast_pow, ← Nat.cast_pow, gcd_natCast _ _ (pow_pos (hp q hqs).pos _)]
    exact Nat.coprime_iff_gcd_eq_one.mp hc'
  have hnot (p : ℕ) (hps : p ∈ s) : ¬(p : ℤ) ∣ a := by
    intro hd
    have hdp : (p : ℤ) ∣ ∏ q ∈ s, (q : ℤ) ^ e q :=
      dvd_trans (dvd_pow_self _ (he p hps).ne') (Finset.dvd_prod_of_mem _ hps)
    obtain ⟨_, _, _, _, hcommon⟩ :=
      DivisibilityTheoryInTheIntegers.gcd_spec a (∏ q ∈ s, (q : ℤ) ^ e q) (Or.inr hn)
    have hh := hcommon p hd hdp
    rw [ha, Nat.cast_one] at hh
    have hh' := Nat.eq_one_of_dvd_one (Int.natCast_dvd_natCast.mp hh)
    have := (hp p hps).two_le
    omega
  rw [exists_square_prod_iff s (fun p => (p : ℤ) ^ e p) a hm hcop]
  apply forall_congr'
  intro p
  apply forall_congr'
  intro hps
  let : Fact p.Prime := ⟨hp p hps⟩
  by_cases htwo : p = 2
  · subst p
    rw [ite_eq_left rfl]
    simp only [Nat.cast_ofNat]
    have ho : Odd a := by
      have h := hnot 2 hps
      have hm := Int.emod_nonneg a (by decide : (2 : ℤ) ≠ 0)
      have ht := Int.emod_lt_of_pos a (by decide : (0 : ℤ) < 2)
      apply Int.odd_iff.mpr
      have hne : a % 2 ≠ 0 := by
        intro hz
        apply h
        apply (modEq_zero_iff 2 a).mp
        change a % 2 = 0 % 2
        simpa only [Int.zero_emod] using hz
      omega
    rcases (by have := he 2 hps; omega : e 2 = 1 ∨ e 2 = 2 ∨ 3 ≤ e 2) with h | h | h
    · rw [h, pow_one]
      exact iff_of_true (exists_square_mod_two a ho) ⟨by omega, by omega⟩

    · rw [h]
      have hf := exists_square_mod_four_iff a ho
      change (∃ x : ℤ, x ^ 2 ≡ a [ZMOD 4]) ↔ _
      constructor
      · intro hx
        exact ⟨fun _ => hf.mp hx, by omega⟩
      · intro hx
        exact hf.mpr (hx.1 rfl)

    · rw [exists_square_two_pow_iff a ho (e 2) h]
      exact ⟨fun h8 => ⟨by omega, fun _ => h8⟩, fun hs => hs.2 h⟩

  · rw [ite_eq_right htwo]
    exact exists_square_prime_pow_iff p htwo a (hnot p hps) (e p) (he p hps)

end ElementaryNumberTheory.TheQuadraticReciprocityLaw
