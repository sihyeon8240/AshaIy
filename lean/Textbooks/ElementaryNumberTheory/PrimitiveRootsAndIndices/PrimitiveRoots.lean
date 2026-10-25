import Textbooks.ElementaryNumberTheory.PrimitiveRootsAndIndices.Orders

namespace ElementaryNumberTheory.PrimitiveRootsAndIndices

open scoped Classical
open EulersGeneralizationOfFermatsTheorem

/-- Lemma: one complete period consists of distinct powers. -/
theorem pow_injective_fin {G : Type*} [Group G] (r : G) (hr : 0 < orderOf r) :
    Function.Injective (fun i : Fin (orderOf r) => r ^ i.val) := by
  intro i j hij
  apply Fin.ext
  have he := (pow_eq_pow_iff_modEq r hr i.val j.val).mp hij
  simpa only [Nat.ModEq, Nat.mod_eq_of_lt i.isLt, Nat.mod_eq_of_lt j.isLt] using he

/-- Theorem: a full-order element's powers enumerate a finite group exactly once. -/
noncomputable def powersEquiv {G : Type*} [Group G] [Fintype G] (r : G)
    (hr : orderOf r = Fintype.card G) : Fin (orderOf r) ≃ G := by
  have hp : 0 < orderOf r := hr ▸ Fintype.card_pos
  have hinj := pow_injective_fin r hp
  have hsurj := (Fintype.bijective_iff_injective_and_card _).mpr
    ⟨hinj, by rw [Fintype.card_fin, hr]⟩
  exact Equiv.ofBijective (fun i => r ^ i.val) hsurj

/-- Theorem: the powers of a primitive root enumerate all reduced residue classes. -/
noncomputable def primitiveRootEquiv (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) : Fin (orderOf r) ≃ (ZMod n)ˣ := by
  apply powersEquiv r
  rw [ZMod.card_units_eq_totient]
  exact (orderOf_eq_of_primitiveRoot hr)

/-- Theorem: every unit is a unique power in one complete period of a primitive root. -/
theorem exists_unique_pow (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) (a : (ZMod n)ˣ) :
    ∃! i : Fin (orderOf r), r ^ i.val = a := by
  let e := primitiveRootEquiv n r hr
  exact ⟨e.symm a, e.apply_symm_apply a,
    fun i hi => e.injective (hi.trans (e.apply_symm_apply a).symm)⟩

/-- Lemma: the totient counts coprime exponents in a complete period. -/
theorem card_coprime_fin (m : ℕ) :
    Fintype.card {i : Fin m // i.val.Coprime m} = Nat.totient m := by
  classical
  let e : {i : Fin m // i.val.Coprime m} ≃
      {i : ℕ // i ∈ (Finset.range m).filter (Nat.Coprime m)} :=
    { toFun := fun i => ⟨i.val.val, Finset.mem_filter.mpr
        ⟨Finset.mem_range.mpr i.val.isLt, i.property.symm⟩⟩
      invFun := fun i => ⟨⟨i.val, Finset.mem_range.mp (Finset.mem_filter.mp i.property).1⟩,
        (Finset.mem_filter.mp i.property).2.symm⟩
      left_inv := fun _ => rfl
      right_inv := fun _ => rfl }
  rw [Fintype.card_congr e, Fintype.card_coe]
  rfl

/-- Theorem: a modulus with a primitive root has phi(phi(n)) primitive residue classes. -/
theorem card_primitiveRoots (n : ℕ) [NeZero n] (r : (ZMod n)ˣ)
    (hr : IsPrimitiveRoot r (Nat.totient n)) :
    Fintype.card {a : (ZMod n)ˣ // IsPrimitiveRoot a (Nat.totient n)} =
      Nat.totient (Nat.totient n) := by
  classical
  let e := primitiveRootEquiv n r hr
  have ho : orderOf r = Nat.totient n := (orderOf_eq_of_primitiveRoot hr)
  have hp := unit_orderOf_pos n r
  have he (i : Fin (orderOf r)) :
      i.val.Coprime (orderOf r) ↔ IsPrimitiveRoot (e i) (Nat.totient n) := by
    change i.val.Coprime (orderOf r) ↔ IsPrimitiveRoot (r ^ i.val) (Nat.totient n)
    rw [isPrimitiveRoot_iff_orderOf _ _, ← ho, orderOf_pow_eq_iff r hp]
  rw [← Fintype.card_congr (e.subtypeEquiv he), card_coprime_fin, ho]

/-- Lemma: the least positive period characterization of primitive roots. -/
theorem isPrimitiveRoot_iff_minimal (n : ℕ) [NeZero n] (r : (ZMod n)ˣ) :
    IsPrimitiveRoot r (Nat.totient n) ↔
      r ^ Nat.totient n = 1 ∧
        ∀ j : ℕ, 0 < j → j < Nat.totient n → r ^ j ≠ 1 := by
  rw [isPrimitiveRoot_iff_orderOf _ _, orderOf_eq_iff (totient_pos _ (NeZero.pos n))]
  exact and_congr_right fun _ => ⟨fun h j hj hlt => h j hlt hj,
    fun h j hlt hj => h j hj hlt⟩

end ElementaryNumberTheory.PrimitiveRootsAndIndices
