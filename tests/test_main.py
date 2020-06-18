#!/usr/bin/env pytest

import pytest
import wirelogd.main as wl


def test_booly():
    assert wl.booly("1") is True
    assert wl.booly("on") is True
    assert wl.booly("enable") is True
    assert wl.booly("enabled") is True
    assert wl.booly("true") is True
    assert wl.booly("yes") is True

    assert wl.booly("0") is False
    assert wl.booly("off") is False
    assert wl.booly("false") is False
    assert wl.booly("disable") is False
    assert wl.booly("disabled") is False
    assert wl.booly("no") is False


def test_config_from_defaults():
    s = (("option", str, "default"),)
    c = wl.config_from_defaults(s)

    assert c == {"option": "default"}


def test_config_from_file(tmp_path):
    s = (
        ("str", str, "default"),
        ("int", int, 0),
        ("booly", wl.booly, True),
        ("dash-option", str, "dash"),
    )
    f = tmp_path / "wirelogd.cfg"
    f.write_text("[wirelogd]\nstr = random-string\nint = 34777\nbooly = no\ndash-option = dash")
    c = wl.config_from_file(s, f)

    assert isinstance(c["str"], str)
    assert c["str"] == "random-string"

    assert isinstance(c["int"], int)
    assert c["int"] == 34777

    assert isinstance(c["booly"], bool)
    assert c["booly"] is False

    assert c["dash-option"] == "dash"


def test_config_from_environment():
    import os
    s = (
        ("str", str, "default"),
        ("int", int, 0),
        ("booly", wl.booly, True),
        ("dash-option", str, "dash"),
    )
    os.environ["WIRELOGD_STR"] = "hello world"
    os.environ["WIRELOGD_INT"] = "42"
    os.environ["WIRELOGD_BOOLY"] = "yes"
    os.environ["WIRELOGD_DASH_OPTION"] = "dash"
    c = wl.config_from_environment(s)

    assert isinstance(c["str"], str)
    assert c["str"] == "hello world"

    assert isinstance(c["int"], int)
    assert c["int"] == 42

    assert isinstance(c["booly"], bool)
    assert c["booly"] is True

    assert c["dash-option"] == "dash"


def test_config_from_args():
    from argparse import Namespace
    s = (
        ("str", str, "default"),
        ("int", int, 0),
        ("booly", wl.booly, True),
        ("dash-option", str, "dash"),
    )
    a = Namespace()
    a.str = "onsenfiche"
    a.int = 1789
    a.booly = "enable"
    a.dash_option = "dash"
    c = wl.config_from_args(s, a)

    assert isinstance(c["str"], str)
    assert c["str"] == "onsenfiche"

    assert isinstance(c["int"], int)
    assert c["int"] == 1789

    assert isinstance(c["booly"], bool)
    assert c["booly"] is True

    assert c["dash-option"] == "dash"


def test_parse_config(tmp_path):
    from argparse import Namespace
    import os
    s = (
        ("from-defaults", str, "default"),
        ("from-file", str, "default"),
        ("from-environment", str, "default"),
        ("from-args", str, "default"),
    )
    f = tmp_path / "wirelogd.cfg"
    f.write_text("[wirelogd]\nfrom-file = file\nfrom-environment = file\nfrom-args = file")
    os.environ["WIRELOGD_FROM_ENVIRONMENT"] = "environment"
    os.environ["WIRELOGD_FROM_ARGS"] = "environment"
    a = Namespace()
    a.from_args = "arg"
    c = wl.parse_config(s, f, a)

    assert c["from-defaults"] == "default"
    assert c["from-file"] == "file"
    assert c["from-environment"] == "environment"
    assert c["from-args"] == "arg"


def test_link_wggw(tmp_path):
    import json
    c = {"publicKey": "mypubkey", "name": "test"}
    f = tmp_path / "wggw-client-uuid-like-filename"
    f.write_text(json.dumps(c))
    n1 = wl.link_wggw(tmp_path, c["publicKey"])
    n2 = wl.link_wggw(tmp_path, "non-existant")

    assert n1 == "test"
    assert n2 == "unknown"


def test_peer_dict():
    p = ["wg0", "mypubkey", "", "endpoint", "allowed-ips", "1", "", "", ""]
    d = wl.peer_dict(p, False, None)

    assert isinstance(d, dict)
    assert d["interface"] == "wg0"


def test_peer_link_wggw(tmp_path):
    import json
    c = {"publicKey": "mypubkey", "name": "test"}
    f = tmp_path / "wggw-client-uuid-like-filename"
    f.write_text(json.dumps(c))
    p = ["wg0", "mypubkey", "", "endpoint", "allowed-ips", "1", "", "", ""]
    d = wl.peer_dict(p, True, tmp_path)

    assert isinstance(d, dict)
    assert d["name"] == "test"
    assert d["public-key"] == "mypubkey"


def test_get_peers(fake_process):
    fake_process.register_subprocess(
        ["wg", "show", "all", "dump"],
        stdout=b"wg0\tpubkey\tpsk\tep\tips\t1\t1\t1\t1\n",
    )
    p = wl.get_peers(False, False, None)

    assert isinstance(p, list)
    assert isinstance(p[0], dict)
    assert p[0]["interface"] == "wg0"


def test_get_peers_sudo(fake_process):
    fake_process.register_subprocess(
        ["sudo", "wg", "show", "all", "dump"],
        stdout=b"wg0\tpubkey\tpsk\tep\tips\t1\t1\t1\t1\n",
    )
    p = wl.get_peers(True, False, None)

    assert isinstance(p, list)
    assert isinstance(p[0], dict)
    assert p[0]["interface"] == "wg0"


def test_check_timeout():
    import time
    timeout = 30
    now = {"latest-handshake": time.time()}
    past = {"latest-handshake": time.time() - timeout}

    assert wl.check_timeout(now, timeout) is False
    assert wl.check_timeout(past, timeout) is True


def test_setup_parser():
    import argparse
    p = wl.setup_parser()
    a = p.parse_args(["--config", "/dev/null"])

    assert isinstance(p, argparse.ArgumentParser)
    assert hasattr(a, "config")
    assert a.config == "/dev/null"


def test_setup_logger_debug():
    import logging
    l = wl.setup_logger({"debug": True})

    assert isinstance(l, logging.Logger)
    assert l.isEnabledFor(logging.DEBUG)


def test_setup_logger_info():
    import logging
    l = wl.setup_logger({"debug": False})

    assert isinstance(l, logging.Logger)
    assert l.isEnabledFor(logging.INFO)


def test_setup_config():
    a = wl.setup_parser().parse_args([])
    c = wl.setup_config(a)

    assert isinstance(c, dict)
    assert "debug" in c.keys()
