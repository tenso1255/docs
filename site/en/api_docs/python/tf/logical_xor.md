page_type: reference
<style> table img { max-width: 100%; } </style>

<!-- DO NOT EDIT! Automatically generated file. -->

# tf.logical_xor

``` python
tf.logical_xor(
    x,
    y,
    name='LogicalXor'
)
```



Defined in [`tensorflow/python/ops/math_ops.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.9/tensorflow/python/ops/math_ops.py).

See the guide: [Control Flow > Logical Operators](../../../api_guides/python/control_flow_ops#Logical_Operators)

x ^ y = (x | y) & ~(x & y).