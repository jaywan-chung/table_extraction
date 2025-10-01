.. table_extraction documentation master file, created by
   sphinx-quickstart on Tue Aug 19 16:28:02 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to table_extraction's documentation!
=================================================

This package can extract several tables from a large table (a pandas DataFrame).

The main application is extracting several tables from an Excel file,
which is useful because many tables are often located in a single tab for convenience.

For extracting tables:

* from a pandas DataFrame: use :py:func:`table_extraction.find_all_table_range`.
* from a Excel file: use :py:class:`excel_table_conversion.ExcelTableConverter`.
  For an example usage, refer to the source code of :py:mod:`convert` module (`convert.py`).

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   modules_core
   modules_app
   modules_util

Document version:
|release|

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
