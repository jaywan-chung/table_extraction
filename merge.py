"""
    This module provides :py:func:`merge_csv` function to merge CSV files into a single pandas DataFrame.

    :copyright: © 2025 by Jaywan Chung
    :license: MIT
"""

import os
import sys

import pandas as pd

from logger import Logger

VERSION = 'v2025-09-29'


def merge_csv(rootdir, header_in_csv_filename: str, tail_in_csv_filename: str, logger: 'Logger',
              delete_errorfile: bool = False) -> pd.DataFrame:
    """Merge all CSV files under the `rootdir` directory into a single pandas DataFrame.

    :param rootdir: Root directory containing CSV files to be merged.
    :type rootdir: str
    :param header_in_csv_filename: Only CSV files starting with `header_in_csv_filename` is merged.
    :type header_in_csv_filename: str
    :param tail_in_csv_filename: Only CSV files ending with `tail_in_csv_filename` is merged.
    :type tail_in_csv_filename: str
    :param logger: A logger for storing messages.
    :type logger: :py:class:`logger.Logger`
    :param delete_errorfile: If `True`, CSV file with header incompatible with other CSV files is deleted.
       Default is `False`.
    :type delete_errorfile: bool
    :return: A merged table.
    :rtype: pandas.DataFrame
    """
    cols = None
    list_df = []
    for subdir, dirs, filenames in os.walk(rootdir):
        for filename in filenames:
            if _acceptable_csv_filename(filename, header_in_csv_filename, tail_in_csv_filename):
                csv_filepath = os.path.join(subdir, filename)
                df = pd.read_csv(os.path.join(subdir, filename))

                error_occurred = False

                if cols is None:
                    cols = df.columns
                    len_cols = len(df.columns)
                if len(df.columns) > len_cols:
                    logger.append_alert(f' !Error: too many columns in {repr(csv_filepath)};'
                                      f' delete {len(df.columns) - len_cols} column(s)\n')
                    error_occurred = True
                elif len(df.columns) < len_cols:
                    logger.append_alert(f' !Error: too few columns in {repr(csv_filepath)};'
                                      f' add {len_cols - len(df.columns)} column(s)\n')
                    error_occurred = True
                elif (df.columns != cols).any():
                    logger.append_alert(f' !Error: table header not match in {repr(csv_filepath)}; '
                                      f'change columns {df.columns[df.columns != cols].tolist()} '
                                      f'into {cols[df.columns != cols].tolist()}\n')
                    error_occurred = True

                if error_occurred:
                    if delete_errorfile:
                        os.remove(csv_filepath)
                        logger.append(f' +-CSV file deleted: {repr(csv_filepath)}\n')
                    continue

                list_df.append(df)

    return pd.concat(list_df, ignore_index=True)


def _acceptable_csv_filename(filename, header_in_csv_filename, tail_in_csv_filename):
    """Return `True` if the filename starts with `header_in_csv_filename` and ends with `tail_in_csv_filename`.

    :param filename: The CSV filename to be checked.
    :type filename: str
    :param header_in_csv_filename: The header of the CSV filename
    :type header_in_csv_filename: str
    :param tail_in_csv_filename: The tail of the CSV filename
    :type tail_in_csv_filename: str
    :return: `True` if the filename starts with `header_in_csv_filename` and ends with `tail_in_csv_filename`.
    :rtype: bool
    """
    return filename.startswith(header_in_csv_filename) and filename.endswith(f'{tail_in_csv_filename}.csv')


def df_to_csv(df, csv_filename, logger):
    """Save the pandas DataFrame as a CSV file.

    :param df: A pandas DataFrame to be saved.
    :type df: pandas.DataFrame
    :param csv_filename: The name of CSV file.
    :type csv_filename: str
    :param logger: A logger for storing messages.
    :type logger: :py:class:`logger.Logger`
    """
    csv_filepath = os.path.join(rootdir, csv_filename)
    df.to_csv(csv_filepath, index=False)
    logger.append(f'CSV file created: {repr(csv_filepath)}\n')


def df_to_excel(df, excel_filename, logger):
    """Save the pandas DataFrame as an Excel file.

    :param df: A pandas DataFrame to be saved.
    :type df: pandas.DataFrame
    :param excel_filename:  The name of Excel file.
    :type excel_filename: str
    :param logger: A logger for storing messages.
    :type logger: :py:class:`logger.Logger`
    """
    excel_filepath = os.path.join(rootdir, excel_filename)
    df.to_excel(excel_filepath, index=False)
    logger.append(f'Excel file created: {repr(excel_filepath)}\n')


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 1:
        rootdir = args[0]

        logger = Logger(print_on_append=True)

        logger.append(f'** TEP merge ({VERSION}) start **\n')

        logger.append(' < Merging KERI TEPs >\n')
        tep_df = merge_csv(rootdir, header_in_csv_filename='zz_TEP', tail_in_csv_filename='_TEP', logger=logger,
                           delete_errorfile=True)
        df_to_csv(tep_df, 'merged_TEP.csv', logger)
        df_to_excel(tep_df, 'merged_TEP.xlsx', logger)
        logger.append(' < Complete >\n')

        logger.append(' < Merging KERI META data >\n')
        meta_df = merge_csv(rootdir, header_in_csv_filename='zz_TEP', tail_in_csv_filename='_META', logger=logger,
                            delete_errorfile=True)
        df_to_csv(meta_df, 'merged_META.csv', logger)
        df_to_excel(meta_df, 'merged_META.xlsx', logger)
        logger.append(' < Complete >\n')

        logger.append(f'** TEP merge complete **\n')
        logger.save_log('merge_log.txt')

        input('Press enter.')

    else:
        print("Usage: python merge.py [rootdir]")
