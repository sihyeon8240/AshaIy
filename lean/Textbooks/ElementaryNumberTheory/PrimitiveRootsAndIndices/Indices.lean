import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.PrimitiveRoots
import Textbooks.ElementaryNumberTheory.TheTheoryOfCongruences.LinearCongruences

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

open scoped Classical
open EulersGeneralizationOfFermatsTheorem

/-- Definition: the index is the positive representative of the exponent of a unit.
The identity has index phi(n), rather than zero. -/
noncomputable def index (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a : (ZMod n)ˣ) : ℕ :=
  let i := (primitiveRootEquiv n r hr).symm a
  if i.val = 0 then Nat.totient n else i.val

/-- Theorem: every index lies between one and phi(n), inclusively. -/
theorem index_bounds (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a : (ZMod n)ˣ) :
    0 < index n r hr a ∧ index n r hr a ≤ Nat.totient n := by
  let i := (primitiveRootEquiv n r hr).symm a
  have hi : i.val < Nat.totient n := by
    rw [(orderOf_eq_of_primitiveRoot hr).symm]
    exact i.isLt
  change 0 < (if i.val = 0 then Nat.totient n else i.val) ∧
    (if i.val = 0 then Nat.totient n else i.val) ≤ Nat.totient n

  split_ifs with hz
  · exact ⟨Nat.totient_pos.mpr (NeZero.pos n), le_refl _⟩
  · exact ⟨Nat.pos_of_ne_zero hz, hi.le⟩

/-- Theorem: raising the primitive root to the index recovers the unit. -/
theorem pow_index (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a : (ZMod n)ˣ) :
    r ^ index n r hr a = a := by
  let e := primitiveRootEquiv n r hr
  let i := e.symm a
  have he : r ^ i.val = a := e.apply_symm_apply a
  change r ^ (if i.val = 0 then Nat.totient n else i.val) = a

  split_ifs with hz
  · rw [hr.pow_eq_one]
    simpa only [hz, pow_zero] using he
  · exact he

/-- Lemma: the index of a power is its exponent modulo phi(n). -/
theorem index_of_pow (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (j : ℕ) :
    index n r hr (r ^ j) ≡ j [MOD Nat.totient n] := by
  have he := (pow_eq_pow_iff_modEq r (unit_orderOf_pos n r) _ j).mp (pow_index n r hr (r ^ j))
  rwa [(orderOf_eq_of_primitiveRoot hr)] at he

/-- Theorem: the index is the smallest positive exponent representing the unit. -/
theorem index_le_of_pow_eq (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a : (ZMod n)ˣ)
    (j : ℕ) (hj : 0 < j) (he : r ^ j = a) : index n r hr a ≤ j := by
  obtain ⟨hpos, hbound⟩ := index_bounds n r hr a
  have hmod : index n r hr a ≡ j [MOD Nat.totient n] := by
    rw [← he]
    exact index_of_pow n r hr j
  by_contra hlt
  have hjlt : j < Nat.totient n := by omega

  by_cases hmax : index n r hr a = Nat.totient n
  · simp only [Nat.ModEq, hmax, Nat.mod_self, Nat.mod_eq_of_lt hjlt] at hmod
    omega
  · have hidxlt : index n r hr a < Nat.totient n := by omega
    simp only [Nat.ModEq, Nat.mod_eq_of_lt hidxlt, Nat.mod_eq_of_lt hjlt] at hmod
    omega

/-- Lemma: a positive exponent within one period determines the exact index. -/
theorem index_eq_of_pow_eq (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a : (ZMod n)ˣ)
    (j : ℕ) (hj : 0 < j) (hbound : j ≤ Nat.totient n) (he : r ^ j = a) :
    index n r hr a = j := by
  have hle := index_le_of_pow_eq n r hr a j hj he
  obtain ⟨hpos, _⟩ := index_bounds n r hr a
  have hmod : index n r hr a ≡ j [MOD Nat.totient n] := by
    rw [← he]
    exact index_of_pow n r hr j

  by_cases hjlt : j < Nat.totient n
  · have hilt : index n r hr a < Nat.totient n := by omega
    simpa only [Nat.ModEq, Nat.mod_eq_of_lt hilt, Nat.mod_eq_of_lt hjlt] using hmod
  · have hjmax : j = Nat.totient n := by omega
    by_contra hne
    have hilt : index n r hr a < Nat.totient n := by omega
    simp only [Nat.ModEq, hjmax, Nat.mod_eq_of_lt hilt, Nat.mod_self] at hmod
    omega
/-- Theorem: the index of a product is the sum of the indices modulo phi(n). -/
theorem index_mul (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a b : (ZMod n)ˣ) :
    index n r hr (a * b) ≡ index n r hr a + index n r hr b [MOD Nat.totient n] := by
  have he : r ^ index n r hr (a * b) = r ^ (index n r hr a + index n r hr b) := by
    rw [pow_index, pow_add, pow_index, pow_index]

  have hmod := (pow_eq_pow_iff_modEq r (unit_orderOf_pos n r) _ _).mp he
  rwa [(orderOf_eq_of_primitiveRoot hr)] at hmod

/-- Theorem: the index of a power is the exponent times the index modulo phi(n). -/
theorem index_pow (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a : (ZMod n)ˣ) (k : ℕ) :
    index n r hr (a ^ k) ≡ k * index n r hr a [MOD Nat.totient n] := by
  have he : r ^ index n r hr (a ^ k) = r ^ (k * index n r hr a) := by
    rw [pow_index, mul_comm k, pow_mul, pow_index]

  have hmod := (pow_eq_pow_iff_modEq r (unit_orderOf_pos n r) _ _).mp he
  rwa [(orderOf_eq_of_primitiveRoot hr)] at hmod

/-- Corollary: the identity has index zero modulo phi(n). -/
theorem index_one_modEq (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) :
    index n r hr 1 ≡ 0 [MOD Nat.totient n] := by
  simpa only [pow_zero] using index_of_pow n r hr 0

/-- Corollary: the primitive root has index one modulo phi(n). -/
theorem index_self_modEq (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) :
    index n r hr r ≡ 1 [MOD Nat.totient n] := by
  simpa only [pow_one] using index_of_pow n r hr 1

/-- Theorem: a power equation is the corresponding linear index congruence. -/
theorem pow_eq_iff_index (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (x a : (ZMod n)ˣ) (k : ℕ) :
    x ^ k = a ↔ k * index n r hr x ≡ index n r hr a [MOD Nat.totient n] := by
  have he : x ^ k = a ↔ r ^ (k * index n r hr x) = r ^ index n r hr a := by
    rw [mul_comm k, pow_mul, pow_index, pow_index]
  rw [he, pow_eq_pow_iff_modEq r (unit_orderOf_pos n r), (orderOf_eq_of_primitiveRoot hr)]

/-- Definition: indices modulo phi(n) identify units with exponent residue classes. -/
noncomputable def indexEquiv (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) : (ZMod n)ˣ ≃ ZMod (Nat.totient n) := by
  have : NeZero (Nat.totient n) := ⟨(Nat.totient_pos.mpr (NeZero.pos n)).ne'⟩
  refine
    { toFun := fun a => (index n r hr a : ZMod (Nat.totient n))
      invFun := fun i => r ^ i.val
      left_inv := ?_
      right_inv := ?_ }
  · intro a
    change r ^ (index n r hr a : ZMod (Nat.totient n)).val = a
    have hm : (index n r hr a % Nat.totient n) ≡ index n r hr a [MOD orderOf r] := by
      rw [(orderOf_eq_of_primitiveRoot hr)]
      exact Nat.mod_modEq _ _
    rw [ZMod.val_natCast, (pow_eq_pow_iff_modEq r (unit_orderOf_pos n r) _ _).mpr hm,
      pow_index]

  · intro i
    have he := (ZMod.natCast_eq_natCast_iff _ _ _).mpr (index_of_pow n r hr i.val)
    exact he.trans (ZMod.natCast_zmod_val i)

/-- Lemma: the earlier linear congruence theorem in residue-class form. -/
theorem exists_zmod_linear_iff (m : ℕ) [NeZero m] (k b : ℕ) :
    (∃ x : ZMod m, (k : ZMod m) * x = b) ↔ Nat.gcd k m ∣ b := by
  have he := TheTheoryOfCongruences.exists_linear_modEq_iff (m : ℤ) k b
  rw [gcd_natCast k m (NeZero.pos m)] at he
  constructor
  · rintro ⟨x, hx⟩
    have hcong : (k : ℤ) * (x.val : ℤ) ≡ b [ZMOD (m : ℤ)] := by
      apply (ZMod.intCast_eq_intCast_iff _ _ m).mp
      simpa only [Int.cast_mul, Int.cast_natCast, ZMod.natCast_zmod_val] using hx
    exact Int.natCast_dvd_natCast.mp (he.mp ⟨x.val, hcong⟩)

  · intro hd
    obtain ⟨x, hx⟩ := he.mpr (Int.natCast_dvd_natCast.mpr hd)
    refine ⟨x, ?_⟩
    have hcast := (ZMod.intCast_eq_intCast_iff _ _ m).mpr hx
    simpa only [Int.cast_mul, Int.cast_natCast] using hcast

/-- Theorem: x^k=a is solvable precisely when gcd(k,phi(n)) divides the index of a. -/
theorem exists_pow_eq_iff_dvd_index (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a : (ZMod n)ˣ) (k : ℕ) :
    (∃ x : (ZMod n)ˣ, x ^ k = a) ↔ Nat.gcd k (Nat.totient n) ∣ index n r hr a := by
  have : NeZero (Nat.totient n) := ⟨(Nat.totient_pos.mpr (NeZero.pos n)).ne'⟩
  let e := indexEquiv n r hr
  have hlinear (x : (ZMod n)ˣ) :
      x ^ k = a ↔ (k : ZMod (Nat.totient n)) * e x = (index n r hr a : ℕ) := by
    rw [pow_eq_iff_index n r hr]
    change k * index n r hr x ≡ index n r hr a [MOD Nat.totient n] ↔
      (k : ZMod (Nat.totient n)) * (index n r hr x : ℕ) = (index n r hr a : ℕ)
    rw [← Nat.cast_mul, ZMod.natCast_eq_natCast_iff]

  rw [← exists_zmod_linear_iff (Nat.totient n) k (index n r hr a)]
  constructor
  · rintro ⟨x, hx⟩
    exact ⟨e x, (hlinear x).mp hx⟩

  · rintro ⟨y, hy⟩
    refine ⟨e.symm y, (hlinear _).mpr ?_⟩
    rw [e.apply_symm_apply]
    exact hy

/-- Lemma: cancellation of the complementary divisor in a product divisibility relation. -/
theorem dvd_mul_div_iff (m d b : ℕ) (hm : 0 < m) (hd : d ∣ m) :
    m ∣ b * (m / d) ↔ d ∣ b := by
  have hdpos := Nat.pos_of_dvd_of_pos hd hm
  have htpos := Nat.div_pos (Nat.le_of_dvd hm hd) hdpos
  have he : d * (m / d) = m := Nat.mul_div_cancel' hd
  calc
    m ∣ b * (m / d) ↔ d * (m / d) ∣ b * (m / d) := by rw [he]
    _ ↔ d ∣ b := Nat.mul_dvd_mul_iff_right htpos

/-- Theorem: the power congruence has a solution precisely when a^(phi(n)/d)=1,
where d=gcd(k,phi(n)). -/
theorem exists_pow_eq_iff (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a : (ZMod n)ˣ) (k : ℕ) :
    (∃ x : (ZMod n)ˣ, x ^ k = a) ↔
      a ^ (Nat.totient n / Nat.gcd k (Nat.totient n)) = 1 := by
  rw [exists_pow_eq_iff_dvd_index n r hr]
  have he : a ^ (Nat.totient n / Nat.gcd k (Nat.totient n)) =
      r ^ (index n r hr a * (Nat.totient n / Nat.gcd k (Nat.totient n))) := by
    rw [pow_mul, pow_index]

  rw [he, pow_eq_one_iff_dvd_order, (orderOf_eq_of_primitiveRoot hr),
    dvd_mul_div_iff (Nat.totient n) _ _ (Nat.totient_pos.mpr (NeZero.pos n))
      (Nat.gcd_dvd_right k (Nat.totient n))]

end ElementaryNumberTheory.PrimitiveRootsAndIndices
