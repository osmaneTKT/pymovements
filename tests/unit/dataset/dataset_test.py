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
"""Test all functionality in pymovements.dataset.dataset."""
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from pymovements import Dataset
from pymovements import DatasetDefinition
from pymovements import DatasetLibrary
from pymovements import DatasetPaths
from pymovements import events
from pymovements import Experiment
from pymovements import GazeDataFrame
from pymovements.exceptions import InvalidProperty


# pylint: disable=too-many-lines

class _UNSET:
    ...


def create_raw_gaze_files_from_fileinfo(gaze_dfs, fileinfo, rootpath):
    rootpath.mkdir(parents=True, exist_ok=True)

    for gaze_df, fileinfo_row in zip(gaze_dfs, fileinfo.to_dicts()):
        filepath = fileinfo_row['filepath']

        for key in fileinfo_row.keys():
            if key in gaze_df.columns:
                gaze_df = gaze_df.drop(key)

        gaze_df.write_csv(rootpath / filepath)


def create_preprocessed_gaze_files_from_fileinfo(gaze_dfs, fileinfo, rootpath):
    rootpath.mkdir(parents=True, exist_ok=True)

    for gaze_df, fileinfo_row in zip(gaze_dfs, fileinfo.to_dicts()):
        filepath = fileinfo_row['filepath']
        filepath = filepath.replace('csv', 'feather')

        for key in fileinfo_row.keys():
            if key in gaze_df.columns:
                gaze_df = gaze_df.frame.drop(key)

        gaze_df.write_ipc(rootpath / filepath)


def create_event_files_from_fileinfo(gaze_dfs, fileinfo, rootpath):
    rootpath.mkdir(parents=True, exist_ok=True)

    for gaze_df, fileinfo_row in zip(gaze_dfs, fileinfo.to_dicts()):
        filepath = fileinfo_row['filepath']
        filepath = filepath.replace('csv', 'feather')

        for key in fileinfo_row.keys():
            if key in gaze_df.columns:
                gaze_df = gaze_df.drop(key)

        gaze_df.write_ipc(rootpath / filepath)


def create_precomputed_files_from_fileinfo(precomputed_dfs, fileinfo, rootpath):
    rootpath.mkdir(parents=True, exist_ok=True)

    for precomputed_df, fileinfo_row in zip(precomputed_dfs, fileinfo.to_dicts()):
        filepath = fileinfo_row['filepath']

        for key in fileinfo_row.keys():
            if key in precomputed_df.columns:
                precomputed_df = precomputed_df.drop(key)

        precomputed_df.write_csv(rootpath / filepath)


def create_precomputed_rm_files_from_fileinfo(precomputed_rm_df, fileinfo, rootpath):
    rootpath.mkdir(parents=True, exist_ok=True)

    for _precomputed_rm_df, fileinfo_row in zip(precomputed_rm_df, fileinfo.to_dicts()):
        filepath = fileinfo_row['filepath']

        for key in fileinfo_row.keys():
            if key in _precomputed_rm_df.columns:
                _precomputed_rm_df = _precomputed_rm_df.drop(key)

        _precomputed_rm_df.write_csv(rootpath / filepath)


def mock_toy(
        rootpath,
        raw_fileformat,
        eyes,
        remote=False,
        has_files=_UNSET,
        extract=_UNSET,
        filename_format_schema_overrides=_UNSET,
):
    if has_files is _UNSET:
        has_files = {
            'gaze': True,
            'precomputed_events': False,
            'precomputed_reading_measures': False,
        }

    if extract is _UNSET:
        extract = None

    if filename_format_schema_overrides is _UNSET:
        filename_format_schema_overrides = {
            'gaze': {'subject_id': pl.Int64},
            'precomputed_events': {'subject_id': pl.Int64},
            'precomputed_reading_measures': {'subject_id': pl.Int64},
        }

    if filename_format_schema_overrides['precomputed_events']:
        subject_ids = list(range(1, 21))
        fileinfo = pl.DataFrame(
            data={'subject_id': subject_ids},
            schema={'subject_id': pl.Int64},
        )
    else:
        subject_ids = [str(idx) for idx in range(1, 21)]
        fileinfo = pl.DataFrame(
            data={'subject_id': subject_ids},
            schema={'subject_id': pl.Utf8},
        )

    fileinfo = fileinfo.with_columns([
        pl.format('{}.' + raw_fileformat, 'subject_id').alias('filepath'),
    ])

    fileinfo = fileinfo.sort(by='filepath')

    gaze_dfs = []
    for fileinfo_row in fileinfo.to_dicts():
        if eyes == 'both':
            gaze_df = pl.from_dict(
                {
                    'subject_id': fileinfo_row['subject_id'],
                    'time': np.arange(1000),
                    'x_left_pix': np.zeros(1000),
                    'y_left_pix': np.zeros(1000),
                    'x_right_pix': np.zeros(1000),
                    'y_right_pix': np.zeros(1000),
                    'trial_id_1': np.concatenate([np.zeros(500), np.ones(500)]),
                    'trial_id_2': ['a'] * 200 + ['b'] * 200 + ['c'] * 600,
                },
                schema={
                    'subject_id': pl.Int64,
                    'time': pl.Int64,
                    'x_left_pix': pl.Float64,
                    'y_left_pix': pl.Float64,
                    'x_right_pix': pl.Float64,
                    'y_right_pix': pl.Float64,
                    'trial_id_1': pl.Float64,
                    'trial_id_2': pl.Utf8,
                },
            )
            pixel_columns = ['x_left_pix', 'y_left_pix', 'x_right_pix', 'y_right_pix']

        elif eyes == 'both+avg':
            gaze_df = pl.from_dict(
                {
                    'subject_id': fileinfo_row['subject_id'],
                    'time': np.arange(1000),
                    'x_left_pix': np.zeros(1000),
                    'y_left_pix': np.zeros(1000),
                    'x_right_pix': np.zeros(1000),
                    'y_right_pix': np.zeros(1000),
                    'x_avg_pix': np.zeros(1000),
                    'y_avg_pix': np.zeros(1000),
                    'trial_id_1': np.concatenate([np.zeros(500), np.ones(500)]),
                    'trial_id_2': ['a'] * 200 + ['b'] * 200 + ['c'] * 600,
                },
                schema={
                    'subject_id': pl.Int64,
                    'time': pl.Int64,
                    'x_left_pix': pl.Float64,
                    'y_left_pix': pl.Float64,
                    'x_right_pix': pl.Float64,
                    'y_right_pix': pl.Float64,
                    'x_avg_pix': pl.Float64,
                    'y_avg_pix': pl.Float64,
                    'trial_id_1': pl.Float64,
                    'trial_id_2': pl.Utf8,
                },
            )
            pixel_columns = [
                'x_left_pix', 'y_left_pix', 'x_right_pix', 'y_right_pix', 'x_avg_pix', 'y_avg_pix',
            ]

        elif eyes == 'left':
            gaze_df = pl.from_dict(
                {
                    'subject_id': fileinfo_row['subject_id'],
                    'time': np.arange(1000),
                    'x_left_pix': np.zeros(1000),
                    'y_left_pix': np.zeros(1000),
                    'trial_id_1': np.concatenate([np.zeros(500), np.ones(500)]),
                    'trial_id_2': ['a'] * 200 + ['b'] * 200 + ['c'] * 600,
                },
                schema={
                    'subject_id': pl.Int64,
                    'time': pl.Int64,
                    'x_left_pix': pl.Float64,
                    'y_left_pix': pl.Float64,
                    'trial_id_1': pl.Float64,
                    'trial_id_2': pl.Utf8,
                },
            )
            pixel_columns = ['x_left_pix', 'y_left_pix']
        elif eyes == 'right':
            gaze_df = pl.from_dict(
                {
                    'subject_id': fileinfo_row['subject_id'],
                    'time': np.arange(1000),
                    'x_right_pix': np.zeros(1000),
                    'y_right_pix': np.zeros(1000),
                    'trial_id_1': np.concatenate([np.zeros(500), np.ones(500)]),
                    'trial_id_2': ['a'] * 200 + ['b'] * 200 + ['c'] * 600,
                },
                schema={
                    'subject_id': pl.Int64,
                    'time': pl.Int64,
                    'x_right_pix': pl.Float64,
                    'y_right_pix': pl.Float64,
                    'trial_id_1': pl.Float64,
                    'trial_id_2': pl.Utf8,
                },
            )
            pixel_columns = ['x_right_pix', 'y_right_pix']
        elif eyes == 'none':
            gaze_df = pl.from_dict(
                {
                    'subject_id': fileinfo_row['subject_id'],
                    'time': np.arange(1000),
                    'x_pix': np.zeros(1000),
                    'y_pix': np.zeros(1000),
                    'trial_id_1': np.concatenate([np.zeros(500), np.ones(500)]),
                    'trial_id_2': ['a'] * 200 + ['b'] * 200 + ['c'] * 600,
                },
                schema={
                    'subject_id': pl.Int64,
                    'time': pl.Int64,
                    'x_pix': pl.Float64,
                    'y_pix': pl.Float64,
                    'trial_id_1': pl.Float64,
                    'trial_id_2': pl.Utf8,
                },
            )
            pixel_columns = ['x_pix', 'y_pix']
        else:
            raise ValueError(f'invalid value for eyes: {eyes}')

        if remote:
            gaze_df = gaze_df.with_columns([
                pl.lit(680.).alias('distance'),
            ])

            distance_column = 'distance'
            distance_cm = None
        else:
            distance_column = None
            distance_cm = 68

        gaze_dfs.append(gaze_df)

    create_raw_gaze_files_from_fileinfo(gaze_dfs, fileinfo, rootpath / 'raw')

    # Create GazeDataFrames for passing as ground truth
    gaze_dfs = [
        GazeDataFrame(gaze_df, pixel_columns=pixel_columns)
        for gaze_df in gaze_dfs
    ]

    preprocessed_gaze_dfs = []
    for fileinfo_row in fileinfo.to_dicts():
        position_columns = [pixel_column.replace('pix', 'pos') for pixel_column in pixel_columns]
        velocity_columns = [pixel_column.replace('pix', 'vel') for pixel_column in pixel_columns]
        acceleration_columns = [
            pixel_column.replace('pix', 'acc') for pixel_column in pixel_columns
        ]

        gaze_data = {
            'subject_id': fileinfo_row['subject_id'],
            'time': np.arange(1000),
        }
        gaze_schema = {
            'subject_id': pl.Int64,
            'time': pl.Int64,
        }

        for column in pixel_columns + position_columns + velocity_columns + acceleration_columns:
            gaze_data[column] = np.zeros(1000)
            gaze_schema[column] = pl.Float64

        # Create GazeDataFrames for passing as ground truth
        gaze_df = GazeDataFrame(
            pl.from_dict(gaze_data, schema=gaze_schema),
            pixel_columns=pixel_columns,
            position_columns=position_columns,
            velocity_columns=velocity_columns,
            acceleration_columns=acceleration_columns,
        )

        preprocessed_gaze_dfs.append(gaze_df)

    create_preprocessed_gaze_files_from_fileinfo(
        preprocessed_gaze_dfs, fileinfo, rootpath / 'preprocessed',
    )

    event_dfs = []
    for fileinfo_row in fileinfo.to_dicts():
        event_df = pl.from_dict(
            {
                'subject_id': fileinfo_row['subject_id'],
                'name': ['saccade', 'fixation'] * 5,
                'onset': np.arange(0, 100, 10),
                'offset': np.arange(5, 105, 10),
                'duration': np.array([5] * 10),
            },
            schema={
                'subject_id': pl.Int64,
                'name': pl.Utf8,
                'onset': pl.Int64,
                'offset': pl.Int64,
                'duration': pl.Int64,
            },
        )
        event_dfs.append(event_df)

    create_event_files_from_fileinfo(event_dfs, fileinfo, rootpath / 'events')

    dataset_definition = DatasetDefinition(
        experiment=Experiment(
            screen_width_px=1280,
            screen_height_px=1024,
            screen_width_cm=38,
            screen_height_cm=30.2,
            distance_cm=distance_cm,
            origin='upper left',
            sampling_rate=1000,
        ),
        filename_format={
            'gaze': r'{subject_id:d}.' + raw_fileformat,
            'precomputed_events': r'{subject_id:d}.' + raw_fileformat,
            'precomputed_reading_measures': r'{subject_id:d}.' + raw_fileformat,
        },
        filename_format_schema_overrides=filename_format_schema_overrides,
        custom_read_kwargs={
            'gaze': {},
            'precomputed_events': {},
            'precomputed_reading_measures': {},
        },
        time_column='time',
        time_unit='ms',
        distance_column=distance_column,
        pixel_columns=pixel_columns,
        has_files=has_files,
        extract=extract,
    )

    precomputed_dfs = []
    for fileinfo_row in fileinfo.to_dicts():
        precomputed_event_df = pl.from_dict(
            {
                'subject_id': fileinfo_row['subject_id'],
                'CURRENT_FIXATION_DURATION': np.arange(1000),
                'CURRENT_FIX_X': np.zeros(1000),
                'CURRENT_FIX_Y': np.zeros(1000),
                'trial_id_1': np.concatenate([np.zeros(500), np.ones(500)]),
                'trial_id_2': ['a'] * 200 + ['b'] * 200 + ['c'] * 600,
            },
            schema={
                'subject_id': pl.Int64,
                'CURRENT_FIXATION_DURATION': pl.Float64,
                'CURRENT_FIX_X': pl.Float64,
                'CURRENT_FIX_Y': pl.Float64,
                'trial_id_1': pl.Float64,
                'trial_id_2': pl.Utf8,
            },
        )
        precomputed_dfs.append(precomputed_event_df)

    create_precomputed_files_from_fileinfo(
        precomputed_dfs,
        fileinfo,
        rootpath / 'precomputed_events',
    )

    precomputed_rm_dfs = []
    for fileinfo_row in fileinfo.to_dicts():
        precomputed_rm_df = pl.from_dict(
            {
                'subject_id': fileinfo_row['subject_id'],
                'number_fix': np.arange(1000),
                'mean_fix_dur': np.zeros(1000),
            },
            schema={
                'subject_id': pl.Int64,
                'number_fix': pl.Float64,
                'mean_fix_dur': pl.Float64,
            },
        )
        precomputed_rm_dfs.append(precomputed_rm_df)

    create_precomputed_rm_files_from_fileinfo(
        precomputed_rm_dfs,
        fileinfo,
        rootpath / 'precomputed_reading_measures',
    )

    return {
        'init_kwargs': {
            'definition': dataset_definition,
            'path': DatasetPaths(root=rootpath, dataset='.'),
        },
        'fileinfo': {
            'gaze': fileinfo,
            'precomputed_events': fileinfo,
            'precomputed_reading_measures': fileinfo,
        },
        'raw_gaze_dfs': gaze_dfs,
        'preprocessed_gaze_dfs': preprocessed_gaze_dfs,
        'event_dfs': event_dfs,
        'precomputed_rm_dfs': precomputed_rm_dfs,
        'eyes': eyes,
        'trial_columns': ['subject_id'],
    }


@pytest.fixture(
    name='gaze_dataset_configuration',
    params=[
        'ToyMono',
        'ToyBino',
        'ToyLeft',
        'ToyRight',
        'ToyBino+Avg',
        'ToyRemote',
    ],
)
def gaze_fixture_dataset(request, tmp_path):
    rootpath = tmp_path

    dataset_type = request.param
    if dataset_type == 'ToyBino':
        dataset_dict = mock_toy(rootpath, raw_fileformat='csv', eyes='both')
    elif dataset_type == 'ToyBino+Avg':
        dataset_dict = mock_toy(rootpath, raw_fileformat='csv', eyes='both+avg')
    elif dataset_type == 'ToyMono':
        dataset_dict = mock_toy(rootpath, raw_fileformat='csv', eyes='none')
    elif dataset_type == 'ToyLeft':
        dataset_dict = mock_toy(rootpath, raw_fileformat='csv', eyes='left')
    elif dataset_type == 'ToyRight':
        dataset_dict = mock_toy(rootpath, raw_fileformat='csv', eyes='right')
    elif dataset_type == 'ToyMat':
        dataset_dict = mock_toy(rootpath, raw_fileformat='mat', eyes='both')
    elif dataset_type == 'ToyRemote':
        dataset_dict = mock_toy(rootpath, raw_fileformat='csv', eyes='both', remote=True)
    else:
        raise ValueError(f'{request.param} not supported as dataset mock')

    yield dataset_dict


def test_init_with_definition_class():
    @dataclass
    class CustomPublicDataset(DatasetDefinition):
        name: str = 'CustomPublicDataset'

    dataset = Dataset(CustomPublicDataset, path='.')

    assert dataset.definition == CustomPublicDataset()


def test_load_correct_fileinfo(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()

    expected_fileinfo = gaze_dataset_configuration['fileinfo']
    assert_frame_equal(dataset.fileinfo['gaze'], expected_fileinfo['gaze'])


def test_load_correct_raw_gaze_dfs(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()

    expected_gaze_dfs = gaze_dataset_configuration['raw_gaze_dfs']
    for result_gaze_df, expected_gaze_df in zip(dataset.gaze, expected_gaze_dfs):
        assert_frame_equal(
            result_gaze_df.frame,
            expected_gaze_df.frame,
            check_column_order=False,
        )


def test_loaded_gazes_do_not_share_experiment_with_definition(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()

    definition = gaze_dataset_configuration['init_kwargs']['definition']

    for gaze in dataset.gaze:
        assert gaze.experiment is not definition.experiment


def test_loaded_gazes_do_not_share_experiment_with_other(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()

    for gaze1 in dataset.gaze:
        for gaze2 in dataset.gaze:
            if gaze1 is gaze2:
                continue

            assert gaze1.experiment is not gaze2.experiment


def test_load_gaze_has_position_columns(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(preprocessed=True)

    for result_gaze_df in dataset.gaze:
        assert 'position' in result_gaze_df.columns


def test_load_correct_preprocessed_gaze_dfs(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(preprocessed=True)

    expected_gaze_dfs = gaze_dataset_configuration['preprocessed_gaze_dfs']
    for result_gaze_df, expected_gaze_df in zip(dataset.gaze, expected_gaze_dfs):
        assert_frame_equal(
            result_gaze_df.frame,
            expected_gaze_df.frame,
            check_column_order=False,
        )


def test_load_correct_trial_columns(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()

    expected_trial_columns = gaze_dataset_configuration['trial_columns']
    for result_gaze_df in dataset.gaze:
        assert result_gaze_df.trial_columns == expected_trial_columns


@pytest.mark.parametrize(
    'gaze_dataset_configuration',
    ['ToyMono'],
    indirect=['gaze_dataset_configuration'],
)
def test_load_fileinfo_column_in_trial_columns_warns(gaze_dataset_configuration):
    # add fileinfo column as trial column
    gaze_dataset_configuration['init_kwargs']['definition'].trial_columns = ['subject_id']

    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])

    with pytest.warns(UserWarning) as record:
        dataset.load()

    expected_msg = 'removed duplicated fileinfo columns from trial_columns: subject_id'
    assert record[0].message.args[0] == expected_msg


def test_load_correct_event_dfs(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(events=True)

    expected_event_dfs = gaze_dataset_configuration['event_dfs']
    for result_event_df, expected_event_df in zip(dataset.events, expected_event_dfs):
        assert_frame_equal(result_event_df.frame, expected_event_df)


@pytest.mark.parametrize(
    ('subset', 'fileinfo_idx'),
    [
        pytest.param(
            {'subject_id': 1},
            [0],
            id='subset_int',
        ),
        pytest.param(
            {'subject_id': [1, 11, 12]},
            [0, 2, 3],
            id='subset_list',
        ),
        pytest.param(
            {'subject_id': range(3)},
            [0, 11],
            id='subset_range',
        ),
    ],
)
def test_load_subset(subset, fileinfo_idx, gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(subset=subset)

    expected_fileinfo = gaze_dataset_configuration['fileinfo']
    expected_fileinfo = expected_fileinfo['gaze'][fileinfo_idx]

    assert_frame_equal(dataset.fileinfo['gaze'], expected_fileinfo)


@pytest.mark.parametrize(
    ('init_kwargs', 'load_kwargs', 'exception'),
    [
        pytest.param(
            {},
            {'subset': 1},
            TypeError,
            id='subset_no_dict',
        ),
        pytest.param(
            {},
            {'subset': {1: 1}},
            TypeError,
            id='subset_no_str_key',
        ),
        pytest.param(
            {},
            {'subset': {'unknown': 1}},
            ValueError,
            id='subset_key_not_in_fileinfo',
        ),
        pytest.param(
            {},
            {'subset': {'subject_id': None}},
            TypeError,
            id='subset_value_invalid_type',
        ),
    ],
)
def test_load_exceptions(init_kwargs, load_kwargs, exception, gaze_dataset_configuration):
    init_kwargs = {**gaze_dataset_configuration['init_kwargs'], **init_kwargs}
    dataset = Dataset(**init_kwargs)

    with pytest.raises(exception):
        dataset.load(**load_kwargs)


@pytest.mark.parametrize(
    ('init_kwargs', 'save_kwargs', 'exception'),
    [
        pytest.param(
            {},
            {'extension': 'invalid'},
            ValueError,
            id='wrong_extension_save_gaze',
        ),
    ],
)
def test_save_gaze_exceptions(init_kwargs, save_kwargs, exception, gaze_dataset_configuration):
    init_kwargs = {**gaze_dataset_configuration['init_kwargs'], **init_kwargs}
    dataset = Dataset(**init_kwargs)

    with pytest.raises(exception):
        dataset.load()
        dataset.pix2deg()
        dataset.pos2vel()
        dataset.pos2acc()
        dataset.save_preprocessed(**save_kwargs)


@pytest.mark.parametrize(
    ('load_kwargs', 'exception'),
    [
        pytest.param(
            {'extension': 'invalid'},
            ValueError,
            id='wrong_extension_load_events',
        ),
    ],
)
def test_load_events_exceptions(
        load_kwargs,
        exception,
        gaze_dataset_configuration,
):
    init_kwargs = {**gaze_dataset_configuration['init_kwargs']}
    dataset = Dataset(**init_kwargs)

    with pytest.raises(exception) as excinfo:
        dataset.load()
        dataset.pix2deg()
        dataset.pos2vel()
        dataset.detect_events(
            method=events.ivt,
            velocity_threshold=45,
            minimum_duration=55,
        )
        dataset.save_events()
        dataset.load_event_files(**load_kwargs)

    msg, = excinfo.value.args
    assert msg == """\
unsupported file format "invalid".\
Supported formats are: [\'csv\', \'txt\', \'tsv\', \'feather\']"""


@pytest.mark.parametrize(
    ('init_kwargs', 'save_kwargs', 'exception'),
    [
        pytest.param(
            {},
            {'extension': 'invalid'},
            ValueError,
            id='wrong_extension_events',
        ),
    ],
)
def test_save_events_exceptions(init_kwargs, save_kwargs, exception, gaze_dataset_configuration):
    init_kwargs = {**gaze_dataset_configuration['init_kwargs'], **init_kwargs}
    dataset = Dataset(**init_kwargs)

    with pytest.raises(exception):
        dataset.load()
        dataset.pix2deg()
        dataset.pos2vel()
        dataset.detect_events(
            method=events.ivt,
            velocity_threshold=45,
            minimum_duration=55,
        )
        dataset.save_events(**save_kwargs)


def test_load_no_files_raises_exception(gaze_dataset_configuration):
    init_kwargs = {**gaze_dataset_configuration['init_kwargs']}
    dataset = Dataset(**init_kwargs)

    shutil.rmtree(dataset.paths.raw, ignore_errors=True)
    dataset.paths.raw.mkdir()

    with pytest.raises(RuntimeError):
        dataset.load()


@pytest.mark.parametrize(
    'gaze_dataset_configuration',
    ['ToyMat'],
    indirect=['gaze_dataset_configuration'],
)
def test_load_mat_file_exception(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])

    with pytest.raises(ValueError):
        dataset.load()


def test_pix2deg(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()

    original_schema = dataset.gaze[0].schema

    dataset.pix2deg()

    expected_schema = {**original_schema, 'position': pl.List(pl.Float64)}
    for result_gaze_df in dataset.gaze:
        assert result_gaze_df.schema == expected_schema


def test_deg2pix(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()

    original_schema = dataset.gaze[0].schema

    dataset.pix2deg()
    dataset.deg2pix(pixel_column='new_pixel')

    expected_schema = {
        **original_schema, 'position': pl.List(pl.Float64),
        'new_pixel': pl.List(pl.Float64),
    }
    for result_gaze_df in dataset.gaze:
        assert result_gaze_df.schema == expected_schema


def test_pos2acc(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()

    original_schema = dataset.gaze[0].schema

    dataset.pos2acc()

    expected_schema = {**original_schema, 'acceleration': pl.List(pl.Float64)}
    for result_gaze_df in dataset.gaze:
        assert result_gaze_df.schema == expected_schema


def test_pos2vel(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()

    original_schema = dataset.gaze[0].schema

    dataset.pos2vel()

    expected_schema = {**original_schema, 'velocity': pl.List(pl.Float64)}
    for result_gaze_df in dataset.gaze:
        assert result_gaze_df.schema == expected_schema


def test_clip(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()

    original_schema = dataset.gaze[0].schema

    dataset.clip(-1000, 1000, input_column='pixel', output_column='pixel_clipped', n_components=2)

    expected_schema = {**original_schema, 'pixel_clipped': pl.List(pl.Float64)}
    for result_gaze_df in dataset.gaze:
        assert result_gaze_df.schema == expected_schema


@pytest.mark.parametrize(
    'detect_event_kwargs',
    [
        pytest.param(
            {
                'method': events.microsaccades,
                'threshold': 1,
                'eye': 'auto',
            },
            id='microsaccades_class',
        ),
        pytest.param(
            {
                'method': 'microsaccades',
                'threshold': 1,
                'eye': 'auto',
            },
            id='microsaccades_string',
        ),
        pytest.param(
            {
                'method': events.fill,
                'eye': 'auto',
            },
            id='fill_class',
        ),
        pytest.param(
            {
                'method': 'fill',
                'eye': 'auto',
            },
            id='fill_string',
        ),
        pytest.param(
            {
                'method': 'ivt',
                'velocity_threshold': 1,
                'minimum_duration': 1,
                'eye': 'auto',
            },
            id='ivt_string',
        ),
        pytest.param(
            {
                'method': events.ivt,
                'velocity_threshold': 1,
                'minimum_duration': 1,
                'eye': 'auto',
            },
            id='ivt_class',
        ),
        pytest.param(
            {
                'method': 'idt',
                'eye': 'auto',
            },
            id='idt_string',
        ),
        pytest.param(
            {
                'method': events.idt,
                'eye': 'auto',
            },
            id='idt_class',
        ),
    ],
)
def test_detect_events_auto_eye(detect_event_kwargs, gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()
    dataset.detect_events(**detect_event_kwargs)

    expected_schema = {
        'subject_id': pl.Int64,
        'name': pl.Utf8,
        'onset': pl.Int64,
        'offset': pl.Int64,
        'duration': pl.Int64,
    }
    for result_event_df in dataset.events:
        assert result_event_df.schema == expected_schema


@pytest.mark.parametrize(
    'detect_event_kwargs',
    [
        pytest.param(
            {
                'method': events.microsaccades,
                'threshold': 1,
                'eye': 'left',
            },
            id='left',
        ),
        pytest.param(
            {
                'method': events.microsaccades,
                'threshold': 1,
                'eye': 'right',
            },
            id='right',
        ),
    ],
)
def test_detect_events_explicit_eye(detect_event_kwargs, gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()

    dataset_eyes = gaze_dataset_configuration['eyes']

    exception = None
    if not dataset_eyes.startswith('both') and detect_event_kwargs['eye'] is not None:
        exception = AttributeError

    if exception is None:
        dataset.detect_events(**detect_event_kwargs)

        expected_schema = {
            'subject_id': pl.Int64,
            'name': pl.Utf8,
            'onset': pl.Int64,
            'offset': pl.Int64,
            'duration': pl.Int64,
        }

        for result_event_df in dataset.events:
            assert result_event_df.schema == expected_schema

    else:
        with pytest.raises(exception):
            dataset.detect_events(**detect_event_kwargs)


@pytest.mark.parametrize(
    ('detect_event_kwargs_1', 'detect_event_kwargs_2', 'expected_schema'),
    [
        pytest.param(
            {
                'method': events.microsaccades,
                'threshold': 1,
                'eye': 'auto',
            },
            {
                'method': events.microsaccades,
                'threshold': 1,
                'eye': 'auto',
            },
            {
                'subject_id': pl.Int64,
                'name': pl.Utf8,
                'onset': pl.Int64,
                'offset': pl.Int64,
                'duration': pl.Int64,
            },
            id='two-saccade-runs',
        ),
        pytest.param(
            {
                'method': events.microsaccades,
                'threshold': 1,
                'eye': 'auto',
            },
            {
                'method': events.ivt,
                'velocity_threshold': 1,
                'minimum_duration': 1,
            },
            {
                'subject_id': pl.Int64,
                'name': pl.Utf8,
                'onset': pl.Int64,
                'offset': pl.Int64,
                'duration': pl.Int64,
            },
            id='one-saccade-one-fixation-run',
        ),
    ],
)
def test_detect_events_multiple_calls(
        detect_event_kwargs_1,
        detect_event_kwargs_2,
        expected_schema,
        gaze_dataset_configuration,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()
    dataset.detect_events(**detect_event_kwargs_1)
    dataset.detect_events(**detect_event_kwargs_2)

    for result_event_df in dataset.events:
        assert result_event_df.schema == expected_schema


@pytest.mark.parametrize(
    'detect_kwargs',
    [
        pytest.param(
            {
                'method': 'microsaccades',
                'threshold': 1,
                'eye': 'auto',
                'clear': False,
                'verbose': True,
            },
            id='left',
        ),
    ],
)
def test_detect_events_alias(gaze_dataset_configuration, detect_kwargs, monkeypatch):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()

    mock = Mock()
    monkeypatch.setattr(dataset, 'detect', mock)

    dataset.detect(**detect_kwargs)
    mock.assert_called_with(**detect_kwargs)


@pytest.mark.parametrize(
    'gaze_dataset_configuration',
    ['ToyMono'],
    indirect=['gaze_dataset_configuration'],
)
def test_detect_events_attribute_error(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()

    detect_event_kwargs = {
        'method': events.microsaccades,
        'threshold': 1,
        'eye': 'right',
    }

    with pytest.raises(AttributeError):
        dataset.detect_events(**detect_event_kwargs)


@pytest.mark.parametrize(
    'gaze_dataset_configuration',
    ['ToyMono'],
    indirect=['gaze_dataset_configuration'],
)
@pytest.mark.parametrize(
    ('rename_arg', 'detect_event_kwargs', 'expected_message'),
    [
        pytest.param(
            {'position': 'custom_position'},
            {
                'method': events.idt,
                'threshold': 1,
            },
            (
                "Column 'position' not found. Available columns are: "
                "['time', 'trial_id_1', 'trial_id_2', 'subject_id', "
                "'pixel', 'custom_position', 'velocity']"
            ),
            id='no_position',
        ),
        pytest.param(
            {'velocity': 'custom_velocity'},
            {
                'method': events.microsaccades,
                'threshold': 1,
            },
            (
                "Column 'velocity' not found. Available columns are: "
                "['time', 'trial_id_1', 'trial_id_2', 'subject_id', "
                "'pixel', 'position', 'custom_velocity']"
            ),
            id='no_velocity',
        ),
    ],
)
def test_detect_events_raises_column_not_found_error(
        gaze_dataset_configuration,
        rename_arg,
        detect_event_kwargs,
        expected_message,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()

    for file_id, _ in enumerate(dataset.gaze):
        dataset.gaze[file_id].frame = dataset.gaze[file_id].frame.rename(rename_arg)

    with pytest.raises(pl.exceptions.ColumnNotFoundError) as excinfo:
        dataset.detect_events(**detect_event_kwargs)

    msg, = excinfo.value.args
    assert msg == expected_message


@pytest.mark.parametrize(
    ('events_init', 'events_expected'),
    [
        pytest.param(
            [],
            [],
            id='empty_list_stays_empty_list',
        ),
        pytest.param(
            [events.EventDataFrame()],
            [events.EventDataFrame()],
            id='empty_df_stays_empty_df',
        ),
        pytest.param(
            [events.EventDataFrame(name='event', onsets=[0], offsets=[99])],
            [events.EventDataFrame()],
            id='single_instance_filled_df_gets_cleared_to_empty_df',
        ),
        pytest.param(
            [
                events.EventDataFrame(name='event', onsets=[0], offsets=[99]),
                events.EventDataFrame(name='event', onsets=[0], offsets=[99]),
            ],
            [events.EventDataFrame(), events.EventDataFrame()],
            id='two_instance_filled_df_gets_cleared_to_two_empty_dfs',
        ),
    ],
)
def test_clear_events(events_init, events_expected, tmp_path):
    dataset = Dataset('ToyDataset', path=tmp_path)
    dataset.events = events_init
    dataset.clear_events()

    if isinstance(events_init, list) and not events_init:
        assert dataset.events == events_expected

    else:
        for events_df_result, events_df_expected in zip(dataset.events, events_expected):
            assert_frame_equal(events_df_result.frame, events_df_expected.frame)


@pytest.mark.parametrize(
    ('detect_event_kwargs', 'events_dirname', 'expected_save_dirpath', 'save_kwargs'),
    [
        pytest.param(
            {'method': events.microsaccades, 'threshold': 1, 'eye': 'auto'},
            None,
            'events',
            {},
            id='none_dirname',
        ),
        pytest.param(
            {'method': events.microsaccades, 'threshold': 1, 'eye': 'auto'},
            'events_test',
            'events_test',
            {},
            id='explicit_dirname',
        ),
        pytest.param(
            {'method': events.microsaccades, 'threshold': 1, 'eye': 'auto'},
            None,
            'events',
            {'extension': 'csv'},
            id='save_events_extension_csv',
        ),
    ],
)
def test_save_events(
        detect_event_kwargs,
        events_dirname,
        expected_save_dirpath,
        save_kwargs,
        gaze_dataset_configuration,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()
    dataset.detect_events(**detect_event_kwargs)

    if events_dirname is None:
        events_dirname = 'events'
    shutil.rmtree(dataset.path / Path(events_dirname), ignore_errors=True)
    shutil.rmtree(dataset.path / Path(expected_save_dirpath), ignore_errors=True)
    dataset.save_events(events_dirname, **save_kwargs)

    assert (dataset.path / expected_save_dirpath).is_dir(), (
        f'data was not written to {dataset.path / Path(expected_save_dirpath)}'
    )


@pytest.mark.parametrize(
    ('detect_event_kwargs', 'events_dirname', 'expected_save_dirpath', 'load_save_kwargs'),
    [
        pytest.param(
            {'method': events.microsaccades, 'threshold': 1, 'eye': 'auto'},
            None,
            'events',
            {},
            id='none_dirname',
        ),
        pytest.param(
            {'method': events.microsaccades, 'threshold': 1, 'eye': 'auto'},
            'events_test',
            'events_test',
            {},
            id='explicit_dirname',
        ),
        pytest.param(
            {'method': events.microsaccades, 'threshold': 1, 'eye': 'auto'},
            None,
            'events',
            {'extension': 'csv'},
            id='load_events_extension_csv',
        ),
    ],
)
def test_load_previously_saved_events_gaze(
        detect_event_kwargs,
        events_dirname,
        expected_save_dirpath,
        load_save_kwargs,
        gaze_dataset_configuration,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()
    dataset.pos2acc()
    dataset.detect_events(**detect_event_kwargs)

    # We must not overwrite the original variable as it's needed in the end.
    if events_dirname is None:
        events_dirname_ = 'events'
    else:
        events_dirname_ = events_dirname

    shutil.rmtree(dataset.path / Path(events_dirname_), ignore_errors=True)
    shutil.rmtree(dataset.path / Path(expected_save_dirpath), ignore_errors=True)
    dataset.save_events(events_dirname, **load_save_kwargs)
    dataset.save_preprocessed(**load_save_kwargs)

    dataset.events = []

    dataset.load(events=True, preprocessed=True, events_dirname=events_dirname, **load_save_kwargs)
    assert dataset.events


@pytest.mark.parametrize(
    ('preprocessed_dirname', 'expected_save_dirpath'),
    [
        pytest.param(
            None,
            'preprocessed',
            id='none_dirname',
        ),
        pytest.param(
            'preprocessed_test',
            'preprocessed_test',
            id='explicit_dirname',
        ),
    ],
)
def test_save_preprocessed_directory_exists(
        preprocessed_dirname,
        expected_save_dirpath,
        gaze_dataset_configuration,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()
    dataset.pos2acc()

    if preprocessed_dirname is None:
        preprocessed_dirname = 'preprocessed'
    shutil.rmtree(dataset.path / Path(preprocessed_dirname), ignore_errors=True)
    shutil.rmtree(dataset.path / Path(expected_save_dirpath), ignore_errors=True)
    dataset.save_preprocessed(preprocessed_dirname)

    assert (dataset.path / expected_save_dirpath).is_dir(), (
        f'data was not written to {dataset.path / Path(expected_save_dirpath)}'
    )


@pytest.mark.parametrize(
    'drop_column',
    [
        'time',
        'pixel',
        'position',
        'velocity',
        'acceleration',
    ],
)
def test_save_preprocessed(gaze_dataset_configuration, drop_column):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()
    dataset.pos2acc()

    dataset.gaze[0].frame = dataset.gaze[0].frame.drop(drop_column)

    preprocessed_dirname = 'preprocessed-test'
    shutil.rmtree(dataset.path / Path(preprocessed_dirname), ignore_errors=True)
    shutil.rmtree(dataset.path / Path(preprocessed_dirname), ignore_errors=True)
    dataset.save_preprocessed(preprocessed_dirname, extension='csv')
    dataset.load_gaze_files(True, preprocessed_dirname, extension='csv')

    assert (dataset.path / preprocessed_dirname).is_dir(), (
        f'data was not written to {dataset.path / Path(preprocessed_dirname)}'
    )


@pytest.mark.parametrize(
    'drop_column',
    [
        'time',
        'pixel',
        'position',
        'velocity',
        'acceleration',
    ],
)
def test_save_preprocessed_has_no_side_effect(gaze_dataset_configuration, drop_column):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()
    dataset.pos2acc()

    dataset.gaze[0].frame = dataset.gaze[0].frame.drop(drop_column)

    old_frame = dataset.gaze[0].frame.clone()

    preprocessed_dirname = 'preprocessed-test'
    shutil.rmtree(dataset.path / Path(preprocessed_dirname), ignore_errors=True)
    shutil.rmtree(dataset.path / Path(preprocessed_dirname), ignore_errors=True)
    dataset.save_preprocessed(preprocessed_dirname, extension='csv')

    new_frame = dataset.gaze[0].frame.clone()

    assert_frame_equal(old_frame, new_frame)


@pytest.mark.parametrize(
    ('expected_save_preprocessed_path', 'expected_save_events_path', 'save_kwargs'),
    [
        pytest.param(
            'preprocessed',
            'events',
            {},
            id='none_dirname',
        ),
        pytest.param(
            'preprocessed',
            'events',
            {'verbose': 2},
            id='verbose_equals_2',
        ),
        pytest.param(
            'preprocessed_test',
            'events',
            {'preprocessed_dirname': 'preprocessed_test'},
            id='explicit_prepocessed_dirname',
        ),
        pytest.param(
            'preprocessed',
            'events_test',
            {'events_dirname': 'events_test'},
            id='explicit_events_dirname',
        ),
        pytest.param(
            'preprocessed',
            'events',
            {'extension': 'csv'},
            id='extension_equals_csv',
        ),
    ],
)
def test_save_creates_correct_directory(
        expected_save_preprocessed_path,
        expected_save_events_path,
        save_kwargs,
        gaze_dataset_configuration,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()

    detect_events_kwargs = {'method': events.microsaccades, 'threshold': 1, 'eye': 'auto'}
    dataset.detect_events(**detect_events_kwargs)

    preprocessed_dirname = save_kwargs.get('preprocessed_dirname', 'preprocessed')
    events_dirname = save_kwargs.get('events_dirname', 'events')

    shutil.rmtree(dataset.path / Path(preprocessed_dirname), ignore_errors=True)
    shutil.rmtree(dataset.path / Path(expected_save_preprocessed_path), ignore_errors=True)
    shutil.rmtree(dataset.path / Path(events_dirname), ignore_errors=True)
    shutil.rmtree(dataset.path / Path(expected_save_events_path), ignore_errors=True)
    dataset.save(**save_kwargs)

    assert (dataset.path / Path(expected_save_preprocessed_path)).is_dir(), (
        f'data was not written to {dataset.path / Path(expected_save_preprocessed_path)}'
    )
    assert (dataset.path / Path(expected_save_events_path)).is_dir(), (
        f'data was not written to {dataset.path / Path(expected_save_events_path)}'
    )


@pytest.mark.parametrize(
    ('expected_save_preprocessed_path', 'expected_save_events_path', 'save_kwargs'),
    [
        pytest.param(
            'preprocessed',
            'events',
            {'extension': 'feather'},
            id='extension_equals_feather',
        ),
        pytest.param(
            'preprocessed',
            'events',
            {'extension': 'csv'},
            id='extension_equals_csv',
        ),
    ],
)
def test_save_files_have_correct_extension(
        expected_save_preprocessed_path,
        expected_save_events_path,
        save_kwargs,
        gaze_dataset_configuration,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.pix2deg()
    dataset.pos2vel()
    dataset.pos2acc()

    detect_events_kwargs = {'method': events.microsaccades, 'threshold': 1, 'eye': 'auto'}
    dataset.detect_events(**detect_events_kwargs)

    preprocessed_dirname = save_kwargs.get('preprocessed_dirname', 'preprocessed')
    events_dirname = save_kwargs.get('events_dirname', 'events')
    extension = save_kwargs.get('extension', 'feather')

    shutil.rmtree(dataset.path / Path(preprocessed_dirname), ignore_errors=True)
    shutil.rmtree(dataset.path / Path(expected_save_preprocessed_path), ignore_errors=True)
    shutil.rmtree(dataset.path / Path(events_dirname), ignore_errors=True)
    shutil.rmtree(dataset.path / Path(expected_save_events_path), ignore_errors=True)
    dataset.save(**save_kwargs)

    preprocessed_dir = dataset.path / Path(expected_save_preprocessed_path)
    preprocessed_file_list = os.listdir(preprocessed_dir)
    extension_list = [a.endswith(extension) for a in preprocessed_file_list]
    extension_sum = sum(extension_list)
    assert extension_sum == len(preprocessed_file_list), (
        f'not all preprocessed files created have correct extension {extension}'
    )

    events_dir = dataset.path / Path(expected_save_events_path)
    events_file_list = os.listdir(events_dir)
    extension_list = [a.endswith(extension) for a in events_file_list]
    extension_sum = sum(extension_list)
    assert extension_sum == len(events_file_list), (
        f'not all events files created have correct extension {extension}'
    )


@pytest.mark.parametrize(
    ('init_path', 'expected_paths'),
    [
        pytest.param(
            '/data/set/path',
            {
                'root': Path('/data/set/path/'),
                'dataset': Path('/data/set/path/'),
                'raw': Path('/data/set/path/raw'),
                'preprocessed': Path('/data/set/path/preprocessed'),
                'events': Path('/data/set/path/events'),
            },
        ),
        pytest.param(
            DatasetPaths(root='/data/set/path', dataset='.'),
            {
                'root': Path('/data/set/path/'),
                'dataset': Path('/data/set/path/'),
                'raw': Path('/data/set/path/raw'),
                'preprocessed': Path('/data/set/path/preprocessed'),
                'events': Path('/data/set/path/events'),
            },
        ),
        pytest.param(
            DatasetPaths(root='/data/set/path', dataset='dataset'),
            {
                'root': Path('/data/set/path/'),
                'dataset': Path('/data/set/path/dataset'),
                'raw': Path('/data/set/path/dataset/raw'),
                'preprocessed': Path('/data/set/path/dataset/preprocessed'),
                'events': Path('/data/set/path/dataset/events'),
            },
        ),
        pytest.param(
            DatasetPaths(root='/data/set/path', dataset='dataset', events='custom_events'),
            {
                'root': Path('/data/set/path/'),
                'dataset': Path('/data/set/path/dataset'),
                'raw': Path('/data/set/path/dataset/raw'),
                'preprocessed': Path('/data/set/path/dataset/preprocessed'),
                'events': Path('/data/set/path/dataset/custom_events'),
            },
        ),
        pytest.param(
            DatasetPaths(
                root='/data/set/path',
                dataset='dataset',
                preprocessed='custom_preprocessed',
            ),
            {
                'root': Path('/data/set/path/'),
                'dataset': Path('/data/set/path/dataset'),
                'raw': Path('/data/set/path/dataset/raw'),
                'preprocessed': Path('/data/set/path/dataset/custom_preprocessed'),
                'events': Path('/data/set/path/dataset/events'),
            },
        ),
        pytest.param(
            DatasetPaths(root='/data/set/path', dataset='dataset', raw='custom_raw'),
            {
                'root': Path('/data/set/path/'),
                'dataset': Path('/data/set/path/dataset'),
                'raw': Path('/data/set/path/dataset/custom_raw'),
                'preprocessed': Path('/data/set/path/dataset/preprocessed'),
                'events': Path('/data/set/path/dataset/events'),
            },
        ),
    ],
)
def test_paths(init_path, expected_paths):
    dataset = Dataset('ToyDataset', path=init_path)

    assert dataset.paths.root == expected_paths['root']
    assert dataset.paths.dataset == expected_paths['dataset']
    assert dataset.path == expected_paths['dataset']
    assert dataset.paths.raw == expected_paths['raw']
    assert dataset.paths.preprocessed == expected_paths['preprocessed']
    assert dataset.paths.events == expected_paths['events']


@pytest.mark.parametrize(
    ('new_fileinfo', 'exception'),
    [
        pytest.param(None, AttributeError),
        pytest.param([], AttributeError),
    ],
)
def test_check_fileinfo(new_fileinfo, exception, tmp_path):
    dataset = Dataset('ToyDataset', path=tmp_path)

    dataset.fileinfo = new_fileinfo

    with pytest.raises(exception):
        dataset._check_fileinfo()


@pytest.mark.parametrize(
    ('new_gaze', 'exception'),
    [
        pytest.param(None, AttributeError),
        pytest.param([], AttributeError),
    ],
)
def test_check_gaze_dataframe(new_gaze, exception, tmp_path):
    dataset = Dataset('ToyDataset', path=tmp_path)

    dataset.gaze = new_gaze

    with pytest.raises(exception):
        dataset._check_gaze_dataframe()


@pytest.mark.parametrize(
    'gaze_dataset_configuration',
    ['ToyBino'],
    indirect=['gaze_dataset_configuration'],
)
def test_check_experiment(gaze_dataset_configuration):
    gaze_dataset_configuration['init_kwargs']['definition'].experiment = None
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()

    with pytest.raises(AttributeError):
        dataset.gaze[0]._check_experiment()


@pytest.mark.parametrize(
    'gaze_dataset_configuration',
    ['ToyBino'],
    indirect=['gaze_dataset_configuration'],
)
def test_velocity_columns(gaze_dataset_configuration):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(preprocessed=True)

    for gaze_df in dataset.gaze:
        assert 'velocity' in gaze_df.columns


@pytest.mark.parametrize(
    ('property_kwargs', 'exception', 'msg_substrings'),
    [
        pytest.param(
            {'event_properties': 'foo'},
            InvalidProperty,
            ('foo', 'invalid', 'valid', 'peak_velocity'),
            id='invalid_property',
        ),

        pytest.param(
            {'event_properties': 'duration'},
            ValueError,
            (
                'event properties already exist and cannot be recomputed',
                'duration', 'Please remove them first',
            ),
            id='existing_column',
        ),
    ],
)
def test_event_dataframe_add_property_raises_exceptions(
        gaze_dataset_configuration,
        property_kwargs,
        exception,
        msg_substrings,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(preprocessed=True, events=True)

    with pytest.raises(exception) as excinfo:
        dataset.compute_event_properties(**property_kwargs)

    msg, = excinfo.value.args
    for msg_substring in msg_substrings:
        assert msg_substring.lower() in msg.lower()


@pytest.mark.parametrize(
    'property_kwargs',
    [
        pytest.param({'event_properties': 'peak_velocity'}, id='peak_velocity'),
    ],
)
def test_event_dataframe_add_property_has_expected_height(
        gaze_dataset_configuration,
        property_kwargs,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(preprocessed=True, events=True)

    expected_heights = [len(event_df) for event_df in dataset.events]

    dataset.compute_event_properties(**property_kwargs)

    for events_df, expected_height in zip(dataset.events, expected_heights):
        assert events_df.frame.height == expected_height


@pytest.mark.parametrize(
    ('property_kwargs', 'expected_schema'),
    [
        pytest.param(
            {'event_properties': 'peak_velocity'},
            {
                'subject_id': pl.Int64,
                'name': pl.Utf8,
                'onset': pl.Int64,
                'offset': pl.Int64,
                'duration': pl.Int64,
                'peak_velocity': pl.Float64,
            },
            id='single_event_peak_velocity',
        ),
        pytest.param(
            {'event_properties': 'location'},
            {
                'subject_id': pl.Int64,
                'name': pl.Utf8,
                'onset': pl.Int64,
                'offset': pl.Int64,
                'duration': pl.Int64,
                'location': pl.List(pl.Float64),
            },
            id='single_event_position',
        ),
    ],
)
def test_event_dataframe_add_property_has_expected_schema(
        gaze_dataset_configuration,
        property_kwargs,
        expected_schema,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(preprocessed=True, events=True)

    dataset.compute_event_properties(**property_kwargs)

    for events_df in dataset.events:
        assert events_df.frame.schema == expected_schema


@pytest.mark.parametrize(
    ('property_kwargs', 'expected_property_columns'),
    [
        pytest.param(
            {'event_properties': 'peak_velocity'},
            ['peak_velocity'],
            id='single_event_peak_velocity',
        ),
        pytest.param(
            {'event_properties': 'location'},
            ['location'],
            id='single_event_location',
        ),
        pytest.param(
            {'event_properties': 'location', 'name': 'fixation'},
            ['location'],
            id='single_event_location_name_fixation',
        ),
        pytest.param(
            {'event_properties': 'peak_velocity', 'name': 'sacc.*'},
            ['peak_velocity'],
            id='single_event_peak_velocity_regex_name_sacc',
        ),
    ],
)
def test_event_dataframe_add_property_effect_property_columns(
        gaze_dataset_configuration,
        property_kwargs,
        expected_property_columns,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(preprocessed=True, events=True)

    dataset.compute_event_properties(**property_kwargs)

    for events_df in dataset.events:
        assert events_df.event_property_columns == expected_property_columns


@pytest.mark.parametrize(
    ('property_kwargs', 'exception', 'exception_msg'),
    [
        pytest.param(
            {'event_properties': 'peak_velocity', 'name': 'taccade'},
            RuntimeError, 'No events with name "taccade" found in data frame',
            id='name_missing',
        ),
    ],
)
def test_event_dataframe_add_property_raises_exception(
        gaze_dataset_configuration,
        property_kwargs,
        exception,
        exception_msg,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(preprocessed=True, events=True)

    with pytest.raises(exception) as excinfo:
        dataset.compute_event_properties(**property_kwargs)

    msg, = excinfo.value.args
    assert msg == exception_msg


@pytest.mark.parametrize(
    'property_kwargs',
    [
        pytest.param(
            {'event_properties': 'peak_velocity'},
            id='single_event_peak_velocity',
        ),
        pytest.param(
            {'event_properties': 'location'},
            id='single_event_position',
        ),
        pytest.param(
            {'event_properties': 'location', 'name': 'fixation'},
            id='single_event_position_name_fixation',
        ),
    ],
)
def test_event_dataframe_add_property_does_not_change_length(
        gaze_dataset_configuration,
        property_kwargs,
):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(preprocessed=True, events=True)

    lengths_pre = [len(events_df.frame) for events_df in dataset.events]
    dataset.compute_event_properties(**property_kwargs)
    lengths_post = [len(events_df.frame) for events_df in dataset.events]

    assert lengths_pre == lengths_post


@pytest.mark.parametrize(
    'property_kwargs',
    [
        pytest.param(
            {
                'event_properties': 'peak_velocity',
                'name': None,
                'verbose': True,
            },
            id='peak_velocity',
        ),
    ],
)
def test_compute_event_properties_alias(gaze_dataset_configuration, property_kwargs, monkeypatch):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load(preprocessed=True, events=True)

    mock = Mock()
    monkeypatch.setattr(dataset, 'compute_event_properties', mock)

    dataset.compute_properties(**property_kwargs)
    mock.assert_called_with(**property_kwargs)


@pytest.fixture(
    name='precomputed_dataset_configuration',
    params=[
        'ToyRightPrecomputedEventAndGaze',
        'ToyPrecomputedEvent',
        'ToyPrecomputedEventNoExtract',
    ],
)
def precomputed_fixture_dataset(request, tmp_path):
    rootpath = tmp_path

    dataset_type = request.param
    if dataset_type == 'ToyRightPrecomputedEventAndGaze':
        dataset_dict = mock_toy(
            rootpath,
            raw_fileformat='csv',
            eyes='right',
            has_files={
                'gaze': True,
                'precomputed_events': True,
                'precomputed_reading_measures': False,
            },
        )
    elif dataset_type == 'ToyPrecomputedEvent':
        dataset_dict = mock_toy(
            rootpath,
            raw_fileformat='csv',
            eyes='right',
            has_files={
                'gaze': False,
                'precomputed_events': True,
                'precomputed_reading_measures': False,
            },
        )
    elif dataset_type == 'ToyPrecomputedEventNoExtract':
        dataset_dict = mock_toy(
            rootpath,
            raw_fileformat='csv',
            eyes='right',
            has_files={
                'gaze': False,
                'precomputed_events': True,
                'precomputed_reading_measures': False,
            },
            filename_format_schema_overrides={'precomputed_events': {}},
        )
    else:
        raise ValueError(f'{request.param} not supported as dataset mock')

    yield dataset_dict


def test_load_correct_fileinfo_precomputed(precomputed_dataset_configuration):
    dataset = Dataset(**precomputed_dataset_configuration['init_kwargs'])
    dataset.load()

    expected_fileinfo = precomputed_dataset_configuration['fileinfo']['precomputed_events']
    assert_frame_equal(dataset.fileinfo['precomputed_events'], expected_fileinfo)


def test_load_no_files_precomputed_raises_exception(precomputed_dataset_configuration):
    init_kwargs = {**precomputed_dataset_configuration['init_kwargs']}
    dataset = Dataset(**init_kwargs)

    shutil.rmtree(dataset.paths.precomputed_events, ignore_errors=True)
    dataset.paths.precomputed_events.mkdir()

    with pytest.raises(RuntimeError):
        dataset.load()


@pytest.fixture(
    name='precomputed_rm_dataset_configuration',
    params=[
        'ToyRightPrecomputedEventAndGazeAndRM',
        'ToyPrecomputedRM',
        'ToyPrecomputedRMNoExtract',
    ],
)
def precomputed_rm_fixture_dataset(request, tmp_path):
    rootpath = tmp_path

    dataset_type = request.param
    if dataset_type == 'ToyRightPrecomputedEventAndGazeAndRM':
        dataset_dict = mock_toy(
            rootpath,
            raw_fileformat='csv',
            eyes='right',
            has_files={
                'gaze': True,
                'precomputed_events': True,
                'precomputed_reading_measures': True,
            },
        )
    elif dataset_type == 'ToyPrecomputedRM':
        dataset_dict = mock_toy(
            rootpath,
            raw_fileformat='csv',
            eyes='right',
            has_files={
                'gaze': False,
                'precomputed_events': False,
                'precomputed_reading_measures': True,
            },
        )
    elif dataset_type == 'ToyPrecomputedRMNoExtract':
        dataset_dict = mock_toy(
            rootpath,
            raw_fileformat='csv',
            eyes='right',
            has_files={
                'gaze': False,
                'precomputed_events': False,
                'precomputed_reading_measures': True,
            },
            filename_format_schema_overrides={
                'precomputed_events': {},
                'precomputed_reading_measures': {},
            },
        )
    else:
        raise ValueError(f'{request.param} not supported as dataset mock')

    yield dataset_dict


def test_load_correct_fileinfo_precomputed_rm(precomputed_rm_dataset_configuration):
    dataset = Dataset(**precomputed_rm_dataset_configuration['init_kwargs'])
    dataset.load()

    all_fileinfo = precomputed_rm_dataset_configuration['fileinfo']
    expected_fileinfo = all_fileinfo['precomputed_reading_measures']
    assert_frame_equal(dataset.fileinfo['precomputed_reading_measures'], expected_fileinfo)


def test_load_no_files_precomputed_rm_raises_exception(precomputed_rm_dataset_configuration):
    init_kwargs = {**precomputed_rm_dataset_configuration['init_kwargs']}
    dataset = Dataset(**init_kwargs)

    shutil.rmtree(dataset.paths.precomputed_reading_measures, ignore_errors=True)
    dataset.paths.precomputed_reading_measures.mkdir()

    with pytest.raises(RuntimeError):
        dataset.load()


@pytest.mark.parametrize(
    ('by', 'expected_len'),
    [
        pytest.param(
            'trial_id_1',
            40,
            id='subset_int',
        ),
        pytest.param(
            'trial_id_2',
            60,
            id='subset_int',
        ),
        pytest.param(
            ['trial_id_1', 'trial_id_2'],
            80,
            id='subset_int',
        ),
    ],
)
def test_load_split_precomputed_events(precomputed_dataset_configuration, by, expected_len):
    dataset = Dataset(**precomputed_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.split_precomputed_events(by)
    assert len(dataset.precomputed_events) == expected_len


def test_dataset_definition_from_yaml(tmp_path):
    tmp_file = tmp_path / 'tmp.yaml'

    dataset_def = DatasetLibrary.get('ToyDataset')
    dataset_def.to_yaml(tmp_file)

    dataset_from_yaml = Dataset(tmp_file, '.')
    assert dataset_from_yaml.definition == dataset_def


@pytest.mark.parametrize(
    ('by', 'expected_len'),
    [
        pytest.param(
            'trial_id_1',
            40,
            id='subset_int',
        ),
        pytest.param(
            'trial_id_2',
            60,
            id='subset_int',
        ),
        pytest.param(
            ['trial_id_1', 'trial_id_2'],
            80,
            id='subset_int',
        ),
    ],
)
def test_load_split_gaze(gaze_dataset_configuration, by, expected_len):
    dataset = Dataset(**gaze_dataset_configuration['init_kwargs'])
    dataset.load()
    dataset.split_gaze_data(by)
    assert len(dataset.gaze) == expected_len
