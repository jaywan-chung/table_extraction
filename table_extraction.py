"""
    This module provides :py:func:`find_all_table_range` function to extract all tables from a pandas DataFrame.
    A table is described by its range in the DataFrame as an instance of :py:class:`TableRange`.
    To realize a table from a table range, use :py:meth:`TableRange.to_dataframe`.

    :copyright: © 2025 by Jaywan Chung
    :license: MIT
"""
import unittest

import numpy as np
import pandas as pd


class TableRange:
    """Represents the region where a table is located.
    The region is a rectangular described by :py:attr:`TableRange.start_pos` and :py:attr:`TableRange.stop_pos`.

    :param start_pos: The position where the table begins: (start_row, start_col).
    :type start_pos: Tuple[int, int]
    :param stop_pos: The position where the table ends: (stop_row, stop_col).
        Rows and columns containing `stop_pos` are **excluded** from the table.
    :type stop_pos: Tuple[int, int]

    :raises ValueError: When the length of `start_pos` or `stop_pos` is not two.
    """
    def __init__(self, start_pos, stop_pos) -> None:
        if (len(start_pos) != 2) or (len(stop_pos) != 2):
            raise ValueError('The length of `start_pos` and `stop_pos` must be two.')

        self.start_row, self.start_col = start_pos
        self.stop_row, self.stop_col = stop_pos

    def __eq__(self, other: 'TableRange') -> bool:
        if isinstance(other, TableRange):
            return (self.start_row, self.start_col, self.stop_row, self.stop_col) == \
                (other.start_row, other.start_col, other.stop_row, other.stop_col)
        return False

    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}(start_pos={self.start_pos}, stop_pos={self.stop_pos})'

    @property
    def start_pos(self) -> 'Tuple[int, int]':
        """Return the position where the table begins.

        :return: (start_row, start_col)
        :rtype: Tuple[int, int]
        """
        return self.start_row, self.start_col

    @property
    def stop_pos(self) -> 'Tuple[int, int]':
        """Return the position where the table ends.
        Rows and columns containing `stop_pos` are **excluded** from the table.

        :return: (stop_row, stop_col)
        :rtype: Tuple[int, int]
        """
        return self.stop_row, self.stop_col

    def fill_inplace(self, array, value) -> None:
        """Assign a value to the table region of a 2D array. The array *changes*.

        :param array: A 2D array to be changed.
        :type array: numpy.ndarray or array_like
        :param value: A scalar value to be assigned.
        :type value: int, float or scalar
        """
        array[self.start_row:self.stop_row, self.start_col:self.stop_col] = value

    def to_dataframe(self, df) -> 'pandas.DataFrame':
        """Return the contents within the table region of a given pandas DataFrame.

        :param df: A given DataFrame containing the table region.
        :type df: pandas.DataFrame
        :return: The contents within the table region.
        :rtype: pandas.DataFrame
        """
        return df.iloc[self.start_row:self.stop_row, self.start_col:self.stop_col]

    def has_min_size(self, min_n_rows, min_n_cols) -> bool:
        """Check to see if the table region has the minimum size.

        :param min_n_rows: The minimum number of rows the table region must have.
        :type min_n_rows: int
        :param min_n_cols: The minimum number of columns the table region must have.
        :type min_n_cols: int
        :return: `True` if the table region has the minimum size, `False` otherwise.
        :rtype: bool
        """
        if self.stop_row - self.start_row < min_n_rows:
            return False
        if self.stop_col - self.start_col < min_n_cols:
            return False
        return True


def find_all_table_range(df: pd.DataFrame, min_n_rows=1, min_n_cols=1) -> 'List[TableRange]':
    """Return all table ranges satisfying the minimum size requirement.

    The first row of a table is supposed to be full of existing (non-missing) values (because it is a header).
    To check existing values, `pandas.DataFrame.notna() <https://pandas.pydata.org/pandas-docs/version/1.1.3/reference/api/pandas.notna.html>`__ is used.
    Then a table is expanded until a row with all missing values is met.
    Hence, other than the header row, a missing value may exist inside a table.

    :param df: The DataFrame to find table ranges.
    :type df: pandas.DataFrame
    :param min_n_rows: The minimum number of rows a table must have. Default: `1`.
    :type min_n_rows: int, optional
    :param min_n_cols: The minimum number of rows a table must have. Default: `1`.
    :type min_n_cols: int, optional
    :return: A list of all table ranges meeting the minimum size requirement.
    :rtype: List[:py:class:`TableRange`]

    Examples:
        >>> import numpy as np
        >>> import pandas as pd
        >>> df = pd.DataFrame([['a', 'b', np.nan, np.nan, np.nan],
        ...                    [0, 10.0, np.nan, 'c', 'd'],
        ...                    [np.nan, np.nan, np.nan, np.nan, -4]])
        >>> find_all_table_range(df)
        [TableRange(start_pos=(0, 0), stop_pos=(2, 2)), TableRange(start_pos=(1, 3), stop_pos=(3, 5))]
        >>> find_all_table_range(df, min_n_rows=1, min_n_cols=3)
        []
    """
    value_exists_at = df.notna().to_numpy()
    last_row, last_col = value_exists_at.shape

    list_table_range = []
    for row in range(last_row):
        for col in range(last_col):
            if value_exists_at[row, col]:
                table_range = _find_table_range_from_boolean_array_starting_at((row, col), value_exists_at)
                if table_range.has_min_size(min_n_rows, min_n_cols):
                    list_table_range.append(table_range)
                    table_range.fill_inplace(value_exists_at, False)

    return list_table_range


def _find_table_range_from_boolean_array_starting_at(start_pos, boolean_array) -> 'TableRange':
    """Find a single table range starting at `start_pos`. The given table is assumed to be boolean type.

    The first row of a table is supposed to be full of `True` values.
    Then a table is expanded until a row with all `False` values is met.
    Hence, other than the header row, a `False` value may exist inside a table.

    :param start_pos: The position where the table range begins.
    :type start_pos: Tuple[int, int]
    :param boolean_array: A 2D array with boolean type.
    :type boolean array: :py:class:`numpy.ndarray(dtype=bool)`
    :return: a table range
    :rtype: :py:class:`TableRange`

    :raises TypeError: When the `boolean_array` is not of boolean type.
    """
    if boolean_array.dtype != bool:
        raise TypeError("'boolean_array' must have a boolean type.")

    start_row, start_col = start_pos
    last_row, last_col = boolean_array.shape
    array_is_false_at = np.logical_not(boolean_array)

    stop_row, stop_col = start_pos
    for col in range(start_col, last_col):
        if array_is_false_at[start_row, col]:
            break
        else:
            stop_col = col + 1
    for row in range(start_row, last_row):
        if array_is_false_at[row, start_col:stop_col].all():
            break
        else:
            stop_row = row + 1

    return TableRange((start_row, start_col), (stop_row, stop_col))


class TableRangeTest(unittest.TestCase):
    def setUp(self):
        self.table_range = TableRange(start_pos=(1, 1), stop_pos=(2, 3))

    def test_eq(self):
        self.assertEqual(self.table_range, self.table_range)
        self.assertNotEqual(self.table_range, TableRange(start_pos=(1, 1), stop_pos=(2, 4)))
        self.assertNotEqual(self.table_range, ((1, 1), (2, 4)))

    def test_repr(self):
        self.assertEqual(repr(self.table_range), 'TableRange(start_pos=(1, 1), stop_pos=(2, 3))')

    def test_init_raise_value_error(self):
        """Test if value error properly occurs when `start_pos` or `stop_pos` is not a tuple of length two."""
        with self.assertRaises(ValueError):
            TableRange(start_pos=(1, ), stop_pos=(2, 3))
        with self.assertRaises(ValueError):
            TableRange(start_pos=(1, 2, 3), stop_pos=(2, 3))
        with self.assertRaises(ValueError):
            TableRange(start_pos=(1, 1), stop_pos=(2,))
        with self.assertRaises(ValueError):
            TableRange(start_pos=(1, 1), stop_pos=(2, 3, 4))

    def test_start_pos_and_stop_pos(self):
        self.assertEqual(self.table_range.start_pos, (1, 1))
        self.assertEqual(self.table_range.stop_pos, (2, 3))

    def test_fill_inplace(self):
        array = np.array([[False, True, True, False],
                          [False, False, True, True],
                          [False, True, False, True]], dtype=bool)
        answer = np.array([[False, True, True, False],
                           [False, False, False, False],
                           [False, True, False, False]], dtype=bool)
        table_range = TableRange(start_pos=(1, 2), stop_pos=(3, 4))
        table_range.fill_inplace(array, False)
        self.assertTrue(np.array_equal(array, answer))

    def test_to_dataframe(self):
        df = pd.DataFrame([['a', 'b', np.nan, np.nan, np.nan],
                           [0, 10.0, np.nan, 'c', 'd'],
                           [np.nan, np.nan, np.nan, np.nan, -4]])
        answer = pd.DataFrame([['c', 'd'], [np.nan, -4]], index=(1, 2), columns=(3, 4))
        table_range = TableRange(start_pos=(1, 3), stop_pos=(3, 5))
        result = table_range.to_dataframe(df)
        self.assertTrue(result.equals(answer))

    def test_has_min_size(self):
        table_range = TableRange(start_pos=(1, 3), stop_pos=(2, 4))
        self.assertTrue(table_range.has_min_size(1, 1))
        self.assertFalse(table_range.has_min_size(2, 1))
        self.assertFalse(table_range.has_min_size(1, 2))


class TableExtractionTest(unittest.TestCase):
    def test_find_table_range_from_boolean_array_starting_at(self):
        boolean_array = np.array([[False, True, True, False],
                                  [False, False, True, False],
                                  [False, True, False, False],
                                  [False, False, False, True],
                                  [False, False, False, False]], dtype=bool)

        table_range = _find_table_range_from_boolean_array_starting_at((0, 0), boolean_array)
        self.assertEqual(table_range, TableRange(start_pos=(0, 0), stop_pos=(0, 0)))

        table_range = _find_table_range_from_boolean_array_starting_at((0, 1), boolean_array)
        self.assertEqual(table_range, TableRange(start_pos=(0, 1), stop_pos=(3, 3)))

        table_range = _find_table_range_from_boolean_array_starting_at((3, 3), boolean_array)
        self.assertEqual(table_range, TableRange(start_pos=(3, 3), stop_pos=(4, 4)))

        int_array = np.array([[1, 2, 3], [4, 5, 6]], dtype=int)
        with self.assertRaises(TypeError):
            _find_table_range_from_boolean_array_starting_at((0, 0), int_array)

    def test_find_all_table_range(self):
        df = pd.DataFrame([['a', 'b', np.nan, np.nan, np.nan],
                           [0, 10.0, np.nan, 'c', 'd'],
                           [np.nan, np.nan, np.nan, np.nan, -4]])

        result = find_all_table_range(df)
        answer = [TableRange(start_pos=(0, 0), stop_pos=(2, 2)),
                  TableRange(start_pos=(1, 3), stop_pos=(3, 5))]
        self.assertEqual(result, answer)

        result = find_all_table_range(df, min_n_rows=1, min_n_cols=3)
        self.assertEqual(result, [])
