import Textbooks.LinearAlgebra.ScalarProductsAndOrthogonality.HermitianProducts

namespace LinearAlgebra.ScalarProductsAndOrthogonality

open RCLike

noncomputable section

variable {𝕜 V : Type*} [RCLike 𝕜] [AddCommGroup V] [Module 𝕜 V]
variable [C : InnerProductSpace.Core 𝕜 V]

/-- Definition: length is the square root of the real diagonal, before any norm exists. -/
def formLength (v : V) : ℝ := Real.sqrt (re (C.inner v v))

local instance : Inner 𝕜 V := C.toInner

local notation "q" => fun v : V => re (C.inner v v)
local notation "B" => C.inner

/-- Lemma: expansion of the nonnegative squared projection remainder. -/
theorem form_remainder_identity (v w : V) :
    q (B v w • v - B v v • w) = q v * (q v * q w - ‖B v w‖ ^ 2) := by
  change InnerProductSpace.Core.normSq (B v w • v - B v v • w) =
    InnerProductSpace.Core.normSq v *
      (InnerProductSpace.Core.normSq v * InnerProductSpace.Core.normSq w - ‖B v w‖ ^ 2)
  rw [← @ofReal_inj 𝕜, InnerProductSpace.Core.ofReal_normSq_eq_inner_self]
  simp only [InnerProductSpace.Core.inner_sub_sub_self,
    InnerProductSpace.Core.inner_smul_left, InnerProductSpace.Core.inner_smul_right,
    conj_ofReal, mul_sub, ← InnerProductSpace.Core.ofReal_normSq_eq_inner_self v,
    ← InnerProductSpace.Core.ofReal_normSq_eq_inner_self w]
  rw [← mul_assoc, mul_conj, RCLike.conj_mul, mul_left_comm,
    ← InnerProductSpace.Core.inner_conj_symm w v, mul_conj]
  push_cast
  ring

/-- Lemma: Schwarz's squared inequality follows from positivity without a norm on vectors. -/
theorem form_schwarz_sq (v w : V) : ‖B v w‖ ^ 2 ≤ q v * q w := by
  by_cases hv : v = 0
  · subst v
    simp only [InnerProductSpace.Core.inner_zero_left, norm_zero, map_zero, zero_mul]
    norm_num

  have hq : 0 < q v := by
    apply lt_of_le_of_ne (C.re_inner_nonneg v)
    intro h
    apply hv
    apply C.definite
    rw [← InnerProductSpace.Core.inner_self_ofReal_re v, ← h, ofReal_zero]

  have h := C.re_inner_nonneg (B v w • v - B v v • w)
  have he := form_remainder_identity (C := C) v w
  dsimp only at he
  rw [he] at h
  nlinarith

/-- Theorem: Schwarz's inequality for the length induced by a positive form. -/
theorem form_schwarz (v w : V) : ‖B v w‖ ≤ formLength (C := C) v * formLength (C := C) w := by
  have hv := Real.sq_sqrt (C.re_inner_nonneg v)
  have hw := Real.sq_sqrt (C.re_inner_nonneg w)
  have hs := form_schwarz_sq (C := C) v w
  have hp : (formLength (C := C) v * formLength (C := C) w) ^ 2 = q v * q w := by
    dsimp [formLength]
    nlinarith [sq_nonneg (Real.sqrt (q v) * Real.sqrt (q w))]
  have hn := mul_nonneg (Real.sqrt_nonneg (q v)) (Real.sqrt_nonneg (q w))
  dsimp [formLength] at *
  nlinarith [norm_nonneg (B v w)]

/-- Theorem: the induced length satisfies the triangle inequality without assuming it. -/
theorem formLength_add_le (v w : V) :
    formLength (C := C) (v + w) ≤ formLength (C := C) v + formLength (C := C) w := by
  have he : q (v + w) = q v + 2 * re (B v w) + q w := by
    dsimp only
    rw [InnerProductSpace.Core.inner_add_add_self]
    simp only [map_add, InnerProductSpace.Core.inner_re_symm w v]
    ring

  have hs := (RCLike.re_le_norm (B v w)).trans (form_schwarz (C := C) v w)
  have hv := Real.sq_sqrt (C.re_inner_nonneg v)
  have hw := Real.sq_sqrt (C.re_inner_nonneg w)
  have ha := Real.sq_sqrt (C.re_inner_nonneg (v + w))
  have hn := Real.sqrt_nonneg (q (v + w))
  have hnv := Real.sqrt_nonneg (q v)
  have hnw := Real.sqrt_nonneg (q w)
  dsimp [formLength] at hs ⊢
  nlinarith

/-- Definition: the standard normed group built using the preceding algebraic triangle proof. -/
@[instance_reducible]
def formNormedAddCommGroup : NormedAddCommGroup V :=
  AddGroupNorm.toNormedAddCommGroup
    { toFun := formLength (C := C)
      map_zero' := by simp only [formLength, InnerProductSpace.Core.inner_zero_left,
        map_zero, Real.sqrt_zero]
      neg' := fun v => by simp only [formLength, InnerProductSpace.Core.inner_neg_left,
        InnerProductSpace.Core.inner_neg_right, neg_neg]
      add_le' := formLength_add_le (C := C)
      eq_zero_of_map_eq_zero' := by
        intro v hv
        have hq := (Real.sqrt_eq_zero (C.re_inner_nonneg v)).mp hv
        apply C.definite
        rw [← InnerProductSpace.Core.inner_self_ofReal_re v, hq, ofReal_zero] }

/-- Lemma: the constructed standard norm is exactly the algebraic length. -/
theorem formNorm_eq (v : V) : @norm V (formNormedAddCommGroup (C := C)).toNorm v =
    formLength (C := C) v := rfl

/-- Lemma: scalar multiplication scales the induced length by the scalar's norm. -/
theorem formLength_smul (a : 𝕜) (v : V) :
    formLength (C := C) (a • v) = ‖a‖ * formLength (C := C) v := by
  dsimp [formLength]
  rw [InnerProductSpace.Core.inner_smul_left, InnerProductSpace.Core.inner_smul_right,
    ← mul_assoc, RCLike.conj_mul, ← ofReal_pow, re_ofReal_mul,
    Real.sqrt_mul (sq_nonneg _), Real.sqrt_sq (norm_nonneg a)]

/-- Definition: the standard inner-product interface over the independently constructed norm. -/
@[instance_reducible]
def formInnerProductSpace :
    letI := formNormedAddCommGroup (C := C)
    InnerProductSpace 𝕜 V := by
  letI := formNormedAddCommGroup (C := C)
  letI : NormedSpace 𝕜 V :=
    { norm_smul_le := fun a v => (formLength_smul (C := C) a v).le }
  exact { C with norm_sq_eq_re_inner := fun v => Real.sq_sqrt (C.re_inner_nonneg v) }

/-- Definition: a positive real bilinear form induces a norm without a prior vector norm. -/
@[instance_reducible]
def realFormNormedGroup {E : Type*} [AddCommGroup E] [Module ℝ E]
    (form : LinearMap.BilinForm ℝ E) (hB : form.IsSymm) (hp : form.toQuadraticMap.PosDef) :
    NormedAddCommGroup E :=
  formNormedAddCommGroup (C := realInnerCore form hB hp)

/-- Definition: a positive Hermitian form induces a norm without a prior vector norm. -/
@[instance_reducible]
def hermitianFormNormedGroup {E : Type*} [AddCommGroup E] [Module ℂ E]
    (H : E →ₗ⋆[ℂ] E →ₗ[ℂ] ℂ) (hH : H.IsSymm) (hp : HermitianPosDef H) :
    NormedAddCommGroup E :=
  formNormedAddCommGroup (C := hermitianInnerCore H hH hp)

end

end LinearAlgebra.ScalarProductsAndOrthogonality
