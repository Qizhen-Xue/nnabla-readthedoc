# Copyright 2021 Sony Corporation.
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

#
# *WARNING*
# THIS FILE IS AUTO-GENERATED BY CODE GENERATOR.
# 1. IMPLEMENT BACKWARD WRT INPUTS OF THE CORRESPONDING FUNCTION
# 2. IMPLEMENT BACKWARD_FUNCTION_CLASS IF NECESSARY (see e.g., affine.py)
# 3. UPDATE THE MAPPING IF NECESSARY (see function_backward_functions.py.tmpl)


import nnabla.functions as F


def bit_shift_backward(grad_inputs, inputs, input_shapes, outputs, output_shapes, direction='LEFT'):
    """
    Args:
      grad_inputs (list of :obj:`nnabla.Variable`): Propagated grads to this backward function.
      inputs (list of :obj:`nnabla.Variable` and None): Input Variables of the forward function
          if this backward function depends on it. Otherwise, None is set instead.
      input_shapes (list of tuple of :obj:`int`): Input shapes of the forward function.
          The shapes of the inputs in which None is set can be passed.
      outputs (list of :obj:`nnabla.Variable` and None): Output Variables of the forward function
          if this backward function depends on it. Otherwise, None is set instead.
      output_shapes (list of tuple of :obj:`int`): Output shapes of the forward function.
          The shapes of the outputs in which None is set can be passed.
      kwargs (dict of arguments): Dictionary of the corresponding function arguments.

    Return:
      list of Variable: Return the gradients wrt inputs of the corresponding function.
    """
    # The inputs and outputs could be cleared by graph engine during forward
    # propagation before this backward function is called. The grad dependency
    # defined by C++ Function class can prevent the deletion. To define it,
    # see Function::grad_depends_input_data, Function::grad_depends_input_data_impl,
    # Function::grad_depends_output_data, Function::auto_grad_depends_input_data,
    # Function::auto_grad_depends_output_data, Function::auto_grad_depends_input_data_impl
    # for more detail.
    dy = grad_inputs[0]
    x0 = inputs[0]
    raise NotImplementedError("bit_shift_backward is not implemented.")
