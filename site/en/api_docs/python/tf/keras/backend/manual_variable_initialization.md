page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>

<!-- DO NOT EDIT! Automatically generated file. -->

# tf.keras.backend.manual_variable_initialization

``` python
tf.keras.backend.manual_variable_initialization(value)
```



Defined in [`tensorflow/python/keras/backend.py`](https://github.com/tensorflow/tensorflow/blob/r1.12/tensorflow/python/keras/backend.py).

Sets the manual variable initialization flag.

This boolean flag determines whether
variables should be initialized
as they are instantiated (default), or if
the user should handle the initialization
(e.g. via `tf.initialize_all_variables()`).

#### Arguments:

* <b>`value`</b>: Python boolean.