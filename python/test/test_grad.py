# Copyright 2019,2020,2021 Sony Corporation.
# Copyright 2021 Sony Group Corporation.
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

import sys
import pytest
import numpy as np
import nnabla as nn
import nnabla.functions as F
import nnabla.parametric_functions as PF
import nnabla.initializer as I
from nnabla.ext_utils import get_extension_context
from nbla_test_utils import list_context
from nnabla.testing import assert_allclose
from nnabla.function import PythonFunction
from nnabla.backward_functions import registry, register

# Proxy to get the appropriate context
ctx_list = [ctx_fname[0] for ctx_fname in list_context('Convolution')]


def SmallResNet(x, test=False, act=F.relu, inplace=False, shared=False):
    h = x

    def conv(x, maps=8, name="conv"):
        h = x
        with nn.parameter_scope(name):
            h = PF.convolution(h, maps, (3, 3), (1, 1), with_bias=True)
            h = PF.batch_normalization(h, batch_stat=not test)
        with nn.parameter_scope("{}-shortcut".format(name)):
            s = PF.convolution(h, maps, (3, 3), (1, 1), with_bias=False)
            h = PF.batch_normalization(h, batch_stat=not test)
        return act(h + s, inplace=inplace) if act in (F.relu, F.leaky_relu) else act(h + s)
    h = conv(h, maps=4, name="conv1")
    h = F.max_pooling(h, (2, 2))
    h = conv(h, maps=4, name="conv2")
    h = conv(h, maps=8, name="conv3") if not shared else conv(
        h, maps=4, name="conv2")
    h = F.average_pooling(h, h.shape[2:])
    h = PF.affine(h, 10)
    return h


@pytest.mark.parametrize("seed", [311])
@pytest.mark.parametrize("ctx", ctx_list)
@pytest.mark.parametrize("auto_forward", [True, False])
@pytest.mark.parametrize("flag_grad_outputs", [True, False])
@pytest.mark.parametrize("act, inplace", [(F.relu, True), (F.relu, False),
                                          (F.leaky_relu, True), (F.leaky_relu, False),
                                          (F.sin, False)])
@pytest.mark.parametrize("shared", [False, True])
def test_grad_resnet(seed, ctx, auto_forward, flag_grad_outputs, act, inplace, shared):
    backend = ctx.backend[0].split(":")[0]
    if backend == 'cuda':
        pytest.skip('CUDA Convolution N-D is only supported in CUDNN extension')

    if sys.version_info[1] >= 9 and auto_forward == True and backend == 'cudnn':
        pytest.skip(
            "Skip to avoid random KeyError with _ModuleLock. Referred to nnabla-ext-cuda issue #481.")

    nn.clear_parameters()

    # Settings
    nn.set_default_context(ctx)
    nn.set_auto_forward(auto_forward)
    b, c, h, w = 4, 3, 32, 32
    n_cls = 10
    rng = np.random.RandomState(seed)

    # Network
    x = nn.Variable.from_numpy_array(rng.randn(b, c, h, w))
    y = nn.Variable.from_numpy_array(rng.randint(0, n_cls, b).reshape(b, 1))
    p = SmallResNet(x, act=act, inplace=inplace, shared=shared)
    loss = F.mean(F.softmax_cross_entropy(p, y))

    # Zerograd, Forward, Backward on the forward graph
    inputs = nn.get_parameters().values()
    [inp.grad.zero() for inp in inputs]
    grad = nn.NdArray.from_numpy_array(
        np.asarray(rng.randn())) if flag_grad_outputs else 1
    if not auto_forward:
        loss.forward()
    loss.backward(grad)

    # Grad
    grad_outputs = grad if flag_grad_outputs else None
    grads = nn.grad([loss], inputs, [grad_outputs])
    if not auto_forward:
        F.sink(*grads, one_input_grad=1).forward()

    # Check between results of var.backward and nn.grad
    for inp, grad in zip(inputs, grads):
        assert_allclose(
            inp.g, grad.d, atol=1e-6)


@pytest.mark.parametrize("seed", [311])
@pytest.mark.parametrize("ctx", ctx_list)
@pytest.mark.parametrize("auto_forward", [True, False])
@pytest.mark.parametrize("inplace", [False, True])
@pytest.mark.parametrize("shared", [False, True])
def test_grad_grad_resnet(seed, ctx, auto_forward, inplace, shared):
    backend = ctx.backend[0].split(":")[0]
    if backend == 'cuda':
        pytest.skip('CUDA Convolution N-D is only supported in CUDNN extension')

    if sys.version_info[1] >= 9 and auto_forward == True and shared == False:
        pytest.skip(
            "Skip to avoid random KeyError with _ModuleLock. Referred to nnabla-ext-cuda issue #481.")

    nn.clear_parameters()

    # Settings
    nn.set_default_context(ctx)
    nn.set_auto_forward(auto_forward)
    b, c, h, w = 4, 3, 32, 32
    n_cls = 10
    rng = np.random.RandomState(seed)

    # Network
    x = nn.Variable.from_numpy_array(
        rng.randn(b, c, h, w)).apply(need_grad=True)
    y = SmallResNet(x, inplace=inplace, shared=shared)

    # Grad of grad
    dx = nn.grad([y], [x])
    ddx = nn.grad([dx[0]], [x])
    ddx[0].forward() if not auto_forward else None
    # Backward of grad
    x.grad.zero()
    dx[0].forward() if not auto_forward else None
    dx[0].backward()

    # Check between results of var.backward and nn.grad
    assert_allclose(x.g, ddx[0].d, atol=1e-6)


@pytest.mark.parametrize("seed", [311])
@pytest.mark.parametrize("ctx", ctx_list)
@pytest.mark.parametrize("auto_forward", [True, False])
def test_multiple_objectives(seed, ctx, auto_forward):

    # Settings
    nn.set_default_context(ctx)
    nn.set_auto_forward(auto_forward)
    b, c, h, w = 4, 3, 32, 32
    n_cls = 10
    rng = np.random.RandomState(seed)

    # Objecive0
    x0 = nn.Variable.from_numpy_array(
        rng.randn(b, c, h, w)).apply(need_grad=True)
    y0 = F.sigmoid(x0)
    # Objecive1
    x1 = nn.Variable.from_numpy_array(
        rng.randn(b, c, h, w)).apply(need_grad=True)
    y1 = F.tanh(x1)

    # Zerograd, Forward, Backward on the forward graph
    g0 = nn.NdArray.from_numpy_array(rng.randn(*x0.shape))
    g1 = nn.NdArray.from_numpy_array(rng.randn(*x1.shape))
    z = y0 * nn.Variable(g0.shape).apply(data=g0) + y1 * \
        nn.Variable(g1.shape).apply(data=g1)
    inputs = [x0, x1]
    [inp.grad.zero() for inp in inputs]
    if not auto_forward:
        z.forward()
    z.backward()

    # Grad
    inputs = [x0, x1]
    outputs = [y0, y1]
    grad_outputs = [g0, g1]
    grads = nn.grad(outputs, inputs, grad_outputs)
    if not auto_forward:
        F.sink(*grads, one_input_grad=1).forward()

    # Check between results of var.backward and nn.grad
    for inp, grad in zip(inputs, grads):
        assert_allclose(
            inp.g, grad.d, atol=1e-6)


@pytest.mark.parametrize("seed", [311])
@pytest.mark.parametrize("ctx", ctx_list)
@pytest.mark.parametrize("auto_forward", [True, False])
@pytest.mark.parametrize("type_grad_outputs", [int, float, np.ndarray, nn.NdArray])
def test_grad_outputs(seed, ctx, auto_forward, type_grad_outputs):

    # Settings
    nn.set_default_context(ctx)
    nn.set_auto_forward(auto_forward)
    b, c, h, w = 4, 3, 32, 32
    n_cls = 10
    rng = np.random.RandomState(seed)

    x = nn.Variable.from_numpy_array(
        rng.randn(b, c, h, w)).apply(need_grad=True)
    y = F.sigmoid(x)

    # Grad outputs
    if type_grad_outputs == int:
        g = rng.randint(-10, 10)
    elif type_grad_outputs == float:
        g = rng.randn()
    elif type_grad_outputs == np.ndarray:
        g = rng.randn(*y.shape)
    elif type_grad_outputs == nn.NdArray:
        g = nn.NdArray.from_numpy_array(rng.randn(*y.shape))

    # Zerograd, Forward, Backward on the forward graph
    inputs = [x]
    [inp.grad.zero() for inp in inputs]
    if not auto_forward:
        y.forward()
    y.backward(g)

    # Grad
    inputs = [x]
    outputs = [y]
    grad_outputs = [g]
    grads = nn.grad(outputs, inputs, grad_outputs)
    if not auto_forward:
        F.sink(*grads, one_input_grad=1).forward()

    # Check between results of var.bacwkard and nn.grad
    for inp, grad in zip(inputs, grads):
        assert_allclose(
            inp.g, grad.d, atol=1e-6)


@pytest.mark.parametrize("seed", [311])
@pytest.mark.parametrize("ctx", ctx_list)
@pytest.mark.parametrize("auto_forward", [True, False])
def test_shared_leaf_variable_basic_arithmetics(seed, ctx, auto_forward):
    def add(x, derivative=0):
        if derivative == 0:
            return x + x + x
        if derivative == 1:
            return 3 * np.ones_like(x)
        if derivative == 2:
            return np.zeros_like(x)

    def sub(x, derivative=0):
        if derivative == 0:
            return x - x - x
        if derivative == 1:
            return -1 * np.ones_like(x)
        if derivative == 2:
            return np.zeros_like(x)

    def mul(x, derivative=0):
        if derivative == 0:
            return x * x * x
        if derivative == 1:
            return 3 * x ** 2
        if derivative == 2:
            return 6 * x

    def div(x, derivative=0):
        if derivative == 0:
            return x / x / x
        if derivative == 1:
            return - x ** -2
        if derivative == 2:
            return 2 * x ** -3

    # Settings
    nn.set_default_context(ctx)
    nn.set_auto_forward(auto_forward)

    for math_type in [add, sub, mul, div]:
        xd = np.random.randn(2, 3) + 0.5
        x = nn.Variable.from_numpy_array(xd).apply(need_grad=True)
        x.grad.zero()
        y = math_type(x)
        # First-order gradient
        dy_dx = nn.grad([y], [x])
        if not auto_forward:
            dy_dx[0].forward()
        assert_allclose(dy_dx[0].d, math_type(xd, 1))
        # Second-order gradient
        dy_dx[0].backward()
        assert_allclose(x.g, math_type(xd, 2))


# TODO: this is an ad-hoc test
@pytest.mark.parametrize("ctx", ctx_list)
def test_compute_simple_hessian(ctx):
    nn.clear_parameters()

    # Network
    state = nn.Variable((1, 2))
    output = PF.affine(state, 1,
                       w_init=I.ConstantInitializer(value=1.),
                       b_init=I.ConstantInitializer(value=1.))
    loss = F.sum(output**2)
    # Input
    state_array = np.array([[1.0, 0.5]])
    state.d = state_array

    # Grad of network
    params = nn.get_parameters().values()
    for param in params:
        param.grad.zero()
    grads = nn.grad([loss], params)
    flat_grads = F.concatenate(*[F.reshape(grad, (-1,)) for grad in grads]) if len(grads) > 1 \
        else F.reshape(grads[0], (-1,))

    # Compute hessian
    hessian = np.zeros(
        (flat_grads.shape[0], flat_grads.shape[0]), dtype=np.float32)
    for i in range(flat_grads.shape[0]):
        flat_grads_i = flat_grads[i]
        flat_grads_i.forward()
        for param in params:
            param.grad.zero()
        flat_grads_i.backward()
        num_index = 0
        for param in params:
            grad = param.g.flatten()  # grad of grad so this is hessian
            hessian[i, num_index:num_index+len(grad)] = grad
            num_index += len(grad)

    actual = hessian
    expected = np.array(
        [[2*state_array[0, 0]**2,
          2*state_array[0, 0]*state_array[0, 1],
          2*state_array[0, 0]],
         [2*state_array[0, 0]*state_array[0, 1],
          2*state_array[0, 1]**2,
          2*state_array[0, 1]],
         [2*state_array[0, 0],
          2*state_array[0, 1],
          2.]]
          )
    assert_allclose(actual, expected)


class IdentityForwardOnlyFunction(PythonFunction):
    @property
    def name(self):
        return self.__class__.__name__

    def min_outputs(self):
        return 1

    def grad_depends_output_data(self, i, o):
        return False

    def grad_depends_input_data(self, i, j):
        return False

    def setup_impl(self, inputs, outputs):
        i0 = inputs[0]
        o0 = outputs[0]
        o0.reset_shape(i0.shape, True)

    def forward_impl(self, inputs, outputs):
        x = inputs[0].data
        y = outputs[0].data
        y.copy_from(x)

    def backward_impl(self, inputs, outputs, propagate_down, accum):
        pass


def IdentityForwardOnlyFunction_backward(inputs):
    raise NotImplementedError(
        "PassForwardOnlyFunction_backward is not implemented.\nThe expected behavior is that this function will not be called.")

# This tests a previously existing bug where a "Propagate down" check in Grad.__call__


def test_nn_grad_propagate_down_check():
    register("IdentityForwardOnlyFunction",
             IdentityForwardOnlyFunction_backward)
    backward_func = registry["IdentityForwardOnlyFunction"]
    assert backward_func is not None

    x = nn.Variable.from_numpy_array(np.random.random((1, 1, 32, 32)))
    y = PF.convolution(x, 1, kernel=(3, 3), pad=(1, 1), with_bias=False)
    z = IdentityForwardOnlyFunction()(y)
    w = F.identity(z)

    # If IdentityForwardOnlyFunction_backward is called in nn.grad, an error will occur.
    v = nn.grad(w, [z])
    v[0].forward()


def test_double_backward_floating_variables():
    x = nn.Variable((2, 2), need_grad=True)
    y = nn.Variable((2, 3), need_grad=True)
    z = nn.Variable((2, 4), need_grad=True)
    w = F.concatenate(*[x, y, z], axis=-1)
    o = F.sin(w)
    dx = nn.grad([o], [x])[0]
    ddx = nn.grad([dx], [x])[0]  # Error must not happen
