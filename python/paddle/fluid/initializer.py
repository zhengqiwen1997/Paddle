#   Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import math
import functools
from . import framework
from . import core
from .framework import (
    in_dygraph_mode,
    default_main_program,
    _current_expected_place,
)
from .lazy_init import lazy_init_helper
from .framework import program_guard
import numpy as np
from .core import VarDesc
from . import unique_name
from .data_feeder import check_variable_and_dtype, check_type, check_dtype
from paddle import _C_ops, _legacy_C_ops
import paddle

__all__ = [
    'Bilinear',
    'BilinearInitializer',
    'NumpyArrayInitializer',
    'set_global_initializer',
]

_global_weight_initializer_ = None
_global_bias_initializer_ = None


class BilinearInitializer(Initializer):
    """
    This initializer can be used in transposed convolution operator to
    act as upsampling. Users can upsample a feature map with shape of
    (B, C, H, W) by any integer factor. The usage is:

    Examples:

        .. code-block:: python

            import math

            import paddle
            import paddle.nn as nn
            from paddle.regularizer import L2Decay

            factor = 2
            C = 2
            B = 8
            H = W = 32
            w_attr = paddle.ParamAttr(learning_rate=0.,
                                      regularizer=L2Decay(0.),
                                      initializer=nn.initializer.Bilinear())
            data = paddle.rand([B, 3, H, W], dtype='float32')
            conv_up = nn.Conv2DTranspose(3,
                                         out_channels=C,
                                         kernel_size=2 * factor - factor % 2,
                                         padding=int(
                                             math.ceil((factor - 1) / 2.)),
                                         stride=factor,
                                         weight_attr=w_attr,
                                         bias_attr=False)
            x = conv_up(data)

    Where, `out_channels=C` and `groups=C` means this is channel-wise transposed
    convolution. The filter shape will be (C, 1, K, K) where K is `kernel_size`,
    This initializer will set a (K, K) interpolation kernel for every channel
    of the filter identically. The resulting shape of the output feature map
    will be (B, C, factor * H, factor * W). Note that the learning rate and the
    weight decay are set to 0 in order to keep coefficient values of bilinear
    interpolation unchanged during training.

    """

    def __init__(self):
        """Constructor for BilinearInitializer."""
        super().__init__()

    def forward(self, var, block=None):
        """Initialize the input tensor with Bilinear initialization.

        Args:
            var(Tensor): Tensor that needs to be initialized.
            block(Block, optional): The block in which initialization ops
                   should be added. Used in static graph only, default None.

        Returns:
            The initialization op
        """
        block = self._check_block(block)

        if not isinstance(var, framework.Variable):
            raise ValueError("var must be framework.Variable.")

        if not isinstance(block, framework.Block):
            raise ValueError("block must be framework.Block.")

        shape = var.shape
        if len(shape) != 4:
            raise ValueError("the length of shape must be 4.")
        if shape[2] != shape[3]:
            raise ValueError("shape[2] must be equal to shape[3].")

        weight = np.zeros(np.prod(var.shape), dtype='float32')
        size = shape[3]
        # factor
        f = np.ceil(size / 2.0)
        # center
        c = (2 * f - 1 - f % 2) / (2.0 * f)
        for i in range(np.prod(shape)):
            x = i % size
            y = (i / size) % size
            weight[i] = (1 - abs(x / f - c)) * (1 - abs(y / f - c))
        weight = np.reshape(weight, shape)

        # to be compatible of fp16 initalizers
        if var.dtype in [
            VarDesc.VarType.FP16,
            VarDesc.VarType.BF16,
            VarDesc.VarType.FP64,
        ]:
            out_dtype = VarDesc.VarType.FP32
            out_var = block.create_var(
                name=unique_name.generate(
                    ".".join(['bilinear_init', var.name, 'tmp'])
                ),
                shape=var.shape,
                dtype=out_dtype,
                type=VarDesc.VarType.LOD_TENSOR,
                persistable=False,
            )
        else:
            out_dtype = var.dtype
            out_var = var

        if out_dtype == VarDesc.VarType.FP32:
            value_name = "fp32_values"
            values = [float(v) for v in weight.flat]
        else:
            raise TypeError("Unsupported dtype %s", var.dtype)

        if np.prod(shape) > 1024 * 1024:
            raise ValueError("The size of input is too big. ")

        if in_dygraph_mode():
            _C_ops.assign_value_(
                out_var,
                list(shape),
                out_dtype,
                values,
                _current_expected_place(),
            )
            if var.dtype in [
                VarDesc.VarType.FP16,
                VarDesc.VarType.BF16,
                VarDesc.VarType.FP64,
            ]:
                var_tmp = _C_ops.cast(out_var, var.dtype)
                var_tmp._share_underline_tensor_to(var)
            else:
                out_var._share_underline_tensor_to(var)
            return None
        else:
            op = block.append_op(
                type='assign_value',
                outputs={'Out': [out_var]},
                attrs={
                    'dtype': out_dtype,
                    'shape': list(shape),
                    value_name: values,
                },
            )

            if var.dtype in [
                VarDesc.VarType.FP16,
                VarDesc.VarType.BF16,
                VarDesc.VarType.FP64,
            ]:
                block.append_op(
                    type="cast",
                    inputs={"X": out_var},
                    outputs={"Out": var},
                    attrs={"in_dtype": out_var.dtype, "out_dtype": var.dtype},
                )

            var.op = op
            return op


class NumpyArrayInitializer(Initializer):
    """Init an parameter with an numpy array
    This op initialize the variable by numpy array.

    Args:
        value (numpy): numpy array to initialize the variable

    Returns:
        A Tensor variable initialized by numpy.

    Examples:
        .. code-block:: python

            import paddle
            import paddle.fluid as fluid
            import numpy
            paddle.enable_static()
            x = fluid.data(name="x", shape=[2, 1], dtype='float32')
            fc = paddle.static.nn.fc(x, size=10,
                weight_attr=fluid.initializer.NumpyArrayInitializer(numpy.array([1,2])))
    """

    def __init__(self, value):
        import numpy

        assert isinstance(value, numpy.ndarray)
        super().__init__()
        self._value = value

    def forward(self, var, block=None):
        """Initialize the input tensor with Numpy array.

        Args:
            var(Tensor): Tensor that needs to be initialized.
            block(Block, optional): The block in which initialization ops
                   should be added. Used in static graph only, default None.

        Returns:
            The initialization op
        """
        block = self._check_block(block)

        assert isinstance(var, framework.Variable)
        assert isinstance(block, framework.Block)

        # to be compatible of fp16 initalizers
        if var.dtype in [VarDesc.VarType.FP16, VarDesc.VarType.BF16]:
            out_dtype = VarDesc.VarType.FP32
            np_value = self._value.astype("float32")
            out_var = block.create_var(
                name=unique_name.generate(
                    ".".join(['numpy_array_init', var.name, 'tmp'])
                ),
                shape=var.shape,
                dtype=out_dtype,
                type=VarDesc.VarType.LOD_TENSOR,
                persistable=False,
            )
        else:
            out_var = var
            out_dtype = var.dtype
            np_value = self._value

        if out_dtype == VarDesc.VarType.FP32:
            value_name = "fp32_values"
            values = [float(v) for v in np_value.flat]
        elif out_dtype == VarDesc.VarType.INT32:
            value_name = "int32_values"
            values = [int(v) for v in np_value.flat]
        else:
            raise ValueError("Unsupported dtype %s", self._value.dtype)
        if self._value.size > 1024 * 1024 * 1024:
            raise ValueError(
                "The size of input is too big. Please consider "
                "saving it to file and 'load_op' to load it"
            )

        if in_dygraph_mode():
            _C_ops.assign_value_(
                out_var,
                list(self._value.shape),
                out_dtype,
                values,
                _current_expected_place(),
            )
            if var.dtype in [VarDesc.VarType.FP16, VarDesc.VarType.BF16]:
                var_tmp = _C_ops.cast(out_var, var.dtype)
                var_tmp._share_underline_tensor_to(var)
            else:
                out_var._share_underline_tensor_to(var)
            return None
        else:
            op = block.append_op(
                type='assign_value',
                outputs={'Out': out_var},
                attrs={
                    'dtype': out_dtype,
                    'shape': list(self._value.shape),
                    value_name: values,
                },
                stop_gradient=True,
            )

            if var.dtype in [VarDesc.VarType.FP16, VarDesc.VarType.BF16]:
                block.append_op(
                    type="cast",
                    inputs={"X": out_var},
                    outputs={"Out": var},
                    attrs={"in_dtype": out_var.dtype, "out_dtype": var.dtype},
                )

            var.op = op
            return op


def set_global_initializer(weight_init, bias_init=None):
    """
    This API is used to set up global model parameter initializer in framework.

    After this API is invoked, the global initializer will takes effect in subsequent code.

    The model parameters include ``weight`` and ``bias`` . In the framework, they correspond
    to ``paddle.ParamAttr`` , which is inherited from ``paddle.Tensor`` , and is a persistable Variable.
    This API only takes effect for model parameters, not for variables created through apis such as
    :ref:`api_fluid_layers_create_global_var` , :ref:`api_fluid_layers_create_tensor`.

    If the initializer is also set up by ``param_attr`` or ``bias_attr`` when creating a network layer,
    the global initializer setting here will not take effect because it has a lower priority.

    If you want to cancel the global initializer in framework, please set global initializer to ``None`` .

    Args:
        weight_init (Initializer): set the global initializer for ``weight`` of model parameters.
        bias_init (Initializer, optional): set the global initializer for ``bias`` of model parameters.
            Default: None.

    Returns:
        None

    Examples:
        .. code-block:: python

            import paddle
            import paddle.nn as nn

            nn.initializer.set_global_initializer(nn.initializer.Uniform(), nn.initializer.Constant())
            x_var = paddle.uniform((2, 4, 8, 8), dtype='float32', min=-1., max=1.)

            # The weight of conv1 is initialized by Uniform
            # The bias of conv1 is initialized by Constant
            conv1 = nn.Conv2D(4, 6, (3, 3))
            y_var1 = conv1(x_var)

            # If set param_attr/bias_attr too, global initializer will not take effect
            # The weight of conv2 is initialized by Xavier
            # The bias of conv2 is initialized by Normal
            conv2 = nn.Conv2D(4, 6, (3, 3),
                weight_attr=nn.initializer.XavierUniform(),
                bias_attr=nn.initializer.Normal())
            y_var2 = conv2(x_var)

            # Cancel the global initializer in framework, it will takes effect in subsequent code
            nn.initializer.set_global_initializer(None)
    """

    check_type(
        weight_init,
        'weight_init',
        (Initializer, type(None)),
        'set_global_initializer',
    )
    global _global_weight_initializer_
    _global_weight_initializer_ = weight_init

    check_type(
        bias_init,
        'bias_init',
        (Initializer, type(None)),
        'set_global_initializer',
    )
    global _global_bias_initializer_
    _global_bias_initializer_ = bias_init


def _global_weight_initializer():
    """
    Return the global weight initializer, The user doesn't need to use it.
    """
    return _global_weight_initializer_


def _global_bias_initializer():
    """
    Return the global weight initializer, The user doesn't need to use it.
    """
    return _global_bias_initializer_


def calculate_gain(nonlinearity, param=None):
    """
    Get the recommended ``gain`` value of some nonlinearity function. ``gain`` value can be used in some
    ``paddle.nn.initializer`` api to adjust the initialization value.

    Args:
        nonlinearity(str): name of nonlinearity activation function. If it is a linear function, such as:
            `linear/conv1d/conv2d/conv3d/conv1d_transpose/conv2d_transpose/conv3d_transpose` , 1.0 will be returned.
        param(bool|int|float, optional): optional parameter for somme nonlinearity function. Now, it only applies to
            'leaky_relu'. Default: None, it will be calculated as 0.01 in the formula.

    Returns:
        A float value, which is the recommended gain for this nonlinearity function.

    Examples:
        .. code-block:: python

            import paddle
            gain = paddle.nn.initializer.calculate_gain('tanh') # 5.0 / 3
            gain = paddle.nn.initializer.calculate_gain('leaky_relu', param=1.0) # 1.0 = math.sqrt(2.0 / (1+param^2))
            initializer = paddle.nn.initializer.Orthogonal(gain)

    """
    if param is None:
        param = 0.01
    else:
        assert isinstance(param, (bool, int, float))
        param = float(param)
    recommended_gain = {
        'sigmoid': 1,
        'linear': 1,
        'conv1d': 1,
        'conv2d': 1,
        'conv3d': 1,
        'conv1d_transpose': 1,
        'conv2d_transpose': 1,
        'conv3d_transpose': 1,
        'tanh': 5.0 / 3,
        'relu': math.sqrt(2.0),
        'leaky_relu': math.sqrt(2.0 / (1 + param**2)),
        'selu': 3.0 / 4,
    }
    if nonlinearity in recommended_gain.keys():
        return recommended_gain[nonlinearity]
    else:
        raise ValueError(
            "nonlinearity function {} is not suppported now.".format(
                nonlinearity
            )
        )


# We short the class name, since users will use the initializer with the package
# name. The sample code:
#
# import paddle
# import paddle.fluid as fluid
#
# hidden = paddle.static.nn.fc(...,
#                          weight_attr=ParamAttr(fluid.initializer.Xavier()))
#
# It is no need to add an `Initializer` as the class suffix
Bilinear = BilinearInitializer
