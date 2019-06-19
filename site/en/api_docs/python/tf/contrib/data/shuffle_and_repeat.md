

page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>


<!-- DO NOT EDIT! Automatically generated file. -->

# tf.contrib.data.shuffle_and_repeat

``` python
tf.contrib.data.shuffle_and_repeat(
    buffer_size,
    count=None,
    seed=None
)
```



Defined in [`tensorflow/contrib/data/python/ops/shuffle_ops.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.8/tensorflow/contrib/data/python/ops/shuffle_ops.py).

See the guide: [Dataset Input Pipeline > Transformations on existing datasets](../../../../../api_guides/python/input_dataset#Transformations_on_existing_datasets)

Shuffles and repeats a Dataset returning a new permutation for each epoch.

`dataset.apply(tf.contrib.data.shuffle_and_repeat(buffer_size, count))`

is equivalent to

`dataset.shuffle(buffer_size, reshuffle_each_iteration=True).repeat(count)`

The difference is that the latter dataset is not serializable. So,
if you need to checkpoint an input pipeline with reshuffling you must use
this implementation.

#### Args:

* <b>`buffer_size`</b>: A <a href="../../../tf/int64"><code>tf.int64</code></a> scalar <a href="../../../tf/Tensor"><code>tf.Tensor</code></a>, representing the
    maximum number elements that will be buffered when prefetching.
* <b>`count`</b>: (Optional.) A <a href="../../../tf/int64"><code>tf.int64</code></a> scalar <a href="../../../tf/Tensor"><code>tf.Tensor</code></a>, representing the
    number of times the dataset should be repeated. The default behavior
    (if `count` is `None` or `-1`) is for the dataset be repeated
    indefinitely.
* <b>`seed`</b>: (Optional.) A <a href="../../../tf/int64"><code>tf.int64</code></a> scalar <a href="../../../tf/Tensor"><code>tf.Tensor</code></a>, representing the
    random seed that will be used to create the distribution. See
    <a href="../../../tf/set_random_seed"><code>tf.set_random_seed</code></a> for behavior.


#### Returns:

A `Dataset` transformation function, which can be passed to
<a href="../../../tf/data/Dataset#apply"><code>tf.data.Dataset.apply</code></a>.