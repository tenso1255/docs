

page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>


<!-- DO NOT EDIT! Automatically generated file. -->

# tf.keras.initializers.glorot_uniform

``` python
tf.keras.initializers.glorot_uniform(seed=None)
```



Defined in [`tensorflow/python/keras/_impl/keras/initializers.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.8/tensorflow/python/keras/_impl/keras/initializers.py).

Glorot uniform initializer, also called Xavier uniform initializer.

It draws samples from a uniform distribution within [-limit, limit]
where `limit` is `sqrt(6 / (fan_in + fan_out))`
where `fan_in` is the number of input units in the weight tensor
and `fan_out` is the number of output units in the weight tensor.

#### Arguments:

* <b>`seed`</b>: A Python integer. Used to seed the random generator.


#### Returns:

    An initializer.

References:
    Glorot & Bengio, AISTATS 2010
    http://jmlr.org/proceedings/papers/v9/glorot10a/glorot10a.pdf