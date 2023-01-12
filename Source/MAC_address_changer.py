import argparse
import sys
import os
import re
import subprocess
from random import randrange
from loguru import logger


def user_log_filter(record):
    return (record['level'].name == 'INFO' or record['level'].name == 'WARNING' or record['level'].name == 'ERROR')


def get_logger():
    logger.remove()
    fmt_terminal = '{message}'
    fmt_debug = '{time} - {level}: {message}'
    fmt_error = '{time: DD.MM.YYYY HH:mm:ss} - {level}: {message}'
    logger.add(sys.stderr, format=fmt_terminal, filter=user_log_filter, level='INFO', backtrace=False, diagnose=False)
    logger.add('debug.log', format=fmt_debug, level='DEBUG', rotation='1 days', compression='zip')
    logger.add('errors.log', format=fmt_error, level='ERROR', rotation='1 days', compression='zip')

def get_args():
    """Validates, processes and retrieves command line arguments for the programm.
    Returns interface name and MAC address string if any.
    """
    parser = argparse.ArgumentParser(
        prog='MAC Changer',
        description='Programm for changing MAC address in Linux OS.'
    )
    parser.add_argument('-i', '--interface',
                        dest='interface',
                        required=True,
                        metavar='Interface',
                        help='Interface to change MAC address on.')
    parser.add_argument('-m', '--mac',
                        dest='newmac_arg',
                        metavar='MAC_Address',
                        help='New MAC address. (Optional)',
                        default='')
    args = parser.parse_args()

    check_mac_result = re.match('[a-fA-F0-9]{2}([-:]?)[a-fA-F0-9]{2}(\\1[a-fA-F0-9]{2}){4}$', args.newmac_arg)
    if args.newmac_arg and not check_mac_result:
        logger.warning(f'\nWARNING: MAC address format is invalid {args.newmac_arg}.\n')
        args.newmac_arg = generate_random_mac()
    else:
        logger.debug(f'MAC address format is valid {args.newmac_arg}.')
    return args


def do_root_permission():
    """Checks if user has root permission and if not try to dwitch to root.
    Returns True if the user has root permission by any means
    """
    if os.geteuid() != 0:
        if subprocess.call(f'sudo -n true >> /dev/null', shell=True) != 0:
            # If sudo credentials expired or was not entered yet
            logger.info('Permission denayed.This operation requires root permission:')
            return subprocess.call(f'sudo -v', shell=True)
    return False


def change_mac(interface, newmac):
    """Changes the MAC address of the provided nework interface to the new one"""
    after_changed = subprocess.check_output(f'sudo ifconfig {interface}', shell=True)
    logger.info(f'Interface configuration {interface} after changing:\n {after_changed.decode("UTF-8")}')
    logger.info(f'Changing MAC address for {interface} to {newmac}.')
    logger.info(f'-> Putting interface {interface} down')
    subprocess.call(f'sudo ifconfig {interface} down', shell=True)
    logger.info(f'-> Change MAC to {newmac}')
    subprocess.call(f'sudo ifconfig {interface} hw ether {newmac}', shell=True)
    logger.info(f'-> Powering up {interface}')
    subprocess.call(f'sudo ifconfig {interface} up', shell=True)
    before_changed = subprocess.check_output(f'sudo ifconfig {interface}', shell=True)
    logger.info(f'Interface configuration {interface} before changing:\n  {before_changed.decode("UTF-8")}')


def generate_random_mac():
    """Generated random MAC, where first part is choosen from the existing OUIs list"""
    logger.info('Generate random MAC? [y/n]: ')
    answer = input().lower()

    while answer != 'y' and answer != 'n':
        logger.info('Your answer is not correct. Should be Y or N: ')
        answer = input().lower()
    logger.info(f'Your answer is {answer}.')

    if answer == 'y':
        industrial_oui = [
            ['CC', '46', 'D6'],  # Cisco
            ['3C', '5A', 'B4'],  # Google
            ['3C', 'D9', '28'],  # HP
            ['24', '46', 'CB']  # Motorola, Lenovo
        ]
        ouirnd = [
            '%02x' % randrange(0, 255),
            '%02x' % randrange(0, 255),
            '%02x' % randrange(0, 255)
        ]
        rnd_industrial_oui = industrial_oui[randrange(0, len(industrial_oui))]
        newmac = ':'.join(rnd_industrial_oui + ouirnd).lower()
        logger.info(f'Random MAC is {newmac}')
        return newmac
    else:
        logger.error('ERROR: MAC address format is invalid.')
        logger.info('Finished...')
        sys.exit('')

@logger.catch
def main():
    get_logger()
    args = get_args()
    logger.info('Processsing...')
    if not do_root_permission():
        logger.info('Accessed...')
        change_mac(args.interface, args.newmac_arg)
        logger.info('Finished...')
    else:
        logger.error('Sorry, but you are not sudo...')
        logger.info('Finished...')


if __name__ == '__main__':
    main()