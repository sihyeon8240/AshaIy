import Textbooks.LinearAlgebra.ScalarProductsAndOrthogonality.DualSpaces
import Textbooks.LinearAlgebra.ScalarProductsAndOrthogonality.CoordinateProducts
import Textbooks.LinearAlgebra.LinearMapsAndMatrices.MatrixMaps
import Mathlib.LinearAlgebra.Matrix.Rank

namespace LinearAlgebra.ScalarProductsAndOrthogonality

open Module Submodule
open scoped BigOperators Matrix

variable {K : Type*} [Field K] {m n : ℕ}

/-- Theorem: a coordinate subspace and its dot-product perpendicular have
complementary dimensions. -/
theorem finrank_add_finrank_dotProduct_orthogonal (W : Submodule K (Fin n → K)) :
    finrank K W + finrank K (W.orthogonalBilin (coordinateProduct n)) = n := by
  have hd := finrank_add_finrank_orthogonalBilin (coordinateProduct n)
    coordinateProduct_isSymm coordinateProduct_separatingLeft W
  rw [Matrices.finrank_coordinates] at hd
  exact hd

/-- Proposition: homogeneous solutions are precisely the vectors perpendicular to all rows. -/
theorem ker_mulVecLin_eq_orthogonal_rows (A : Matrix (Fin m) (Fin n) K) :
    LinearMap.ker A.mulVecLin =
      (span K (Set.range A.row)).orthogonalBilin (coordinateProduct n) := by
  ext x
  change A *ᵥ x = 0 ↔
    x ∈ orthogonalSpace (coordinateProduct n) (span K (Set.range A.row) : Set (Fin n → K))
  rw [orthogonalSpace_span]
  change A *ᵥ x = 0 ↔ ∀ y ∈ Set.range A.row, coordinateProduct n y x = 0
  simp only [Set.forall_mem_range, coordinateProduct_eq_dotProduct,
    VectorSpaces.dotProduct, funext_iff, Matrix.mulVec, _root_.dotProduct,
    Pi.zero_apply, Matrix.row_apply]

/-- Proposition: the image of a matrix map is the span of its columns. -/
theorem range_mulVecLin_eq_span_cols (A : Matrix (Fin m) (Fin n) K) :
    LinearMap.range A.mulVecLin = span K (Set.range A.col) := by
  apply le_antisymm

  · rintro y ⟨x, rfl⟩
    rw [Matrix.mulVecLin_apply, Matrices.mulVec_eq_combination]
    apply Submodule.sum_mem
    intro j _
    exact Submodule.smul_mem _ _ (subset_span ⟨j, rfl⟩)

  · apply span_le.mpr
    rintro y ⟨j, rfl⟩
    exact ⟨Pi.single j 1, LinearMapsAndMatrices.mulVecLin_single A j⟩

/-- Proposition: matrix rank is column rank, the dimension of the column span. -/
theorem rank_eq_finrank_span_cols (A : Matrix (Fin m) (Fin n) K) :
    A.rank = finrank K (span K (Set.range A.col)) := by
  change finrank K (LinearMap.range A.mulVecLin) = _
  rw [range_mulVecLin_eq_span_cols]

/-- Theorem: matrix rank is also row rank, the dimension of the row span. -/
theorem rank_eq_finrank_span_row (A : Matrix (Fin m) (Fin n) K) :
    A.rank = finrank K (span K (Set.range A.row)) := by
  have hr := finrank_add_finrank_dotProduct_orthogonal (span K (Set.range A.row))
  rw [← ker_mulVecLin_eq_orthogonal_rows] at hr
  have hc := LinearMappings.rank_nullity A.mulVecLin
  rw [Matrices.finrank_coordinates] at hc
  change n = finrank K (LinearMap.ker A.mulVecLin) + A.rank at hc
  omega

/-- Corollary: the row rank and column rank of every rectangular matrix are equal. -/
theorem finrank_span_row_eq_finrank_span_cols (A : Matrix (Fin m) (Fin n) K) :
    finrank K (span K (Set.range A.row)) = finrank K (span K (Set.range A.col)) := by
  rw [← rank_eq_finrank_span_row, rank_eq_finrank_span_cols]

/-- Theorem: a homogeneous system has dimension the number of unknowns minus its rank. -/
theorem finrank_ker_mulVecLin (A : Matrix (Fin m) (Fin n) K) :
    finrank K (LinearMap.ker A.mulVecLin) = n - A.rank := by
  have hd := LinearMappings.rank_nullity A.mulVecLin
  rw [Matrices.finrank_coordinates] at hd
  change n = finrank K (LinearMap.ker A.mulVecLin) + A.rank at hd
  omega

end LinearAlgebra.ScalarProductsAndOrthogonality
