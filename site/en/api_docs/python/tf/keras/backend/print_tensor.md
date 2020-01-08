page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>

<!-- DO NOT EDIT! Automatically generated file. -->

# tf.keras.backend.print_tensor

``` python
tf.keras.backend.print_tensor(
    x,
    message=''
)
```



Defined in [`tensorflow/python/keras/backend.py`](https://github.com/tensorflow/tensorflow/blob/r1.12/tensorflow/python/keras/backend.py).

Prints `message` and the tensor value when evaluated.

Note that `print_tensor` returns a new tensor identical to `x`
which should be used in the following code. Otherwise the
print operation is not taken into account during evaluation.

Example:

```python
   >>> x = K.print_tensor(x, message="x is: ")
```

#### Arguments:

* <b>`x`</b>: Tensor to print.
* <b>`message`</b>: Message to print jointly with the tensor.


#### Returns:

The same tensor `x`, unchanged.