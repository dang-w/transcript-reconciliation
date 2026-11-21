"""The pure check of the scan: which bytes are findings. No file system, no gitleaks."""

from reconcile.scan import check_bytes


def rules(data: bytes, denied: list[bytes] | None = None, keys: list[bytes] | None = None) -> set[str]:
    return {rule for rule, _ in check_bytes(data, denied=denied or [], keys=keys or [])}


def test_clean_text_has_no_finding():
    text = b"pytest 9.2.0 on 127.0.0.1, version 3.14.10, /opt/venv/bin/python, 8.8.8.8, $HOME/.local/bin"
    assert rules(text) == set()


def test_home_directory_paths():
    assert rules(b'File "/Users' + b"/someone/x.py") == {"home-directory path"}
    assert rules(b"/home" + b"/user/.cache/x") == {"home-directory path"}


def test_tailnet_address_and_name():
    assert rules(b"connect to 100.101" + b".102.103") == {"tailnet address"}
    assert rules(b"100.63.0.1 and 100.128.0.1") == set()  # outside 100.64/10
    assert rules(b"host box.tail1234.ts" + b".net") == {"tailnet name"}


def test_private_network_addresses():
    for address in (b"192.168" + b".5.1", b"10" + b".0.0.7", b"172" + b".16.4.2", b"172" + b".31.255.255"):
        assert rules(b"nameserver " + address + b"\n") == {"private network address"}, address
    assert rules(b"172" + b".32.0.1") == set()
    assert rules(b"1.10" + b".0.0.7") == set()  # the tail of a longer dotted number is not an address
    assert rules(b"the 192.168" + b".5.x network") == set()


def test_local_host_names_but_not_cgroup_files():
    assert rules(b"ssh printer.lo" + b"cal") == {"local host name"}
    assert rules(b"/sys/fs/cgroup/memory" + b".events.lo" + b"cal") == set()
    assert rules(b"/sys/fs/cgroup/a/b/cpu" + b".stat.lo" + b"cal 0") == set()


def test_denylist_matches_whole_words_only():
    assert rules(b"user=alice", denied=[b"alice"]) == {"denylist"}
    assert rules(b"malice and alice2", denied=[b"alice"]) == set()
    found = check_bytes(b"alice alice", denied=[b"alice"], keys=[])
    assert found[("denylist", "alice")] == 2


def test_key_contents_are_found_and_not_shown():
    found = check_bytes(b"Authorization: Bearer k-123", denied=[], keys=[b"k-123"])
    assert list(found) == [("contents of a local key file", "(not shown)")]
