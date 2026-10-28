import Textbooks.LinearAlgebra.Determinants.Characterization
import Textbooks.LinearAlgebra.ScalarProductsAndOrthogonality.MatrixRank

namespace LinearAlgebra.Determinants

open Matrix Module Submodule
open scoped BigOperators

variable {K V : Type*} [Field K] [AddCommGroup V] [Module K V]

/-- Lemma: extend an independent subset inside a finite generating set. -/
private theorem extend_basis_subset (t s : Finset V) (hs : s ⊆ t)
    (hi : LinearIndepOn K id (s : Set V)) :
    ∃ u : Finset V, u ⊆ t ∧ VectorSpaces.IsBasisOf u (span K (t : Set V)) := by
  classical

  by_cases he : span K (s : Set V) = span K (t : Set V)
  · exact ⟨s, hs, hi, he⟩

  have hn : ¬(t : Set V) ⊆ span K (s : Set V) := by
    intro ht
    exact he (le_antisymm (span_mono hs) (span_le.mpr ht))

  obtain ⟨x, hxt, hxs⟩ := Set.not_subset.mp hn
  have hx : x ∉ s := fun hx => hxs (subset_span hx)

  have hin : LinearIndepOn K id (↑(insert x s) : Set V) := by
    simpa only [Finset.coe_insert] using VectorSpaces.independent_insert hi hxs

  exact extend_basis_subset t (insert x s) (Finset.insert_subset hxt hs) hin
termination_by t.card - s.card
decreasing_by
  classical

  have hc := Finset.card_le_card (Finset.insert_subset hxt hs)
  rw [Finset.card_insert_of_notMem hx] at hc ⊢
  omega

/-- Lemma: a finite generating set contains a basis of its span. -/
theorem exists_basis_subset (t : Finset V) :
    ∃ s : Finset V, s ⊆ t ∧ VectorSpaces.IsBasisOf s (span K (t : Set V)) := by
  classical

  exact extend_basis_subset t ∅ (Finset.empty_subset _)
    (by simp only [Finset.coe_empty, linearIndepOn_empty])

/-- Lemma: an independent family spans a space of dimension its index cardinality. -/
theorem finrank_span_independent {ι : Type*} [Fintype ι] (v : ι → V)
    (hv : LinearIndependent K v) :
    finrank K (span K (Set.range v)) = Fintype.card ι := by
  classical

  let b := Module.Basis.span hv
  exact Module.finrank_eq_card_basis b

/-- Lemma: a matrix of rank at least r contains r independent rows. -/
theorem exists_independent_rows {m n r : ℕ} (A : Matrix (Fin m) (Fin n) K)
    (hr : r ≤ A.rank) :
    ∃ e : Fin r ↪ Fin m, LinearIndependent K (fun i => A.row (e i)) := by
  classical

  let t := Finset.univ.image A.row
  obtain ⟨s, hs, hb⟩ := exists_basis_subset (K := K) t

  have hspan : span K (t : Set (Fin n → K)) = span K (Set.range A.row) := by
    congr 1
    ext x
    simp only [t, Finset.mem_coe, Finset.mem_image, Finset.mem_univ, true_and,
      Set.mem_range]

  have hc : s.card = A.rank := by
    rw [← VectorSpaces.finrank_eq_card_of_basisOf hb, hspan,
      ScalarProductsAndOrthogonality.rank_eq_finrank_span_row]

  obtain ⟨u, hus, hu⟩ := Finset.exists_subset_card_eq (hc ▸ hr)
  let e : Fin r ≃ u := (Fintype.equivFinOfCardEq (by simpa using hu)).symm

  have hmem (x : u) : ∃ i : Fin m, A.row i = (x : Fin n → K) := by
    have hx := hs (hus x.property)
    simpa only [t, Finset.mem_image, Finset.mem_univ, true_and] using hx

  choose f hf using hmem

  have hfi : Function.Injective f := by
    intro x y h
    apply Subtype.ext
    exact (hf x).symm.trans ((congrArg A.row h).trans (hf y))

  refine ⟨⟨f ∘ e, hfi.comp e.injective⟩, ?_⟩
  have hi : LinearIndependent K (fun x : u => (x : Fin n → K)) :=
    hb.1.mono hus
  have he := hi.comp e e.injective
  convert he using 1
  funext i
  exact hf (e i)

/-- Lemma: selecting rows and columns cannot increase rank. -/
theorem rank_submatrix_le {m n p q : ℕ} (A : Matrix (Fin m) (Fin n) K)
    (e : Fin p → Fin m) (f : Fin q → Fin n) :
    (A.submatrix e f).rank ≤ A.rank := by
  let B := A.submatrix e id

  have hcol : (B.submatrix id f).rank ≤ B.rank := by
    rw [ScalarProductsAndOrthogonality.rank_eq_finrank_span_cols,
      ScalarProductsAndOrthogonality.rank_eq_finrank_span_cols]
    apply Submodule.finrank_mono
    apply Submodule.span_mono
    rintro v ⟨j, rfl⟩
    exact ⟨f j, rfl⟩

  have hrow : B.rank ≤ A.rank := by
    change (A.submatrix e (Equiv.refl (Fin n))).rank ≤ A.rank
    rw [Matrix.rank, Matrix.rank, Matrix.mulVecLin_submatrix,
      LinearMap.range_comp, LinearMap.range_comp]

    have hid : LinearMap.funLeft K K (Equiv.refl (Fin n)).symm = LinearMap.id := rfl
    rw [hid, LinearMap.range_id, Submodule.map_top]
    exact Submodule.finrank_map_le _ _

  exact hcol.trans hrow

/-- Theorem: rank at least r is equivalent to a nonzero r by r subdeterminant. -/
theorem le_rank_iff_exists_subdet {m n r : ℕ} (A : Matrix (Fin m) (Fin n) K) :
    r ≤ A.rank ↔ ∃ (e : Fin r ↪ Fin m) (f : Fin r ↪ Fin n),
      (A.submatrix e f).det ≠ 0 := by
  constructor

  · intro hr
    obtain ⟨e, he⟩ := exists_independent_rows A hr
    let B := A.submatrix e id

    have hB : B.rank = r := by
      rw [ScalarProductsAndOrthogonality.rank_eq_finrank_span_row]
      simpa only [Fintype.card_fin] using finrank_span_independent B.row he

    have ht : B.transpose.rank = r := by
      rw [ScalarProductsAndOrthogonality.rank_eq_finrank_span_row]
      change finrank K (span K (Set.range B.col)) = r
      rw [← ScalarProductsAndOrthogonality.rank_eq_finrank_span_cols, hB]

    obtain ⟨f, hf⟩ := exists_independent_rows B.transpose ht.ge
    exact ⟨e, f, (linearIndependent_cols_iff_det_ne_zero _).mp hf⟩

  · rintro ⟨e, f, hdet⟩
    have hi := (linearIndependent_cols_iff_det_ne_zero _).mpr hdet

    have hc : (A.submatrix e f).rank = r := by
      rw [ScalarProductsAndOrthogonality.rank_eq_finrank_span_cols]
      simpa only [Fintype.card_fin] using
        finrank_span_independent (A.submatrix e f).col hi

    rw [← hc]
    exact rank_submatrix_le A e f

/-- Corollary: rank is the largest order of a nonzero square subdeterminant. -/
theorem rank_isGreatest_subdet {m n : ℕ} (A : Matrix (Fin m) (Fin n) K) :
    IsGreatest {r : ℕ | ∃ (e : Fin r ↪ Fin m) (f : Fin r ↪ Fin n),
      (A.submatrix e f).det ≠ 0} A.rank := by
  exact ⟨(le_rank_iff_exists_subdet A).mp le_rfl,
    fun _ h => (le_rank_iff_exists_subdet A).mpr h⟩

end LinearAlgebra.Determinants
