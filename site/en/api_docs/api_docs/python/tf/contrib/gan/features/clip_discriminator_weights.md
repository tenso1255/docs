

page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>


<!-- DO NOT EDIT! Automatically generated file. -->

# tf.contrib.gan.features.clip_discriminator_weights

``` python
tf.contrib.gan.features.clip_discriminator_weights(
    optimizer,
    model,
    weight_clip
)
```



Defined in [`tensorflow/contrib/gan/python/features/python/clip_weights_impl.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.10/tensorflow/contrib/gan/python/features/python/clip_weights_impl.py).

Modifies an optimizer so it clips weights to a certain value.

#### Args:

* <b>`optimizer`</b>: An optimizer to perform variable weight clipping.
* <b>`model`</b>: A GANModel namedtuple.
* <b>`weight_clip`</b>: Positive python float to clip discriminator weights. Used to
    enforce a K-lipschitz condition, which is useful for some GAN training
    schemes (ex WGAN: https://arxiv.org/pdf/1701.07875).


#### Returns:

An optimizer to perform weight clipping after updates.


#### Raises:

* <b>`ValueError`</b>: If `weight_clip` is less than 0.