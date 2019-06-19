

page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>


<!-- DO NOT EDIT! Automatically generated file. -->

# tf.contrib.layers.check_feature_columns

``` python
tf.contrib.layers.check_feature_columns(feature_columns)
```



Defined in [`tensorflow/contrib/layers/python/layers/feature_column_ops.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.8/tensorflow/contrib/layers/python/layers/feature_column_ops.py).

See the guide: [Layers (contrib) > Feature columns](../../../../../api_guides/python/contrib.layers#Feature_columns)

Checks the validity of the set of FeatureColumns.

#### Args:

* <b>`feature_columns`</b>: An iterable of instances or subclasses of FeatureColumn.


#### Raises:

* <b>`ValueError`</b>: If `feature_columns` is a dict.
* <b>`ValueError`</b>: If there are duplicate feature column keys.