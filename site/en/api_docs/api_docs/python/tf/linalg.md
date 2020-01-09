

page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>


<!-- DO NOT EDIT! Automatically generated file. -->

# Module: tf.linalg



Defined in [`tensorflow/linalg/__init__.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.10/tensorflow/linalg/__init__.py).

Operations for linear algebra.

## Classes

[`class LinearOperator`](../tf/linalg/LinearOperator): Base class defining a [batch of] linear operator[s].

[`class LinearOperatorBlockDiag`](../tf/linalg/LinearOperatorBlockDiag): Combines one or more `LinearOperators` in to a Block Diagonal matrix.

[`class LinearOperatorCirculant`](../tf/linalg/LinearOperatorCirculant): `LinearOperator` acting like a circulant matrix.

[`class LinearOperatorCirculant2D`](../tf/linalg/LinearOperatorCirculant2D): `LinearOperator` acting like a block circulant matrix.

[`class LinearOperatorCirculant3D`](../tf/linalg/LinearOperatorCirculant3D): `LinearOperator` acting like a nested block circulant matrix.

[`class LinearOperatorComposition`](../tf/linalg/LinearOperatorComposition): Composes one or more `LinearOperators`.

[`class LinearOperatorDiag`](../tf/linalg/LinearOperatorDiag): `LinearOperator` acting like a [batch] square diagonal matrix.

[`class LinearOperatorFullMatrix`](../tf/linalg/LinearOperatorFullMatrix): `LinearOperator` that wraps a [batch] matrix.

[`class LinearOperatorIdentity`](../tf/linalg/LinearOperatorIdentity): `LinearOperator` acting like a [batch] square identity matrix.

[`class LinearOperatorKronecker`](../tf/linalg/LinearOperatorKronecker): Kronecker product between two `LinearOperators`.

[`class LinearOperatorLowRankUpdate`](../tf/linalg/LinearOperatorLowRankUpdate): Perturb a `LinearOperator` with a rank `K` update.

[`class LinearOperatorLowerTriangular`](../tf/linalg/LinearOperatorLowerTriangular): `LinearOperator` acting like a [batch] square lower triangular matrix.

[`class LinearOperatorScaledIdentity`](../tf/linalg/LinearOperatorScaledIdentity): `LinearOperator` acting like a scaled [batch] identity matrix `A = c I`.

## Functions

[`adjoint(...)`](../tf/linalg/adjoint): Transposes the last two dimensions of and conjugates tensor `matrix`.

[`band_part(...)`](../tf/matrix_band_part): Copy a tensor setting everything outside a central band in each innermost matrix

[`cholesky(...)`](../tf/cholesky): Computes the Cholesky decomposition of one or more square matrices.

[`cholesky_solve(...)`](../tf/cholesky_solve): Solves systems of linear eqns `A X = RHS`, given Cholesky factorizations.

[`cross(...)`](../tf/cross): Compute the pairwise cross product.

[`det(...)`](../tf/matrix_determinant): Computes the determinant of one or more square matrices.

[`diag(...)`](../tf/matrix_diag): Returns a batched diagonal tensor with a given batched diagonal values.

[`diag_part(...)`](../tf/matrix_diag_part): Returns the batched diagonal part of a batched tensor.

[`eigh(...)`](../tf/self_adjoint_eig): Computes the eigen decomposition of a batch of self-adjoint matrices.

[`eigvalsh(...)`](../tf/self_adjoint_eigvals): Computes the eigenvalues of one or more self-adjoint matrices.

[`einsum(...)`](../tf/einsum): A generalized contraction between tensors of arbitrary dimension.

[`expm(...)`](../tf/linalg/expm): Computes the matrix exponential of one or more square matrices:

[`eye(...)`](../tf/eye): Construct an identity matrix, or a batch of matrices.

[`inv(...)`](../tf/matrix_inverse): Computes the inverse of one or more square invertible matrices or their

[`logdet(...)`](../tf/linalg/logdet): Computes log of the determinant of a hermitian positive definite matrix.

[`logm(...)`](../tf/linalg/logm): Computes the matrix logarithm of one or more square matrices:

[`lstsq(...)`](../tf/matrix_solve_ls): Solves one or more linear least-squares problems.

[`norm(...)`](../tf/norm): Computes the norm of vectors, matrices, and tensors. (deprecated arguments)

[`qr(...)`](../tf/qr): Computes the QR decompositions of one or more matrices.

[`set_diag(...)`](../tf/matrix_set_diag): Returns a batched matrix tensor with new batched diagonal values.

[`slogdet(...)`](../tf/linalg/slogdet): Computes the sign and the log of the absolute value of the determinant of

[`solve(...)`](../tf/matrix_solve): Solves systems of linear equations.

[`svd(...)`](../tf/svd): Computes the singular value decompositions of one or more matrices.

[`tensor_diag(...)`](../tf/diag): Returns a diagonal tensor with a given diagonal values.

[`tensor_diag_part(...)`](../tf/diag_part): Returns the diagonal part of the tensor.

[`tensordot(...)`](../tf/tensordot): Tensor contraction of a and b along specified axes.

[`trace(...)`](../tf/trace): Compute the trace of a tensor `x`.

[`transpose(...)`](../tf/matrix_transpose): Transposes last two dimensions of tensor `a`.

[`triangular_solve(...)`](../tf/matrix_triangular_solve): Solves systems of linear equations with upper or lower triangular matrices by

