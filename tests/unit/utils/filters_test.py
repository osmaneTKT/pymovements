# Copyright (c) 2025 The pymovements Project Authors
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
"""Tests deprecated utils.filters."""
import re

import numpy as np
import pytest

from pymovements import __version__
from pymovements.utils.filters import events_split_nans
from pymovements.utils.filters import filter_candidates_remove_nans


@pytest.mark.filterwarnings('ignore::DeprecationWarning')
@pytest.mark.parametrize('filter_function', [events_split_nans, filter_candidates_remove_nans])
def test_filter_function(filter_function):
    candidates = [[0, 1], [2, 3]]
    values = np.array([(np.nan, np.nan), (0, 0), (0, 0), (0, 0)])

    filter_function(candidates=candidates, values=values)


@pytest.mark.parametrize('filter_function', [events_split_nans, filter_candidates_remove_nans])
def test_filter_function_deprecated(filter_function):
    candidates = [[0, 1], [2, 3]]
    values = np.array([(np.nan, np.nan), (0, 0), (0, 0), (0, 0)])

    with pytest.raises(DeprecationWarning):
        filter_function(candidates=candidates, values=values)


@pytest.mark.parametrize('filter_function', [events_split_nans, filter_candidates_remove_nans])
def test_filter_function_removed(filter_function):
    candidates = [[0, 1], [2, 3]]
    values = np.array([(np.nan, np.nan), (0, 0), (0, 0), (0, 0)])

    with pytest.raises(DeprecationWarning) as info:
        filter_function(candidates=candidates, values=values)

    regex = re.compile(r'.*will be removed in v(?P<version>[0-9]*[.][0-9]*[.][0-9]*)[.)].*')

    msg = info.value.args[0]
    remove_version = regex.match(msg).groupdict()['version']
    current_version = __version__.split('+')[0]
    assert current_version < remove_version, (
        f'utils/filters.py was planned to be removed in v{remove_version}. '
        f'Current version is v{current_version}.'
    )
