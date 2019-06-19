page_type: reference
<style> table img { max-width: 100%; } </style>

<!-- DO NOT EDIT! Automatically generated file. -->

# tf.ones

``` python
tf.ones(
    shape,
    dtype=tf.float32,
    name=None
)
```



Defined in [`tensorflow/python/ops/array_ops.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.9/tensorflow/python/ops/array_ops.py).

See the guide: [Constants, Sequences, and Random Values > Constant Value Tensors](../../../api_guides/python/constant_op#Constant_Value_Tensors)

Creates a tensor with all elements set to 1.

This operation returns a tensor of type `dtype` with shape `shape` and all
elements set to 1.

For example:

```python
tf.ones([2, 3], tf.int32)  # [[1, 1, 1], [1, 1, 1]]
```

#### Args:

* <b>`shape`</b>: A list of integers, a tuple of integers, or a 1-D `Tensor` of type
    `int32`.
* <b>`dtype`</b>: The type of an element in the resulting `Tensor`.
* <b>`name`</b>: A name for the operation (optional).


#### Returns:

A `Tensor` with all elements set to 1.