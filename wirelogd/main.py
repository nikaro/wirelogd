#!/usr/bin/python3

"""
Wirelogd is a logging daemon for WireGuard.

Since WireGuard itself does not log the state of its peers (and since it is UDP
based so, there no concept of "connection state"), Wirelogd relies on the
latest handshake to determine if a peer is active or inactive. While there is
trafic the handshake should be renewed every 2 minutes. If there is no trafic,
handshake is not renewed. Based on this behavior we assume that if there is no
new handshake after a while (default Wirelogd timeout value is 5 minutes), the
client is probably inactive.
"""

import argparse
import configparser
import json
import logging
import os
import pathlib
import subprocess  # nosec
import sys
import time
from functools import lru_cache


@lru_cache(maxsize=6)
def booly(value: str) -> bool:
    """Return a boolean from values like 'yes', 'no', etc."""
    truthy_values = (
        '1',
        'on',
        'enable',
        'enabled',
        'true',
        'yes',
    )

    return str(value).lower() in truthy_values


def config_from_defaults(struct: tuple) -> dict:
    """Return dict from defaults."""
    return {x: y for x, _, y in struct}


def config_from_file(struct: tuple, config_path: str) -> dict:
    """Return dict from configparser."""
    configfile = configparser.ConfigParser()
    if not pathlib.Path(config_path).exists():
        return {}
    configfile.read(config_path)

    return {
        x: y(configfile.get('wirelogd', x))
        for x, y, _ in struct
        if configfile.get('wirelogd', x, fallback=None)
    }


def config_from_environment(struct: tuple) -> dict:
    """Return dict from environment."""
    return {
        x: y(os.environ['WIRELOGD_' + x.upper().replace('-', '_')])
        for x, y, _ in struct
        if os.getenv('WIRELOGD_' + x.upper().replace('-', '_'))
    }


def config_from_args(struct: tuple, args: argparse.Namespace) -> dict:
    """Return dict from args."""
    return {
        x: y(getattr(args, x.replace('-', '_')))
        for x, y, _ in struct
        if (
            hasattr(args, x.replace('-', '_'))
            and getattr(args, x.replace('-', '_'))
        )
    }


def parse_config(struct: tuple, path: str, args: argparse.Namespace) -> dict:
    """Return config from: args > environment > configfile > defaults."""
    config: dict = {}

    # set defaults
    config_defaults = config_from_defaults(struct)
    config.update(config_defaults)

    # set from configuration file
    config_file = config_from_file(struct, path)
    config.update(config_file)

    # set from environment variables
    config_env = config_from_environment(struct)
    config.update(config_env)

    # set from command-line arguments
    config_args = config_from_args(struct, args)
    config.update(config_args)

    return config


@lru_cache(maxsize=128)
def link_wggw(path: str, pubkey: str) -> str:
    """Return name from wg-gen-web config matching with public key."""
    files = pathlib.Path(path).glob('*-*-*-*-*')
    for conf_path in files:
        with open(conf_path) as conf_fp:
            conf = json.load(conf_fp)
        if conf['publicKey'] == pubkey:
            return conf['name']

    return 'unknown'


def peer_dict(peer: list, wggw: bool, wggw_path: str) -> dict:
    """Return structured dict from wg peer dump line."""
    fpeer = {
        'interface': peer[0],
        'public-key': peer[1],
        'endpoint': peer[3],
        'allowed-ips': peer[4],
        'latest-handshake': float(peer[5]),
        'name': 'unknown',
    }

    if wggw and wggw_path:
        fpeer['name'] = link_wggw(wggw_path, fpeer['public-key'])

    return fpeer


def get_peers(sudo: bool, wggw: bool, wggw_path: str) -> tuple:
    """Return list of peers, each peer as dict of informations."""
    # run command
    cmd = ['wg', 'show', 'all', 'dump']
    if sudo:
        cmd.insert(0, 'sudo')
    try:
        res = subprocess.run(cmd, capture_output=True, check=True)  # nosec
    except subprocess.CalledProcessError:
        sys.exit('executing `%s` failed' % ' '.join(cmd))
    except FileNotFoundError:
        sys.exit('wireguard-tools are not installed')

    # filter and format peers (client peers have 9 columns)
    peers_list = [
        x.split()
        for x in res.stdout.decode().strip().split('\n')
        if len(x.split()) == 9
    ]
    peers = tuple(peer_dict(x, wggw, wggw_path) for x in peers_list)

    return peers


def check_timeout(peer: dict, timeout: int) -> bool:
    """Return True if timeout is reached."""
    # elapsed time between now and latest peer handshake
    elapsed_time = time.time() - peer['latest-handshake']
    expired = elapsed_time > timeout

    return expired


def run_loop(config: dict, log: logging.Logger):
    """Run loop executing actions and logging results."""
    # initialize activity state tracking
    activity_state: dict = {}

    log.info('starting wirelodg')
    while True:
        peers = get_peers(
            config['sudo'],
            config['wg-gen-web'],
            config['wg-gen-web-path'],
        )
        log.debug('%s', peers)
        for peer in peers:
            key = f"{peer['public-key']}-{peer['interface']}"
            was_active = activity_state.get(key, False)
            timedout = check_timeout(peer, config['timeout'])
            if was_active and timedout:
                # log inactive connection
                activity_state[key] = False
                log.info(
                    '%s - %s - %s - %s - %s - inactive',
                    peer['name'],
                    peer['public-key'],
                    peer['endpoint'],
                    peer['allowed-ips'],
                    peer['interface'],
                )
            elif not was_active and not timedout:
                # log new active connection
                activity_state[key] = True
                log.info(
                    '%s - %s - %s - %s - %s - active',
                    peer['name'],
                    peer['public-key'],
                    peer['endpoint'],
                    peer['allowed-ips'],
                    peer['interface'],
                )
        time.sleep(config['refresh'])


def setup_parser() -> argparse.ArgumentParser:
    """Set the main arguments."""
    parser = argparse.ArgumentParser(prog='wirelogd', description=__doc__)
    parser.add_argument(
        '--config', '-c',
        help='path to configuration file',
        metavar='str',
    )
    parser.add_argument(
        '--debug', '-d',
        help='enable debug logging',
        action='store_true',
    )
    parser.add_argument(
        '--refresh', '-r',
        help='refresh interval in seconds',
        type=int,
        metavar='int',
    )
    parser.add_argument(
        '--sudo', '-s',
        help='run subprocess commands with sudo',
        action='store_true',
    )
    parser.add_argument(
        '--timeout', '-t',
        help='wireguard handshake timeout in seconds',
        type=int,
        metavar='int',
    )
    parser.add_argument(
        '--wg-gen-web', '-w',
        help='link peer with its wg-gen-web config name',
        action='store_true',
    )
    parser.add_argument(
        '--wg-gen-web-path',
        help='path where wg-gen-web store its config files',
        metavar='str',
    )

    return parser


def setup_config(args: argparse.Namespace) -> dict:
    """Set the main configuration."""
    config_struct = (
        # settings, type to cast, default
        ('debug', booly, False),
        ('refresh', int, 5),
        ('sudo', booly, False),
        ('timeout', int, 300),
        ('wg-gen-web', booly, False),
        ('wg-gen-web-path', str, '/etc/wireguard/'),
    )

    config_path = (
        args.config
        or os.getenv('WIRELOGD_CONFIG')
        or '/etc/wirelogd.cfg'
    )

    config = parse_config(config_struct, config_path, args)

    return config


def setup_logger(config: dict) -> logging.Logger:
    """Set the main logger."""
    log_level = logging.DEBUG if config['debug'] else logging.INFO

    log_format = logging.Formatter('%(levelname)s - %(message)s')

    log_stream = logging.StreamHandler()
    log_stream.setFormatter(log_format)
    log_stream.setLevel(log_level)

    logger = logging.getLogger('wirelogd')
    logger.setLevel(log_level)
    logger.addHandler(log_stream)

    return logger


def main():
    """Run main instructions."""
    try:
        args = setup_parser().parse_args()
        config = setup_config(args)
        log = setup_logger(config)

        run_loop(config, log)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()
