import Textbooks.ElementaryNumberTheory.TheQuadraticReciprocityLaw.SupplementaryLaws
import Textbooks.ElementaryNumberTheory.PrimesAndTheirDistribution.SieveOfEratosthenes

namespace ElementaryNumberTheory.TheQuadraticReciprocityLaw

open PrimesAndTheirDistribution PrimitiveRootsAndIndices

/-- Lemma: there is a prime one modulo four beyond every bound. -/
theorem exists_prime_one_mod_four_gt (B : ℕ) :
    ∃ q : ℕ, q.Prime ∧ q % 4 = 1 ∧ B < q := by
  let N := (2 * B.factorial) ^ 2 + 1
  have hN : 1 < N := by
    have := Nat.factorial_pos B
    dsimp only [N]
    nlinarith
  obtain ⟨q, hq, hd, _⟩ := exists_prime_divisor N hN
  have hqp : q.Prime := Nat.prime_def.mpr hq
  let : Fact q.Prime := ⟨hqp⟩
  have hzero : (N : ZMod q) = 0 := (ZMod.natCast_eq_zero_iff N q).mpr hd
  have hodd : q ≠ 2 := by
    intro h
    have hh : N % 2 = 0 := Nat.mod_eq_zero_of_dvd (h ▸ hd)
    have hNodd : N % 2 = 1 := Nat.odd_iff.mp ⟨2 * B.factorial ^ 2, by dsimp only [N]; ring⟩
    omega
  have hroot : (2 * (B.factorial : ℤ)) ^ 2 ≡ -1 [ZMOD (q : ℤ)] := by
    apply (TheTheoryOfCongruences.modEq_iff_dvd_sub _ _ _).mpr
    have hi := Int.natCast_dvd_natCast.mpr hd
    simpa only [N, Nat.cast_add, Nat.cast_pow, Nat.cast_mul, Nat.cast_ofNat,
      Nat.cast_one, sub_neg_eq_add] using hi
  have hmod := (FermatsTheorem.exists_square_eq_neg_one_iff q hq
    (hqp.odd_of_ne_two hodd)).mp ⟨_, hroot⟩
  refine ⟨q, hqp, hmod, ?_⟩
  by_contra hn
  have hf := factorial_multiple B q hqp.pos (by omega : q ≤ B)
  have hfzero := (ZMod.natCast_eq_zero_iff B.factorial q).mpr hf
  simp only [N, Nat.cast_add, Nat.cast_pow, Nat.cast_mul, Nat.cast_ofNat, Nat.cast_one,
    hfzero, mul_zero, zero_pow (by decide : 2 ≠ 0), zero_add] at hzero
  exact one_ne_zero hzero

/-- Theorem: infinitely many primes are one modulo four. -/
theorem infinite_primes_one_mod_four : {q : ℕ | q.Prime ∧ q % 4 = 1}.Infinite := by
  apply Set.infinite_of_forall_exists_gt
  intro B
  obtain ⟨q, hq, hmod, hgt⟩ := exists_prime_one_mod_four_gt B
  exact ⟨q, ⟨hq, hmod⟩, hgt⟩

/-- Lemma: there is a prime seven modulo eight beyond every bound. -/
theorem exists_prime_seven_mod_eight_gt (B : ℕ) :
    ∃ q : ℕ, q.Prime ∧ q % 8 = 7 ∧ B < q := by
  let N := 8 * B.factorial ^ 2 - 1
  have hfac := Nat.factorial_pos B
  have hsq := pow_pos hfac 2
  have hNeq : N + 1 = 8 * B.factorial ^ 2 := Nat.sub_add_cancel (by omega)
  have hN : 0 < N := by omega
  have hNmod : N % 8 = 7 := by omega
  obtain ⟨l, hl, hprod⟩ := exists_prime_factors N hN
  have hclass (q : ℕ) (hql : q ∈ l) : q % 8 = 1 ∨ q % 8 = 7 := by
    have hqp := Nat.prime_def.mpr (hl q hql)
    let : Fact q.Prime := ⟨hqp⟩
    have hd : q ∣ N := hprod ▸ List.dvd_prod hql
    have hzero := (ZMod.natCast_eq_zero_iff N q).mpr hd
    have he := congrArg (fun n : ℕ => (n : ZMod q)) hNeq
    simp only [Nat.cast_add, Nat.cast_one, hzero, zero_add, Nat.cast_mul,
      Nat.cast_ofNat, Nat.cast_pow] at he
    have hodd : q ≠ 2 := by
      intro h
      have hh : N % 2 = 0 := Nat.mod_eq_zero_of_dvd (h ▸ hd)
      omega
    apply (isSquare_two_iff hodd).mp
    refine ⟨4 * (B.factorial : ZMod q), ?_⟩
    linear_combination 2 * he
  have hex : ∃ q ∈ l, q % 8 = 7 := by
    by_contra h
    have hone : ∀ q ∈ l, q % 8 = 1 := by
      intro q hq
      exact (hclass q hq).resolve_right (fun he => h ⟨q, hq, he⟩)
    have hpmod : l.prod % 8 = 1 := by
      have haux : ∀ u : List ℕ, (∀ q ∈ u, q % 8 = 1) → u.prod % 8 = 1 := by
        intro u
        induction u with
        | nil => intro _; decide
        | cons q u ih =>
          intro hu
          rw [List.prod_cons, Nat.mul_mod, hu q List.mem_cons_self,
            ih (fun r hr => hu r (List.mem_cons_of_mem q hr)), one_mul]
      exact haux l hone
    rw [hprod, hNmod] at hpmod
    omega
  obtain ⟨q, hql, hmod⟩ := hex
  have hqp := Nat.prime_def.mpr (hl q hql)
  have hd : q ∣ N := hprod ▸ List.dvd_prod hql
  refine ⟨q, hqp, hmod, ?_⟩
  by_contra hn
  have hf := factorial_multiple B q hqp.pos (by omega : q ≤ B)
  have hdsq : q ∣ 8 * B.factorial ^ 2 := dvd_mul_of_dvd_right (dvd_pow hf (by decide : 2 ≠ 0)) 8
  have hd1 : q ∣ 1 := by
    have hh := Nat.dvd_sub hdsq hd
    have he : 8 * B.factorial ^ 2 - N = 1 := by omega
    rwa [he] at hh
  have := Nat.eq_one_of_dvd_one hd1
  have := hqp.two_le
  omega

/-- Theorem: infinitely many primes are seven modulo eight. -/
theorem infinite_primes_seven_mod_eight : {q : ℕ | q.Prime ∧ q % 8 = 7}.Infinite := by
  apply Set.infinite_of_forall_exists_gt
  intro B
  obtain ⟨q, hq, hmod, hgt⟩ := exists_prime_seven_mod_eight_gt B
  exact ⟨q, ⟨hq, hmod⟩, hgt⟩

end ElementaryNumberTheory.TheQuadraticReciprocityLaw
