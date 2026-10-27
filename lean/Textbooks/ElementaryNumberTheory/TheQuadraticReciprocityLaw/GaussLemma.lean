import Textbooks.ElementaryNumberTheory.TheQuadraticReciprocityLaw.LegendreSymbol
import Mathlib.Data.ZMod.ValMinAbs

namespace ElementaryNumberTheory.TheQuadraticReciprocityLaw

open scoped BigOperators

variable {p : ℕ} [Fact p.Prime]

/-- Definition: the positive representatives in the lower half of the residue system. -/
def halfResidues (p : ℕ) : Finset ℕ := Finset.Ico 1 (p / 2 + 1)

/-- Definition: the number of multiples in the half-system whose remainders exceed p/2. -/
def gaussCount (p : ℕ) (a : ℤ) : ℕ :=
  ((halfResidues p).filter fun k : ℕ => p / 2 < ((a : ZMod p) * (k : ZMod p)).val).card

/-- Definition: the permutation of the half-system given by signed absolute remainders. -/
private noncomputable def halfAbsEquiv (hp : p ≠ 2) (a : ZMod p) (ha : a ≠ 0) :
    {k // k ∈ halfResidues p} ≃ {k // k ∈ halfResidues p} := by
  classical
  have hb {k : ℕ} (hk : k ∈ halfResidues p) : 0 < k ∧ k ≤ p / 2 ∧ k < p := by
    have := Finset.mem_Ico.mp hk
    have := Nat.div_lt_self (Fact.out : p.Prime).pos (by decide : 1 < 2)
    omega
  have hcast {k : ℕ} (hk : k ∈ halfResidues p) : (k : ZMod p) ≠ 0 := by
    intro h
    have hd := (ZMod.natCast_eq_zero_iff k p).mp h
    have := Nat.le_of_dvd (hb hk).1 hd
    have := (hb hk).2.2
    omega
  let f : {k // k ∈ halfResidues p} → {k // k ∈ halfResidues p} := fun i =>
    ⟨(a * i.val : ZMod p).valMinAbs.natAbs, Finset.mem_Ico.mpr ⟨by
      apply Nat.pos_of_ne_zero
      intro h
      have hz := (ZMod.valMinAbs_eq_zero _).mp (Int.natAbs_eq_zero.mp h)
      exact mul_ne_zero ha (hcast i.property) hz,
      Nat.lt_succ_of_le (ZMod.natAbs_valMinAbs_le _)⟩⟩
  have hi : Function.Injective f := by
    intro i j hij
    have he := ZMod.natAbs_valMinAbs_eq_natAbs_valMinAbs.mp (congrArg Subtype.val hij)
    rcases he with he | he
    · have hij' := mul_left_cancel₀ ha he
      apply Subtype.ext
      simpa only [ZMod.val_cast_of_lt (hb i.property).2.2,
        ZMod.val_cast_of_lt (hb j.property).2.2] using congrArg ZMod.val hij'

    · have hz : a * ((i.val + j.val : ℕ) : ZMod p) = 0 := by
        rw [Nat.cast_add, mul_add, he, neg_add_cancel]
      have hd := (ZMod.natCast_eq_zero_iff (i.val + j.val) p).mp
        ((mul_eq_zero.mp hz).resolve_left ha)
      have hle := Nat.le_of_dvd (by have := (hb i.property).1; omega) hd
      have hi := (hb i.property).2.1
      have hj := (hb j.property).2.1
      have ho := Nat.odd_iff.mp ((Fact.out : p.Prime).odd_of_ne_two hp)
      omega
  exact Equiv.ofBijective f ((Fintype.bijective_iff_injective_and_card f).mpr ⟨hi, rfl⟩)

/-- Lemma: taking signed absolute remainders preserves the product of the half-system. -/
private theorem prod_halfAbs (hp : p ≠ 2) (a : ZMod p) (ha : a ≠ 0) :
    (∏ k ∈ halfResidues p, ((a * k).valMinAbs.natAbs : ZMod p)) =
      ∏ k ∈ halfResidues p, (k : ZMod p) := by
  have he := (halfAbsEquiv hp a ha).prod_comp
    (fun k : {k // k ∈ halfResidues p} => (k.val : ZMod p))
  change (∏ k : {k // k ∈ halfResidues p}, ((a * k.val).valMinAbs.natAbs : ZMod p)) =
    ∏ k : {k // k ∈ halfResidues p}, (k.val : ZMod p) at he
  rw [Finset.prod_coe_sort
    (s := halfResidues p) (f := fun k : ℕ => ((a * k).valMinAbs.natAbs : ZMod p)),
    Finset.prod_coe_sort (s := halfResidues p) (f := fun k : ℕ => (k : ZMod p))] at he
  exact he

/-- Theorem: Gauss's lemma computes the Legendre symbol by the number of upper remainders. -/
theorem gauss_lemma (hp : p ≠ 2) (a : ℤ) (ha : (a : ZMod p) ≠ 0) :
    legendreSym p a = (-1 : ℤ) ^ gaussCount p a := by
  classical
  let P : ZMod p := ∏ k ∈ halfResidues p, (k : ZMod p)
  have hP : P ≠ 0 := by
    apply Finset.prod_ne_zero_iff.mpr
    intro k hk hzero
    have hk := Finset.mem_Ico.mp hk
    have hd := (ZMod.natCast_eq_zero_iff k p).mp hzero
    have := Nat.le_of_dvd (by omega : 0 < k) hd
    have := Nat.div_lt_self (Fact.out : p.Prime).pos (by decide : 1 < 2)
    omega
  have hterm (k : ℕ) : (a : ZMod p) * k =
      (if p / 2 < ((a : ZMod p) * k).val then -1 else 1) *
        (((a : ZMod p) * k).valMinAbs.natAbs : ZMod p) := by
    rw [ZMod.natCast_natAbs_valMinAbs]
    split_ifs <;> first | omega | ring
  have hprod : (a : ZMod p) ^ (p / 2) * P =
      (-1 : ZMod p) ^ gaussCount p a * P := by
    calc
      _ = ∏ k ∈ halfResidues p, ((a : ZMod p) * k) := by
        rw [Finset.prod_mul_distrib, Finset.prod_const]
        simp only [halfResidues, Nat.card_Ico, Nat.add_sub_cancel, P]
      _ = (∏ k ∈ halfResidues p,
          if p / 2 < ((a : ZMod p) * k).val then (-1 : ZMod p) else 1) *
          ∏ k ∈ halfResidues p, (((a : ZMod p) * k).valMinAbs.natAbs : ZMod p) := by
        rw [Finset.prod_congr rfl (fun k _ => hterm k), Finset.prod_mul_distrib]
      _ = _ := by
        rw [prod_halfAbs hp _ ha]
        simp only [Finset.prod_ite, Finset.prod_const, one_pow, mul_one, gaussCount, P]
  apply sign_eq_of_cast_eq hp (legendreSym_eq_one_or_neg_one ha) (neg_one_pow_eq_or ℤ _)
  rw [legendreSym_eq_pow hp, Int.cast_pow, Int.cast_neg, Int.cast_one]
  exact mul_right_cancel₀ hP hprod

/-- Lemma: the absolute-remainder permutation also preserves the sum of the half-system. -/
private theorem sum_halfAbs (hp : p ≠ 2) (a : ZMod p) (ha : a ≠ 0) :
    (∑ k ∈ halfResidues p, (a * k).valMinAbs.natAbs) = ∑ k ∈ halfResidues p, k := by
  have he := (halfAbsEquiv hp a ha).sum_comp
    (fun k : {k // k ∈ halfResidues p} => k.val)
  change (∑ k : {k // k ∈ halfResidues p}, (a * k.val).valMinAbs.natAbs) =
    ∑ k : {k // k ∈ halfResidues p}, k.val at he
  rw [Finset.sum_coe_sort (s := halfResidues p) (f := fun k : ℕ => (a * k).valMinAbs.natAbs),
    Finset.sum_coe_sort (s := halfResidues p) (f := fun k : ℕ => k)] at he
  exact he

/-- Lemma: for an odd numerator, Gauss's count has the parity of the floor sum. -/
theorem gaussCount_mod_two (hp : p ≠ 2) (a : ℕ) (haodd : Odd a)
    (ha : (a : ZMod p) ≠ 0) :
    gaussCount p a % 2 = (∑ k ∈ halfResidues p, k * a / p) % 2 := by
  classical
  have hp2 : (p : ZMod 2) = 1 := by
    exact (ZMod.natCast_eq_natCast_iff _ _ 2).mpr
      (Nat.odd_iff.mp ((Fact.out : p.Prime).odd_of_ne_two hp))
  have ha2 : (a : ZMod 2) = 1 :=
    (ZMod.natCast_eq_natCast_iff _ _ 2).mpr (Nat.odd_iff.mp haodd)
  have hterm (k : ℕ) :
      (((a : ZMod p) * k).val : ZMod 2) =
        (((a : ZMod p) * k).valMinAbs.natAbs : ZMod 2) +
          if p / 2 < ((a : ZMod p) * k).val then 1 else 0 := by
    let r := ((a : ZMod p) * (k : ZMod p)).val
    have hr := ZMod.val_lt ((a : ZMod p) * (k : ZMod p))
    rw [ZMod.valMinAbs_natAbs_eq_min]
    by_cases h : p / 2 < r
    · rw [ite_eq_left h, min_eq_right (by omega : p - r ≤ r), Nat.cast_sub (by omega), hp2]
      simp only [sub_eq_add_neg, ZMod.neg_eq_self_mod_two]
      change (r : ZMod 2) = 1 + r + 1
      calc
        (r : ZMod 2) = r + ((1 : ZMod 2) + 1) := by
          rw [show (1 : ZMod 2) + 1 = 0 by decide, add_zero]
        _ = _ := by ring

    · rw [ite_eq_right h, min_eq_left (by omega : r ≤ p - r), add_zero]
  have hsum := congrArg (fun n : ℕ => (n : ZMod 2)) (sum_halfAbs hp (a : ZMod p) ha)
  simp only [Nat.cast_sum] at hsum
  have hdecomp (k : ℕ) : (k : ZMod 2) =
      (((a : ZMod p) * k).val : ZMod 2) + (k * a / p : ℕ) := by
    have h := congrArg (fun n : ℕ => (n : ZMod 2)) (Nat.mod_add_div (k * a) p)
    simp only [Nat.cast_add, Nat.cast_mul, hp2, ha2, mul_one, one_mul] at h
    simpa only [← Nat.cast_mul, ZMod.val_natCast, Nat.mul_comm] using h.symm
  have he : (gaussCount p a : ZMod 2) = (∑ k ∈ halfResidues p, k * a / p : ℕ) := by
    have hs := Finset.sum_congr (s₁ := halfResidues p) rfl (fun k _ => hdecomp k)
    simp only [hterm, Finset.sum_add_distrib] at hs
    rw [hsum] at hs
    have hc : (∑ k ∈ halfResidues p,
        if p / 2 < ((a : ZMod p) * k).val then (1 : ZMod 2) else 0) = gaussCount p a := by
      simp only [Finset.sum_boole, gaussCount, Int.cast_natCast]
    rw [hc] at hs
    have hh : (gaussCount p a : ZMod 2) +
        (∑ k ∈ halfResidues p, ((k * a / p : ℕ) : ZMod 2)) = 0 := by
      exact add_left_cancel (by simpa only [add_assoc, add_zero] using hs.symm)
    simpa only [Nat.cast_sum, ZMod.neg_eq_self_mod_two] using eq_neg_of_add_eq_zero_left hh
  exact (ZMod.natCast_eq_natCast_iff _ _ 2).mp he

/-- Theorem: the floor-sum form of Gauss's lemma for odd numerators. -/
theorem eisenstein_lemma (hp : p ≠ 2) (a : ℕ) (haodd : Odd a) (ha : (a : ZMod p) ≠ 0) :
    legendreSym p a = (-1 : ℤ) ^ ∑ k ∈ halfResidues p, k * a / p := by
  rw [gauss_lemma hp a (by simpa only [Int.cast_natCast] using ha)]
  conv_lhs => rw [neg_one_pow_eq_pow_mod_two]
  conv_rhs => rw [neg_one_pow_eq_pow_mod_two]
  rw [gaussCount_mod_two hp a haodd ha]

end ElementaryNumberTheory.TheQuadraticReciprocityLaw
