#   Copyright (c) 2019 PaddlePaddle Authors. All Rights Reserved.
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

import unittest

import gradient_checker
import numpy as np
from decorator_helper import prog_scope

import paddle
import paddle.fluid as fluid
import paddle.fluid.core as core


class TestElementwiseMulDoubleGradCheck(unittest.TestCase):
    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.005
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape, dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.multiply(x, y)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape).astype(dtype)

        gradient_checker.double_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


class TestElementwiseMulBroadcastDoubleGradCheck(unittest.TestCase):
    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.005
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape[:-1], dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.tensor.math._multiply_with_axis(x, y, axis=0)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape[:-1]).astype(dtype)

        gradient_checker.double_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


class TestElementwiseAddDoubleGradCheck(unittest.TestCase):
    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.005
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape, dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.add(x, y)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape).astype(dtype)

        gradient_checker.double_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


class TestElementwiseAddBroadcastDoubleGradCheck(unittest.TestCase):
    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.005
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape[:-1], dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.tensor.math._add_with_axis(x, y, axis=0)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape[:-1]).astype(dtype)

        gradient_checker.double_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


class TestElementwiseSubDoubleGradCheck(unittest.TestCase):
    def subtract_wrapper(self, x):
        return paddle.subtract(x[0], x[1])

    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.005
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape, dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.subtract(x, y)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape).astype(dtype)

        gradient_checker.double_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps
        )
        gradient_checker.double_grad_check_for_dygraph(
            self.subtract_wrapper,
            [x, y],
            out,
            x_init=[x_arr, y_arr],
            place=place,
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


class TestElementwiseSubBroadcastDoubleGradCheck(unittest.TestCase):
    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.005
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape[:-1], dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.tensor.math._subtract_with_axis(x, y, axis=0)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape[:-1]).astype(dtype)

        gradient_checker.double_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


class TestElementwiseDivDoubleGradCheck(unittest.TestCase):
    def divide_wrapper(self, x):
        return paddle.divide(x[0], x[1])

    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.0001
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape, dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.tensor.math._divide_with_axis(x, y, axis=0)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr[np.abs(y_arr) < 0.005] = 0.02

        gradient_checker.double_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps, atol=1e-3
        )
        gradient_checker.double_grad_check_for_dygraph(
            self.divide_wrapper,
            [x, y],
            out,
            x_init=[x_arr, y_arr],
            place=place,
            atol=1e-3,
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


class TestElementwiseDivBroadcastDoubleGradCheck(unittest.TestCase):
    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.0001
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape[1:-1], dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.tensor.math._divide_with_axis(x, y, axis=1)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape[1:-1]).astype(dtype)
        y_arr[np.abs(y_arr) < 0.005] = 0.02

        gradient_checker.double_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps, atol=1e-3
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


class TestElementwiseAddTripleGradCheck(unittest.TestCase):
    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.005
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape, dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.add(x, y)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape).astype(dtype)

        gradient_checker.triple_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


class TestElementwiseAddBroadcastTripleGradCheck(unittest.TestCase):
    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.005
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape[:-1], dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.tensor.math._add_with_axis(x, y, axis=0)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape[:-1]).astype(dtype)

        gradient_checker.triple_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


class TestElementwiseMulTripleGradCheck(unittest.TestCase):
    def multiply_wrapper(self, x):
        return paddle.multiply(x[0], x[1])

    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.005
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape, dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.multiply(x, y)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape).astype(dtype)

        gradient_checker.triple_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps
        )
        gradient_checker.triple_grad_check_for_dygraph(
            self.multiply_wrapper,
            [x, y],
            out,
            x_init=[x_arr, y_arr],
            place=place,
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


class TestElementwiseMulBroadcastTripleGradCheck(unittest.TestCase):
    @prog_scope()
    def func(self, place):
        # the shape of input variable should be clearly specified, not inlcude -1.
        shape = [2, 3, 4, 5]
        eps = 0.005
        dtype = np.float64

        x = paddle.static.data('x', shape, dtype)
        y = paddle.static.data('y', shape[:-1], dtype)
        x.persistable = True
        y.persistable = True
        out = paddle.tensor.math._add_with_axis(x, y, axis=0)
        x_arr = np.random.uniform(-1, 1, shape).astype(dtype)
        y_arr = np.random.uniform(-1, 1, shape[:-1]).astype(dtype)

        gradient_checker.triple_grad_check(
            [x, y], out, x_init=[x_arr, y_arr], place=place, eps=eps
        )

    def test_grad(self):
        paddle.enable_static()
        places = [fluid.CPUPlace()]
        if core.is_compiled_with_cuda():
            places.append(fluid.CUDAPlace(0))
        for p in places:
            self.func(p)


if __name__ == "__main__":
    unittest.main()
