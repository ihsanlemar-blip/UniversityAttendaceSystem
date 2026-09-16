"""Unit tests for Milestone 14 ClientNetworkResolver.

Invariants Tested:
- Trusted reverse proxy chain stripping (right-to-left).
- Anti-spoofing: Untrusted peers cannot spoof source IP via X-Forwarded-For.
- Longest Prefix Match (LPM) and building-scoped network zone resolution.
- IPv4 and IPv6 parsing.
"""

import uuid
from unittest.mock import MagicMock

from starlette.datastructures import Headers

from backend.app.core.constants import NetworkZoneStatus, NetworkZoneType
from backend.app.models.campus_network import CampusNetworkZone
from backend.app.security.resolver import ClientNetworkResolver


def _create_mock_request(client_host: str, headers_dict: dict[str, str] | None = None) -> MagicMock:
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = client_host
    request.headers = Headers(headers_dict or {})
    return request


def _make_zone(
    cidr: str,
    priority: int = 100,
    building_id: uuid.UUID | None = None,
    zone_type: str = NetworkZoneType.CAMPUS_TRUSTED.value,
    status: str = NetworkZoneStatus.ACTIVE.value,
    allow_student_presence: bool = True,
    allow_lecturer_operations: bool = True,
) -> CampusNetworkZone:
    zone = CampusNetworkZone(
        university_id=uuid.uuid4(),
        name=f"Zone-{cidr}",
        code=f"Z-{cidr.replace('/', '_').replace(':', '_')}",
        network_cidr=cidr,
        ip_version=6 if ":" in cidr else 4,
        building_id=building_id,
        zone_type=zone_type,
        status=status,
        priority=priority,
        allow_student_presence=allow_student_presence,
        allow_lecturer_operations=allow_lecturer_operations,
    )
    zone.id = uuid.uuid4()
    return zone


class TestClientNetworkResolver:
    def test_direct_peer_without_headers(self) -> None:
        """Direct connection without XFF returns peer IP directly."""
        req = _create_mock_request("198.51.100.25")
        ip = ClientNetworkResolver.resolve_client_ip(req)
        assert ip == "198.51.100.25"

    def test_untrusted_peer_spoofing_xff(self) -> None:
        """Untrusted direct peer attempting to send X-Forwarded-For is ignored."""
        # 198.51.100.25 is NOT in default TRUSTED_PROXY_CIDRS (127.0.0.1/32, ::1/128)
        req = _create_mock_request(
            "198.51.100.25",
            {"x-forwarded-for": "10.20.30.40, 10.50.60.70"},
        )
        ip = ClientNetworkResolver.resolve_client_ip(req)
        # MUST return the immediate peer IP, ignoring the spoofed header
        assert ip == "198.51.100.25"

    def test_trusted_proxy_single_hop(self) -> None:
        """Single trusted reverse proxy passes through real client IP."""
        req = _create_mock_request(
            "127.0.0.1",
            {"x-forwarded-for": "203.0.113.195"},
        )
        ip = ClientNetworkResolver.resolve_client_ip(req)
        assert ip == "203.0.113.195"

    def test_trusted_proxy_multi_hop_chain(self) -> None:
        """Right-to-left stripping through multiple trusted proxies."""
        # Configure trusted proxies: 127.0.0.1, 10.0.0.0/8
        trusted = ["127.0.0.1/32", "10.0.0.0/8"]
        # Chain: RealClient (198.51.100.55), Proxy1 (10.0.0.2), Proxy2 (127.0.0.1)
        req = _create_mock_request(
            "127.0.0.1",
            {"x-forwarded-for": "198.51.100.55, 10.0.0.2"},
        )
        ip = ClientNetworkResolver.resolve_client_ip(req, trusted_proxies=trusted)
        assert ip == "198.51.100.55"

    def test_trusted_proxy_ipv6(self) -> None:
        """IPv6 client through trusted proxy."""
        req = _create_mock_request(
            "::1",
            {"x-forwarded-for": "2001:db8:cafe::1234"},
        )
        ip = ClientNetworkResolver.resolve_client_ip(req)
        assert ip == "2001:db8:cafe::1234"

    def test_longest_prefix_match(self) -> None:
        """Resolver selects zone with most specific prefix match (LPM)."""
        zone_broad = _make_zone("10.0.0.0/8", priority=50)
        zone_campus = _make_zone("10.20.0.0/16", priority=100)
        zone_lab = _make_zone("10.20.30.0/24", priority=100)

        zones = [zone_broad, zone_campus, zone_lab]

        matched = ClientNetworkResolver.match_network_zone(
            client_ip_str="10.20.30.45",
            available_zones=zones,
        )
        assert matched is not None
        assert matched.id == zone_lab.id

    def test_building_scoped_preference(self) -> None:
        """Building-scoped zone takes precedence over general zone of same prefix."""
        bid = uuid.uuid4()
        zone_general = _make_zone("10.20.30.0/24", priority=100, building_id=None)
        zone_building = _make_zone("10.20.30.0/24", priority=100, building_id=bid)

        zones = [zone_general, zone_building]

        matched = ClientNetworkResolver.match_network_zone(
            client_ip_str="10.20.30.45",
            available_zones=zones,
            target_building_id=bid,
        )
        assert matched is not None
        assert matched.id == zone_building.id

    def test_inactive_zone_ignored(self) -> None:
        """Inactive zones are not matched."""
        zone_inactive = _make_zone("10.20.30.0/24", status=NetworkZoneStatus.DISABLED.value)
        matched = ClientNetworkResolver.match_network_zone(
            client_ip_str="10.20.30.45",
            available_zones=[zone_inactive],
        )
        assert matched is None

    def test_is_ip_in_zone(self) -> None:
        """Verify is_ip_in_zone helper for IPv4 and IPv6."""
        zone_v4 = _make_zone("172.16.0.0/16")
        zone_v6 = _make_zone("2001:db8:85a3::/64")

        assert ClientNetworkResolver.is_ip_in_zone("172.16.5.10", zone_v4) is True
        assert ClientNetworkResolver.is_ip_in_zone("172.17.5.10", zone_v4) is False
        assert ClientNetworkResolver.is_ip_in_zone("2001:db8:85a3::1", zone_v6) is True
        assert ClientNetworkResolver.is_ip_in_zone("2001:db8:85a4::1", zone_v6) is False
