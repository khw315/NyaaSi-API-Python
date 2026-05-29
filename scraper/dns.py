"""
DNS-over-HTTPS (DoH) custom resolver for bypassing ISP blocks.
Patches urllib3.util.connection.create_connection to resolve target hosts
using Quad9 or AdGuard DNS-over-HTTPS servers.
"""

import os
import struct
import socket
import logging
import urllib3.util.connection as urllib3_conn
import requests

logger = logging.getLogger("scraper.dns")

# Hardcoded bootstrap IPs for DoH servers to prevent circular lookups
BOOTSTRAP_IPS = {
    "dns.quad9.net": "9.9.9.9",
    "dns.adguard-dns.com": "94.140.14.14"
}

_original_create_connection = urllib3_conn.create_connection
_in_doh_resolve = False

def build_dns_query(domain: str) -> bytes:
    """Build a standard DNS binary query header + question for Type A, Class IN."""
    header = struct.pack("!HHHHHH", 0, 0x0100, 1, 0, 0, 0)
    question = b""
    for part in domain.split("."):
        if not part:
            continue
        part_bytes = part.encode("utf-8")
        question += struct.pack("B", len(part_bytes)) + part_bytes
    question += b"\x00"
    question += struct.pack("!HH", 1, 1)
    return header + question

def parse_dns_response(data: bytes) -> list[str]:
    """Parse a standard DNS binary response to extract IPv4 addresses (Type A)."""
    if len(data) < 12:
        return []
    id_, flags, qdcount, ancount, nscount, arcount = struct.unpack("!HHHHHH", data[:12])
    offset = 12
    for _ in range(qdcount):
        while True:
            length = data[offset]
            if length == 0:
                offset += 1
                break
            elif (length & 0xC0) == 0xC0:
                offset += 2
                break
            else:
                offset += 1 + length
        offset += 4
        
    ips = []
    for _ in range(ancount):
        if offset >= len(data):
            break
        while True:
            if offset >= len(data):
                break
            length = data[offset]
            if length == 0:
                offset += 1
                break
            elif (length & 0xC0) == 0xC0:
                offset += 2
                break
            else:
                offset += 1 + length
        
        if offset + 10 > len(data):
            break
        type_, class_, ttl, rdlength = struct.unpack("!HHIH", data[offset:offset+10])
        offset += 10
        
        if offset + rdlength > len(data):
            break
        rdata = data[offset:offset+rdlength]
        offset += rdlength
        
        if type_ == 1 and rdlength == 4:
            ip = ".".join(str(b) for b in rdata)
            ips.append(ip)
    return ips

def resolve_doh_adguard(domain: str) -> list[str]:
    """Query AdGuard DNS JSON API."""
    url = f"https://dns.adguard-dns.com/resolve?name={domain}&type=A"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            ips = []
            for answer in data.get("Answer", []):
                if answer.get("type") == 1:
                    ips.append(answer.get("data"))
            return ips
    except Exception as e:
        logger.warning(f"AdGuard DoH failed to resolve {domain}: {e}")
    return []

def resolve_doh_quad9(domain: str) -> list[str]:
    """Query Quad9 standard DoH via POST binary wire format."""
    url = "https://dns.quad9.net/dns-query"
    query_data = build_dns_query(domain)
    headers = {
        "Content-Type": "application/dns-message",
        "Accept": "application/dns-message"
    }
    try:
        resp = requests.post(url, data=query_data, headers=headers, timeout=5)
        if resp.status_code == 200:
            return parse_dns_response(resp.content)
    except Exception as e:
        logger.warning(f"Quad9 DoH failed to resolve {domain}: {e}")
    return []

def resolve_domain(domain: str, provider: str = "quad9") -> str:
    """Resolve domain using configured DoH provider with fallback support."""
    global _in_doh_resolve
    if _in_doh_resolve:
        return None
        
    _in_doh_resolve = True
    try:
        ips = []
        if provider == "adguard":
            ips = resolve_doh_adguard(domain)
            if not ips:
                logger.warning("AdGuard DoH failed, falling back to Quad9...")
                ips = resolve_doh_quad9(domain)
        else:
            ips = resolve_doh_quad9(domain)
            if not ips:
                logger.warning("Quad9 DoH failed, falling back to AdGuard...")
                ips = resolve_doh_adguard(domain)
                
        if ips:
            logger.info(f"Resolved {domain} to {ips[0]} via DoH")
            return ips[0]
    finally:
        _in_doh_resolve = False
    return None

def make_patched_create_connection(provider: str = "quad9"):
    def patched_create_connection(address, *args, **kwargs):
        host, port = address
        # Bypass bootstrapping loops
        if host in BOOTSTRAP_IPS:
            ip = BOOTSTRAP_IPS[host]
            return _original_create_connection((ip, port), *args, **kwargs)
            
        # Only intercept targets nyaa.si and sukebei.nyaa.si
        if host in ("nyaa.si", "sukebei.nyaa.si"):
            ip = resolve_domain(host, provider=provider)
            if ip:
                return _original_create_connection((ip, port), *args, **kwargs)
                
        return _original_create_connection(address, *args, **kwargs)
    return patched_create_connection

def setup_doh(provider: str = "quad9"):
    """Installs the patched connection resolver globally in urllib3."""
    provider = provider.lower()
    logger.info(f"Initializing DNS-over-HTTPS (DoH) engine using provider: {provider}")
    urllib3_conn.create_connection = make_patched_create_connection(provider)
