page_type: reference
<style> table img { max-width: 100%; } </style>

<!-- DO NOT EDIT! Automatically generated file. -->

# tf.contrib.framework.get_local_variables

``` python
tf.contrib.framework.get_local_variables(
    scope=None,
    suffix=None
)
```



Defined in [`tensorflow/contrib/framework/python/ops/variables.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.9/tensorflow/contrib/framework/python/ops/variables.py).

See the guide: [Framework (contrib) > Variables](../../../../../api_guides/python/contrib.framework#Variables)

Gets the list of local variables, filtered by scope and/or suffix.

#### Args:

* <b>`scope`</b>: an optional scope for filtering the variables to return.
* <b>`suffix`</b>: an optional suffix for filtering the variables to return.


#### Returns:

a list of variables in collection with scope and suffix.