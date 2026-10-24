import Textbooks.MathematicalAnalysis.BasicTopology.MetricSpaces
import Mathlib.Analysis.BoxIntegral.Partition.Additive

namespace MathematicalAnalysis.TheRiemannStieltjesIntegral

open Set BoxIntegral

noncomputable section

/-- Definition: a nondegenerate real interval represented by a one-dimensional
box in reversed coordinates, whose membership describes half-open ownership. -/
def intervalBox (a b : ℝ) (hab : a < b) : Box Unit :=
  ⟨fun _ => -b, fun _ => -a, fun _ => neg_lt_neg hab⟩

/-- Definition: the half-open interval used only for disjoint partition ownership. -/
def halfOpenCell (I : Box Unit) : Set ℝ := Ico (-I.upper ()) (-I.lower ())

/-- Definition: the closed subinterval on which Darboux extrema and tags are evaluated. -/
def cell (I : Box Unit) : Set ℝ := Icc (-I.upper ()) (-I.lower ())

/-- Definition: a partition is a finite family of boxes whose half-open cells
are disjoint and cover the half-open ambient interval. Evaluation includes both endpoints. -/
abbrev Partition (I : Box Unit) := {P : Prepartition I // P.IsPartition}

/-- Definition: refinement means that every cell of the finer partition lies
in a cell of the coarser partition. -/
def Refines {I : Box Unit} (Q P : Partition I) : Prop := Q.val ≤ P.val

/-- Definition: the Stieltjes increment on a cell is the change of its integrator. -/
def increment (α : ℝ → ℝ) (I : Box Unit) : ℝ := α (-I.lower ()) - α (-I.upper ())

/-- Definition: the length of an interval cell. -/
def cellLength (I : Box Unit) : ℝ := I.upper () - I.lower ()

/-- Definition: the mesh of a partition is the largest length of its cells. -/
def mesh {I : Box Unit} (P : Partition I) : ℝ :=
  P.val.boxes.sup' P.property.nonempty_boxes cellLength

/-- Lemma: a box's evaluation cell is the stated closed interval. -/
theorem cell_intervalBox (a b : ℝ) (hab : a < b) : cell (intervalBox a b hab) = Icc a b := by
  simp only [cell, intervalBox, neg_neg]

/-- Lemma: a box's ownership cell is the stated half-open interval. -/
theorem halfOpenCell_intervalBox (a b : ℝ) (hab : a < b) :
    halfOpenCell (intervalBox a b hab) = Ico a b := by
  simp only [halfOpenCell, intervalBox, neg_neg]

/-- Lemma: reversing the coordinate identifies ownership cells with boxes. -/
theorem neg_mem_box (I : Box Unit) (x : ℝ) :
    (fun _ : Unit => -x) ∈ I ↔ x ∈ halfOpenCell I := by
  constructor
  · intro h
    have hx := h ()
    exact ⟨by linarith [hx.2], by linarith [hx.1]⟩
  · intro hx i
    cases i
    exact ⟨by linarith [hx.2], by linarith [hx.1]⟩

/-- Lemma: containment of boxes preserves their ownership cells. -/
theorem halfOpenCell_mono {I J : Box Unit} (h : I ≤ J) : halfOpenCell I ⊆ halfOpenCell J := by
  intro x hx
  exact (neg_mem_box J x).mp (h ((neg_mem_box I x).mpr hx))

/-- Lemma: every cell has positive length. -/
theorem cellLength_pos (I : Box Unit) : 0 < cellLength I := sub_pos.mpr (I.lower_lt_upper ())

/-- Lemma: containment of boxes gives containment of their real cells. -/
theorem cell_mono {I J : Box Unit} (h : I ≤ J) : cell I ⊆ cell J := by
  intro x hx
  have hl := (Box.le_iff_bounds.mp h).1 ()
  have hu := (Box.le_iff_bounds.mp h).2 ()
  exact ⟨by
    dsimp [cell] at hx ⊢
    linarith [hx.1], by
    dsimp [cell] at hx ⊢
    linarith [hx.2]⟩

/-- Definition: the increments as a finitely additive interval function.
The generic interface supplies only finite subdivision bookkeeping. -/
def incrementAdditive (α : ℝ → ℝ) : BoxAdditiveMap Unit ℝ ⊤ :=
  BoxAdditiveMap.ofMapSplitAdd (increment α) ⊤ (by
    intro I _ i x hx
    cases i
    rw [Box.splitLower_def hx, Box.splitUpper_def hx]
    change (α (-I.lower ()) - α (-x)) + (α (-x) - α (-I.upper ())) =
      α (-I.lower ()) - α (-I.upper ())
    ring)

/-- Lemma: the increments telescope over a partition. -/
theorem sum_increments {I : Box Unit} (P : Partition I) (α : ℝ → ℝ) :
    ∑ J ∈ P.val.boxes, increment α J = increment α I :=
  (incrementAdditive α).sum_partition_boxes le_top P.property

/-- Lemma: the lengths of the cells sum to the interval length. -/
theorem sum_cellLengths {I : Box Unit} (P : Partition I) :
    ∑ J ∈ P.val.boxes, cellLength J = cellLength I := by
  have h := sum_increments P (fun x : ℝ => x)
  simpa only [increment, cellLength, neg_sub_neg] using h

/-- Definition: the common refinement consists of all nonempty intersections of cells. -/
def commonRefinement {I : Box Unit} (P Q : Partition I) : Partition I :=
  ⟨P.val ⊓ Q.val, P.property.inf Q.property⟩

/-- Lemma: a common refinement refines both partitions. -/
theorem commonRefinement_refines {I : Box Unit} (P Q : Partition I) :
    Refines (commonRefinement P Q) P ∧ Refines (commonRefinement P Q) Q :=
  ⟨inf_le_left, inf_le_right⟩

end

end MathematicalAnalysis.TheRiemannStieltjesIntegral
