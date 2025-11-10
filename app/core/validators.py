import re
import asyncio
from typing import List, Set
import aiohttp


class EmailValidators:
    def __init__(self):
        self.disposable_domains: Set[str] = set()
        self.role_account_prefixes: Set[str] = {
            'admin', 'support', 'info', 'contact', 'sales',
            'help', 'newsletter', 'noreply', 'hello', 'service',
            'marketing', 'news', 'feedback', 'webmaster', 'postmaster'
        }
        self._load_disposable_domains()

    def _load_disposable_domains(self):

        self.disposable_domains = {
            'tempmail.com', 'mailinator.com', 'guerrillamail.com',
            '10minutemail.com', 'throwawaymail.com', 'yopmail.com',
            'fakeinbox.com', 'trashmail.com', 'getairmail.com'
        }

    def validate_syntax(self, email: str) -> bool:

        pattern = r'^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$'

        if not re.match(pattern, email):
            return False

        local_part, domain = email.split('@')

        if len(local_part) > 64:
            return False

        if len(domain) > 253:
            return False

        if '..' in local_part or '..' in domain:
            return False

        return True

    def is_disposable_email(self, email: str) -> bool:

        domain = email.split('@')[1].lower()
        return domain in self.disposable_domains

    def is_role_account(self, email: str) -> bool:

        local_part = email.split('@')[0].lower()
        return any(prefix in local_part for prefix in self.role_account_prefixes)

    def normalize_email(self, email: str) -> str:

        email = email.lower().strip()

        if 'gmail.com' in email or 'googlemail.com' in email:
            local_part, domain = email.split('@')
            local_part = local_part.replace('.', '').split('+')[0]
            return f"{local_part}@{domain}"

        return email