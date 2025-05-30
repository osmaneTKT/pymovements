# Copyright (c) 2023-2025 The pymovements Project Authors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Provides plotting related functionality.

.. rubric:: Functions

.. autosummary::
   :toctree:
   :recursive:

    heatmap
    main_sequence_plot
    traceplot
    tsplot
"""
from pymovements.plotting.heatmap import heatmap
from pymovements.plotting.main_sequence_plot import main_sequence_plot
from pymovements.plotting.scanpathplot import scanpathplot
from pymovements.plotting.traceplot import traceplot
from pymovements.plotting.tsplot import tsplot

__all__ = [
    'heatmap',
    'main_sequence_plot',
    'scanpathplot',
    'traceplot',
    'tsplot',
]
