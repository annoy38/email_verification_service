import aiosmtplib
import socket
import random
from typing import Optional, Dict, Any, List
import asyncio


class SMTPChecker:
    def __init__(self, timeout: int = 10, from_email: str = 'verify@example.com'):
        self.timeout = timeout
        self.from_email = from_email

    async def check_smtp(self, email: str, mx_server: str) -> Dict[str, Any]:

        try:
            # Connect to SMTP server with better error handling
            smtp = aiosmtplib.SMTP(
                hostname=mx_server,
                port=25,
                timeout=self.timeout
            )

            await smtp.connect()
            await smtp.ehlo()

            mail_result = await smtp.mail(self.from_email)
            if not mail_result[0] == 250:
                await smtp.quit()
                return {'status': 'error', 'error': f"MAIL command failed: {mail_result[1]}"}

            code, message = await smtp.rcpt(email)

            await smtp.quit()

            if code == 250:
                return {'status': 'valid', 'code': code,
                        'message': message.decode() if hasattr(message, 'decode') else str(message)}
            elif code == 550:
                return {'status': 'invalid', 'code': code,
                        'message': message.decode() if hasattr(message, 'decode') else str(message)}
            else:
                return {'status': 'unknown', 'code': code,
                        'message': message.decode() if hasattr(message, 'decode') else str(message)}

        except (aiosmtplib.SMTPConnectError, aiosmtplib.SMTPTimeoutError,
                aiosmtplib.SMTPServerDisconnected, socket.timeout,
                ConnectionRefusedError, OSError, Exception) as e:
            return {'status': 'error', 'error': str(e)}

    async def verify_email_smtp(self, email: str, mx_servers: List[str]) -> Dict[str, Any]:

        if not mx_servers:
            return {'status': 'no_mx_servers'}

        for mx_server in mx_servers[:2]:
            result = await self.check_smtp(email, mx_server)

            if result['status'] in ['valid', 'invalid']:
                return result

            await asyncio.sleep(1)

        return {'status': 'unknown', 'reason': 'all_servers_failed'}

    async def detect_catch_all(self, domain: str, mx_server: str) -> bool:

        try:

            random_part = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=15))
            test_email = f'{random_part}@{domain}'

            result = await self.check_smtp(test_email, mx_server)
            return result.get('status') == 'valid'
        except Exception:
            return False