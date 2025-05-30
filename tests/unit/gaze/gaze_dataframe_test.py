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
"""Test all GazeDataFrame functionality."""
import polars as pl
import pytest
from polars.testing import assert_frame_equal

import pymovements as pm


@pytest.mark.filterwarnings('ignore:GazeDataFrame contains data but no.*:UserWarning')
@pytest.mark.parametrize(
    'init_arg',
    [
        pytest.param(
            None,
            id='None',
        ),
        pytest.param(
            pl.DataFrame(),
            id='no_eye_velocity_columns',
        ),
    ],
)
def test_gaze_dataframe_init(init_arg):
    gaze_df = pm.GazeDataFrame(init_arg)
    assert isinstance(gaze_df.frame, pl.DataFrame)


@pytest.mark.filterwarnings('ignore:GazeDataFrame contains data but no.*:UserWarning')
@pytest.mark.parametrize(
    ('init_df', 'velocity_columns'),
    [
        pytest.param(
            pl.DataFrame(schema={'x_vel': pl.Float64, 'y_vel': pl.Float64}),
            ['x_vel', 'y_vel'],
            id='no_eye_velocity_columns',
        ),
        pytest.param(
            pl.DataFrame(schema={'abc': pl.Int64, 'x_vel': pl.Float64, 'y_vel': pl.Float64}),
            ['x_vel', 'y_vel'],
            id='no_eye_velocity_columns_with_other_columns',
        ),
        pytest.param(
            pl.DataFrame(schema={'x_right_vel': pl.Float64, 'y_right_vel': pl.Float64}),
            ['x_right_vel', 'y_right_vel'],
            id='right_eye_velocity_columns',
        ),
        pytest.param(
            pl.DataFrame(schema={'x_left_vel': pl.Float64, 'y_left_vel': pl.Float64}),
            ['x_left_vel', 'y_left_vel'],
            id='left_eye_velocity_columns',
        ),
        pytest.param(
            pl.DataFrame(
                schema={
                    'x_left_vel': pl.Float64, 'y_left_vel': pl.Float64,
                    'x_right_vel': pl.Float64, 'y_right_vel': pl.Float64,
                },
            ),
            ['x_left_vel', 'y_left_vel', 'x_right_vel', 'y_right_vel'],
            id='both_eyes_velocity_columns',
        ),
    ],
)
def test_gaze_dataframe_velocity_columns(init_df, velocity_columns):
    gaze_df = pm.GazeDataFrame(init_df, velocity_columns=velocity_columns)

    assert 'velocity' in gaze_df.columns


@pytest.mark.filterwarnings('ignore:GazeDataFrame contains data but no.*:UserWarning')
@pytest.mark.parametrize(
    ('init_df', 'pixel_columns'),
    [
        pytest.param(
            pl.DataFrame(schema={'x_pix': pl.Float64, 'y_pix': pl.Float64}),
            ['x_pix', 'y_pix'],
            id='no_eye_pix_pos_columns',
        ),
        pytest.param(
            pl.DataFrame(schema={'abc': pl.Int64, 'x_pix': pl.Float64, 'y_pix': pl.Float64}),
            ['x_pix', 'y_pix'],
            id='no_eye_pix_pos_columns_with_other_columns',
        ),
        pytest.param(
            pl.DataFrame(schema={'x_right_pix': pl.Float64, 'y_right_pix': pl.Float64}),
            ['x_right_pix', 'y_right_pix'],
            id='right_eye_pix_pos_columns',
        ),
        pytest.param(
            pl.DataFrame(schema={'x_left_pix': pl.Float64, 'y_left_pix': pl.Float64}),
            ['x_left_pix', 'y_left_pix'],
            id='left_eye_pix_pos_columns',
        ),
        pytest.param(
            pl.DataFrame(
                schema={
                    'x_left_pix': pl.Float64, 'y_left_pix': pl.Float64,
                    'x_right_pix': pl.Float64, 'y_right_pix': pl.Float64,
                },
            ),
            ['x_left_pix', 'y_left_pix', 'x_right_pix', 'y_right_pix'],
            id='both_eyes_pix_pos_columns',
        ),
    ],
)
def test_gaze_dataframe_pixel_position_columns(init_df, pixel_columns):
    gaze_df = pm.GazeDataFrame(init_df, pixel_columns=pixel_columns)

    assert 'pixel' in gaze_df.columns


@pytest.mark.filterwarnings('ignore:GazeDataFrame contains data but no.*:UserWarning')
@pytest.mark.parametrize(
    ('init_df', 'position_columns'),
    [
        pytest.param(
            pl.DataFrame(schema={'x_pos': pl.Float64, 'y_pos': pl.Float64}),
            ['x_pos', 'y_pos'],
            id='no_eye_pos_columns',
        ),
        pytest.param(
            pl.DataFrame(schema={'abc': pl.Int64, 'x_pos': pl.Float64, 'y_pos': pl.Float64}),
            ['x_pos', 'y_pos'],
            id='no_eye_pos_columns_with_other_columns',
        ),
        pytest.param(
            pl.DataFrame(schema={'x_right_pos': pl.Float64, 'y_right_pos': pl.Float64}),
            ['x_right_pos', 'y_right_pos'],
            id='right_eye_pos_columns',
        ),
        pytest.param(
            pl.DataFrame(schema={'x_left_pos': pl.Float64, 'y_left_pos': pl.Float64}),
            ['x_left_pos', 'y_left_pos'],
            id='left_eye_pos_columns',
        ),
        pytest.param(
            pl.DataFrame(
                schema={
                    'x_left_pos': pl.Float64, 'y_left_pos': pl.Float64,
                    'x_right_pos': pl.Float64, 'y_right_pos': pl.Float64,
                },
            ),
            ['x_left_pos', 'y_left_pos', 'x_right_pos', 'y_right_pos'],
            id='both_eyes_pos_columns',
        ),
    ],
)
def test_gaze_dataframe_position_columns(init_df, position_columns):
    gaze_df = pm.GazeDataFrame(init_df, position_columns=position_columns)

    assert 'position' in gaze_df.columns


@pytest.mark.filterwarnings('ignore:GazeDataFrame contains data but no.*:UserWarning')
def test_gaze_dataframe_copy_with_experiment():
    gaze = pm.GazeDataFrame(
        pl.DataFrame(schema={'x': pl.Float64, 'y': pl.Float64}),
        experiment=pm.Experiment(1024, 768, 38, 30, 60, 'center', 1000),
        position_columns=['x', 'y'],
    )

    gaze_copy = gaze.clone()

    # We want to have separate dataframes but with the exact same data.
    assert gaze.frame is not gaze_copy.frame
    assert_frame_equal(gaze.frame, gaze_copy.frame)

    # We want to have separate experiment instances but the same values.
    assert gaze.experiment is not gaze_copy.experiment
    assert gaze.experiment == gaze_copy.experiment


@pytest.mark.filterwarnings('ignore:GazeDataFrame contains data but no.*:UserWarning')
def test_gaze_dataframe_copy_no_experiment():
    gaze = pm.GazeDataFrame(
        pl.DataFrame(schema={'x': pl.Float64, 'y': pl.Float64}),
        experiment=None,
        position_columns=['x', 'y'],
    )

    gaze_copy = gaze.clone()

    # We want to have separate dataframes but with the exact same data.
    assert gaze.frame is not gaze_copy.frame
    assert_frame_equal(gaze.frame, gaze_copy.frame)

    # We want to have separate experiment instances but the same values.
    assert gaze.experiment is gaze_copy.experiment


@pytest.mark.filterwarnings('ignore:GazeDataFrame contains data but no.*:UserWarning')
def test_gaze_dataframe_split():
    gaze = pm.GazeDataFrame(
        pl.DataFrame(
            {
                'x': [0, 1, 2, 3],
                'y': [1, 1, 0, 0],
                'trial_id': [0, 1, 1, 2],
            },
            schema={'x': pl.Float64, 'y': pl.Float64, 'trial_id': pl.Int8},
        ),
        experiment=None,
        position_columns=['x', 'y'],
    )

    split_gaze = gaze.split('trial_id')
    assert all(gaze_df.frame.n_unique('trial_id') == 1 for gaze_df in split_gaze)
    assert len(split_gaze) == 3
    assert_frame_equal(gaze.frame.filter(pl.col('trial_id') == 0), split_gaze[0].frame)
    assert_frame_equal(gaze.frame.filter(pl.col('trial_id') == 1), split_gaze[1].frame)
    assert_frame_equal(gaze.frame.filter(pl.col('trial_id') == 2), split_gaze[2].frame)


@pytest.mark.filterwarnings('ignore:GazeDataFrame contains data but no.*:UserWarning')
def test_gaze_dataframe_compute_event_properties_no_events():
    gaze = pm.GazeDataFrame(
        pl.DataFrame(schema={'x': pl.Float64, 'y': pl.Float64, 'trial_id': pl.Int8}),
        position_columns=['x', 'y'],
        trial_columns=['trial_id'],
    )

    with pytest.warns(
        UserWarning,
        match='No events available to compute event properties. Did you forget to use detect()?',
    ):
        gaze.compute_event_properties('amplitude')
