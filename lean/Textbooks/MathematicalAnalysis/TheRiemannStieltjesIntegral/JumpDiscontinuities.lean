import Textbooks.MathematicalAnalysis.TheRiemannStieltjesIntegral.FiniteDiscontinuities

namespace MathematicalAnalysis.TheRiemannStieltjesIntegral

open Set BoxIntegral

noncomputable section

/-- Definition: the right-continuous unit jump at a point. -/
def unitJump (c x : ℝ) : ℝ := if c ≤ x then 1 else 0

/-- Lemma: the unit jump is increasing. -/
theorem unitJump_monotone (c : ℝ) : Monotone (unitJump c) := by
  intro x y hxy
  by_cases hx : c ≤ x
  · simp [unitJump, hx, hx.trans hxy]
  · by_cases hy : c ≤ y <;> simp [unitJump, hx, hy]

/-- Lemma: the unit jump is bounded on every closed interval. -/
theorem unitJump_bounded (I : Box Unit) (c : ℝ) :
    Bornology.IsBounded (unitJump c '' cell I) := by
  apply bounded_of_absolute_bound I (unitJump c) 1
  intro x _
  dsimp [unitJump]
  split_ifs <;> norm_num

/-- Lemma: the oscillation-weighted increment equals the increment of a unit jump. -/
theorem unitJump_cell_gap (J : Box Unit) (c : ℝ) :
    (cellSup (unitJump c) J - cellInf (unitJump c) J) * increment (unitJump c) J =
      increment (unitJump c) J := by
  by_cases hl : c ≤ -J.upper ()
  · have hr := hl.trans (neg_le_neg (J.lower_le_upper ()))
    simp [increment, unitJump, hl, hr]
  by_cases hr : c ≤ -J.lower ()
  · have hb := unitJump_bounded J c
    have hinf : cellInf (unitJump c) J = 0 := by
      apply le_antisymm
      · have h := csInf_le hb.bddBelow
          (show unitJump c (-J.upper ()) ∈ unitJump c '' cell J from
            ⟨_, ⟨le_rfl, neg_le_neg (J.lower_le_upper ())⟩, rfl⟩)
        simpa only [unitJump, ite_eq_right hl, cellInf] using h
      · apply le_csInf (cell_image_nonempty _ J)
        rintro _ ⟨x, _, rfl⟩
        dsimp [unitJump]
        split_ifs <;> norm_num
    have hsup : cellSup (unitJump c) J = 1 := by
      apply le_antisymm
      · apply csSup_le (cell_image_nonempty _ J)
        rintro _ ⟨x, _, rfl⟩
        dsimp [unitJump]
        split_ifs <;> norm_num
      · have h := le_csSup hb.bddAbove
          (show unitJump c (-J.lower ()) ∈ unitJump c '' cell J from
            ⟨_, ⟨neg_le_neg (J.lower_le_upper ()), le_rfl⟩, rfl⟩)
        simpa only [unitJump, ite_eq_left hr, cellSup] using h
    simp [hinf, hsup]
  · simp [increment, unitJump, hl, hr]

/-- Lemma: every partition retains a gap of one at a shared interior or right-endpoint jump. -/
theorem unitJump_partition_gap (a b c : ℝ) (hab : a < b) (hc : c ∈ Ioc a b)
    (P : Partition (intervalBox a b hab)) :
    upperSum (unitJump c) (unitJump c) P - lowerSum (unitJump c) (unitJump c) P = 1 := by
  rw [upperSum, lowerSum, ← Finset.sum_sub_distrib]
  simp_rw [← sub_mul, unitJump_cell_gap]
  rw [sum_increments]
  simp [increment, intervalBox, unitJump, not_le.mpr hc.1, hc.2]

/-- Theorem: a shared unit jump inside an interval or at its right endpoint prevents
Darboux-Stieltjes integrability. -/
theorem unitJump_not_stieltjesIntegrable (a b c : ℝ) (hab : a < b) (hc : c ∈ Ioc a b) :
    ¬StieltjesIntegrable (intervalBox a b hab) (unitJump c) (unitJump c) := by
  intro h
  have hb := unitJump_bounded (intervalBox a b hab) c
  obtain ⟨P, hP⟩ := (stieltjesIntegrable_iff_gap _ _ _ hb
    ((unitJump_monotone c).monotoneOn _)).mp h 1 zero_lt_one
  rw [unitJump_partition_gap a b c hab hc P] at hP
  exact lt_irrefl _ hP

/-- Theorem: the same jump is Riemann integrable for the continuous identity integrator. -/
theorem unitJump_riemannIntegrable (I : Box Unit) (c : ℝ) :
    RiemannIntegrable I (unitJump c) := by
  classical
  apply riemannIntegrable_finite_discontinuities I _ (unitJump_bounded I c) {c}
  intro x _ hxc
  have hne : x ≠ c := by simpa only [Finset.mem_singleton] using hxc
  apply ContinuousAt.continuousWithinAt
  rcases lt_or_gt_of_ne hne with hlt | hgt
  · apply (continuousAt_const : ContinuousAt (fun _ : ℝ => (0 : ℝ)) x).congr
    filter_upwards [eventually_lt_nhds hlt] with y hy
    simp [unitJump, not_le.mpr hy]
  · apply (continuousAt_const : ContinuousAt (fun _ : ℝ => (1 : ℝ)) x).congr
    filter_upwards [eventually_gt_nhds hgt] with y hy
    simp [unitJump, hy.le]

end

end MathematicalAnalysis.TheRiemannStieltjesIntegral
