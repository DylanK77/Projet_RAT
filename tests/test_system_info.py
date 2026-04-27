from __future__ import annotations

from rat.core.system_info import SystemInfo, collect_system_info


def test_collect_returns_system_info() -> None:
    info = collect_system_info()
    assert isinstance(info, SystemInfo)


def test_system_info_fields_not_empty() -> None:
    info = collect_system_info()
    assert info.hostname
    assert info.username
    assert info.os
    assert info.python


def test_system_info_to_dict_keys() -> None:
    info = collect_system_info()
    d = info.to_dict()
    assert set(d.keys()) == {"hostname", "username", "os", "os_version", "arch", "python"}


def test_system_info_to_dict_values_are_strings() -> None:
    info = collect_system_info()
    for key, val in info.to_dict().items():
        assert isinstance(val, str), f"Field {key!r} should be str, got {type(val)}"


def test_system_info_frozen() -> None:
    import pytest
    info = collect_system_info()
    with pytest.raises(Exception):
        info.hostname = "tampered"  # type: ignore[misc]