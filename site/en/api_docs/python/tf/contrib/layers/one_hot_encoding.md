page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>

<!-- DO NOT EDIT! Automatically generated file. -->

# tf.contrib.layers.one_hot_encoding

``` python
tf.contrib.layers.one_hot_encoding(
    labels,
    num_classes,
    on_value=1.0,
    off_value=0.0,
    outputs_collections=None,
    scope=None
)
```



Defined in [`tensorflow/contrib/layers/python/layers/layers.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.10/tensorflow/contrib/layers/python/layers/layers.py).

See the guide: [Layers (contrib) > Higher level ops for building neural network layers](../../../../../api_guides/python/contrib.layers#Higher_level_ops_for_building_neural_network_layers)

Transform numeric labels into onehot_labels using <a href="../../../tf/one_hot"><code>tf.one_hot</code></a>.

#### Args:

* <b>`labels`</b>: [batch_size] target labels.
* <b>`num_classes`</b>: Total number of classes.
* <b>`on_value`</b>: A scalar defining the on-value.
* <b>`off_value`</b>: A scalar defining the off-value.
* <b>`outputs_collections`</b>: Collection to add the outputs.
* <b>`scope`</b>: Optional scope for name_scope.


#### Returns:

One-hot encoding of the labels.