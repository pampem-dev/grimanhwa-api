from django.core.cache import cache
from django.conf import settings
import time

class TrackOnlineUsersMiddleware:
    """Middleware to track all online users (authenticated and anonymous) by IP address"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get client IP address
        ip_address = self.get_client_ip(request)

        if ip_address:
            # Get current online users set
            online_users = cache.get('online_users', {})

            # Update/set this IP's timestamp
            online_users[ip_address] = time.time()

            # Remove old entries (older than timeout)
            timeout = getattr(settings, 'ONLINE_USER_TIMEOUT', 300)  # Default 5 minutes
            current_time = time.time()
            online_users = {
                ip: timestamp for ip, timestamp in online_users.items()
                if current_time - timestamp < timeout
            }

            # Store back in cache
            cache.set('online_users', online_users, timeout + 60)  # Extra buffer

        # Process request
        response = self.get_response(request)

        return response

    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
