"""
    This module provides :py:class:`ExcelTableConverter` class to extract tables from Excel files.
    To define the shape of tables in Excel files, :py:class:`ExcelTableFormat` class is used.

    :copyright: © 2025 by Jaywan Chung
    :license: MIT
"""

from collections.abc import Callable
from dataclasses import dataclass
import os
import shutil
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

from table_extraction import find_all_table_range


class ExcelTableConverter:
    """Provides features for extracting tables from Excel files.

    **Note**: To read an Excel file, `pandas.read_excel() <https://pandas.pydata.org/pandas-docs/version/1.1.3/reference/api/pandas.read_excel.html>`__ is used.
    Hence, a supported engine (`xlrd`, `openpyxl`, etc.) is required.

    :param table_format: A format for describing a valid table in Excel files.
       Only tables that meet this format will be extracted.
    :type table_format: :py:class:`ExcelTableFormat`
    :param logger: A logger for storing messages from converter.
    :type logger: :py:class:`logger.Logger`
    :param transform_table: A callback function for transforming extracted tables.
       Default is `None`, which means doing nothing by calling :py:func:`identity_transform` function.
       For an example callback function, refer to the source code of :py:func:`add_longname_and_shortname`.
    :type transform_table: Callabe, optional

    :ivar table_format: The format describing a valid table in Excel files.
    :vartype table_format: :py:class:`ExcelTableFormat`
    :ivar logger: The logger storing messages from converter.
    :vartype logger: :py:class:`logger.Logger`

    Example callback function: The following function does no transform.
        >>> def identity_transform(df, table_range, table):
        ...     return table
    """
    def __init__(self, table_format, logger, transform_table=None) -> None:
        self.table_format: 'ExcelTableFormat' = table_format
        self.logger: 'Logger' = logger
        self._transform_table: Callable = identity_transform

        if transform_table is not None:
            self._transform_table: Callable = transform_table

    def convert_all_to_csv(self, source_rootdir, target_rootdir,
                           skip_converted=False, backup_excel=False, tail_in_csv_filename='') -> None:
        """Extract tables from Excel files and save as CSV files.
        All Excel files in root directory and subdirectories are converted.
        Tables in a single Excel file are merged and saved as a corresponding, single CSV file.

        :param source_rootdir: Root directory containing Excel files to be converted.
        :type source_rootdir: str
        :param target_rootdir: Target root directory that will contain converted CSV files.
        :type target_rootdir: str
        :param skip_converted: If `True`, skip converting Excel file if it is already converted; that is,
           a converted CSV file exists, and its last modification date is later than
           the last modification date of the Excel file.
           Default is `False`.
        :type skip_converted: bool, optional
        :param backup_excel: If `True`, the original Excel file is copied into the target directory.
           Default is `False`.
           **Note**: If CSV conversion has been skipped, then **backup is also skipped** regardless of this option.
        :type backup_excel: bool, optional
        :param tail_in_csv_filename: A tail name to be attached in the original name.
           For example, if tail name is '_converted', then `excel.xlsx` file is converted to `excel_converted.csv` file.
        :type tail_in_csv_filename: str, optional
        """
        for subdir, dirs, filenames in os.walk(source_rootdir):
            relative_path = os.path.relpath(subdir, source_rootdir)
            target_dir = os.path.join(target_rootdir, relative_path)
            for filename in filenames:
                if not self.table_format.acceptable_excel_filename(filename):
                    continue

                source_excel_filepath = os.path.join(subdir, filename)
                target_excel_filepath = os.path.join(target_dir, filename)
                target_csv_filepath = _convert_to_csv_filepath(target_excel_filepath,
                                                               tail_in_csv_filename=tail_in_csv_filename)

                if skip_converted and _already_converted(source_excel_filepath, target_csv_filepath):
                    continue

                self.convert_to_csv(source_excel_filepath, target_csv_filepath)

                if backup_excel:
                    self._backup_excel(source_excel_filepath, target_excel_filepath)

    def convert_to_csv(self, source_excel_filepath, target_csv_filepath) -> None:
        """Extract tables from source Excel file and save as the target CSV file.
        All tables in the Excel file are merged and saved as a single CSV file.
        Target directory will be created if missing.

        :param source_excel_filepath: Excel filepath to be extracted.
        :type source_excel_filepath: str
        :param target_csv_filepath: Target CSV filepath.
        :type target_csv_filepath: str
        """
        target_dir = os.path.dirname(target_csv_filepath)
        _create_dir_if_missing(target_dir, self.logger)

        table_df = self.extract_table_from_excel_file(source_excel_filepath)
        table_df.to_csv(target_csv_filepath, index=False)

        self.logger.append(f"File created: '{target_csv_filepath}'\n")

    def _backup_excel(self, source_excel_filepath, target_excel_filepath) -> None:
        """Copy the source Excel file to the target filepath.

        :param source_excel_filepath: The source Excel filepath.
        :type source_excel_filepath: str
        :param target_excel_filepath: The target Excel filepath.
        :type target_excel_filepath: str
        """
        target_dir = os.path.dirname(target_excel_filepath)
        _create_dir_if_missing(target_dir, self.logger)
        _copy_file(source_excel_filepath, target_excel_filepath, self.logger)

    def extract_table_from_excel_file(self, excel_filepath) -> 'pandas.DataFrame':
        """Extract all tables from an Excel file and merge into a single pandas DataFrame.

        **Note**: To read an Excel file, `pandas.read_excel() <https://pandas.pydata.org/pandas-docs/version/1.1.3/reference/api/pandas.read_excel.html>`__ is used.

        :param excel_filepath: An Excel filepath.
        :type excel_filepath: str
        :return: A merged table.
        :rtype: pandas.DataFrame
        """
        sheets = pd.read_excel(excel_filepath, sheet_name=None, header=None)

        table_list = []
        for sheet_name in sheets.keys():
            if not self.table_format.acceptable_sheet_name(sheet_name):
                continue

            table = self.extract_table_from_sheet(sheets, sheet_name)
            table_list.append(table)

        if len(table_list) == 0:
            return pd.DataFrame([])
        return pd.concat(table_list, ignore_index=True)

    def extract_table_from_sheet(self, sheets, sheet_name) -> 'pandas.DataFrame':
        """Extract all tables from a target sheet (of an Excel file) and merge into a single pandas DataFrame.

        :param sheets: All sheets (of an Excel file).
           This is a dictionary where the keys are sheet names and the items are pandas DataFrames.
        :type sheets: dict
        :param sheet_name: The name of the target sheet.
           Of all sheets, only the sheet named `sheet_name` is processed.
        :type sheet_name: str
        :return: A merged table.
        :rtype: pandas.DataFrame
        """

        table_list = []
        df = sheets[sheet_name]
        list_table_range = find_all_table_range(df, min_n_rows=self.table_format.min_n_rows,
                                                min_n_cols=self.table_format.min_n_cols)
        for table_range in list_table_range:
            table = self._get_table(df, table_range)
            table = self._transform_table(df, table_range, table)
            table_list.append(table)

        if len(table_list) == 0:
            return pd.DataFrame([])
        return pd.concat(table_list, ignore_index=True)

    def _get_table(self, df, table_range) -> 'pandas.DataFrame':
        """Return the table by restricting `df` in `table_range` and imposing header columns.
        The location (row offset) of header in `df` is defined in :py:attr:`ExcelTableFormat.header_row_offset`.

        :param df: The whole DataFrame.
        :type df: pandas.DataFrame
        :param table_range: The range of table in `df`.
        :type table_range: :py:class:`table_extraction.TableRange`
        :return: The table with a header column.
        :rtype: pandas.DataFrame
        """
        table = table_range.to_dataframe(df)
        columns = table.iloc[self.table_format.header_row_offset, :]
        columns.name = None
        table = table.iloc[self.table_format.header_row_offset + 1:, :].reset_index(drop=True)
        table.columns = columns

        return table


@dataclass
class ExcelTableFormat:
    """Represents a valid shape of a table and check the validity.

    :param min_n_rows: The minimum number of rows where a table must have.
    :type min_n_rows: int
    :param min_n_cols: The minimum number of columns where a table must have.
    :type min_n_cols: int
    :param header_row_offset: The row offset of the header of a table.
        Default is 0, which means the first row of the table is header.
    :type header_row_offset: int, optional
    :param header_in_sheet_name: A sheet name must start with `header_in_sheet_name`. If not, the sheet is skipped.
        Default is ''.
    :type header_in_sheet_name: str, optional
    :param header_in_filename: An Excel filename must start with `header_in_filename`. If not, the file is skipped.
        Default is ''.
    :type header_in_filename: str, optional
    """
    #: The minimum number of rows where a table must have.
    min_n_rows: int
    #: The minimum number of columns where a table must have.
    min_n_cols: int
    #: The row offset of the header of a table. Default is 0, which means the first row of the table is header.
    header_row_offset: int = 0
    #: A sheet name must start with `header_in_sheet_name`. If not, the sheet is skipped. Default is ''.
    header_in_sheet_name: str = ''
    #: An Excel filename must start with `header_in_filename`. If not, the file is skipped. Default is ''.
    header_in_filename: str = ''

    def acceptable_sheet_name(self, sheet_name) -> bool:
        """Check to see if the sheet name is valid.

        :param sheet_name: The name of a sheet.
        :type sheet_name: str
        :return: `True` if `sheet_name` starts with :py:attr:`ExcelTableFormat.header_in_sheet_name`.
        :rtype: bool
        """
        return sheet_name.startswith(self.header_in_sheet_name)

    def acceptable_excel_filename(self, filename) -> bool:
        """Check to see if the filename is a valid Excel filename.

        :param filename: The name of an Excel file.
        :type filename: str
        :return: `True` if `filename` starts with :py:attr:`ExcelTableFormat.header_in_filename` and ends with `.xlsx`.
        :rtype: bool
        """
        return filename.startswith(self.header_in_filename) and filename.endswith('.xlsx')

    def acceptable_csv_filename(self, filename) -> bool:
        """Check to see if the filename is a valid CSV filename.

        :param filename: The name of a CSV file.
        :type filename: str
        :return: `True` if `filename` starts with :py:attr:`ExcelTableFormat.header_in_filename` and ends with `.csv`.
        :rtype: bool
        """
        return filename.startswith(self.header_in_filename) and filename.endswith('.csv')


def identity_transform(df, table_range, table):
    """A callback function for transforming extracted tables. This function does nothing.

    **Note**: To create a custom callback function, match the parameters and the return type.

    :param df: The entire dataframe containing the table.
    :type df: pandas.DataFrame
    :param table_range: The range of the extracted table in `df`.
    :type table_range: :py:class:`table_extraction.TableRange`
    :param table: The extracted table.
    :type table: pandas.DataFrame
    :return: Transformed table. This is equal to the input parameter `table`.
    :rtype: pandas.DataFrame
    """
    return table


def add_longname_and_shortname(df, table_range, table):
    """A callback function for adding longname and shortname columns to table.
    Can be used as an input for `transform_table` parameter of :py:class:`ExcelTableConverter` class.

    The longname and shortname appear in the first column, before the first row of the table.
    That is, the row offsets of longname and shortname are -2 and -1, respectively.

    :param df: The entire dataframe containing the table.
    :type df: pandas.DataFrame
    :param table_range: The range of extracted table in `df`.
    :type table_range: :py:class:`table_extraction.TableRange`
    :param table: The extracted table.
    :type table: pandas.DataFrame
    :return: The table transformed by adding longname and shortname columns.
    :rtype: pandas.DataFrame

    """
    LONGNAME_ROW_OFFSET = -2
    SHORTNAME_ROW_OFFSET = -1

    longname = df.iloc[table_range.start_row + LONGNAME_ROW_OFFSET, table_range.start_col]
    shortname = df.iloc[table_range.start_row + SHORTNAME_ROW_OFFSET, table_range.start_col]
    table.insert(0, 'longname', longname)
    table.insert(1, 'shortname', shortname)
    return table


def _already_converted(source_filepath, target_filepath):
    """Return `True` if `target_filepath` is already converted; that is, `target_filepath` file exists,
     and its last modification date is later than the last modification date of the `source_filepath`.

    :param source_filepath:
    :type source_filepath: str
    :param target_filepath:
    :type target_filepath: str
    :return: Return `True` if `target_filepath` is already converted. Return `False` otherwise.
    :rtype: bool
    """
    if not os.path.exists(target_filepath):
        return False
    if os.path.getmtime(source_filepath) > os.path.getmtime(target_filepath):
        return False
    return True


def _create_dir_if_missing(target_dir, logger) -> None:
    """Create target directory if it is missing.

    :param target_dir: Target directory to be created.
    :type target_dir: str
    :param logger: A logger for storing result message.
    :type logger: :py:class:`logger.Logger`
    """
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        logger.append(f"Directory created: '{target_dir}'\n")


def _copy_file(source_filepath, target_filepath, logger) -> None:
    """Copy source filepath to target filepath.

    :param source_filepath: Source filepath to be copied.
    :type source_filepath: str
    :param target_filepath: Target filepath.
    :type target_filepath: str
    :param logger: A logger for storing result message.
    :type logger: :py:class:`logger.Logger`
    """
    shutil.copy(source_filepath, target_filepath)
    logger.append(f"File copied: '{target_filepath}'\n")


def _convert_to_csv_filepath(filepath, tail_in_csv_filename='') -> str:
    """Convert the extension of the given filepath to a CSV filepath. `tail_in_csv_filename` is added to the filename.
    For example, if tail name is '_converted', then `excel.xlsx` file is converted to `excel_converted.csv` file.

    :param filepath: A filepath to be changed.
    :type filepath: str
    :param tail_in_csv_filename: Tail name to be added in the filename. Default is ''.
    :type tail_in_csv_filename: str, optional
    :return: A CSV filepath.
    :rtype: str
    """
    filename_wo_ext, ext = os.path.splitext(filepath)
    return f'{filename_wo_ext}{tail_in_csv_filename}.csv'


class ExcelTableFormatTest(unittest.TestCase):
    def setUp(self):
        self.format = ExcelTableFormat(min_n_rows=3, min_n_cols=4, header_row_offset=2,
                                       header_in_sheet_name='TEP', header_in_filename='zz_TEP')

    def test_accept_sheet(self):
        self.assertTrue(self.format.acceptable_sheet_name('TEP_sheet'))
        self.assertFalse(self.format.acceptable_sheet_name('not_TEP_sheet'))

    def test_accept_excel_file(self):
        self.assertTrue(self.format.acceptable_excel_filename('zz_TEP_data.xlsx'))
        self.assertFalse(self.format.acceptable_excel_filename('zz_TEP_data.txt'))
        self.assertFalse(self.format.acceptable_excel_filename('not_TEP_data.xlsx'))

    def test_accept_csv_file(self):
        self.assertTrue(self.format.acceptable_csv_filename('zz_TEP_data.csv'))
        self.assertFalse(self.format.acceptable_csv_filename('zz_TEP_data.txt'))
        self.assertFalse(self.format.acceptable_csv_filename('not_TEP_data.csv'))


class ExcelTableConverterTest(unittest.TestCase):
    def setUp(self) -> None:
        table_format = ExcelTableFormat(min_n_rows=3, min_n_cols=4, header_row_offset=1,
                                        header_in_sheet_name='TEP', header_in_filename='zz_TEP')
        self.logger = Mock()
        self.converter = ExcelTableConverter(table_format, self.logger, transform_table=add_longname_and_shortname)

    def test_convert_all_to_csv(self):
        source_excel_filepath = os.path.join('.', 'zz_TEP_1.xlsx')
        target_excel_filepath = os.path.join('.', '.', 'zz_TEP_1.xlsx')
        target_csv_filepath = os.path.join('.', '.', 'zz_TEP_1_converted.csv')

        self.converter.convert_to_csv = Mock()
        self.converter._backup_excel = Mock()
        with patch('os.walk', return_value=([('.', [], ['zz_TEP_1.xlsx', 'not_TEP.xlsx'])])):
            # Assume target csv file was not converted.
            with patch(f'{__name__}._already_converted', return_value=False):
                self._mock_call_convert_all_to_csv(
                    '.', '.', skip_converted=True, backup_excel=True, tail_in_csv_filename='_converted')
                self.converter.convert_to_csv.assert_called_once_with(source_excel_filepath, target_csv_filepath)
                self.converter._backup_excel.assert_called_once_with(source_excel_filepath, target_excel_filepath)

                self._mock_call_convert_all_to_csv(
                    '.', '.', skip_converted=True, backup_excel=False, tail_in_csv_filename='_converted')
                self.converter.convert_to_csv.assert_called_once_with(source_excel_filepath, target_csv_filepath)
                self.converter._backup_excel.assert_not_called()

                self._mock_call_convert_all_to_csv(
                    '.', '.', skip_converted=False, backup_excel=True, tail_in_csv_filename='_converted')
                self.converter.convert_to_csv.assert_called_once_with(source_excel_filepath, target_csv_filepath)
                self.converter._backup_excel.assert_called_once_with(source_excel_filepath, target_excel_filepath)

                self._mock_call_convert_all_to_csv(
                    '.', '.', skip_converted=False, backup_excel=False, tail_in_csv_filename='_converted')
                self.converter.convert_to_csv.assert_called_once_with(source_excel_filepath, target_csv_filepath)
                self.converter._backup_excel.assert_not_called()

            # Assume target csv file was already converted.
            with patch(f'{__name__}._already_converted', return_value=True):
                self._mock_call_convert_all_to_csv(
                    '.', '.', skip_converted=True, backup_excel=True, tail_in_csv_filename='_converted')
                self.converter.convert_to_csv.assert_not_called()
                # Skip backup because target csv already exists.
                self.converter._backup_excel.assert_not_called()

                self._mock_call_convert_all_to_csv(
                    '.', '.', skip_converted=True, backup_excel=False, tail_in_csv_filename='_converted')
                self.converter.convert_to_csv.assert_not_called()
                self.converter._backup_excel.assert_not_called()

                self._mock_call_convert_all_to_csv(
                    '.', '.', skip_converted=False, backup_excel=True, tail_in_csv_filename='_converted')
                self.converter.convert_to_csv.assert_called_once_with(source_excel_filepath, target_csv_filepath)
                self.converter._backup_excel.assert_called_once_with(source_excel_filepath, target_excel_filepath)

                self._mock_call_convert_all_to_csv(
                    '.', '.', skip_converted=False, backup_excel=False, tail_in_csv_filename='_converted')
                self.converter.convert_to_csv.assert_called_once_with(source_excel_filepath, target_csv_filepath)
                self.converter._backup_excel.assert_not_called()

    def _mock_call_convert_all_to_csv(self, source_rootdir, target_rootdir,
                                      skip_converted=False, backup_excel=False, tail_in_csv_filename='') -> None:
        self.converter.convert_to_csv.reset_mock()
        self.converter._backup_excel.reset_mock()

        self.converter.convert_all_to_csv(
            source_rootdir, target_rootdir,
            skip_converted=skip_converted, backup_excel=backup_excel, tail_in_csv_filename=tail_in_csv_filename)

    def test_convert_to_csv(self):
        mock_table_df = Mock()
        self.converter.extract_table_from_excel_file = Mock(return_value=mock_table_df)

        with patch(f'{__name__}._create_dir_if_missing') as mock_create_dir_if_missing:
            self.converter.convert_to_csv(r'.\source\excel.xlsx', r'.\target\converted.csv')
            mock_create_dir_if_missing.assert_called_once_with(r'.\target', self.converter.logger)
            self.converter.extract_table_from_excel_file.assert_called_once_with(r'.\source\excel.xlsx')
            mock_table_df.to_csv.assert_called_once_with(r'.\target\converted.csv', index=False)
            self.logger.append.assert_called_once()

    def test_backup_excel(self):
        with patch(f'{__name__}._create_dir_if_missing') as mock_create_dir_if_missing:
            with patch(f'{__name__}._copy_file') as mock_copy_file:
                self.converter._backup_excel(r'.\source\excel.xlsx', r'.\target\excel.xlsx')
                mock_create_dir_if_missing.assert_called_once_with(r'.\target', self.logger)
                mock_copy_file.assert_called_once_with(r'.\source\excel.xlsx', r'.\target\excel.xlsx', self.logger)

    def test_extract_table_from_excel_file(self):
        df1 = pd.DataFrame([['TEP_sheet1_longname', np.nan, np.nan, np.nan, np.nan],
                            ['TEP_sheet1_shortname', np.nan, np.nan, np.nan, np.nan],
                            ['c1', 'c2', 'c3', 'c4', np.nan],
                            ['temp(C)', 'rho', 'alpha', 'kappa', np.nan],
                            [25, 8.09e-6, 1.79e-4, 1.32, np.nan],
                            [50, 8.77e-6, 1.81e-4, 1.28, np.nan]])
        df2 = pd.DataFrame([['not_tep_sheet_longname', np.nan, np.nan, np.nan, np.nan],
                            ['not_tep_sheet_shortname', np.nan, np.nan, np.nan, np.nan],
                            ['c1', 'c2', 'c3', 'c4', np.nan],
                            ['temp(C)', 'rho', 'alpha', 'kappa', np.nan],
                            [1, 2, 3, 4, np.nan],
                            [5, 6, 7, 8, np.nan]])
        df3 = pd.DataFrame([['TEP_sheet2_longname', np.nan, np.nan, np.nan, np.nan],
                            ['TEP_sheet2_shortname', np.nan, np.nan, np.nan, np.nan],
                            ['c1', 'c2', 'c3', 'c4', np.nan],
                            ['temp(C)', 'rho', 'alpha', 'kappa', np.nan],
                            [25, 7.87e-6, 1.75e-4, 1.34, np.nan],
                            [50, 8.55e-6, 1.79e-4, 1.30, np.nan]])
        answer = pd.DataFrame([['TEP_sheet1_longname', 'TEP_sheet1_shortname', 25, 8.09e-6, 1.79e-4, 1.32],
                               ['TEP_sheet1_longname', 'TEP_sheet1_shortname', 50, 8.77e-6, 1.81e-4, 1.28],
                               ['TEP_sheet2_longname', 'TEP_sheet2_shortname', 25, 7.87e-6, 1.75e-4, 1.34],
                               ['TEP_sheet2_longname', 'TEP_sheet2_shortname', 50, 8.55e-6, 1.79e-4, 1.30]],
                              columns=('longname', 'shortname', 'temp(C)', 'rho', 'alpha', 'kappa'), dtype='object')
        sheets = {'TEP_sheet1': df1, 'not_tep_sheet': df2, 'TEP_sheet2': df3}

        with patch('pandas.read_excel', return_value=sheets):
            result_df = self.converter.extract_table_from_excel_file('mock_file.xlsx')
        self.assertTrue(result_df.equals(answer))

    def test_extract_table_from_excel_file_return_empty_dataframe(self):
        with patch('pandas.read_excel', return_value={}):
            result_df = self.converter.extract_table_from_excel_file('mock_file.xlsx')
        self.assertTrue(result_df.empty)

    def test_extract_table_from_sheet_return_empty_dataframe(self):
        df1 = pd.DataFrame([['TEP_sheet1_longname', np.nan, np.nan, np.nan],
                            ['TEP_sheet1_shortname', np.nan, np.nan, np.nan],
                            ['c1', 'c2', 'c3', np.nan],
                            ['temp(C)', 'rho', 'alpha', np.nan],
                            [25, 8.09e-6, 1.79e-4, np.nan],
                            [50, 8.77e-6, 1.81e-4, np.nan]])
        sheets = {'TEP_sheet1': df1}
        result_df = self.converter.extract_table_from_sheet(sheets, 'TEP_sheet1')
        self.assertTrue(result_df.empty)


class TepExtractionFunctionTest(unittest.TestCase):
    def test_identity_transform(self):
        table_range = Mock()
        table = pd.DataFrame([4, 5, 6])
        result = identity_transform(pd.DataFrame([1, 2, 3]), table_range, table)
        self.assertTrue(result.equals(table))

    def test_already_converted(self):
        source_filepath = 'source'
        target_filepath = 'target'
        with patch('os.path.exists', return_value=False):
            self.assertFalse(_already_converted(source_filepath, target_filepath))
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getmtime') as mock:
                values = {source_filepath: 1, target_filepath: 10}
                mock.side_effect = lambda arg: values[arg]
                self.assertTrue(_already_converted(source_filepath, target_filepath))
            with patch('os.path.getmtime') as mock:
                values = {source_filepath: 10, target_filepath: 1}
                mock.side_effect = lambda arg: values[arg]
                self.assertFalse(_already_converted(source_filepath, target_filepath))

    def test_convert_to_csv_filepath(self):
        result = _convert_to_csv_filepath('C://a//b//data.xlsx', tail_in_csv_filename='_converted')
        self.assertEqual('C://a//b//data_converted.csv', result)

    def test_create_dir_if_missing(self):
        with patch('os.makedirs') as mock_makedirs:
            with patch('os.path.exists', return_value=True):
                logger = Mock()
                _create_dir_if_missing('existing_dir', logger)
                mock_makedirs.assert_not_called()
                logger.append.assert_not_called()

            with patch('os.path.exists', return_value=False):
                logger = Mock()
                _create_dir_if_missing('missing_dir', logger)
                mock_makedirs.assert_called_once_with('missing_dir')
                logger.append.assert_called_once()

    def test_copy_file(self):
        source_filepath = 'source_filepath'
        target_filepath = 'target_filepath'
        logger = Mock()
        with patch('shutil.copy') as mock_copy:
            _copy_file(source_filepath, target_filepath, logger)
            mock_copy.assert_called_once_with(source_filepath, target_filepath)
            logger.append.assert_called_once()
