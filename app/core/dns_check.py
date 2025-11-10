import dns.resolver
import dns.asyncresolver
from typing import Tuple, List, Optional, Dict
import asyncio


class DNSChecker:
    def __init__(self, dns_servers: List[str] = None):
        self.resolver = dns.asyncresolver.Resolver()
        if dns_servers:
            self.resolver.nameservers = dns_servers

    async def check_mx_records(self, domain: str) -> Tuple[bool, List[str]]:

        try:
            answers = await self.resolver.resolve(domain, 'MX')
            mx_servers = [str(r.exchange).rstrip('.') for r in answers]
            return True, mx_servers
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN,
                dns.resolver.NoNameservers, dns.resolver.Timeout):
            return False, []

    async def check_domain_exists(self, domain: str) -> bool:

        try:
            await self.resolver.resolve(domain, 'A')
            return True
        except:
            try:
                await self.resolver.resolve(domain, 'AAAA')
                return True
            except:
                return False

    async def verify_domain(self, email: str) -> Dict[str, any]:

        domain = email.split('@')[1]

        has_mx, mx_servers = await self.check_mx_records(domain)
        domain_exists = await self.check_domain_exists(domain)

        return {
            'has_mx_records': has_mx,
            'mx_servers': mx_servers,
            'domain_exists': domain_exists,
            'is_valid_domain': has_mx or domain_exists
        }