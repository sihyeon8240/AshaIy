module

public import Textbooks.ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares.FourSquareDescent
public import Textbooks.ElementaryNumberTheory.PrimesAndTheirDistribution.PrimeFactorization

public section

namespace ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares

/-- Theorem: every positive integer is a sum of four integer squares,
with zero coordinates allowed. -/
theorem four_sq (n : ℕ) (hn : 0 < n) :
    ∃ a b c d : ℤ, (n : ℤ) = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2 := by
  obtain ⟨l, hl, hprod⟩ := PrimesAndTheirDistribution.exists_prime_factors n hn
  have hlist (l : List ℕ) (hl : ∀ p ∈ l, PrimesAndTheirDistribution.isPrime p) :
      ∃ a b c d : ℤ, (l.prod : ℤ) = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2 := by
    induction l with
    | nil => exact ⟨1, 0, 0, 0, by norm_num⟩
    | cons p l ih =>
      have hp := hl p List.mem_cons_self
      have hp' : p.Prime := Nat.prime_def.mpr
        ⟨by
          have := hp.1
          omega, hp.2⟩
      simpa only [List.prod_cons, Nat.cast_mul] using
        four_sq_mul (prime_four_sq p hp') (ih (fun q hq => hl q (List.mem_cons_of_mem p hq)))

  rw [← hprod]
  exact hlist l hl

/-- Corollary: every nonnegative integer has a representation by four nonnegative squares. -/
theorem four_sq_nat (n : ℕ) : ∃ a b c d : ℕ, n = a ^ 2 + b ^ 2 + c ^ 2 + d ^ 2 := by
  by_cases hn : n = 0
  · subst n
    exact ⟨0, 0, 0, 0, by norm_num⟩

  · obtain ⟨a, b, c, d, h⟩ := four_sq n (by omega)
    refine ⟨a.natAbs, b.natAbs, c.natAbs, d.natAbs, ?_⟩
    have heq : (n : ℤ) = (a.natAbs : ℤ) ^ 2 + (b.natAbs : ℤ) ^ 2 +
        (c.natAbs : ℤ) ^ 2 + (d.natAbs : ℤ) ^ 2 := by
      simpa only [Int.natCast_natAbs, sq_abs] using h
    exact_mod_cast heq

end ElementaryNumberTheory.RepresentationOfIntegersAsSumsOfSquares
