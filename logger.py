"""
    This module provides :py:class:`Logger` class for logging colored terminal text.
    A colored text is defined by :py:class:`ColorMsg` class that depends on
    `colorama <https://pypi.org/project/colorama/>`__ package.

    :copyright: © 2025 by Jaywan Chung
    :license: MIT
"""
from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch, mock_open, call

from colorama import init as colorama_init
from colorama import deinit as colorama_deinit
from colorama import Fore, Style, Back


class Logger:
    """A logger for storing **colored** terminal texts.

    For available color/style formatting constants,
    refer to `colorama <https://pypi.org/project/colorama/>`__ description.

    *Note*: `colorama <https://pypi.org/project/colorama/>`__ package is automatically initialized
    when creating a :py:class:`Logger` instance.

    :param print_on_append: If `True`, the message is immediately printed when it is appened. Default is `False`.
    :type print_on_append: bool, optional
    :param alert_color: The color of alert text. Default is red.
    :type alert_color: str, optional
    :param alert_style: The style of alert text. Default is no style.
    :type alert_style: str, optional
    :param alert_background_color: The background color of alert text. Default is no color.
    :type alert_background_color: str, optional

    Examples:
        >>> logger = Logger()
        >>> logger.append('plain text')
        >>> logger.append_alert('alert text')
        >>> logger.save_log('log.txt')
        >>> logger.clear_log()
    """
    _colorama_initializeed: bool = False

    def __init__(self, print_on_append=False, alert_color=Fore.RED, alert_style='', alert_background_color='') -> None:
        if not Logger._colorama_initializeed:
            # Initialize colorama for Windows compatibility
            colorama_init()
            Logger._colorama_initializeed = True

        self._log: 'List[ColorMsg]' = []
        self.print_on_append: bool = print_on_append
        self.alert_color: str = alert_color
        self.alert_style: str = alert_style
        self.alert_background_color: str = alert_background_color

    def __del__(self) -> None:
        if Logger._colorama_initializeed:
            colorama_deinit()
        self.clear_log()

    @property
    def last_msg(self) -> 'ColorMsg':
        """Return the last log message.

        :return: The last message.
        :rtype: :py:class:`ColorMsg`
        """
        if len(self._log) == 0:
            return ColorMsg('')
        return self._log[-1]

    def append(self, msg_or_str) -> None:
        """Append a message to log. A message can be a colored text or a string.

        :param msg_or_str: A message to append.
        :type msg_or_str: :py:class:`ColorMsg` or str
        """
        msg = msg_or_str
        if isinstance(msg_or_str, str):
            text = msg_or_str
            msg = ColorMsg(text)
        if not isinstance(msg, ColorMsg):
            raise TypeError('`msg_or_str` must be a `ColorMsg` instance or a string.')

        self._log.append(msg)
        if self.print_on_append:
            msg.print()

    def append_alert(self, text) -> None:
        """Append an alert text to log.
        The color and style of the text is automatically imposed as promised
        when initializing the :py:class:`Logger` instance.

        :param text: An alert text to append.
        :type text: str

        :raises TypeError: When `text` is not a string.
        """
        if not isinstance(text, str):
            raise TypeError('`text` must be a string!')

        self.append(ColorMsg(text, color=self.alert_color, style=self.alert_style,
                             background_color=self.alert_background_color))

    def clear_log(self) -> None:
        """Clear log. All messages are deleted.
        """
        self._log.clear()

    def save_log(self, path) -> None:
        """Save log as a txt file.

        :param path: A filepath.
        :type path: str
        """
        with open(path, 'w') as f:
            for msg in self._log:
                f.write(msg._text)


class ColorMsg:
    """Represents a colored terminal text. Text color, background color and text style can be specified.
    For available formatting constants, refer to `colorama <https://pypi.org/project/colorama/>`__ description.

    **Warning**: Before using this class, call `colorama.init()`
    to initialize `colorama <https://pypi.org/project/colorama/>`__ package.

    :param text: A plain text.
    :type text: str
    :param color: A `colorama` constant formatting text color. Default is no color.
    :type color: str, optional
    :param style: A `colorama` constant formatting text style. Default is no style.
    :type style: str, optional
    :param background_color: A `colorama` constant formatting background color. Default is no color.
    :type background_color: str, optional

    Examples:
        >>> from colorama import init, Fore, Style, Back
        >>> init()
        >>> text = 'dim green text with white background'
        >>> msg = ColorMsg(text, color=Fore.GREEN, style=Style.DIM, background_color=Back.WHITE)
        >>> msg.print()
        \x1b[2m\x1b[32m\x1b[47mdim green text with white background\x1b[0m
        >>> msg.text
        dim green text with white background
    """
    def __init__(self, text, color='', style='', background_color='') -> None:
        self._text: str = text
        self._color: str = color
        self._style: str = style
        self._background_color: str = background_color

    def __repr__(self) -> str:
        result = f'{self.__class__.__qualname__}({repr(self._text)}'
        if self._color:
            result += f', color={repr(self._color)}'
        if self._style:
            result += f', style={repr(self._style)}'
        if self._background_color:
            result += f', background_color={repr(self._background_color)}'
        result += ')'
        return result

    def __str__(self) -> str:
        return f'{self._style}{self._color}{self._background_color}{self._text}{Style.RESET_ALL}'

    def __eq__(self, other) -> bool:
        """Check equality between :py:class:`ColorMsg` classes.
        All properties (Text, text color, style, background color) must be equal.

        :param other: A variable to be compared.
        :type other: :py:class:`ColorMsg` or other
        :return: `True` if two `ColorMsg` are exactly the same. Return `False` otherwise.
        :rtype: bool
        """
        if not isinstance(other, ColorMsg):
            return False

        text_eq = self.text == other.text
        color_eq = self._color == other._color
        style_eq = self._style == other._style
        background_eq = self._background_color == other._background_color
        return text_eq and color_eq and style_eq and background_eq

    @property
    def text(self) -> str:
        """Return the plain text without color or style.

        :return: The plain text.
        :rtype: str
        """
        return self._text

    def print(self) -> None:
        """Print the colored terminal text **without newline**.
        """
        print(str(self), end='')


class LoggerTest(unittest.TestCase):
    def setUp(self):
        self.logger = Logger()

    def tearDown(self):
        del self.logger

    def test_empty_last_msg(self):
        self.assertEqual(self.logger.last_msg, ColorMsg(''))

    def test_append_str(self):
        text = 'plain text'
        self.logger.append(text)
        self.assertEqual(self.logger.last_msg, ColorMsg(text))

    def test_append_raise_error(self):
        self.assertRaises(TypeError, self.logger.append, 1)

    def test_print_on_append(self):
        self.logger.print_on_append = True
        text = 'dim green text with white background'
        msg = ColorMsg(text, color=Fore.GREEN, style=Style.DIM, background_color=Back.WHITE)

        # Redirect stdout to the StringIO object
        captured_output = StringIO()
        with redirect_stdout(captured_output):
            self.logger.append(msg)
        printed_string = captured_output.getvalue()

        self.assertEqual(printed_string, str(msg))

    def test_append_alert(self):
        self.logger.alert_color = Fore.RED
        self.logger.alert_style = Style.BRIGHT
        self.logger.alert_background_color = Back.CYAN
        self.logger.append_alert('alert!')
        self.assertEqual(self.logger.last_msg, ColorMsg('alert!', color=Fore.RED, style=Style.BRIGHT,
                                                        background_color=Back.CYAN))

    def test_append_alert_raise_error(self):
        self.assertRaises(TypeError, self.logger.append_alert, ColorMsg('alert!'))

    def test_clear(self):
        self.logger.append('first msg')
        self.logger.append('second msg')
        self.logger.clear_log()
        self.assertEqual(self.logger.last_msg, ColorMsg(''))

    def test_save_log(self):
        self.logger.append('first msg\n')
        self.logger.append_alert('alert!\n')
        self.logger.append(ColorMsg('color msg', color=Fore.YELLOW))
        m = mock_open()
        with patch('builtins.open', m):
            self.logger.save_log('log.txt')

        m.assert_called_once_with('log.txt', 'w')
        handle = m()
        handle.write.assert_has_calls([
            call('first msg\n'),
            call('alert!\n'),
            call('color msg')
        ])


class ColorMsgTest(unittest.TestCase):
    def test_no_color_text(self):
        text = 'no color text'
        msg = ColorMsg(text)
        self.assertEqual(msg._text, text)
        self.assertEqual(repr(msg), f'ColorMsg({repr(text)})')
        self.assertEqual(str(msg), f'{text}{Style.RESET_ALL}')

    def test_red_text(self):
        text = 'red text'
        msg = ColorMsg(text, color=Fore.RED)
        self.assertEqual(msg._text, text)
        self.assertEqual(repr(msg), f'ColorMsg({repr(text)}, color={repr(Fore.RED)})')
        self.assertEqual(str(msg), f'{Fore.RED}{text}{Style.RESET_ALL}')

    def test_bright_yellow_text(self):
        text = 'bright yellow text'
        msg = ColorMsg(text, color=Fore.YELLOW, style=Style.BRIGHT)
        self.assertEqual(msg._text, text)
        self.assertEqual(repr(msg), f'ColorMsg({repr(text)}, color={repr(Fore.YELLOW)}, style={repr(Style.BRIGHT)})')
        self.assertEqual(str(msg), f'{Style.BRIGHT}{Fore.YELLOW}{text}{Style.RESET_ALL}')

    def test_magenta_background_text(self):
        text = 'magenta background text'
        msg = ColorMsg(text, background_color=Back.MAGENTA)
        self.assertEqual(msg._text, text)
        self.assertEqual(repr(msg), f'ColorMsg({repr(text)}, background_color={repr(Back.MAGENTA)})')
        self.assertEqual(str(msg), f'{Back.MAGENTA}{text}{Style.RESET_ALL}')

    def test_msg_print(self):
        text = 'dim green text with white background'
        msg = ColorMsg(text, color=Fore.GREEN, style=Style.DIM, background_color=Back.WHITE)

        # Redirect stdout to the StringIO object
        captured_output = StringIO()
        with redirect_stdout(captured_output):
            msg.print()
        printed_msg = captured_output.getvalue()

        self.assertEqual(printed_msg, str(msg))

    def test_eq(self):
        text = 'dim cyan text with yellow background'
        color = Fore.CYAN
        style = Style.DIM
        background_color = Back.YELLOW
        msg = ColorMsg(text, color, style, background_color)

        self.assertTrue(msg == ColorMsg(text, color, style, background_color))
        self.assertTrue(msg != ColorMsg('different text', color, style, background_color))
        self.assertTrue(msg != text)
        self.assertTrue(msg != ColorMsg(text, '', style, background_color))
        self.assertTrue(msg != ColorMsg(text, color, '', background_color))
        self.assertTrue(msg != ColorMsg(text, color, style, ''))
