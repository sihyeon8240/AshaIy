import Textbooks.ElementaryNumberTheory.EulersGeneralizationOfFermatsTheorem.Totient
import Textbooks.ElementaryNumberTheory.DivisibilityTheoryInTheIntegers.LeastCommonMultiple

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

open scoped Classical
open NumberTheoreticFunctions EulersGeneralizationOfFermatsTheorem

/-- Lemma: the common-divisor characterization translates the local gcd to natural arithmetic. -/
theorem gcd_natCast (k m : ℕ) (hm : 0 < m) :
    DivisibilityTheoryInTheIntegers.gcd k m = Nat.gcd k m := by
  have hmz : (m : ℤ) ≠ 0 := by exact_mod_cast hm.ne'
  obtain ⟨_, hdk, hdm, _, hgreatest⟩ := DivisibilityTheoryInTheIntegers.gcd_spec k m (Or.inr hmz)

  apply Nat.dvd_antisymm
  · exact Nat.dvd_gcd (Int.natCast_dvd_natCast.mp hdk) (Int.natCast_dvd_natCast.mp hdm)
  · exact Int.natCast_dvd_natCast.mp (hgreatest (Nat.gcd k m)
      (Int.natCast_dvd_natCast.mpr (Nat.gcd_dvd_left k m))
      (Int.natCast_dvd_natCast.mpr (Nat.gcd_dvd_right k m)))

/-- Lemma: the same natural gcd translation when the first input is positive. -/
theorem gcd_natCast_of_pos_left (k m : ℕ) (hk : 0 < k) :
    DivisibilityTheoryInTheIntegers.gcd k m = Nat.gcd k m := by
  rw [DivisibilityTheoryInTheIntegers.gcd_eq_of_common_divisors k m m k (fun _ => and_comm),
    gcd_natCast m k hk, Nat.gcd_comm]

/-- Lemma: the book's Euclid lemma cancels a coprime natural factor. -/
theorem nat_dvd_of_dvd_mul_of_coprime (a b c : ℕ) (ha : 0 < a)
    (hc : a.Coprime b) (hd : a ∣ b * c) : a ∣ c := by
  have hg := (coprime_iff_gcd_eq_one a b ha).mp hc
  have h := DivisibilityTheoryInTheIntegers.dvd_of_dvd_mul_of_coprime a b c hg
    (by exact_mod_cast hd)
  exact Int.natCast_dvd_natCast.mp h

/-- Lemma: the book's product-of-coprime-divisors lemma in natural arithmetic. -/
theorem nat_mul_dvd_of_coprime (a b c : ℕ) (ha : 0 < a)
    (hc : a.Coprime b) (hd : a ∣ c) (he : b ∣ c) : a * b ∣ c := by
  have h := DivisibilityTheoryInTheIntegers.mul_dvd_of_coprime a b c
    ((coprime_iff_gcd_eq_one a b ha).mp hc)
    (Int.natCast_dvd_natCast.mpr hd) (Int.natCast_dvd_natCast.mpr he)
  exact_mod_cast h

/-- Lemma: the book's Euclid lemma identifies a prime divisor of a finite product. -/
theorem prime_dvd_finset_prod (p : ℕ) (hp : PrimesAndTheirDistribution.isPrime p)
    (s : Finset ℕ) (f : ℕ → ℕ) (h : p ∣ s.prod f) : ∃ q ∈ s, p ∣ f q := by
  induction s using Finset.induction_on with
  | empty =>
    rw [Finset.prod_empty] at h
    have := Nat.eq_one_of_dvd_one h
    have := hp.1
    omega

  | @insert a s has ih =>
    rw [Finset.prod_insert has] at h
    rcases PrimesAndTheirDistribution.prime_dvd_mul_nat p (f a) (s.prod f) hp h with ha | hs
    · exact ⟨a, Finset.mem_insert_self a s, ha⟩
    · obtain ⟨q, hq, hpq⟩ := ih hs
      exact ⟨q, Finset.mem_insert_of_mem hq, hpq⟩

/-- Lemma: a prime divisor belongs to the support of the book's exponent vector. -/
theorem prime_mem_primeExponents_support (p n : ℕ) (hp : PrimesAndTheirDistribution.isPrime p)
    (hn : 0 < n) (hd : p ∣ n) : p ∈ (primeExponents n).support := by
  have hp0 : 0 < p := by
    have := hp.1
    omega
  have he : primeExponents p = Finsupp.single p 1 := by
    simpa only [pow_one] using primeExponents_prime_pow p 1 hp
  have hle := (dvd_iff_primeExponents_le p n hp0 hn).mp hd
  rw [he] at hle
  have h := hle p
  simp only [Finsupp.single_eq_same] at h
  exact Finsupp.mem_support_iff.mpr (by omega)

/-- Lemma: prime-supported exponent vectors with disjoint supports have coprime values. -/
theorem coprime_factorValues_of_disjoint (e f : ℕ →₀ ℕ)
    (he : ∀ p ∈ e.support, PrimesAndTheirDistribution.isPrime p)
    (hf : ∀ p ∈ f.support, PrimesAndTheirDistribution.isPrime p)
    (hdis : Disjoint e.support f.support) : (factorValue e).Coprime (factorValue f) := by
  have hepos := factorValue_pos e he
  have hfpos := factorValue_pos f hf
  have heu : primeExponents (factorValue e) = e := (primeExponents_unique _ hepos e he rfl).symm
  have hfu : primeExponents (factorValue f) = f := (primeExponents_unique _ hfpos f hf rfl).symm
  apply (coprime_iff_gcd_eq_one (factorValue e) (factorValue f) hepos).mpr
  let g := DivisibilityTheoryInTheIntegers.gcd (factorValue e) (factorValue f)
  obtain ⟨hgpos, hge, hgf, _, _⟩ := DivisibilityTheoryInTheIntegers.gcd_spec
    (factorValue e) (factorValue f) (Or.inl (by exact_mod_cast hepos.ne'))
  by_contra hg1
  have hg : 1 < g := by omega
  obtain ⟨l, hl, hprod⟩ := PrimesAndTheirDistribution.exists_prime_factors g (by omega)
  have hlne : l ≠ [] := by
    intro h
    rw [h] at hprod
    simp only [List.prod_nil] at hprod
    omega
  obtain ⟨p, hp⟩ := List.exists_mem_of_ne_nil l hlne
  have hpprime := hl p hp
  have hpd : p ∣ g := hprod ▸ List.dvd_prod hp
  have hp0 : 0 < p := by
    have := hpprime.1
    omega
  have hpe := (dvd_iff_primeExponents_le p (factorValue e) hp0 hepos).mp
    (hpd.trans (Int.natCast_dvd_natCast.mp hge))
  have hpf := (dvd_iff_primeExponents_le p (factorValue f) hp0 hfpos).mp
    (hpd.trans (Int.natCast_dvd_natCast.mp hgf))
  have hpp : primeExponents p = Finsupp.single p 1 := by
    simpa only [pow_one] using primeExponents_prime_pow p 1 hpprime
  rw [hpp, heu] at hpe
  rw [hpp, hfu] at hpf
  have hpepos : 0 < e p := by
    have h := hpe p
    simp only [Finsupp.single_eq_same] at h
    omega
  have hpfpos : 0 < f p := by
    have h := hpf p
    simp only [Finsupp.single_eq_same] at h
    omega

  exact (Finset.disjoint_left.mp hdis) (Finsupp.mem_support_iff.mpr hpepos.ne')
    (Finsupp.mem_support_iff.mpr hpfpos.ne')

/-- Lemma: assigning each prime's larger exponent to one factor splits the local lcm
as the product of coprime divisors of the two inputs. -/
theorem exists_coprime_lcm_factors (a b : ℕ) (ha : 0 < a) (hb : 0 < b) :
    ∃ u v : ℕ, 0 < u ∧ 0 < v ∧ u ∣ a ∧ v ∣ b ∧ u.Coprime v ∧
      u * v = DivisibilityTheoryInTheIntegers.lcm a b := by
  let e := primeExponents a
  let f := primeExponents b
  let u := e.filter (fun p => f p ≤ e p)
  let v := f.filter (fun p => ¬f p ≤ e p)
  have he := (primeExponents_spec a ha).1
  have hf := (primeExponents_spec b hb).1
  have huprime : ∀ p ∈ u.support, PrimesAndTheirDistribution.isPrime p := by
    intro p hp
    exact he p (Finset.mem_of_mem_filter p (by simpa only [u, Finsupp.support_filter] using hp))
  have hvprime : ∀ p ∈ v.support, PrimesAndTheirDistribution.isPrime p := by
    intro p hp
    exact hf p (Finset.mem_of_mem_filter p (by simpa only [v, Finsupp.support_filter] using hp))
  have hu0 := factorValue_pos u huprime
  have hv0 := factorValue_pos v hvprime
  have huval : primeExponents (factorValue u) = u :=
    (primeExponents_unique _ hu0 u huprime rfl).symm
  have hvval : primeExponents (factorValue v) = v :=
    (primeExponents_unique _ hv0 v hvprime rfl).symm
  have huv : u + v = e ⊔ f := by
    ext p
    simp only [u, v, Finsupp.add_apply, Finsupp.filter_apply, Finsupp.sup_apply]
    by_cases h : f p ≤ e p
    · simp only [h, not_true_eq_false, ite_true, ite_false, add_zero]
      exact (max_eq_left h).symm
    · simp only [h, not_false_eq_true, ite_true, ite_false, zero_add]
      exact (max_eq_right (by omega)).symm
  have hdis : Disjoint u.support v.support := by
    apply Finset.disjoint_left.mpr
    intro p hpu hpv
    have hu := Finsupp.mem_support_iff.mp hpu
    have hv := Finsupp.mem_support_iff.mp hpv
    simp only [u, v, Finsupp.filter_apply] at hu hv
    by_cases h : f p ≤ e p
    · simp only [h, not_true_eq_false, ite_false, ne_eq, not_true_eq_false] at hv
    · simp only [h, ite_false, ne_eq, not_true_eq_false] at hu
  have hcop := coprime_factorValues_of_disjoint u v huprime hvprime hdis
  have huvd : primeExponents (factorValue u * factorValue v) = e ⊔ f := by
    rw [primeExponents_mul _ _ hu0 hv0, huval, hvval, huv]
  have hmult := mul_pos hu0 hv0
  have hda : a ∣ factorValue u * factorValue v := by
    apply (dvd_iff_primeExponents_le _ _ ha hmult).mpr
    rw [huvd]
    exact le_sup_left
  have hdb : b ∣ factorValue u * factorValue v := by
    apply (dvd_iff_primeExponents_le _ _ hb hmult).mpr
    rw [huvd]
    exact le_sup_right

  refine ⟨factorValue u, factorValue v, hu0, hv0, ?_, ?_, hcop, ?_⟩
  · apply (dvd_iff_primeExponents_le _ _ hu0 ha).mpr
    rw [huval]
    change u ≤ e
    intro p
    simp only [u, Finsupp.filter_apply]
    split_ifs <;> omega
  · apply (dvd_iff_primeExponents_le _ _ hv0 hb).mpr
    rw [hvval]
    change v ≤ f
    intro p
    simp only [v, Finsupp.filter_apply]
    split_ifs <;> omega

  · symm
    apply DivisibilityTheoryInTheIntegers.lcm_eq_of_least a b
      (by exact_mod_cast ha.ne') (by exact_mod_cast hb.ne') _ hmult
      (Int.natCast_dvd_natCast.mpr hda) (Int.natCast_dvd_natCast.mpr hdb)
    intro c hac hbc hc
    have hc0 : 0 < c.toNat := by omega
    have hceq : (c.toNat : ℤ) = c := Int.toNat_of_nonneg hc.le
    have hca : a ∣ c.toNat := Int.natCast_dvd_natCast.mp (hceq.symm ▸ hac)
    have hcb : b ∣ c.toNat := Int.natCast_dvd_natCast.mp (hceq.symm ▸ hbc)
    have hle : e ⊔ f ≤ primeExponents c.toNat := sup_le
      ((dvd_iff_primeExponents_le a c.toNat ha hc0).mp hca)
      ((dvd_iff_primeExponents_le b c.toNat hb hc0).mp hcb)
    have hd : factorValue u * factorValue v ∣ c.toNat := by
      apply (dvd_iff_primeExponents_le _ _ hmult hc0).mpr
      rwa [huvd]
    have hbound := Nat.le_of_dvd hc0 hd
    have hzbound : ((factorValue u * factorValue v : ℕ) : ℤ) ≤ c.toNat := by
      exact_mod_cast hbound
    rwa [hceq] at hzbound

end ElementaryNumberTheory.PrimitiveRootsAndIndices
