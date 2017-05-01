import mock
import unittest

import numpy

import chainer
from chainer import cuda
from chainer import functions
from chainer.functions.connection import convolution_2d
from chainer import gradient_check
from chainer import testing
from chainer.testing import attr
from chainer.testing import condition

@testing.parameterize(*(testing.product({
    'c_contiguous': [True, False],
    'cover_all': [True, False],
    'x_dtype': [numpy.float32],
    'W_dtype': [numpy.float32],
}) + testing.product({
    'c_contiguous': [False],
    'cover_all': [False],
    'x_dtype': [numpy.float16, numpy.float32, numpy.float64],
    'W_dtype': [numpy.float16, numpy.float32, numpy.float64],
})))
class TestConvolution2DFunctionMKLDNN(unittest.TestCase):

    def setUp(self):
        in_channels = 3
        out_channels = 2
        kh, kw = (3, 3)
        self.stride = 2
        self.pad = 1
        self.use_mkldnn = 'always'
        self.W = numpy.random.normal(
            0, numpy.sqrt(1. / (kh * kw * in_channels)),
            (out_channels, in_channels, kh, kw)).astype(self.W_dtype)
        self.b = numpy.random.uniform(
            -1, 1, out_channels).astype(self.x_dtype)

        self.x = numpy.random.uniform(
            -1, 1, (2, 3, 4, 3)).astype(self.x_dtype)
        if self.cover_all:
            self.gy = numpy.random.uniform(-1, 1,
                                           (2, 2, 3, 2)).astype(self.x_dtype)
        else:
            self.gy = numpy.random.uniform(
                -1, 1, (2, 2, 2, 2)).astype(self.x_dtype)
        self.check_forward_options = {}
        self.check_backward_options = {'dtype': numpy.float64}
        if self.x_dtype == numpy.float16 or self.W_dtype == numpy.float16:
            self.check_forward_options = {'atol': 5e-4, 'rtol': 5e-3}
            self.check_backward_options = {
                'dtype': numpy.float64, 'atol': 5e-4, 'rtol': 5e-3}

    def test_forward_consistency(self, nobias=False):
        x_cpu = chainer.Variable(self.x)
        W_cpu = chainer.Variable(self.W)
        b_cpu = None if nobias else chainer.Variable(self.b)
        with chainer.using_config('use_mkldnn', 'never'):
            y_cpu = functions.convolution_2d(
                x_cpu, W_cpu, b_cpu, stride=self.stride, pad=self.pad,
                cover_all=self.cover_all)

        x_mkl = chainer.Variable(self.x)
        W_mkl = chainer.Variable(self.W)
        b_mkl = None if nobias else chainer.Variable(self.b)
        with chainer.using_config('use_mkldnn', self.use_mkldnn):
            y_mkl = functions.convolution_2d(
                x_mkl, W_mkl, b_mkl, stride=self.stride, pad=self.pad,
                cover_all=self.cover_all)

        testing.assert_allclose(
            y_mkl.data, y_mkl.data.get(), **self.check_forward_options)

    def check_backward(self, x_data, W_data, b_data, y_grad):
        xp = cuda.get_array_module(x_data)
        if not self.c_contiguous:
            x_data = xp.asfortranarray(x_data)
            W_data = xp.asfortranarray(W_data)
            y_grad = xp.asfortranarray(y_grad)
            self.assertFalse(x_data.flags.c_contiguous)
            self.assertFalse(W_data.flags.c_contiguous)
            self.assertFalse(y_grad.flags.c_contiguous)
            if b_data is not None:
                b = xp.empty((len(b_data) * 2,), dtype=self.b.dtype)
                b[::2] = b_data
                b_data = b[::2]
                self.assertFalse(b_data.flags.c_contiguous)

        args = (x_data, W_data)
        if b_data is not None:
            args = args + (b_data,)

        with chainer.using_config('use_mkldnn', self.use_cudnn):
            gradient_check.check_backward(
                convolution_2d.Convolution2DFunction(
                    self.stride, self.pad, self.cover_all),
                args, y_grad, **self.check_backward_options)

    @condition.retry(3)
    def test_backward_cpu(self):
        self.check_backward(self.x, self.W, self.b, self.gy)

    @condition.retry(3)
    def test_backward_cpu_nobias(self):
        self.check_backward(self.x, self.W, None, self.gy)

testing.run_module(__name__, __file__)
