from flask import request
from backend.models.usage import UsageTracking
from typing import Tuple, Optional


class RateLimiter:
    """Rate limiting for anonymous users"""

    def __init__(self, max_submissions_per_year: int = 5):
        self.max_submissions = max_submissions_per_year

    def get_client_identifier(self) -> Tuple[str, str]:
        """
        Get client IP address and fingerprint from request.

        Returns:
            Tuple of (ip_address, fingerprint)
        """
        # Get IP address (handle proxies)
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()

        # Get browser fingerprint from header (set by frontend JS)
        fingerprint = request.headers.get('X-Browser-Fingerprint', 'unknown')

        return ip_address, fingerprint

    def check_limit(self) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Check if anonymous user can make a submission.

        Returns:
            Tuple of (can_submit, error_message, remaining_submissions)
        """
        ip_address, fingerprint = self.get_client_identifier()
        tracking = UsageTracking.get_or_create(ip_address, fingerprint)

        if tracking.can_submit(self.max_submissions):
            remaining = self.max_submissions - tracking.submission_count
            return True, None, remaining
        else:
            return False, f"You have reached the maximum of {self.max_submissions} submissions per year. Please register for unlimited access.", 0

    def record_submission(self):
        """Record a successful submission for the current user"""
        ip_address, fingerprint = self.get_client_identifier()
        tracking = UsageTracking.get_or_create(ip_address, fingerprint)
        tracking.increment_submission()

    def get_remaining_submissions(self) -> int:
        """Get number of remaining submissions for anonymous user"""
        ip_address, fingerprint = self.get_client_identifier()
        tracking = UsageTracking.get_or_create(ip_address, fingerprint)
        return max(0, self.max_submissions - tracking.submission_count)
