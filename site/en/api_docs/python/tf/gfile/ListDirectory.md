page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>

<!-- DO NOT EDIT! Automatically generated file. -->

# tf.gfile.ListDirectory

``` python
tf.gfile.ListDirectory(dirname)
```



Defined in [`tensorflow/python/lib/io/file_io.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.11/tensorflow/python/lib/io/file_io.py).

Returns a list of entries contained within a directory.

The list is in arbitrary order. It does not contain the special entries "."
and "..".

#### Args:

* <b>`dirname`</b>: string, path to a directory


#### Returns:

[filename1, filename2, ... filenameN] as strings


#### Raises:

errors.NotFoundError if directory doesn't exist