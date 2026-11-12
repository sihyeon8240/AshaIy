module

public import Textbooks.LinearAlgebra.SymmetricHermitianAndUnitaryOperators.Transpose
public import Textbooks.LinearAlgebra.SymmetricHermitianAndUnitaryOperators.Unitary

public section

namespace LinearAlgebra.SymmetricHermitianAndUnitaryOperators

variable {E : Type*} [NormedAddCommGroup E] [InnerProductSpace ℝ E]

/-- Lemma: positive definiteness makes the real inner product nondegenerate. -/
theorem real_inner_separatingLeft : (innerₗ E).SeparatingLeft := by
  intro v hv
  exact (inner_self_eq_zero (𝕜 := ℝ)).mp (hv v)

variable [Module.Finite ℝ E]

/-- Lemma: the algebraic transpose for the real inner product is its adjoint. -/
theorem transpose_inner_eq_adjoint (A : Module.End ℝ E) :
    transpose (innerₗ E) real_inner_separatingLeft A = adjoint A := by
  symm
  apply transpose_unique (innerₗ E) ⟨fun v w => real_inner_comm _ _⟩
  exact inner_adjoint_right A

/-- Theorem: a real operator is unitary exactly when its transpose is a left inverse. -/
theorem isUnitary_iff_transpose_mul_self (A : Module.End ℝ E) :
    IsUnitary A ↔ transpose (innerₗ E) real_inner_separatingLeft A * A = 1 := by
  rw [transpose_inner_eq_adjoint]
  exact isUnitary_iff_adjoint_mul_self A

end LinearAlgebra.SymmetricHermitianAndUnitaryOperators
