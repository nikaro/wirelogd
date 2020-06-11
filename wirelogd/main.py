#!/usr/bin/env python3

"""WireGuard logging."""

import argparse
import configparser
import json
import os
import pathlib
import subprocess
import sys
import time


def getboolean(value: str) -> bool:
    """Return a boolean from values like 'yes', 'no', etc."""

    truthy_values = (
        "1",
        "on",
        "enable",
        "enabled",
        "true",
        "yes",
    )

    return str(value).lower() in truthy_values


def config_from_file(struct: tuple, config_path: str) -> dict:
    """Return dict from configparser."""

    configfile = configparser.ConfigParser()
    if not pathlib.Path(config_path).exists():
        return {}
    configfile.read(config_path)

    return {
        x: y(configfile.get("wirelogd", x))
        for x, y in struct
        if configfile.get("wirelogd", x, fallback=None)
    }


def config_from_environment(struct: tuple) -> dict:
    """Return dict from environment."""

    return {
        x: y(os.environ["WIRELOGD_" + x.upper()])
        for x, y in struct
        if os.getenv("WIRELOGD_" + x.upper().replace("-", "_"))
    }


def config_from_args(struct: tuple, args: argparse.Namespace) -> dict:
    """Return dict from args."""

    return {
        x: y(getattr(args, x))
        for x, y in struct
        if getattr(args, x.replace("-", "_"))
    }


def parse_config(config_path: str, args: argparse.Namespace) -> dict:
    """Return config from: args > environment > configfile > defaults."""

    config: dict = {}
    config_struct = (
        # settings, type to cast
        ("refresh", int),
        ("sudo", getboolean),
        ("timeout", int),
        ("wg-gen-web", getboolean),
    )

    # set defaults
    config.update({
        "refresh": 5,
        "sudo": False,
        "timeout": 300,
        "wg-gen-web": False,
    })

    # set from configuration file
    config_file = config_from_file(config_struct, config_path)
    config.update(config_file)

    # set from environment variables
    config_env = config_from_environment(config_struct)
    config.update(config_env)

    # set from command-line arugments
    config_args = config_from_args(config_struct, args)
    config.update(config_args)

    return config


def link_wggw(pubkey: str) -> str:
    """Return name from wg-gen-web config matching with public key."""

    files = pathlib.Path("/etc/wireguard/").glob("*-*-*-*-*")
    for wggw_conf_path in files:
        with open(wggw_conf_path) as wggw_conf:
            data = json.load(wggw_conf)
        if data["publicKey"] == pubkey:
            return data["name"]

    return ""


def peer_dict(peer: list, wggw: bool) -> dict:
    """Return structured dict from wg peer dump line."""

    fpeer = {
        "interface": peer[0],
        "public-key": peer[1],
        "endpoint": peer[3],
        "allowed-ips": peer[4],
        "latest-handshake": float(peer[5]),
    }

    if wggw:
        fpeer["name"] = link_wggw(fpeer["public-key"])

    return fpeer


def get_peers(sudo: bool, wggw: bool) -> list:
    """Return list of peers, each peer as dict of informations."""

    # run command
    cmd = ["wg", "show", "all", "dump"]
    if sudo:
        cmd.insert(0, "sudo")
    try:
        res = subprocess.run(cmd, capture_output=True, check=True, text=True)
    except Exception:
        sys.exit("error while executing: '{}'".format(" ".join(cmd)))

    # filter and format peers (client peers have 9 columns)
    peers_list = [
        x.split()
        for x in res.stdout.strip().split("\n")
        if x.split() == 9
    ]
    peers = [peer_dict(x, wggw) for x in peers_list]

    return list(peers)


def check_timeout(peer: dict, timeout: int) -> bool:
    """Return True if timeout is reached."""

    # elapsed time between now and latest peer handshake
    elapsed_time = time.time() - peer["latest-handshake"]
    expired = elapsed_time > timeout

    return expired


def run_loop(config):
    """Run loop executing actions and logging results."""

    # intialize activity state tracking
    activity_state: dict = {}

    while True:
        peers = get_peers(config["sudo"], config["wg-gen-web"])
        for peer in peers:
            was_active = activity_state.get(peer["public-key"], False)
            timedout = check_timeout(peer, config["timeout"])
            if was_active and timedout:
                # log inactive connection
                activity_state[peer["public-key"]] = False
                print(peer["public-key"] + " inactive")
            elif not was_active and not timedout:
                # log new active connection
                activity_state[peer["public-key"]] = True
                print(peer["public-key"] + " active from " + peer["endpoint"])
        time.sleep(config.refresh)


def main():
    """Main function."""

    parser = argparse.ArgumentParser(description="Wireguard logging.")
    parser.add_argument(
        "--config", "-c",
        help="path to configuration file [/etc/wireguard/wirelogd.ini]",
    )
    parser.add_argument(
        "--refresh", "-r",
        help="refresh interval in seconds [5]",
        type=int,
    )
    parser.add_argument(
        "--sudo", "-s",
        help="run subprocess commands with sudo",
        action="store_true",
    )
    parser.add_argument(
        "--timeout", "-t",
        help="wireguard handshake timeout in seconds [300]",
        type=int,
    )
    parser.add_argument(
        "--wg-gen-web", "-w",
        help="link peer with its wg-gen-web config",
        action="store_true",
    )
    args = parser.parse_args()

    config_path = (
        args.config
        or os.getenv("WIRELOGD_CONFIG")
        or "/etc/wireguard/wirelogd.ini"
    )
    config = parse_config(config_path, args)

    run_loop(config)


if __name__ == '__main__':
    main()
