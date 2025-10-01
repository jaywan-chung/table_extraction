# TEP convert v2025-09-29 by Jaywan Chung

import sys

from excel_table_conversion import ExcelTableFormat, ExcelTableConverter, add_longname_and_shortname
from logger import Logger

VERSION = 'v2025-09-29'


def convert(source_rootdir, target_rootdir, logger):
    """Extract thermoelectric property (TEP) tables from Excel files and save as CSV files.
    The table format follows KERI (Korea Electrotechnology Research Institute) protocol.

    :param source_rootdir: Root directory containing Excel files to be converted.
    :type source_rootdir: str
    :param target_rootdir: Target root directory that will contain converted CSV files.
    :type target_rootdir: str
    :param logger: A logger for storing messages.
    :type logger: :py:class:`logger.Logger`
    """
    tep_format = ExcelTableFormat(min_n_rows=3, min_n_cols=4, header_row_offset=1,
                                  header_in_sheet_name='TEP', header_in_filename='zz_TEP')
    meta_format = ExcelTableFormat(min_n_rows=4, min_n_cols=6, header_row_offset=2,
                                   header_in_sheet_name='META', header_in_filename='zz_TEP')

    tep_converter = ExcelTableConverter(tep_format, logger, transform_table=add_longname_and_shortname)
    meta_converter = ExcelTableConverter(meta_format, logger)

    logger.append(' < Converting KERI TEPs >\n')
    tep_converter.convert_all_to_csv(source_rootdir, target_rootdir,
                                     skip_converted=True, backup_excel=True, tail_in_csv_filename='_TEP')
    logger.append(' < Complete >\n')

    logger.append(' < Converting KERI META data >\n')
    meta_converter.convert_all_to_csv(source_rootdir, target_rootdir,
                                      skip_converted=True, backup_excel=True, tail_in_csv_filename='_META')
    logger.append(' < Complete >\n')


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 2:
        source_rootdir = args[0]
        target_rootdir = args[1]
        logger = Logger(print_on_append=True)

        logger.append(f'** TEP conversion ({VERSION}) start **\n')
        convert(source_rootdir, target_rootdir, logger)
        logger.append('** TEP conversion complete **\n')
        logger.save_log('convert_log.txt')
        input('Press enter.')
    else:
        print('Usage: python convert.py [source_rootdir] [target_rootdir]')
