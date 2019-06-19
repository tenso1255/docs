page_type: reference
<style> table img { max-width: 100%; } </style>

<!-- DO NOT EDIT! Automatically generated file. -->

# tf.gfile.MakeDirs

``` python
tf.gfile.MakeDirs(dirname)
```



Defined in [`tensorflow/python/lib/io/file_io.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.9/tensorflow/python/lib/io/file_io.py).

Creates a directory and all parent/intermediate directories.

It succeeds if dirname already exists and is writable.

#### Args:

* <b>`dirname`</b>: string, name of the directory to be created


#### Raises:

* <b>`errors.OpError`</b>: If the operation fails.