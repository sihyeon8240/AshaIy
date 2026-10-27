import Textbooks.ElementaryNumberTheory.TheQuadraticReciprocityLaw.LegendreSymbol

namespace ElementaryNumberTheory.TheQuadraticReciprocityLaw

open TheTheoryOfCongruences
open PrimitiveRootsAndIndices

/-- Lemma: congruences descend to every divisor of the modulus. -/
theorem modEq_of_dvd {m n a b : ℤ} (hmn : m ∣ n) (h : a ≡ b [ZMOD n]) :
    a ≡ b [ZMOD m] :=
  (modEq_iff_dvd_sub _ _ _).mpr (dvd_trans hmn ((modEq_iff_dvd_sub _ _ _).mp h))

/-- Lemma: an odd prime admits the linear correction needed to lift a nonzero square root. -/
theorem lift_square_root (p : ℕ) [Fact p.Prime] (hp : p ≠ 2) (a x : ℤ)
    (ha : ¬(p : ℤ) ∣ a) (n : ℕ) (hx : x ^ 2 ≡ a [ZMOD (p : ℤ) ^ (n + 1)]) :
    ∃ y : ℤ, y ^ 2 ≡ a [ZMOD (p : ℤ) ^ (n + 2)] ∧
      y ≡ x [ZMOD (p : ℤ) ^ (n + 1)] := by
  have hroot := modEq_of_dvd (dvd_pow_self (p : ℤ) (by omega : n + 1 ≠ 0)) hx
  have hxne : (x : ZMod p) ≠ 0 := by
    intro h
    have hh := (ZMod.intCast_eq_intCast_iff _ _ p).mpr hroot
    simp only [Int.cast_pow, h, zero_pow (by decide : 2 ≠ 0)] at hh
    exact ha ((ZMod.intCast_zmod_eq_zero_iff_dvd a p).mp hh.symm)
  obtain ⟨b, hb⟩ := (modEq_iff_dvd_sub _ _ _).mp hx
  let t : ZMod p := -(b : ZMod p) / (2 * (x : ZMod p))
  have ht : 2 * x * (t.val : ℤ) ≡ -b [ZMOD (p : ℤ)] := by
    apply (ZMod.intCast_eq_intCast_iff _ _ p).mp
    simp only [Int.cast_mul, Int.cast_ofNat, Int.cast_natCast,
      ZMod.natCast_zmod_val, Int.cast_neg]
    exact mul_div_cancel₀ _ (mul_ne_zero (two_ne_zero hp) hxne)
  obtain ⟨c, hc⟩ := (modEq_iff_dvd_sub _ _ _).mp ht
  refine ⟨x + (p : ℤ) ^ (n + 1) * t.val, ?_, ?_⟩

  · apply (modEq_iff_dvd_sub _ _ _).mpr
    refine ⟨c + (p : ℤ) ^ n * (t.val : ℤ) ^ 2, ?_⟩
    have he : x ^ 2 = a + (p : ℤ) ^ (n + 1) * b := by linarith
    have hf : 2 * x * (t.val : ℤ) + b = p * c := by linarith
    calc
      (x + (p : ℤ) ^ (n + 1) * t.val) ^ 2 - a =
          (p : ℤ) ^ (n + 1) * (2 * x * t.val + b) +
            ((p : ℤ) ^ (n + 1)) ^ 2 * (t.val : ℤ) ^ 2 := by
        nlinarith [he]
      _ = _ := by rw [hf]; simp only [pow_succ]; ring

  · apply (modEq_iff_dvd_sub _ _ _).mpr
    exact ⟨t.val, by ring⟩

/-- Theorem: a nonzero integer is a square at every positive power of an odd prime exactly
when its Legendre symbol is one. -/
theorem exists_square_prime_pow_iff (p : ℕ) [Fact p.Prime] (hp : p ≠ 2)
    (a : ℤ) (ha : ¬(p : ℤ) ∣ a) (n : ℕ) (hn : 0 < n) :
    (∃ x : ℤ, x ^ 2 ≡ a [ZMOD (p : ℤ) ^ n]) ↔ legendreSym p a = 1 := by
  have hane : (a : ZMod p) ≠ 0 := fun h => ha ((ZMod.intCast_zmod_eq_zero_iff_dvd a p).mp h)
  have hbase : (∃ x : ℤ, x ^ 2 ≡ a [ZMOD (p : ℤ)]) ↔ legendreSym p a = 1 := by
    rw [legendreSym_eq_one_iff hane]
    constructor
    · rintro ⟨x, hx⟩
      have h := (ZMod.intCast_eq_intCast_iff _ _ p).mpr hx
      refine ⟨(x : ZMod p), ?_⟩
      simpa only [Int.cast_pow, pow_two, Int.cast_mul] using h.symm

    · rintro ⟨x, hx⟩
      refine ⟨x.val, (ZMod.intCast_eq_intCast_iff _ _ p).mp ?_⟩
      simpa only [Int.cast_pow, Int.cast_natCast, ZMod.natCast_zmod_val,
        pow_two, Int.cast_mul] using hx.symm
  constructor
  · rintro ⟨x, hx⟩
    exact hbase.mp ⟨x, modEq_of_dvd (dvd_pow_self _ hn.ne') hx⟩

  · intro h
    have hiter : ∀ k : ℕ, ∃ x : ℤ, x ^ 2 ≡ a [ZMOD (p : ℤ) ^ (k + 1)] := by
      intro k
      induction k with
      | zero => simpa only [zero_add, pow_one] using hbase.mpr h
      | succ k ih =>
        obtain ⟨x, hx⟩ := ih
        obtain ⟨y, hy, _⟩ := lift_square_root p hp a x ha k hx
        exact ⟨y, hy⟩
    simpa only [Nat.sub_add_cancel hn] using hiter (n - 1)

/-- Lemma: a square congruent to an odd integer has an odd root. -/
private theorem odd_of_square_modEq {a x : ℤ} (ha : Odd a) {n : ℤ}
    (hn : (2 : ℤ) ∣ n) (hx : x ^ 2 ≡ a [ZMOD n]) : Odd x := by
  have hh := modEq_of_dvd hn hx
  have hm := Int.odd_iff.mp ha
  change x ^ 2 % 2 = a % 2 at hh
  have he := ((Int.mod_modEq x 2).pow 2).symm
  change x ^ 2 % 2 = (x % 2) ^ 2 % 2 at he
  rw [he] at hh
  have hb := Int.emod_nonneg x (by decide : (2 : ℤ) ≠ 0)
  have ht := Int.emod_lt_of_pos x (by decide : (0 : ℤ) < 2)
  apply Int.odd_iff.mpr
  rcases (by omega : x % 2 = 0 ∨ x % 2 = 1) with h | h
  · norm_num [h, hm] at hh
  · exact h

/-- Theorem: an odd integer is a square modulo two. -/
theorem exists_square_mod_two (a : ℤ) (ha : Odd a) : ∃ x : ℤ, x ^ 2 ≡ a [ZMOD 2] := by
  refine ⟨1, ?_⟩
  change 1 ^ 2 % 2 = a % 2
  rw [Int.odd_iff.mp ha]
  decide

/-- Theorem: an odd integer is a square modulo four exactly when it is one modulo four. -/
theorem exists_square_mod_four_iff (a : ℤ) (ha : Odd a) :
    (∃ x : ℤ, x ^ 2 ≡ a [ZMOD 4]) ↔ a ≡ 1 [ZMOD 4] := by
  constructor
  · rintro ⟨x, hx⟩
    have ho := odd_of_square_modEq ha (by decide : (2 : ℤ) ∣ 4) hx
    exact hx.symm.trans (modEq_of_dvd (by decide : (4 : ℤ) ∣ 8) (odd_square_modEq_one x ho))

  · intro h
    exact ⟨1, by simpa only [one_pow] using h.symm⟩

/-- Theorem: above exponent two, an odd integer is a square modulo a power of two exactly
when it is one modulo eight. -/
theorem exists_square_two_pow_iff (a : ℤ) (ha : Odd a) (n : ℕ) (hn : 3 ≤ n) :
    (∃ x : ℤ, x ^ 2 ≡ a [ZMOD (2 : ℤ) ^ n]) ↔ a ≡ 1 [ZMOD 8] := by
  constructor
  · rintro ⟨x, hx⟩
    have ho := odd_of_square_modEq ha (dvd_pow_self _ (by omega : n ≠ 0)) hx
    have h8 := modEq_of_dvd (show (8 : ℤ) ∣ 2 ^ n from pow_dvd_pow 2 hn) hx
    exact h8.symm.trans (odd_square_modEq_one x ho)

  · intro h
    have hiter : ∀ j : ℕ, ∃ x : ℤ, x ^ 2 ≡ a [ZMOD (2 : ℤ) ^ (j + 3)] := by
      intro j
      induction j with
      | zero =>
        exact ⟨1, by
          simpa only [one_pow, show (2 : ℤ) ^ (0 + 3) = 8 by decide] using h.symm⟩
      | succ j ih =>
        obtain ⟨x, hx⟩ := ih
        obtain ⟨b, hb⟩ := (modEq_iff_dvd_sub _ _ _).mp hx
        rcases Int.even_or_odd b with ⟨c, hc⟩ | ⟨c, hc⟩
        · refine ⟨x, (modEq_iff_dvd_sub _ _ _).mpr ⟨c, ?_⟩⟩
          rw [hb, hc]
          simp only [pow_succ]
          ring

        · have ho := odd_of_square_modEq ha (dvd_pow_self _ (by omega : j + 3 ≠ 0)) hx
          obtain ⟨d, hd⟩ := ho
          refine ⟨x + (2 : ℤ) ^ (j + 2),
            (modEq_iff_dvd_sub _ _ _).mpr ⟨c + d + 1 + (2 : ℤ) ^ j, ?_⟩⟩
          have he : x ^ 2 = a + (2 : ℤ) ^ (j + 3) * b := by linarith
          calc
            (x + (2 : ℤ) ^ (j + 2)) ^ 2 - a =
                (2 : ℤ) ^ (j + 3) * b +
                  2 * x * (2 : ℤ) ^ (j + 2) + ((2 : ℤ) ^ (j + 2)) ^ 2 := by
              nlinarith [he]
            _ = _ := by rw [hc, hd]; simp only [pow_succ]; ring
    simpa only [Nat.sub_add_cancel hn] using hiter (n - 3)

end ElementaryNumberTheory.TheQuadraticReciprocityLaw
