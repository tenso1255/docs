

page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>


<!-- DO NOT EDIT! Automatically generated file. -->

# tf.keras.datasets.mnist.load_data

``` python
tf.keras.datasets.mnist.load_data(path='mnist.npz')
```



Defined in [`tensorflow/python/keras/_impl/keras/datasets/mnist.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.8/tensorflow/python/keras/_impl/keras/datasets/mnist.py).

Loads the MNIST dataset.

#### Arguments:

* <b>`path`</b>: path where to cache the dataset locally
        (relative to ~/.keras/datasets).


#### Returns:

Tuple of Numpy arrays: `(x_train, y_train), (x_test, y_test)`.