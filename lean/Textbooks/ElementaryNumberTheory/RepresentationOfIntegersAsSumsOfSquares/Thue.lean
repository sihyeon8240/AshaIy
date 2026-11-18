module

public import Textbooks.ElementaryNumberTheory.TheQuadraticReciprocityLaw.LegendreSymbol
public import Mathlib.Data.Nat.Sqrt

import Mathlib.Data.Fintype.Pigeonhole
import Mathlib.Tactic.Linarith

public section

namespace ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares

/-- Lemma: a multiple of a positive modulus whose square is smaller than the modulus is zero. -/
theorem eq_zero_of_dvd_of_sq_lt {p : ℕ} (hp : 0 < p) {x : ℤ}
    (hd : (p : ℤ) ∣ x) (hx : x ^ 2 < p) : x = 0 := by
  obtain ⟨k, rfl⟩ := hd
  have hp' : (0 : ℤ) < p := by exact_mod_cast hp
  by_contra hk
  have hk' : k ≠ 0 := by
    intro h
    simp only [h, mul_zero, not_true_eq_false] at hk
  have hk2 : 1 ≤ k ^ 2 := by
    have := sq_nonneg k
    have := pow_ne_zero 2 hk'
    omega
  nlinarith [sq_nonneg (p : ℤ), mul_nonneg (sq_nonneg (p : ℤ)) (sub_nonneg.mpr hk2)]

/-- Lemma: Thue's small solution has nonzero coordinates of absolute value less than
the square root of the prime; the bounds are expressed without real square roots. -/
theorem thue (p : ℕ) (hp : p.Prime) (a : ℤ) (ha : ¬(p : ℤ) ∣ a) :
    ∃ x y : ℤ, x ≠ 0 ∧ y ≠ 0 ∧ x ^ 2 < p ∧ y ^ 2 < p ∧
      a * x ≡ y [ZMOD (p : ℤ)] := by
  let : Fact p.Prime := ⟨hp⟩
  have hs : p.sqrt ^ 2 < p := by
    have hle := Nat.sqrt_le' p
    rcases lt_or_eq_of_le hle with h | h
    · exact h
    · have hd : p.sqrt ∣ p := ⟨p.sqrt, by nlinarith [h]⟩
      rcases hp.eq_one_or_self_of_dvd _ hd with he | he
      · rw [he] at h
        norm_num at h
        exact (hp.ne_one h.symm).elim
      · rw [he] at h
        have := hp.two_le
        nlinarith

  let f : Fin (p.sqrt + 1) × Fin (p.sqrt + 1) → ZMod p :=
    fun u => a * u.1.val - u.2.val
  have hcard : Fintype.card (ZMod p) <
      Fintype.card (Fin (p.sqrt + 1) × Fin (p.sqrt + 1)) := by
    simp only [ZMod.card, Fintype.card_prod, Fintype.card_fin]
    have := Nat.lt_succ_sqrt' p
    nlinarith

  obtain ⟨u, v, huv, heq⟩ := Fintype.exists_ne_map_eq_of_card_lt f hcard
  let x : ℤ := (u.1.val : ℤ) - v.1.val
  let y : ℤ := (u.2.val : ℤ) - v.2.val
  have hbound (i j : Fin (p.sqrt + 1)) : ((i.val : ℤ) - j.val) ^ 2 < p := by
    have hi : (i.val : ℤ) ≤ p.sqrt := by exact_mod_cast Nat.le_of_lt_succ i.isLt
    have hj : (j.val : ℤ) ≤ p.sqrt := by exact_mod_cast Nat.le_of_lt_succ j.isLt
    have hs' : (p.sqrt : ℤ) ^ 2 < p := by exact_mod_cast hs
    have hi0 := Int.natCast_nonneg i.val
    have hj0 := Int.natCast_nonneg j.val
    nlinarith [mul_nonneg (sub_nonneg.mpr hi) hj0,
      mul_nonneg (sub_nonneg.mpr hj) hi0, sq_nonneg ((i.val : ℤ) - j.val)]

  have hx := hbound u.1 v.1
  have hy := hbound u.2 v.2

  have hc : (a : ZMod p) * (x : ZMod p) = (y : ZMod p) := by
    change (a : ZMod p) * u.1.val - u.2.val =
      (a : ZMod p) * v.1.val - v.2.val at heq
    dsimp only [x, y]
    push_cast
    linear_combination heq

  have hxy : x = 0 → y = 0 → False := by
    intro hx0 hy0
    apply huv
    apply Prod.ext <;> apply Fin.ext
    · dsimp only [x] at hx0
      omega
    · dsimp only [y] at hy0
      omega

  have hx0 : x ≠ 0 := by
    intro hz
    have hd : (p : ℤ) ∣ y := by
      apply (ZMod.intCast_zmod_eq_zero_iff_dvd y p).mp
      simpa only [hz, Int.cast_zero, mul_zero, eq_comm] using hc
    exact hxy hz (eq_zero_of_dvd_of_sq_lt hp.pos hd hy)

  have hy0 : y ≠ 0 := by
    intro hz
    have ha0 : (a : ZMod p) ≠ 0 := by
      exact fun hz => ha ((ZMod.intCast_zmod_eq_zero_iff_dvd a p).mp hz)
    have hxc : (x : ZMod p) = 0 := by
      apply (mul_eq_zero.mp ?_).resolve_left ha0
      simpa only [hz, Int.cast_zero] using hc
    exact hx0 (eq_zero_of_dvd_of_sq_lt hp.pos
      ((ZMod.intCast_zmod_eq_zero_iff_dvd x p).mp hxc) hx)

  refine ⟨x, y, hx0, hy0, hx, hy, ?_⟩
  apply (ZMod.intCast_eq_intCast_iff _ _ p).mp
  simpa only [Int.cast_mul] using hc

end ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares
