module

public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.FourSquareIdentity
public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.ThreeSquares
public import Mathlib.Data.ZMod.ValMinAbs

public section

namespace ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares

/-- Lemma: squaring preserves an integer residue modulo two. -/
private theorem sq_mod_two (a : ℤ) : a ^ 2 % 2 = a % 2 := by
  have h0 := Int.emod_nonneg a (by decide : (2 : ℤ) ≠ 0)
  have h2 := Int.emod_lt_of_pos a (by decide : (0 : ℤ) < 2)
  interval_cases ha : a % 2 <;> norm_num [pow_two, Int.mul_emod, ha]

/-- Lemma: equal-parity coordinates can be halved by their half-sum and half-difference. -/
private theorem halve_pair {a b : ℤ} (h : a % 2 = b % 2) :
    2 * (((a + b) / 2) ^ 2 + ((a - b) / 2) ^ 2) = a ^ 2 + b ^ 2 := by
  have hsum : 2 * ((a + b) / 2) = a + b := by omega
  have hdiff : 2 * ((a - b) / 2) = a - b := by omega
  have hs := congrArg (fun x : ℤ => x ^ 2) hsum
  have hd := congrArg (fun x : ℤ => x ^ 2) hdiff
  nlinarith only [hs, hd]

/-- Lemma: a sum of four squares representing twice an integer can be halved
by pairing coordinates of equal parity. -/
theorem four_sq_of_two_mul {n a b c d : ℤ}
    (h : 2 * n = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2) :
    ∃ x y z w : ℤ, n = x ^ 2 + y ^ 2 + z ^ 2 + w ^ 2 := by
  have hm := congrArg (fun t : ℤ => t % 2) h
  have ha := sq_mod_two a
  have hb := sq_mod_two b
  have hc := sq_mod_two c
  have hd := sq_mod_two d
  have hpair : (a % 2 = b % 2 ∧ c % 2 = d % 2) ∨
      (a % 2 = c % 2 ∧ b % 2 = d % 2) ∨
      (a % 2 = d % 2 ∧ b % 2 = c % 2) := by omega
  rcases hpair with ⟨hab, hcd⟩ | ⟨hac, hbd⟩ | ⟨had, hbc⟩
  · refine ⟨(a + b) / 2, (a - b) / 2, (c + d) / 2, (c - d) / 2, ?_⟩
    apply mul_left_cancel₀ (by decide : (2 : ℤ) ≠ 0)
    linear_combination h - halve_pair hab - halve_pair hcd

  · refine ⟨(a + c) / 2, (a - c) / 2, (b + d) / 2, (b - d) / 2, ?_⟩
    apply mul_left_cancel₀ (by decide : (2 : ℤ) ≠ 0)
    linear_combination h - halve_pair hac - halve_pair hbd

  · refine ⟨(a + d) / 2, (a - d) / 2, (b + c) / 2, (b - c) / 2, ?_⟩
    apply mul_left_cancel₀ (by decide : (2 : ℤ) ≠ 0)
    linear_combination h - halve_pair had - halve_pair hbc

/-- Lemma: an odd multiplier strictly between one and the prime admits a smaller
positive multiplier, using balanced residues and Euler's identity. -/
theorem four_sq_odd_descent {p k : ℕ} (hp : p.Prime) (hk1 : 1 < k) (hkp : k < p)
    (hkodd : ¬2 ∣ k) {a b c d : ℤ}
    (h : (k : ℤ) * p = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2) :
    ∃ r : ℕ, 0 < r ∧ r < k ∧
      ∃ x y z w : ℤ, (r : ℤ) * p = x ^ 2 + y ^ 2 + z ^ 2 + w ^ 2 := by
  let : NeZero k := ⟨by omega⟩
  let f : ℤ → ℤ := fun x => (x : ZMod k).valMinAbs
  have hf (x : ℤ) : (f x : ZMod k) = x := ZMod.coe_valMinAbs _
  have hsmall (x : ℤ) : 2 * (f x).natAbs < k := by
    have hbound := (x : ZMod k).natAbs_valMinAbs_le
    have hk2 := Nat.mod_lt k (by decide : 0 < 2)
    have hkrem : k % 2 ≠ 0 := by simpa only [Nat.dvd_iff_mod_eq_zero] using hkodd
    dsimp only [f]
    omega

  have hdiv : k ∣ (f a).natAbs ^ 2 + (f b).natAbs ^ 2 +
      (f c).natAbs ^ 2 + (f d).natAbs ^ 2 := by
    rw [← Int.natCast_dvd_natCast, ← ZMod.intCast_zmod_eq_zero_iff_dvd]
    push_cast [sq_abs, hf]
    have hc := congrArg (fun x : ℤ => (x : ZMod k)) h
    push_cast at hc
    simpa only [ZMod.natCast_self, zero_mul, eq_comm, pow_two] using hc
  obtain ⟨r, hr⟩ := hdiv
  have hrint : (f a) ^ 2 + (f b) ^ 2 + (f c) ^ 2 + (f d) ^ 2 = (k : ℤ) * r := by
    have := congrArg (fun x : ℕ => (x : ℤ)) hr
    simpa only [Nat.cast_add, Nat.cast_pow, Int.natCast_natAbs, sq_abs, Nat.cast_mul] using this

  have hrpos : 0 < r := by
    by_contra hle
    have hr0 : r = 0 := by omega
    have hfzero : f a = 0 ∧ f b = 0 ∧ f c = 0 ∧ f d = 0 := by
      rw [hr0, Nat.cast_zero, mul_zero] at hrint
      have ha := sq_nonneg (f a)
      have hb := sq_nonneg (f b)
      have hc := sq_nonneg (f c)
      have hd := sq_nonneg (f d)
      exact ⟨by nlinarith, by nlinarith, by nlinarith, by nlinarith⟩
    have hcoord (x : ℤ) (hx : f x = 0) : (k : ℤ) ∣ x := by
      apply (ZMod.intCast_zmod_eq_zero_iff_dvd x k).mp
      rw [← hf x, hx, Int.cast_zero]
    obtain ⟨x, hx⟩ := hcoord a hfzero.1
    obtain ⟨y, hy⟩ := hcoord b hfzero.2.1
    obtain ⟨z, hz⟩ := hcoord c hfzero.2.2.1
    obtain ⟨w, hw⟩ := hcoord d hfzero.2.2.2
    have hdp : (k : ℤ) ∣ (p : ℤ) := by
      refine ⟨x ^ 2 + y ^ 2 + z ^ 2 + w ^ 2, ?_⟩
      apply mul_left_cancel₀ (by exact_mod_cast (by omega : k ≠ 0) : (k : ℤ) ≠ 0)
      rw [hx, hy, hz, hw] at h
      nlinarith only [h]
    have := hp.eq_one_or_self_of_dvd k (Int.natCast_dvd_natCast.mp hdp)
    omega

  have hrlt : r < k := by
    have hbound (x : ℤ) : 4 * (f x).natAbs ^ 2 < k ^ 2 := by
      have hx := hsmall x
      have hs := Nat.pow_le_pow_left (by omega : 2 * (f x).natAbs ≤ k - 1) 2
      have hk : k - 1 + 1 = k := by omega
      nlinarith
    have ha := hbound a
    have hb := hbound b
    have hc := hbound c
    have hd := hbound d
    nlinarith [hr]

  let A := a * f a + b * f b + c * f c + d * f d
  let B := a * f b - b * f a + c * f d - d * f c
  let C := a * f c - b * f d - c * f a + d * f b
  let D := a * f d + b * f c - c * f b - d * f a
  have hA : (k : ℤ) ∣ A := by
    apply (ZMod.intCast_zmod_eq_zero_iff_dvd A k).mp
    dsimp only [A]
    push_cast [hf]
    have hc := congrArg (fun x : ℤ => (x : ZMod k)) h
    push_cast at hc
    simpa only [ZMod.natCast_self, zero_mul, eq_comm, pow_two] using hc
  have hB : (k : ℤ) ∣ B := by
    apply (ZMod.intCast_zmod_eq_zero_iff_dvd B k).mp
    dsimp only [B]
    push_cast [hf]
    ring
  have hC : (k : ℤ) ∣ C := by
    apply (ZMod.intCast_zmod_eq_zero_iff_dvd C k).mp
    dsimp only [C]
    push_cast [hf]
    ring
  have hD : (k : ℤ) ∣ D := by
    apply (ZMod.intCast_zmod_eq_zero_iff_dvd D k).mp
    dsimp only [D]
    push_cast [hf]
    ring

  obtain ⟨x, hx⟩ := hA
  obtain ⟨y, hy⟩ := hB
  obtain ⟨z, hz⟩ := hC
  obtain ⟨w, hw⟩ := hD
  have hid : ((k : ℤ) * p) * ((k : ℤ) * r) = A ^ 2 + B ^ 2 + C ^ 2 + D ^ 2 := by
    rw [h, ← hrint]
    exact four_square_identity a b c d (f a) (f b) (f c) (f d)

  refine ⟨r, hrpos, hrlt, x, y, z, w, ?_⟩
  apply mul_left_cancel₀ (pow_ne_zero 2
    (by exact_mod_cast (by omega : k ≠ 0) : (k : ℤ) ≠ 0))
  rw [hx, hy, hz, hw] at hid
  nlinarith only [hid]

/-- Theorem: every prime is a sum of four integer squares. -/
theorem prime_four_sq (p : ℕ) (hp : p.Prime) :
    ∃ a b c d : ℤ, (p : ℤ) = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2 := by
  classical
  obtain ⟨k₀, hk₀, hk₀p, hrep⟩ := exists_small_four_sq_multiple p hp
  let P : ℕ → Prop := fun k => 0 < k ∧
    ∃ a b c d : ℤ, (k : ℤ) * p = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2
  have hex : ∃ k, P k := ⟨k₀, hk₀, by simpa only [Nat.cast_mul] using hrep⟩
  let k := Nat.find hex
  obtain ⟨hkpos, a, b, c, d, h⟩ := Nat.find_spec hex
  change 0 < k at hkpos
  change (k : ℤ) * p = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2 at h
  have hmin (r : ℕ) (hr : P r) : k ≤ r := Nat.find_min' hex hr
  have hkp : k < p := lt_of_le_of_lt (hmin k₀ ⟨hk₀, by
    simpa only [Nat.cast_mul] using hrep⟩) hk₀p

  by_cases hk1 : k = 1
  · exact ⟨a, b, c, d, by simpa only [hk1, Nat.cast_one, one_mul] using h⟩

  · have hkgt : 1 < k := by omega
    by_cases hkeven : 2 ∣ k
    · obtain ⟨r, hr⟩ := hkeven
      have hrpos : 0 < r := by omega
      have hrlt : r < k := by omega
      have hh : 2 * ((r : ℤ) * p) = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2 := by
        rw [hr, Nat.cast_mul, Nat.cast_ofNat] at h
        nlinarith only [h]
      have hnew := four_sq_of_two_mul hh
      have := hmin r ⟨hrpos, hnew⟩
      omega

    · obtain ⟨r, hrpos, hrlt, hnew⟩ := four_sq_odd_descent hp hkgt hkp hkeven h
      have := hmin r ⟨hrpos, hnew⟩
      omega

end ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares
