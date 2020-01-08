

page_type: reference
<style> table img { max-width: 100%; } </style>


<!-- DO NOT EDIT! Automatically generated file. -->

# tf.local_variables_initializer

### Aliases:

* `tf.initializers.local_variables`
* `tf.local_variables_initializer`

``` python
tf.local_variables_initializer()
```



Defined in [`tensorflow/python/ops/variables.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.9/tensorflow/python/ops/variables.py).

See the guide: [Variables > Variable helper functions](../../../api_guides/python/state_ops#Variable_helper_functions)

Returns an Op that initializes all local variables.

This is just a shortcut for `variables_initializer(local_variables())`

#### Returns:

An Op that initializes all local variables in the graph.