import Textbooks.ElementaryNumberTheory.TheQuadraticReciprocityLaw.GaussLemma

namespace ElementaryNumberTheory.TheQuadraticReciprocityLaw

open scoped BigOperators

/-- Lemma: a floor counts the positive lattice ordinates below a line. -/
private theorem floor_eq_card (p q k : ℕ) (hp : 0 < p) (hk : k ≤ p / 2) :
    k * q / p = ((halfResidues q).filter fun j => j * p ≤ k * q).card := by
  have hb : k * q / p ≤ q / 2 := by
    calc
      _ ≤ p / 2 * q / p := Nat.div_le_div_right (Nat.mul_le_mul_right q hk)
      _ ≤ _ := Nat.div_mul_div_le_div _ _ _
  have he : ((halfResidues q).filter fun j => j * p ≤ k * q) =
      Finset.Ico 1 (k * q / p + 1) := by
    ext j
    simp only [Finset.mem_filter, halfResidues, Finset.mem_Ico]
    have hd : j * p ≤ k * q ↔ j ≤ k * q / p := (Nat.le_div_iff_mul_le hp).symm
    omega
  rw [he, Nat.card_Ico, Nat.add_sub_cancel]

/-- Lemma: the two floor sums partition the lattice rectangle between distinct primes. -/
theorem floor_sum_identity (p q : ℕ) [Fact p.Prime] [Fact q.Prime] (hne : p ≠ q) :
    (∑ k ∈ halfResidues p, k * q / p) + (∑ j ∈ halfResidues q, j * p / q) =
      p / 2 * (q / 2) := by
  classical
  have hq : (q : ZMod p) ≠ 0 := by
    intro h
    have hd := (ZMod.natCast_eq_zero_iff q p).mp h
    have he := (Fact.out : q.Prime).eq_one_or_self_of_dvd p hd
    have := (Fact.out : p.Prime).two_le
    omega
  have hsum (r s : ℕ) (hr : 0 < r) :
      (∑ k ∈ halfResidues r, k * s / r) =
        ∑ k ∈ halfResidues r, ∑ j ∈ halfResidues s, if j * r ≤ k * s then 1 else 0 := by
    apply Finset.sum_congr rfl
    intro k hk
    rw [floor_eq_card r s k hr (by have := Finset.mem_Ico.mp hk; omega)]
    simp only [Finset.card_eq_sum_ones, Finset.sum_filter]
  rw [hsum p q (Fact.out : p.Prime).pos, hsum q p (Fact.out : q.Prime).pos]
  conv_lhs => rhs; rw [Finset.sum_comm]
  rw [← Finset.sum_add_distrib]
  have hterm (i : ℕ) (hi : i ∈ halfResidues p) (j : ℕ) (hj : j ∈ halfResidues q) :
      (if j * p ≤ i * q then 1 else 0) + (if i * q ≤ j * p then 1 else 0) = (1 : ℕ) := by
    have hne' : j * p ≠ i * q := by
      intro he
      have hz : (i : ZMod p) * q = 0 := by
        have hh := congrArg (fun n : ℕ => (n : ZMod p)) he
        simpa only [Nat.cast_mul, ZMod.natCast_self, mul_zero] using hh.symm
      have hzero := (mul_eq_zero.mp hz).resolve_right hq
      have hd := (ZMod.natCast_eq_zero_iff i p).mp hzero
      have hi := Finset.mem_Ico.mp hi
      have hlt := Nat.div_lt_self (Fact.out : p.Prime).pos (by decide : 1 < 2)
      have hle := Nat.le_of_dvd (by omega : 0 < i) hd
      omega
    split_ifs <;> omega
  calc
    _ = ∑ i ∈ halfResidues p, ∑ j ∈ halfResidues q, 1 := by
      apply Finset.sum_congr rfl
      intro i hi
      rw [← Finset.sum_add_distrib]
      exact Finset.sum_congr rfl (fun j hj => hterm i hi j hj)
    _ = _ := by simp only [Finset.sum_const, smul_eq_mul, halfResidues, Nat.card_Ico,
      Nat.add_sub_cancel, mul_one]

/-- Theorem: quadratic reciprocity for distinct odd primes. -/
theorem quadratic_reciprocity (p q : ℕ) [Fact p.Prime] [Fact q.Prime]
    (hp : p ≠ 2) (hq : q ≠ 2) (hne : p ≠ q) :
    legendreSym p q * legendreSym q p = (-1 : ℤ) ^ (p / 2 * (q / 2)) := by
  have hcast (r s : ℕ) [Fact r.Prime] [Fact s.Prime] (hrs : r ≠ s) :
      (s : ZMod r) ≠ 0 := by
    intro h
    have hd := (ZMod.natCast_eq_zero_iff s r).mp h
    have he := (Fact.out : s.Prime).eq_one_or_self_of_dvd r hd
    have := (Fact.out : r.Prime).two_le
    omega
  rw [eisenstein_lemma hp q ((Fact.out : q.Prime).odd_of_ne_two hq) (hcast p q hne),
    eisenstein_lemma hq p ((Fact.out : p.Prime).odd_of_ne_two hp) (hcast q p hne.symm),
    ← pow_add, floor_sum_identity p q hne]

end ElementaryNumberTheory.TheQuadraticReciprocityLaw
