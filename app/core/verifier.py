# app/core/verifier.py
import asyncio
from typing import List, Dict, Any
from app.core.validators import EmailValidators
from app.core.dns_check import DNSChecker
from app.core.smtp_check import SMTPChecker
from app.utils.cache import CacheManager
from app.models.results import VerificationResult, VerificationStatus
from config import Config
from app.core.rate_limiter import DomainRateLimiter

# keys and TTLs
MX_CACHE_PREFIX = "mx:"
EMAIL_CACHE_PREFIX = "email_verify:"
MX_CACHE_TTL = 60 * 60 * 24  # 24 hours
RESULT_CACHE_TTL = Config.CACHE_TTL  # from config


class EmailVerifier:
    def __init__(self):
        self.validators = EmailValidators()
        self.dns_checker = DNSChecker(Config.DNS_SERVERS)
        self.smtp_checker = SMTPChecker(timeout=Config.SMTP_TIMEOUT, from_email=Config.FROM_EMAIL)
        self.cache = CacheManager(Config.REDIS_HOST, Config.REDIS_PORT, Config.REDIS_DB)
        self.global_semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_VERIFICATIONS)
        # domain limiter: default 60 calls per 60 seconds (1 per second)
        self.domain_limiter = DomainRateLimiter(default_max_calls=60, window_seconds=60)

    async def _get_cached_mx(self, domain: str) -> List[str]:
        key = MX_CACHE_PREFIX + domain
        cached = await self.cache.get(key)
        if cached and isinstance(cached, dict) and cached.get("mx"):
            return cached.get("mx")
        return []

    async def _set_cached_mx(self, domain: str, mx_servers: List[str]):
        key = MX_CACHE_PREFIX + domain
        await self.cache.set(key, {"mx": mx_servers}, ttl=MX_CACHE_TTL)

    async def verify_single(self, email: str) -> VerificationResult:
        """Verify a single email address with MX caching and domain-level rate limiting."""
        # Normalize
        email = self.validators.normalize_email(email)

        cache_key = EMAIL_CACHE_PREFIX + email
        # check cached final result first
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return VerificationResult(**cached_result)

        # Acquire global semaphore to control total concurrency
        async with self.global_semaphore:
            details = {
                'syntax_valid': False,
                'is_disposable': False,
                'is_role_account': False,
                'domain_verified': False,
                'smtp_verified': False,
                'is_catch_all': False,
                'quality_score': 0
            }

            # Step 1: syntax
            if not self.validators.validate_syntax(email):
                result = self._create_result(email, VerificationStatus.INVALID, 0, details)
                await self.cache.set(cache_key, result.dict(), ttl=RESULT_CACHE_TTL)
                return result
            details['syntax_valid'] = True

            # Step 2: disposable/role
            if self.validators.is_disposable_email(email):
                details['is_disposable'] = True
                result = self._create_result(email, VerificationStatus.DISPOSABLE, 20, details)
                await self.cache.set(cache_key, result.dict(), ttl=RESULT_CACHE_TTL)
                return result

            if self.validators.is_role_account(email):
                details['is_role_account'] = True

            domain = email.split('@', 1)[1].lower()

            # Step 3: MX cache check
            mx_servers = await self._get_cached_mx(domain)
            if not mx_servers:
                # not cached -> check DNS
                domain_result = await self.dns_checker.verify_domain(email)
                if not domain_result['is_valid_domain']:
                    result = self._create_result(email, VerificationStatus.INVALID, 30, details)
                    await self.cache.set(cache_key, result.dict(), ttl=RESULT_CACHE_TTL)
                    return result

                details['domain_verified'] = True
                mx_servers = domain_result.get('mx_servers', [])
                # cache MX servers
                if mx_servers:
                    await self._set_cached_mx(domain, mx_servers)
            else:
                # we have cached MX - set domain_verified
                details['domain_verified'] = True

            # Step 4: SMTP check with domain rate limiting
            if mx_servers:
                # Determine per-domain limit: you can customize mapping for high-volume domains
                # Example: Gmail is aggressive, set low concurrent calls per minute if you want
                per_domain_limit = 60  # default: 60/min
                # Acquire a slot in domain limiter (will wait if limit reached)
                await self.domain_limiter.acquire(domain, max_calls=per_domain_limit)

                # Use SMTP checker (tries multiple MX hosts)
                smtp_result = await self.smtp_checker.verify_email_smtp(email, mx_servers)
                status = smtp_result.get('status')

                if status == 'valid':
                    details['smtp_verified'] = True
                    # check catch-all (quick check only on first MX)
                    try:
                        is_catch_all = await self.smtp_checker.detect_catch_all(domain, mx_servers[0])
                        details['is_catch_all'] = is_catch_all
                    except Exception:
                        is_catch_all = False
                    if is_catch_all:
                        final_status = VerificationStatus.CATCH_ALL
                        quality = 75
                    else:
                        final_status = VerificationStatus.VALID
                        quality = 95
                elif status == 'invalid':
                    final_status = VerificationStatus.INVALID
                    quality = 40
                elif status in ('unknown', 'no_mx_servers', 'error'):
                    final_status = VerificationStatus.RISKY
                    quality = 65
                else:
                    final_status = VerificationStatus.UNKNOWN
                    quality = 50
            else:
                # no mx (rare, but handled)
                final_status = VerificationStatus.RISKY
                quality = 60

            details['quality_score'] = quality
            result = self._create_result(email, final_status, quality, details)

            # Cache final result
            await self.cache.set(cache_key, result.dict(), ttl=RESULT_CACHE_TTL)

            return result

    async def verify_bulk(self, emails: List[str]) -> List[VerificationResult]:
        """Verify multiple emails concurrently but respecting global semaphore and per-domain limits."""
        # create tasks but don't fire them all at once to avoid spike; let asyncio schedule
        tasks = [self.verify_single(email) for email in emails]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results = []
        for res in results:
            if isinstance(res, Exception):
                final_results.append(VerificationResult(
                    email="unknown",
                    status=VerificationStatus.UNKNOWN,
                    quality_score=0,
                    details={'error': str(res)},
                    is_verified=False
                ))
            else:
                final_results.append(res)
        return final_results

    def _create_result(self, email: str, status: VerificationStatus, quality_score: int, details: Dict[str, Any]) -> VerificationResult:
        return VerificationResult(
            email=email,
            status=status,
            quality_score=quality_score,
            details=details,
            is_verified=status in [VerificationStatus.VALID, VerificationStatus.CATCH_ALL]
        )
