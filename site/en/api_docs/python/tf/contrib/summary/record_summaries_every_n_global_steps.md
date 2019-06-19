

page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>


<!-- DO NOT EDIT! Automatically generated file. -->

# tf.contrib.summary.record_summaries_every_n_global_steps

``` python
tf.contrib.summary.record_summaries_every_n_global_steps(
    n,
    global_step=None
)
```



Defined in [`tensorflow/contrib/summary/summary_ops.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.8/tensorflow/contrib/summary/summary_ops.py).

Sets the should_record_summaries Tensor to true if global_step % n == 0.