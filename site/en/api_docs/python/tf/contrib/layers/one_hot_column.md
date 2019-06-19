page_type: reference
<style> table img { max-width: 100%; } </style>

<!-- DO NOT EDIT! Automatically generated file. -->

# tf.contrib.layers.one_hot_column

``` python
tf.contrib.layers.one_hot_column(sparse_id_column)
```



Defined in [`tensorflow/contrib/layers/python/layers/feature_column.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.9/tensorflow/contrib/layers/python/layers/feature_column.py).

See the guide: [Layers (contrib) > Feature columns](../../../../../api_guides/python/contrib.layers#Feature_columns)

Creates an `_OneHotColumn` for a one-hot or multi-hot repr in a DNN.

#### Args:

* <b>`sparse_id_column`</b>: A _SparseColumn which is created by
      `sparse_column_with_*`
      or crossed_column functions. Note that `combiner` defined in
      `sparse_id_column` is ignored.


#### Returns:

An _OneHotColumn.