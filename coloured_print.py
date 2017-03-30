#! /ustr/bin/env python

#import ctypes
from ctypes import *
import logging
import os
import re

stdout_handle = windll.kernel32.GetStdHandle
SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute

class ColourisingStreamHandler(logging.StreamHandler):

    ANSI_REGEX = re.compile(r'\x1b\[((?:\d+)(?:;(?:\d+))*)m')
    # colour names to indices
    colour_map = {
        'black': 0,
        'red': 1,
        'green': 2,
        'yellow': 3,
        'blue': 4,
        'magenta': 5,
        'cyan': 6,
        'white': 7,
    }

    #levels to (background, foreground, bold/intense)
    if os.name == 'nt':
        level_map = {
            logging.DEBUG: (None, 'blue', True),
            logging.INFO: (None, 'white', False),
            logging.WARNING: (None, 'yellow', True),
            logging.ERROR: (None, 'red', True),
            logging.CRITICAL: ('red', 'white', True),
        }
    else:
        level_map = {
            logging.DEBUG: (None, 'blue', False),
            logging.INFO: (None, 'black', False),
            logging.WARNING: (None, 'yellow', False),
            logging.ERROR: (None, 'red', False),
            logging.CRITICAL: ('red', 'white', True),
        }
    csi = '\x1b['
    reset = '\x1b[0m'

    @property
    def is_tty(self):
        isatty = getattr(self.stream, 'isatty', None)
        return isatty and isatty()

    def emit(self, record):
        try:
            message = self.format(record)
            stream = self.stream
            if not self.is_tty:
                stream.write(message)
            else:
                self.output_colourised(message)
            stream.write(getattr(self, 'terminator', '\n'))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    if os.name != 'nt':
        def output_colourised(self, message):
            self.stream.write(message)
    else:
        nt_colour_map = {
            0: 0x00,    # black
            1: 0x04,    # red
            2: 0x02,    # green
            3: 0x06,    # yellow
            4: 0x01,    # blue
            5: 0x05,    # magenta
            6: 0x03,    # cyan
            7: 0x07,    # white
        }

        def output_colourised(self, message):
            msgsplit = self.ANSI_REGEX.split(message)
            write = self.stream.write
            handle = None
            fd = getattr(self.stream, 'fileno', None)
            if fd is not None:
                fd = fd()
                if fd in (1, 2): # stdout or stderr
                    handle = stdout_handle(-10 - fd)
            while msgsplit:
                text = msgsplit.pop(0)
                if text:
                    write(text)
                if msgsplit:
                    params = msgsplit.pop(0)
                    if handle is not None:
                        params = [int(p) for p in params.split(';')]
                        colour = 0
                        for p in params:
                            if 40 <= p <= 47:
                                colour |= self.nt_colour_map[p - 40] << 4
                            elif 30 <= p <= 37:
                                colour |= self.nt_colour_map[p - 30]
                            elif p == 1:
                                colour |= 0x08 # foreground intensity on
                            elif p == 0: # reset to default colour
                                colour = 0x07
                            else:
                                pass # error condition ignored
                        SetConsoleTextAttribute(handle, colour)

    def colourise(self, message, record):
        if record.levelno in self.level_map:
            bg, fg, bold = self.level_map[record.levelno]
            params = []
            if bg in self.colour_map:
                params.append(str(self.colour_map[bg] + 40))
            if fg in self.colour_map:
                params.append(str(self.colour_map[fg] + 30))
            if bold:
                params.append('1')
            if params:
                message = ''.join((self.csi, ';'.join(params),
                                   'm', message, self.reset))
        return message

    def format(self, record):
        message = logging.StreamHandler.format(self, record)
        if self.is_tty:
            # Don't colourise any traceback
            msgsplit = message.split('\n', 1)
            msgsplit[0] = self.colourise(msgsplit[0], record)
            message = '\n'.join(msgsplit)
        return message

def print_in_colour(colour, message):
    """ Print In Colour
    0 = black
    1 = Blue
    2 = Green
    3 = Cyan
    4 = Red
    5 = Magenta
    6 = Brown
    7 = Light Gray
    8 = Dark Gray
    Intensity - All colours beyond here have Instensity factored in
    9 = Light Blue
    10 = Light Green
    11 = Light Cyan
    12 = Light Red
    13 = Light Magenta
    14 = Yellow
    15 = White
    Entries beyond this point change background colour too
    16 -> 31 Blue background
    32 -> 47 Green background
    48 -> 63 Cyan background
    64 -> 79 Red background
    80 -> 95 Magenta background
    96 -> 111 Brown background
    112 -> 127 Light Grey background
    128 -> 143 Dark Grey background
    144 -> 159 Light Blue background
    160 -> 175 Light Green background
    176 -> 191 Light Cyan background
    192 -> 207 Light Red background
    208 -> 223 Light Magenta background
    224 -> 239 Yellow background
    240 -> 255 White background
    """

    stdout_handle.restype = c_ulong
    h = stdout_handle(c_ulong(0xfffffff5))
    SetConsoleTextAttribute(h, colour)

    print message

    # Return back to white (modify for alternative colour)
    SetConsoleTextAttribute(h, 15)
