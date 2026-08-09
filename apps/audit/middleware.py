"""
Audit log middleware — captures IP address and user agent for audit logs.
"""


class AuditLogMiddleware:
    """Attaches metadata needed for audit logging to the request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.audit_ip = self._get_client_ip(request)
        request.audit_user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
        return self.get_response(request)

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
