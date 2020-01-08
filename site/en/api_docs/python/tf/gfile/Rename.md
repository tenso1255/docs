page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>

<!-- DO NOT EDIT! Automatically generated file. -->

# tf.gfile.Rename

``` python
tf.gfile.Rename(
    oldname,
    newname,
    overwrite=False
)
```



Defined in [`tensorflow/python/lib/io/file_io.py`](https://github.com/tensorflow/tensorflow/blob/r1.12/tensorflow/python/lib/io/file_io.py).

Rename or move a file / directory.

#### Args:

* <b>`oldname`</b>: string, pathname for a file
* <b>`newname`</b>: string, pathname to which the file needs to be moved
* <b>`overwrite`</b>: boolean, if false it's an error for `newname` to be occupied by
      an existing file.


#### Raises:

* <b>`errors.OpError`</b>: If the operation fails.