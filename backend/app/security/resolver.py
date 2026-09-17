"""Client Network Resolver for Milestone 14 Campus Presence & Anti-Cheat Hardening.

Invariants Enforced:
- Server-observed source IP authority (INV-01, INV-03).
- Client-reported IP or SSID headers are NEVER trusted.
- Forwarding headers (X-Forwarded-For, Forwarded) are evaluated ONLY if the direct
  peer socket address matches an explicitly configured TRUSTED_PROXY_CIDRS range.
- Untrusted clients sending spoofed X-Forwarded-For are pinned to their direct peer IP.
- Longest Prefix Match (LPM) CIDR resolution with building-level affinity tie-breaking.
- Strict multi-tenant isolation (zones resolved solely within request university_id).
- Remote VPN subnets excluded from physical presence unless explicitly allowed.
"""

import ipaddress
import logging
import uuid

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.constants import NetworkZoneStatus, NetworkZoneType
from backend.app.models.campus_network import CampusNetworkZone

logger = logging.getLogger(__name__)


class ClientNetworkResolver:
    """Safely determines client source IP and resolves matching CampusNetworkZone."""

    @staticmethod
    def parse_cidr_list(
        cidr_config: str | list[str] | None,
    ) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """Parse comma-delimited or list of CIDR strings into ipaddress network objects."""
        if not cidr_config:
            return []
        if isinstance(cidr_config, str):
            raw_list = [c.strip() for c in cidr_config.split(",") if c.strip()]
        else:
            raw_list = [str(c).strip() for c in cidr_config if str(c).strip()]

        networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for raw in raw_list:
            try:
                # strict=False allows host bits like 192.168.1.5/24 to normalize to 192.168.1.0/24
                net = ipaddress.ip_network(raw, strict=False)
                networks.append(net)
            except ValueError:
                logger.warning(f"Invalid CIDR configuration ignored: {raw}")
        return networks

    @classmethod
    def is_ip_in_cidrs(
        cls,
        ip_str: str,
        trusted_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
    ) -> bool:
        """Check if an IP string falls within any of the configured networks."""
        try:
            ip_obj = ipaddress.ip_address(ip_str.strip())
            return any(ip_obj in net for net in trusted_networks)
        except ValueError:
            return False

    @classmethod
    def extract_effective_client_ip(
        cls,
        request: Request,
        trusted_proxy_cidrs: str | list[str] | None = None,
    ) -> tuple[str, bool, bool]:
        """Extract authoritative effective source IP from request.

        Returns:
            tuple[effective_ip, is_forwarded_from_trusted_proxy, spoof_detected]
        """
        settings = get_settings()
        proxy_config = (
            trusted_proxy_cidrs if trusted_proxy_cidrs is not None else settings.TRUSTED_PROXY_CIDRS
        )
        trusted_proxy_nets = cls.parse_cidr_list(proxy_config)

        # 1. Inspect direct peer socket
        direct_peer = (
            request.client.host.strip() if request.client and request.client.host else "127.0.0.1"
        )
        if direct_peer == "testclient":
            direct_peer = "127.0.0.1"

        # Check for forwarded headers
        xff_header = request.headers.get("X-Forwarded-For", "").strip()
        has_forwarded_headers = bool(xff_header)

        # 2. Check if immediate peer is a trusted proxy
        is_trusted_peer = cls.is_ip_in_cidrs(direct_peer, trusted_proxy_nets)

        if not is_trusted_peer:
            # Untrusted direct peer. Any forwarded header MUST be completely ignored.
            # If the untrusted peer sends an XFF with an internal/campus IP, record spoof attempt.
            spoof_detected = False
            if has_forwarded_headers:
                raw_hops = [h.strip() for h in xff_header.split(",") if h.strip()]
                for hop in raw_hops:
                    try:
                        hop_ip = ipaddress.ip_address(hop)
                        if hop_ip.is_private or hop_ip.is_loopback:
                            spoof_detected = True
                            break
                    except ValueError:
                        continue
            return direct_peer, False, spoof_detected

        # 3. Direct peer is a trusted proxy -> parse X-Forwarded-For chain from right to left
        if not xff_header:
            return direct_peer, False, False

        raw_hops = [h.strip() for h in xff_header.split(",") if h.strip()]
        if not raw_hops:
            return direct_peer, False, False

        # Evaluate right-to-left: strip trusted proxies in the chain
        # The first untrusted IP encountered from the right is the genuine client.
        effective_ip = direct_peer
        found_untrusted = False
        for hop in reversed(raw_hops):
            try:
                ipaddress.ip_address(hop)  # validate syntax
            except ValueError:
                continue

            if not cls.is_ip_in_cidrs(hop, trusted_proxy_nets):
                effective_ip = hop
                found_untrusted = True
                break

        if not found_untrusted and raw_hops:
            # If all hops are trusted proxies, the client is the leftmost hop
            effective_ip = raw_hops[0]

        return effective_ip, True, False

    @classmethod
    def resolve_client_ip(
        cls,
        request: Request,
        trusted_proxies: str | list[str] | None = None,
    ) -> str:
        """Convenience method to return effective client IP string directly."""
        effective_ip, _, _ = cls.extract_effective_client_ip(request, trusted_proxies)
        return effective_ip

    @classmethod
    def is_ip_in_zone(cls, ip_str: str, zone: CampusNetworkZone) -> bool:
        """Check if an IP string falls within a specific CampusNetworkZone's CIDR."""
        try:
            ip_obj = ipaddress.ip_address(ip_str.strip())
            net_obj = ipaddress.ip_network(zone.network_cidr, strict=False)
            return ip_obj in net_obj
        except ValueError:
            return False

    @classmethod
    def match_network_zone(
        cls,
        client_ip_str: str,
        available_zones: list[CampusNetworkZone],
        target_building_id: uuid.UUID | None = None,
        for_lecturer: bool = False,
        allow_vpn: bool = False,
    ) -> CampusNetworkZone | None:
        """Resolve client IP to the most specific active CampusNetworkZone in-memory.

        Invariants:
        - Inactive/disabled zones never match.
        - Longest Prefix Match (LPM) wins.
        - Building match preferred over university-wide.
        - REMOTE_VPN zones excluded unless allow_vpn=True.
        """
        try:
            ip_obj = ipaddress.ip_address(client_ip_str.strip())
        except ValueError:
            return None

        matching_zones: list[tuple[CampusNetworkZone, int, bool]] = []
        for zone in available_zones:
            if zone.status != NetworkZoneStatus.ACTIVE.value:
                continue

            if for_lecturer and not zone.allow_lecturer_operations:
                continue
            if not for_lecturer and not zone.allow_student_presence:
                continue

            if zone.zone_type == NetworkZoneType.REMOTE_VPN.value and not allow_vpn:
                continue

            try:
                net_obj = ipaddress.ip_network(zone.network_cidr, strict=False)
            except ValueError:
                continue

            if ip_obj in net_obj:
                prefix_len = net_obj.prefixlen
                is_building_match = bool(
                    target_building_id and zone.building_id == target_building_id
                )
                matching_zones.append((zone, prefix_len, is_building_match))

        if not matching_zones:
            return None

        matching_zones.sort(
            key=lambda item: (
                1 if item[2] else 0,
                item[1],
                item[0].priority,
                str(item[0].id),
            ),
            reverse=True,
        )
        return matching_zones[0][0]

    @classmethod
    async def match_campus_network_zone(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        client_ip: str,
        preferred_building_id: uuid.UUID | None = None,
        for_lecturer: bool = False,
        allow_vpn: bool = False,
    ) -> CampusNetworkZone | None:
        """Resolve client IP to the most specific active CampusNetworkZone for this university."""
        # Fetch all active zones for the university
        stmt = select(CampusNetworkZone).where(
            CampusNetworkZone.university_id == university_id,
            CampusNetworkZone.status == NetworkZoneStatus.ACTIVE.value,
        )
        if for_lecturer:
            stmt = stmt.where(CampusNetworkZone.allow_lecturer_operations.is_(True))
        else:
            stmt = stmt.where(CampusNetworkZone.allow_student_presence.is_(True))

        res = await db.execute(stmt)
        zones = list(res.scalars().all())

        return cls.match_network_zone(
            client_ip_str=client_ip,
            available_zones=zones,
            target_building_id=preferred_building_id,
            for_lecturer=for_lecturer,
            allow_vpn=allow_vpn,
        )
