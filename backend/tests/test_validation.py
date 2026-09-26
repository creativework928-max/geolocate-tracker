import pytest

from app.services.geolocation_service import (
    InvalidIPAddressError,
    NonPublicIPAddressError,
    is_public_ip,
    parse_ip,
    validate_public_ip,
)


def test_ipv4_validation():
    assert validate_public_ip("8.8.8.8") == "8.8.8.8"


def test_ipv6_validation():
    assert validate_public_ip("2001:4860:4860::8888") == (
        "2001:4860:4860::8888"
    )


@pytest.mark.parametrize(
    "value",
    [
        "not-an-ip",
        "999.999.999.999",
        "",
        "1.2.3",
    ],
)
def test_invalid_ip_rejected(value):
    with pytest.raises(InvalidIPAddressError):
        validate_public_ip(value)


@pytest.mark.parametrize(
    "value",
    [
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "127.0.0.1",
        "169.254.1.1",
        "224.0.0.1",
        "0.0.0.0",
        "::1",
        "fc00::1",
        "fe80::1",
    ],
)
def test_non_public_ip_rejected(value):
    with pytest.raises(NonPublicIPAddressError):
        validate_public_ip(value)


def test_parse_ip_detects_ipv4():
    address = parse_ip("8.8.8.8")
    assert address.version == 4


def test_parse_ip_detects_ipv6():
    address = parse_ip("2001:4860:4860::8888")
    assert address.version == 6


def test_public_ip_predicate():
    assert is_public_ip(parse_ip("1.1.1.1"))
    assert not is_public_ip(parse_ip("127.0.0.1"))