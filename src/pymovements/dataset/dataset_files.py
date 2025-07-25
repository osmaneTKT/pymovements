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
"""Functionality to scan, load and save dataset files."""
from __future__ import annotations

import warnings
from copy import deepcopy
from pathlib import Path
from typing import Any

import polars as pl
from tqdm.auto import tqdm

from pymovements._utils._paths import match_filepaths
from pymovements._utils._strings import curly_to_regex
from pymovements.dataset.dataset_definition import DatasetDefinition
from pymovements.dataset.dataset_paths import DatasetPaths
from pymovements.events import EventDataFrame
from pymovements.events.precomputed import PrecomputedEventDataFrame
from pymovements.gaze.gaze_dataframe import GazeDataFrame
from pymovements.gaze.io import from_asc
from pymovements.gaze.io import from_csv
from pymovements.gaze.io import from_ipc
from pymovements.reading_measures import ReadingMeasures


def scan_dataset(definition: DatasetDefinition, paths: DatasetPaths) -> pl.DataFrame:
    """Infer information from filepaths and filenames.

    Parameters
    ----------
    definition: DatasetDefinition
        The dataset definition.
    paths: DatasetPaths
        The dataset paths.

    Returns
    -------
    pl.DataFrame
        File information dataframe.

    Raises
    ------
    AttributeError
        If no regular expression for parsing filenames is defined.
    RuntimeError
        If an error occurred during matching filenames or no files have been found.
    """
    # Get all filepaths that match regular expression.
    _fileinfo_dicts = {}
    if definition.has_files['gaze']:
        fileinfo_dicts = match_filepaths(
            path=paths.raw,
            regex=curly_to_regex(definition.filename_format['gaze']),
            relative=True,
        )
        if not fileinfo_dicts:
            raise RuntimeError(f'no matching files found in {paths.raw}')

        fileinfo_df = pl.from_dicts(data=fileinfo_dicts, infer_schema_length=1)
        fileinfo_df = fileinfo_df.sort(by='filepath')
        if definition.filename_format_schema_overrides['gaze']:
            items = definition.filename_format_schema_overrides['gaze'].items()
            fileinfo_df = fileinfo_df.with_columns([
                pl.col(fileinfo_key).cast(fileinfo_dtype)
                for fileinfo_key, fileinfo_dtype in items
            ])
        _fileinfo_dicts['gaze'] = fileinfo_df

    if definition.has_files['precomputed_events']:
        fileinfo_dicts = match_filepaths(
            path=paths.precomputed_events,
            regex=curly_to_regex(definition.filename_format['precomputed_events']),
            relative=True,
        )
        if not fileinfo_dicts:
            raise RuntimeError(f'no matching files found in {paths.precomputed_events}')
        fileinfo_df = pl.from_dicts(data=fileinfo_dicts, infer_schema_length=1)
        fileinfo_df = fileinfo_df.sort(by='filepath')
        if definition.filename_format_schema_overrides['precomputed_events']:
            items = definition.filename_format_schema_overrides['precomputed_events'].items()
            fileinfo_df = fileinfo_df.with_columns([
                pl.col(fileinfo_key).cast(fileinfo_dtype)
                for fileinfo_key, fileinfo_dtype in items
            ])
        _fileinfo_dicts['precomputed_events'] = fileinfo_df

    pc_rm = 'precomputed_reading_measures'
    if definition.has_files[pc_rm]:
        fileinfo_dicts = match_filepaths(
            path=paths.precomputed_reading_measures,
            regex=curly_to_regex(definition.filename_format[pc_rm]),
            relative=True,
        )
        if not fileinfo_dicts:
            raise RuntimeError(f'no matching files found in {paths.precomputed_reading_measures}')
        fileinfo_df = pl.from_dicts(data=fileinfo_dicts, infer_schema_length=1)
        fileinfo_df = fileinfo_df.sort(by='filepath')
        if definition.filename_format_schema_overrides[pc_rm]:
            _schema_overrides = definition.filename_format_schema_overrides[pc_rm]
            items = _schema_overrides.items()
            fileinfo_df = fileinfo_df.with_columns([
                pl.col(fileinfo_key).cast(fileinfo_dtype)
                for fileinfo_key, fileinfo_dtype in items
            ])
        _fileinfo_dicts[pc_rm] = fileinfo_df

    return _fileinfo_dicts


def load_event_files(
        definition: DatasetDefinition,
        fileinfo: pl.DataFrame,
        paths: DatasetPaths,
        events_dirname: str | None = None,
        extension: str = 'feather',
) -> list[EventDataFrame]:
    """Load all event files according to fileinfo dataframe.

    Parameters
    ----------
    definition: DatasetDefinition
        The dataset definition.
    fileinfo: pl.DataFrame
        A dataframe holding file information.
    paths: DatasetPaths
        Path of directory containing event files.
    events_dirname: str | None
        One-time usage of an alternative directory name to save data relative to dataset path.
        This argument is used only for this single call and does not alter
        :py:meth:`pymovements.Dataset.events_rootpath`.
    extension: str
        Specifies the file format for loading data. Valid options are: `csv`, `feather`,
        `tsv`, `txt`.
        (default: 'feather')

    Returns
    -------
    list[EventDataFrame]
        List of event dataframes.

    Raises
    ------
    AttributeError
        If `fileinfo` is None or the `fileinfo` dataframe is empty.
    ValueError
        If extension is not in list of valid extensions.
    """
    event_dfs: list[EventDataFrame] = []

    # read and preprocess input files
    for fileinfo_row in tqdm(fileinfo.to_dicts()):
        filepath = Path(fileinfo_row['filepath'])
        filepath = paths.raw / filepath

        filepath = paths.raw_to_event_filepath(
            filepath,
            events_dirname=events_dirname,
            extension=extension,
        )

        if extension == 'feather':
            event_df = pl.read_ipc(filepath)
        elif extension in {'csv', 'tsv', 'txt'}:
            event_df = pl.read_csv(filepath)
        else:
            valid_extensions = ['csv', 'txt', 'tsv', 'feather']
            raise ValueError(
                f'unsupported file format "{extension}".'
                f'Supported formats are: {valid_extensions}',
            )

        # Add fileinfo columns to dataframe.
        event_df = add_fileinfo(
            definition=definition,
            df=event_df,
            fileinfo=fileinfo_row,
        )

        event_dfs.append(EventDataFrame(event_df))

    return event_dfs


def load_gaze_files(
        definition: DatasetDefinition,
        fileinfo: pl.DataFrame,
        paths: DatasetPaths,
        preprocessed: bool = False,
        preprocessed_dirname: str | None = None,
        extension: str = 'feather',
) -> list[GazeDataFrame]:
    """Load all available gaze data files.

    Parameters
    ----------
    definition: DatasetDefinition
        The dataset definition.
    fileinfo: pl.DataFrame
        A dataframe holding file information.
    paths: DatasetPaths
        Path of directory containing event files.
    preprocessed : bool
        If ``True``, saved preprocessed data will be loaded, otherwise raw data will be loaded.
        (default: False)
    preprocessed_dirname : str | None
        One-time usage of an alternative directory name to save data relative to
        :py:meth:`pymovements.Dataset.path`.
        This argument is used only for this single call and does not alter
        :py:meth:`pymovements.Dataset.preprocessed_rootpath`.
    extension: str
        Specifies the file format for loading data. Valid options are: `csv`, `feather`,
        `txt`, `tsv`.
        (default: 'feather')

    Returns
    -------
    list[GazeDataFrame]
        Returns self, useful for method cascading.

    Raises
    ------
    AttributeError
        If `fileinfo` is None or the `fileinfo` dataframe is empty.
    RuntimeError
        If file type of gaze file is not supported.
    """
    gaze_dfs: list[GazeDataFrame] = []

    # Read gaze files from fileinfo attribute.
    for fileinfo_row in tqdm(fileinfo.to_dicts()):
        filepath = Path(fileinfo_row['filepath'])
        filepath = paths.raw / filepath

        if preprocessed:
            filepath = paths.get_preprocessed_filepath(
                filepath, preprocessed_dirname=preprocessed_dirname,
                extension=extension,
            )

        gaze_df = load_gaze_file(
            filepath=filepath,
            fileinfo_row=fileinfo_row,
            definition=deepcopy(definition),
            preprocessed=preprocessed,
        )
        gaze_dfs.append(gaze_df)

    return gaze_dfs


def load_gaze_file(
        filepath: Path,
        fileinfo_row: dict[str, Any],
        definition: DatasetDefinition,
        preprocessed: bool = False,
) -> GazeDataFrame:
    """Load a gaze data file as GazeDataFrame.

    Parameters
    ----------
    filepath: Path
        Path of gaze file.
    fileinfo_row: dict[str, Any]
        A dictionary holding file information.
    definition: DatasetDefinition
        The dataset definition.
    preprocessed: bool
        If ``True``, saved preprocessed data will be loaded, otherwise raw data will be loaded.
        (default: False)

    Returns
    -------
    GazeDataFrame
        The resulting GazeDataFrame

    Raises
    ------
    RuntimeError
        If file type of gaze file is not supported.
    ValueError
        If extension is not in list of valid extensions.
    """
    fileinfo_columns = {
        column: fileinfo_row[column] for column in
        [column for column in fileinfo_row.keys() if column != 'filepath']
    }

    # check if we have any trial columns specified.
    if not definition.trial_columns:
        trial_columns = list(fileinfo_columns)
    else:  # check for duplicates and merge.
        trial_columns = definition.trial_columns

        # Make sure fileinfo row is not duplicated as a trial_column:
        if set(trial_columns).intersection(list(fileinfo_columns)):
            dupes = set(trial_columns).intersection(list(fileinfo_columns))
            warnings.warn(
                f'removed duplicated fileinfo columns from trial_columns: {", ".join(dupes)}',
            )
            trial_columns = list(set(trial_columns).difference(list(fileinfo_columns)))

        # expand trial columns with added fileinfo columns
        trial_columns = list(fileinfo_columns) + trial_columns

    if filepath.suffix in {'.csv', '.txt', '.tsv'}:
        if preprocessed:
            # Time unit is always milliseconds for preprocessed data if a time column is present.
            time_unit = 'ms'

            gaze_df = from_csv(
                filepath,
                time_unit=time_unit,
                auto_column_detect=True,
                trial_columns=trial_columns,  # this includes all fileinfo_columns.
                add_columns=fileinfo_columns,
                # column_schema_overrides is used for fileinfo_columns passed as add_columns.
                column_schema_overrides=definition.filename_format_schema_overrides['gaze'],
            )
        else:
            gaze_df = from_csv(
                filepath,
                definition=definition,
                trial_columns=trial_columns,  # this includes all fileinfo_columns.
                add_columns=fileinfo_columns,
                # column_schema_overrides is used for fileinfo_columns passed as add_columns.
                column_schema_overrides=definition.filename_format_schema_overrides['gaze'],
            )
    elif filepath.suffix == '.feather':
        gaze_df = from_ipc(
            filepath,
            experiment=definition.experiment,
            trial_columns=trial_columns,  # this includes all fileinfo_columns.
            add_columns=fileinfo_columns,
            # column_schema_overrides is used for fileinfo_columns passed as add_columns.
            column_schema_overrides=definition.filename_format_schema_overrides['gaze'],
        )
    elif filepath.suffix == '.asc':
        gaze_df = from_asc(
            filepath,
            definition=definition,
            trial_columns=trial_columns,  # this includes all fileinfo_columns.
            add_columns=fileinfo_columns,
            # column_schema_overrides is used for fileinfo_columns passed as add_columns.
            column_schema_overrides=definition.filename_format_schema_overrides['gaze'],
        )
    else:
        valid_extensions = ['csv', 'tsv', 'txt', 'feather', 'asc']
        raise ValueError(
            f'unsupported file format "{filepath.suffix}".'
            f'Supported formats are: {valid_extensions}',
        )

    return gaze_df


def load_precomputed_reading_measures(
        definition: DatasetDefinition,
        fileinfo: pl.DataFrame,
        paths: DatasetPaths,
) -> list[ReadingMeasures]:
    """Load text stimulus from file.

    Parameters
    ----------
    definition:  DatasetDefinition
        Dataset definition to load precomputed events.
    fileinfo: pl.DataFrame
        Information about the files.
    paths: DatasetPaths
        Adjustable paths to extract datasets.

    Returns
    -------
    list[ReadingMeasures]
        Return list of precomputed event dataframes.
    """
    precomputed_reading_measures = []
    for filepath in fileinfo.to_dicts():
        data_path = paths.precomputed_reading_measures / Path(filepath['filepath'])
        precomputed_reading_measures.append(
            load_precomputed_reading_measure_file(
                data_path,
                definition.custom_read_kwargs['precomputed_reading_measures'],
            ),
        )
    return precomputed_reading_measures


def load_precomputed_reading_measure_file(
        data_path: str | Path,
        custom_read_kwargs: dict[str, Any] | None = None,
) -> ReadingMeasures:
    """Load precomputed events from files.

    Parameters
    ----------
    data_path:  str | Path
        Path to file to be read.
    custom_read_kwargs: dict[str, Any] | None
        Custom read keyword arguments for polars. (default: None)

    Returns
    -------
    ReadingMeasures
        Returns the text stimulus file.
    """
    data_path = Path(data_path)
    if custom_read_kwargs is None:
        custom_read_kwargs = {}

    valid_extensions = {'.csv', '.tsv', '.txt'}
    if data_path.suffix in valid_extensions:
        precomputed_reading_measure_df = pl.read_csv(data_path, **custom_read_kwargs)
    else:
        raise ValueError(
            f'unsupported file format "{data_path.suffix}". '
            f'Supported formats are: {", ".join(sorted(valid_extensions))}',
        )

    return ReadingMeasures(precomputed_reading_measure_df)


def load_precomputed_event_files(
        definition: DatasetDefinition,
        fileinfo: pl.DataFrame,
        paths: DatasetPaths,
) -> list[PrecomputedEventDataFrame]:
    """Load text stimulus from file.

    Parameters
    ----------
    definition:  DatasetDefinition
        Dataset definition to load precomputed events.
    fileinfo: pl.DataFrame
        Information about the files.
    paths: DatasetPaths
        Adjustable paths to extract datasets.

    Returns
    -------
    list[PrecomputedEventDataFrame]
        Return list of precomputed event dataframes.
    """
    precomputed_events = []
    for filepath in fileinfo.to_dicts():
        data_path = paths.precomputed_events / Path(filepath['filepath'])
        precomputed_events.append(
            load_precomputed_event_file(
                data_path,
                definition.custom_read_kwargs['precomputed_events'],
            ),
        )
    return precomputed_events


def load_precomputed_event_file(
        data_path: str | Path,
        custom_read_kwargs: dict[str, Any] | None = None,
) -> PrecomputedEventDataFrame:
    """Load precomputed events from files.

    Parameters
    ----------
    data_path:  str | Path
        Path to file to be read.
    custom_read_kwargs: dict[str, Any] | None
        Custom read keyword arguments for polars. (default: None)

    Returns
    -------
    PrecomputedEventDataFrame
        Returns the text stimulus file.
    """
    data_path = Path(data_path)
    if custom_read_kwargs is None:
        custom_read_kwargs = {}

    valid_extensions = {'.csv', '.tsv', '.txt'}
    if data_path.suffix in valid_extensions:
        precomputed_event_df = pl.read_csv(data_path, **custom_read_kwargs)
    else:
        raise ValueError(
            f'unsupported file format "{data_path.suffix}". '
            f'Supported formats are: {", ".join(sorted(valid_extensions))}',
        )

    return PrecomputedEventDataFrame(data=precomputed_event_df)


def add_fileinfo(
        definition: DatasetDefinition,
        df: pl.DataFrame,
        fileinfo: dict[str, Any],
) -> pl.DataFrame:
    """Add columns from fileinfo to dataframe.

    Parameters
    ----------
    definition: DatasetDefinition
        The dataset definition.
    df: pl.DataFrame
        Base dataframe to add fileinfo to.
    fileinfo : dict[str, Any]
        Dictionary of fileinfo row.

    Returns
    -------
    pl.DataFrame
        Dataframe with added columns from fileinfo dictionary keys.
    """
    df = df.select(
        [
            pl.lit(value).alias(column)
            for column, value in fileinfo.items()
            if column != 'filepath' and column not in df.columns
        ] + [pl.all()],
    )

    # Cast columns from fileinfo according to specification.
    _schema_overrides = definition.filename_format_schema_overrides['gaze']
    df = df.with_columns([
        pl.col(fileinfo_key).cast(fileinfo_dtype)
        for fileinfo_key, fileinfo_dtype in _schema_overrides.items()
    ])
    return df


def save_events(
        events: list[EventDataFrame],
        fileinfo: pl.DataFrame,
        paths: DatasetPaths,
        events_dirname: str | None = None,
        verbose: int = 1,
        extension: str = 'feather',
) -> None:
    """Save events to files.

    Data will be saved as feather files to ``Dataset.events_roothpath`` with the same directory
    structure as the raw data.

    Parameters
    ----------
    events: list[EventDataFrame]
        The event dataframes to save.
    fileinfo: pl.DataFrame
        A dataframe holding file information.
    paths: DatasetPaths
        Path of directory containing event files.
    events_dirname: str | None
        One-time usage of an alternative directory name to save data relative to dataset path.
        This argument is used only for this single call and does not alter
        :py:meth:`pymovements.Dataset.events_rootpath`. (default: None)
    verbose: int
        Verbosity level (0: no print output, 1: show progress bar, 2: print saved filepaths)
        (default: 1)
    extension: str
        Specifies the file format for loading data. Valid options are: `csv`, `feather`.
        (default: 'feather')

    Raises
    ------
    ValueError
        If extension is not in list of valid extensions.
    """
    disable_progressbar = not verbose

    for file_id, event_df in enumerate(tqdm(events, disable=disable_progressbar)):
        raw_filepath = paths.raw / Path(fileinfo[file_id, 'filepath'])
        events_filepath = paths.raw_to_event_filepath(
            raw_filepath, events_dirname=events_dirname,
            extension=extension,
        )

        event_df_out = event_df.frame.clone()
        for column in event_df_out.columns:
            if column in fileinfo.columns:
                event_df_out = event_df_out.drop(column)

        if verbose >= 2:
            print('Save file to', events_filepath)

        events_filepath.parent.mkdir(parents=True, exist_ok=True)
        if extension == 'feather':
            event_df_out.write_ipc(events_filepath)
        elif extension == 'csv':
            event_df_out.write_csv(events_filepath)
        else:
            valid_extensions = ['csv', 'feather']
            raise ValueError(
                f'unsupported file format "{extension}".'
                f'Supported formats are: {valid_extensions}',
            )


def save_preprocessed(
        gaze: list[GazeDataFrame],
        fileinfo: pl.DataFrame,
        paths: DatasetPaths,
        preprocessed_dirname: str | None = None,
        verbose: int = 1,
        extension: str = 'feather',
) -> None:
    """Save preprocessed gaze files.

    Data will be saved as feather files to ``Dataset.preprocessed_roothpath`` with the same
    directory structure as the raw data.

    Parameters
    ----------
    gaze: list[GazeDataFrame]
        The gaze dataframes to save.
    fileinfo: pl.DataFrame
        A dataframe holding file information.
    paths: DatasetPaths
        Path of directory containing event files.
    preprocessed_dirname: str | None
        One-time usage of an alternative directory name to save data relative to dataset path.
        This argument is used only for this single call and does not alter
        :py:meth:`pymovements.Dataset.preprocessed_rootpath`. (default: None)
    verbose: int
        Verbosity level (0: no print output, 1: show progress bar, 2: print saved filepaths)
        (default: 1)
    extension: str
        Specifies the file format for loading data. Valid options are: `csv`, `feather`.
        (default: 'feather')

    Raises
    ------
    ValueError
        If extension is not in list of valid extensions.
    """
    disable_progressbar = not verbose

    for file_id, gaze_df in enumerate(tqdm(gaze, disable=disable_progressbar)):
        gaze_df = gaze_df.clone()

        raw_filepath = paths.raw / Path(fileinfo[file_id, 'filepath'])
        preprocessed_filepath = paths.get_preprocessed_filepath(
            raw_filepath, preprocessed_dirname=preprocessed_dirname,
            extension=extension,
        )

        if extension == 'csv':
            gaze_df.unnest()

        for column in gaze_df.columns:
            if column in fileinfo.columns:
                gaze_df.frame = gaze_df.frame.drop(column)

        if verbose >= 2:
            print('Save file to', preprocessed_filepath)

        preprocessed_filepath.parent.mkdir(parents=True, exist_ok=True)
        if extension == 'feather':
            gaze_df.frame.write_ipc(preprocessed_filepath)
        elif extension == 'csv':
            gaze_df.frame.write_csv(preprocessed_filepath)
        else:
            valid_extensions = ['csv', 'feather']
            raise ValueError(
                f'unsupported file format "{extension}".'
                f'Supported formats are: {valid_extensions}',
            )


def take_subset(
        fileinfo: pl.DataFrame,
        subset: dict[
            str, bool | float | int | str | list[bool | float | int | str],
        ] | None = None,
) -> pl.DataFrame:
    """Take a subset of the fileinfo dataframe.

    Parameters
    ----------
    fileinfo: pl.DataFrame
        File information dataframe.
    subset: dict[str, bool | float | int | str | list[bool | float | int | str]] | None
        If specified, take a subset of the dataset. All keys in the dictionary must be
        present in the fileinfo dataframe inferred by `scan_dataset()`. Values can be either
        bool, float, int , str or a list of these. (default: None)

    Returns
    -------
    pl.DataFrame
        Subset of file information dataframe.

    Raises
    ------
    ValueError
        If dictionary key is not a column in the fileinfo dataframe.
    TypeError
        If dictionary key or value is not of valid type.
    """
    if subset is None:
        return fileinfo

    if not isinstance(subset, dict):
        raise TypeError(f'subset must be of type dict but is of type {type(subset)}')

    for subset_key, subset_value in subset.items():
        if not isinstance(subset_key, str):
            raise TypeError(
                f'subset keys must be of type str but key {subset_key} is of type'
                f' {type(subset_key)}',
            )

        if subset_key not in fileinfo['gaze'].columns:
            raise ValueError(
                f'subset key {subset_key} must be a column in the fileinfo attribute.'
                f" Available columns are: {fileinfo['gaze'].columns}",
            )

        if isinstance(subset_value, (bool, float, int, str)):
            column_values = [subset_value]
        elif isinstance(subset_value, (list, tuple, range)):
            column_values = subset_value
        else:
            raise TypeError(
                f'subset values must be of type bool, float, int, str, range, or list, '
                f'but value of pair {subset_key}: {subset_value} is of type {type(subset_value)}',
            )

        fileinfo['gaze'] = fileinfo['gaze'].filter(pl.col(subset_key).is_in(column_values))
    return fileinfo
