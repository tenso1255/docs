page_type: reference
<style> table img { max-width: 100%; } </style>

<!-- DO NOT EDIT! Automatically generated file. -->

# tf.keras.backend.eye

``` python
tf.keras.backend.eye(
    size,
    dtype=None,
    name=None
)
```



Defined in [`tensorflow/python/keras/backend.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.9/tensorflow/python/keras/backend.py).

Instantiate an identity matrix and returns it.

#### Arguments:

* <b>`size`</b>: Integer, number of rows/columns.
* <b>`dtype`</b>: String, data type of returned Keras variable.
* <b>`name`</b>: String, name of returned Keras variable.


#### Returns:

    A Keras variable, an identity matrix.

Example:
```python
    >>> from keras import backend as K
    >>> kvar = K.eye(3)
    >>> K.eval(kvar)
    array([[ 1.,  0.,  0.],
           [ 0.,  1.,  0.],
           [ 0.,  0.,  1.]], dtype=float32)
```