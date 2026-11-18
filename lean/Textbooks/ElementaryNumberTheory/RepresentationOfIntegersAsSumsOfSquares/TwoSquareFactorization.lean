module

public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.TwoSquarePrimes
public import Textbooks.ElementaryNumberTheory.CertainNonlinearDiophantineEquations.CoprimePowers
public import Mathlib.Algebra.Squarefree.Basic

public section

namespace ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares

open NumberTheoreticFunctions PrimitiveRootsAndIndices

/-- Lemma: a prime divides a positive integer exactly when its prime exponent is positive. -/
theorem prime_dvd_iff_primeExponents_pos {p n : ℕ} (hp : p.Prime) (hn : 0 < n) :
    p ∣ n ↔ 0 < primeExponents n p := by
  have he : primeExponents p = Finsupp.single p 1 := by
    simpa only [pow_one] using primeExponents_prime_pow p 1 (isPrime_of_prime p hp)
  rw [dvd_iff_primeExponents_le p n hp.pos hn, he, Finsupp.single_le_iff]
  omega

/-- Lemma: a represented positive integer has even exponent at every prime three modulo four. -/
theorem even_primeExponents_of_sq_add_sq (n : ℕ) (hn : 0 < n)
    (h : ∃ a b : ℤ, (n : ℤ) = a ^ 2 + b ^ 2) :
    ∀ p : ℕ, p.Prime → p % 4 = 3 → Even (primeExponents n p) := by
  induction n using Nat.strong_induction_on with
  | h n ih =>
    intro p hp hp4
    by_cases hd : p ∣ n
    · obtain ⟨a, b, hab⟩ := h
      have hdiv : (p : ℤ) ∣ a ^ 2 + b ^ 2 := by
        rw [← hab]
        exact_mod_cast hd
      obtain ⟨⟨c, hc⟩, ⟨d, hd⟩⟩ := prime_dvd_sq_add_sq hp hp4 hdiv

      let m := c.natAbs ^ 2 + d.natAbs ^ 2
      have hm : (m : ℤ) = c ^ 2 + d ^ 2 := by
        simp only [m, Nat.cast_add, Nat.cast_pow, Int.natCast_natAbs, sq_abs]
      have heq : n = p ^ 2 * m := by
        rw [hc, hd] at hab
        have heq' : (n : ℤ) = (p : ℤ) ^ 2 * m := by nlinarith [hm]
        exact_mod_cast heq'
      have hmpos : 0 < m := by nlinarith [heq]
      have hmlt : m < n := by
        calc
          m < 4 * m := by omega
          _ ≤ p ^ 2 * m := Nat.mul_le_mul_right m (by nlinarith [hp.two_le])
          _ = n := heq.symm

      have hev := ih m hmlt hmpos ⟨c, d, hm⟩ p hp hp4
      rw [heq, primeExponents_mul (p ^ 2) m (pow_pos hp.pos _) hmpos,
        primeExponents_prime_pow p 2 (isPrime_of_prime p hp), Finsupp.add_apply,
        Finsupp.single_eq_same]
      exact (by decide : Even 2).add hev

    · have hz : primeExponents n p = 0 := by
        have := (prime_dvd_iff_primeExponents_pos hp hn).not.mp hd
        omega
      rw [hz]
      exact Even.zero

/-- Lemma: a power of a represented integer is a sum of two integer squares. -/
theorem sq_add_sq_pow {n : ℤ} (h : ∃ a b : ℤ, n = a ^ 2 + b ^ 2) (k : ℕ) :
    ∃ a b : ℤ, n ^ k = a ^ 2 + b ^ 2 := by
  induction k with
  | zero => exact ⟨1, 0, by norm_num⟩
  | succ k ih =>
    rw [pow_succ]
    exact sq_add_sq_mul ih h

/-- Corollary: the exponent test characterizes positive sums of two integer squares. -/
theorem sq_add_sq_iff_even_primeExponents (n : ℕ) (hn : 0 < n) :
    (∃ a b : ℤ, (n : ℤ) = a ^ 2 + b ^ 2) ↔
      ∀ p : ℕ, p.Prime → p % 4 = 3 → Even (primeExponents n p) := by
  refine ⟨even_primeExponents_of_sq_add_sq n hn, ?_⟩
  intro h
  have hpower (p : ℕ) (hp : p ∈ (primeExponents n).support) :
      ∃ a b : ℤ, (p : ℤ) ^ primeExponents n p = a ^ 2 + b ^ 2 := by
    have hpbook := (primeExponents_spec n hn).1 p hp
    have hprime : p.Prime := Nat.prime_def.mpr
      ⟨by
        have := hpbook.1
        omega, hpbook.2⟩
    by_cases hp4 : p % 4 = 3
    · obtain ⟨k, hk⟩ := h p hprime hp4
      refine ⟨(p : ℤ) ^ k, 0, ?_⟩
      rw [hk, pow_add]
      ring

    · apply sq_add_sq_pow
      by_cases hp2 : p = 2
      · subst p
        exact ⟨1, 1, by norm_num⟩
      · apply (prime_sq_add_sq_iff hprime hp2).mpr
        have := Nat.odd_iff.mp (hprime.odd_of_ne_two hp2)
        omega

  have hprod (s : Finset ℕ)
      (hs : ∀ p ∈ s, ∃ a b : ℤ, (p : ℤ) ^ primeExponents n p = a ^ 2 + b ^ 2) :
      ∃ a b : ℤ, (∏ p ∈ s, (p : ℤ) ^ primeExponents n p) = a ^ 2 + b ^ 2 := by
    classical
    induction s using Finset.induction_on with
    | empty => exact ⟨1, 0, by norm_num⟩
    | @insert p s hp ih =>
      rw [Finset.prod_insert hp]
      exact sq_add_sq_mul (hs p (Finset.mem_insert_self p s))
        (ih (fun q hq => hs q (Finset.mem_insert_of_mem hq)))

  have hv : (n : ℤ) = ∏ p ∈ (primeExponents n).support, (p : ℤ) ^ primeExponents n p := by
    have := congrArg (fun k : ℕ => (k : ℤ)) (primeExponents_spec n hn).2
    simpa only [factorValue, Finsupp.prod, Nat.cast_prod, Nat.cast_pow] using this.symm

  rw [hv]
  exact hprod _ hpower

/-- Lemma: a prime exponent in a squarefree positive integer is at most one. -/
theorem primeExponents_le_one_of_squarefree {m p : ℕ} (hm : 0 < m)
    (hs : Squarefree m) (hp : p.Prime) : primeExponents m p ≤ 1 := by
  by_contra hle
  have hdiv : p ^ 2 ∣ m := by
    rw [dvd_iff_primeExponents_le _ m (pow_pos hp.pos _) hm,
      primeExponents_prime_pow p 2 (isPrime_of_prime p hp), Finsupp.single_le_iff]
    omega
  have hunit := hs p (by simpa only [pow_two] using hdiv)
  exact hp.ne_one (Nat.isUnit_iff.mp hunit)

/-- Theorem: for n=N²m with squarefree m, n is a sum of two squares exactly when
m has no prime divisor congruent to three modulo four. -/
theorem sq_add_sq_iff_squarefree_part (n N m : ℕ) (hn : 0 < n)
    (heq : n = N ^ 2 * m) (hm : Squarefree m) :
    (∃ a b : ℤ, (n : ℤ) = a ^ 2 + b ^ 2) ↔
      ∀ p : ℕ, p.Prime → p ∣ m → p % 4 ≠ 3 := by
  have hN : 0 < N := by
    by_contra h
    have hz : N = 0 := by omega
    rw [hz, zero_pow two_ne_zero, zero_mul] at heq
    omega
  have hmpos : 0 < m := by nlinarith [heq]
  have hexp (p : ℕ) : primeExponents n p = 2 * primeExponents N p + primeExponents m p := by
    rw [heq, primeExponents_mul (N ^ 2) m (pow_pos hN _) hmpos,
      CertainNonlinearDiophantineEquations.primeExponents_pow N 2 hN,
      Finsupp.add_apply]
    simp only [Finsupp.smul_apply, smul_eq_mul]

  rw [sq_add_sq_iff_even_primeExponents n hn]
  constructor
  · intro h p hp hpm hp4
    have hpos := (prime_dvd_iff_primeExponents_pos hp hmpos).mp hpm
    have hle := primeExponents_le_one_of_squarefree hmpos hm hp
    have he : primeExponents m p = 1 := by omega
    obtain ⟨k, hk⟩ := h p hp hp4
    rw [hexp p, he] at hk
    omega

  · intro h p hp hp4
    have hnot : ¬p ∣ m := fun hd => h p hp hd hp4
    have he : primeExponents m p = 0 := by
      have := (prime_dvd_iff_primeExponents_pos hp hmpos).not.mp hnot
      omega
    rw [hexp p, he, add_zero]
    exact ⟨primeExponents N p, by omega⟩

end ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares
