page_type: reference
<style>{% include "site-assets/css/style.css" %}</style>

<!-- DO NOT EDIT! Automatically generated file. -->

# Module: tf.nn.rnn_cell



Defined in [`tensorflow/nn/rnn_cell/__init__.py`](https://www.github.com/tensorflow/tensorflow/blob/r1.10/tensorflow/nn/rnn_cell/__init__.py).

Module for constructing RNN Cells.

## Classes

[`class BasicLSTMCell`](../../tf/contrib/rnn/BasicLSTMCell): Basic LSTM recurrent network cell.

[`class BasicRNNCell`](../../tf/contrib/rnn/BasicRNNCell): The most basic RNN cell.

[`class DeviceWrapper`](../../tf/contrib/rnn/DeviceWrapper): Operator that ensures an RNNCell runs on a particular device.

[`class DropoutWrapper`](../../tf/contrib/rnn/DropoutWrapper): Operator adding dropout to inputs and outputs of the given cell.

[`class GRUCell`](../../tf/contrib/rnn/GRUCell): Gated Recurrent Unit cell (cf. http://arxiv.org/abs/1406.1078).

[`class LSTMCell`](../../tf/contrib/rnn/LSTMCell): Long short-term memory unit (LSTM) recurrent network cell.

[`class LSTMStateTuple`](../../tf/contrib/rnn/LSTMStateTuple): Tuple used by LSTM Cells for `state_size`, `zero_state`, and output state.

[`class MultiRNNCell`](../../tf/contrib/rnn/MultiRNNCell): RNN cell composed sequentially of multiple simple cells.

[`class RNNCell`](../../tf/contrib/rnn/RNNCell): Abstract object representing an RNN cell.

[`class ResidualWrapper`](../../tf/contrib/rnn/ResidualWrapper): RNNCell wrapper that ensures cell inputs are added to the outputs.

