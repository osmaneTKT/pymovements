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
"""Module to create a GazeDataFrame from a numpy array."""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
import polars as pl

from pymovements._utils import _checks
from pymovements.events.frame import EventDataFrame
from pymovements.gaze.experiment import Experiment
from pymovements.gaze.gaze_dataframe import GazeDataFrame


def from_numpy(
        data: np.ndarray | None = None,
        experiment: Experiment | None = None,
        events: EventDataFrame | None = None,
        *,
        trial: np.ndarray | None = None,
        time: np.ndarray | None = None,
        pixel: np.ndarray | None = None,
        position: np.ndarray | None = None,
        velocity: np.ndarray | None = None,
        acceleration: np.ndarray | None = None,
        distance: np.ndarray | None = None,
        schema: list[str] | None = None,
        orient: Literal['col', 'row'] = 'col',
        trial_columns: str | list[str] | None = None,
        time_column: str | None = None,
        time_unit: str | None = None,
        pixel_columns: list[str] | None = None,
        position_columns: list[str] | None = None,
        velocity_columns: list[str] | None = None,
        acceleration_columns: list[str] | None = None,
        distance_column: str | None = None,
) -> GazeDataFrame:
    """Get a :py:class:`~pymovements.gaze.GazeDataFrame` from a numpy array.

    There are two mutually exclusive ways of conversion.

    **Single data array**: Pass a single numpy array via `data` and specify its schema and
    orientation. You can then additionally pass column specifiers, e.g. `time_column` and
    `position_columns`.

    **Column specific arrays**: For each type of signal, you can pass the numpy array explicitly,
    e.g. `position` or `velocity`. You must not pass `data` or any column list specifiers using this
    method.

    Parameters
    ----------
    data: np.ndarray | None
        Two-dimensional data represented as a numpy ndarray. (default: None)
    experiment: Experiment | None
        The experiment definition. (default: None)
    events: EventDataFrame | None
        A dataframe of events in the gaze signal. (default: None)
    trial: np.ndarray | None
        Array of trial identifiers for each timestep. (default: None)
    time: np.ndarray | None
        Array of timestamps. (default: None)
    pixel: np.ndarray | None
        Array of gaze pixel positions. (default: None)
    position: np.ndarray | None
        Array of gaze positions in degrees of visual angle. (default: None)
    velocity: np.ndarray | None
        Array of gaze velocities in degrees of visual angle per second. (default: None)
    acceleration: np.ndarray | None
        Array of gaze accelerations in degrees of visual angle per square second. (default: None)
    distance: np.ndarray | None
        Array of eye-to-screen distances in millimiters. (default: None)
    schema: list[str] | None
        A list of column names. (default: None)
    orient: Literal['col', 'row']
        Whether to interpret the two-dimensional data as columns or as rows. (default: 'col')
    trial_columns: str | list[str] | None
        The name of the trial columns in the input data frame. If the list is empty or None,
        the input data frame is assumed to contain only one trial. If the list is not empty,
        the input data frame is assumed to contain multiple trials and the transformation
        methods will be applied to each trial separately. (default: None)
    time_column: str | None
        The name of the timestamp column in the input data frame. (default: None)
    time_unit: str | None
        The unit of the timestamps in the timestamp column in the input data frame. Supported
        units are 's' for seconds, 'ms' for milliseconds and 'step' for steps. If the unit is
        'step' the experiment definition must be specified. All timestamps will be converted to
        milliseconds. If time_unit is None, milliseconds are assumed. (default: None)
    pixel_columns: list[str] | None
        The name of the pixel position columns in the input data frame. (default: None)
    position_columns: list[str] | None
        The name of the dva position columns in the input data frame. (default: None)
    velocity_columns: list[str] | None
        The name of the dva velocity columns in the input data frame. (default: None)
    acceleration_columns: list[str] | None
        The name of the dva acceleration columns in the input data frame. (default: None)
    distance_column: str | None
        The name of the column containing eye-to-screen distance in millimiters for each sample
        in the input data frame. If specified, the column will be used for pixel to dva
        transformations. If not specified, the constant eye-to-screen distance will be taken from
        the experiment definition. (default: None)

    Returns
    -------
    GazeDataFrame
        Returns gaze data frame read from numpy array.

    Examples
    --------
    Creating an example numpy array with 4 columns and 100 rows. We call this layout column
    orientation.
    >>> import numpy as np
    >>> import pymovements as pm
    >>>
    >>> arr = np.zeros((3, 100))
    >>> arr.shape
    (3, 100)

    Specifying the underlying schema:
    >>> schema = ['t', 'x', 'y']

    Pass the array as ``data`` to ``pm.gaze.from_numpy()``, by specifying schema and components.
    >>> gaze = pm.gaze.from_numpy(
    ...     arr,
    ...     schema=schema,
    ...     time_column='t',
    ...     time_unit='ms',
    ...     position_columns=['x', 'y'],
    ...     orient='col',
    ... )
    >>> gaze.frame
    shape: (100, 2)
    ┌──────┬────────────┐
    │ time ┆ position   │
    │ ---  ┆ ---        │
    │ i64  ┆ list[f64]  │
    ╞══════╪════════════╡
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ …    ┆ …          │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    └──────┴────────────┘

    Use the ``orient`` keyword argument to specify the layout of your array.
    >>> arr.T.shape
    (100, 3)

    >>> gaze = pm.gaze.from_numpy(
    ...     arr.T,
    ...     schema=schema,
    ...     time_column='t',
    ...     time_unit='ms',
    ...     position_columns=['x', 'y'],
    ...     orient='row',
    ... )
    >>> gaze.frame
    shape: (100, 2)
    ┌──────┬────────────┐
    │ time ┆ position   │
    │ ---  ┆ ---        │
    │ i64  ┆ list[f64]  │
    ╞══════╪════════════╡
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ …    ┆ …          │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    └──────┴────────────┘

    Pass the data explicitly via the specific keyword arguments, without having to specify a schema.
    >>> gaze = pm.gaze.from_numpy(
    ...     time=arr[0],
    ...     time_unit='ms',
    ...     position=arr[[1, 2]],
    ...     orient='col',
    ... )
    >>> gaze.frame
    shape: (100, 2)
    ┌──────┬────────────┐
    │ time ┆ position   │
    │ ---  ┆ ---        │
    │ i64  ┆ list[f64]  │
    ╞══════╪════════════╡
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ …    ┆ …          │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    │ 0    ┆ [0.0, 0.0] │
    └──────┴────────────┘
    """
    # Either data or {time, pixel, position, velocity, acceleration} must be None.
    _checks.check_is_mutual_exclusive(data=data, time=time)
    _checks.check_is_mutual_exclusive(data=data, pixel=pixel)
    _checks.check_is_mutual_exclusive(data=data, position=position)
    _checks.check_is_mutual_exclusive(data=data, velocity=velocity)
    _checks.check_is_mutual_exclusive(data=data, acceleration=acceleration)
    _checks.check_is_mutual_exclusive(data=data, distance=distance)

    if data is not None:
        df = pl.from_numpy(data=data, schema=schema, orient=orient)
        return GazeDataFrame(
            data=df,
            experiment=experiment,
            events=events,
            trial_columns=trial_columns,
            time_column=time_column,
            time_unit=time_unit,
            pixel_columns=pixel_columns,
            position_columns=position_columns,
            velocity_columns=velocity_columns,
            acceleration_columns=acceleration_columns,
            distance_column=distance_column,
        )

    # Initialize with an empty DataFrame, as every column specifier could be None.
    dfs: list[pl.DataFrame] = [pl.DataFrame()]

    trial_columns = None
    if trial is not None:
        df = pl.from_numpy(data=trial, schema=['trial'], orient=orient)
        dfs.append(df)
        trial_columns = 'trial'

    time_column = None
    if time is not None:
        df = pl.from_numpy(data=time, schema=['time'], orient=orient)
        dfs.append(df)
        time_column = 'time'

    pixel_columns = None
    if pixel is not None:
        df = pl.from_numpy(data=pixel, orient=orient).select(pl.all().name.prefix('pixel_'))
        dfs.append(df)
        pixel_columns = df.columns

    position_columns = None
    if position is not None:
        df = pl.from_numpy(data=position, orient=orient).select(pl.all().name.prefix('position_'))
        dfs.append(df)
        position_columns = df.columns

    velocity_columns = None
    if velocity is not None:
        df = pl.from_numpy(data=velocity, orient=orient).select(pl.all().name.prefix('velocity_'))
        dfs.append(df)
        velocity_columns = df.columns

    acceleration_columns = None
    if acceleration is not None:
        df = pl.from_numpy(data=acceleration, orient=orient)
        df = df.select(pl.all().name.prefix('acceleration_'))
        dfs.append(df)
        acceleration_columns = df.columns

    distance_column = None
    if distance is not None:
        df = pl.from_numpy(data=distance, schema=['distance'], orient=orient)
        dfs.append(df)
        distance_column = 'distance'

    df = pl.concat(dfs, how='horizontal')
    return GazeDataFrame(
        data=df,
        experiment=experiment,
        events=events,
        time_column=time_column,
        time_unit=time_unit,
        trial_columns=trial_columns,
        pixel_columns=pixel_columns,
        position_columns=position_columns,
        velocity_columns=velocity_columns,
        acceleration_columns=acceleration_columns,
        distance_column=distance_column,
    )


def from_pandas(
        data: pd.DataFrame,
        experiment: Experiment | None = None,
        events: EventDataFrame | None = None,
        *,
        trial_columns: str | list[str] | None = None,
        time_column: str | None = None,
        time_unit: str | None = None,
        pixel_columns: list[str] | None = None,
        position_columns: list[str] | None = None,
        velocity_columns: list[str] | None = None,
        acceleration_columns: list[str] | None = None,
        distance_column: str | None = None,
) -> GazeDataFrame:
    """Get a :py:class:`~pymovements.gaze.GazeDataFrame` from a pandas DataFrame.

    Parameters
    ----------
    data: pd.DataFrame
        Data represented as a pandas DataFrame.
    experiment : Experiment | None
        The experiment definition. (default: None)
    events: EventDataFrame | None
        A dataframe of events in the gaze signal. (default: None)
    trial_columns: str | list[str] | None
        The name of the trial columns in the input data frame. If the list is empty or None,
        the input data frame is assumed to contain only one trial. If the list is not empty,
        the input data frame is assumed to contain multiple trials and the transformation
        methods will be applied to each trial separately. (default: None)
    time_column: str | None
        The name of the timestamp column in the input data frame. (default: None)
    time_unit: str | None
        The unit of the timestamps in the timestamp column in the input data frame. Supported
        units are 's' for seconds, 'ms' for milliseconds and 'step' for steps. If the unit is
        'step' the experiment definition must be specified. All timestamps will be converted to
        milliseconds. If time_unit is None, milliseconds are assumed. (default: None)
    pixel_columns: list[str] | None
        The name of the pixel position columns in the input data frame. (default: None)
    position_columns: list[str] | None
        The name of the dva position columns in the input data frame. (default: None)
    velocity_columns: list[str] | None
        The name of the dva velocity columns in the input data frame. (default: None)
    acceleration_columns: list[str] | None
        The name of the dva acceleration columns in the input data frame. (default: None)
    distance_column: str | None
        The name of the column containing eye-to-screen distance in millimeters for each sample
        in the input data frame. If specified, the column will be used for pixel to dva
        transformations. If not specified, the constant eye-to-screen distance will be taken from
        the experiment definition. (default: None)

    Returns
    -------
    GazeDataFrame
        Returns gaze data frame read from pandas data frame.
    """
    df = pl.from_pandas(data=data)
    return GazeDataFrame(
        data=df,
        experiment=experiment,
        events=events,
        trial_columns=trial_columns,
        time_column=time_column,
        time_unit=time_unit,
        pixel_columns=pixel_columns,
        position_columns=position_columns,
        velocity_columns=velocity_columns,
        acceleration_columns=acceleration_columns,
        distance_column=distance_column,
    )
