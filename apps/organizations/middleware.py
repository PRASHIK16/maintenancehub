"""
Organization middleware — injects current org into request.
"""


class OrganizationMiddleware:
    """
    Attaches the user's organization to the request object.
    This avoids repeated DB hits in views when accessing request.org.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.org = request.user.organization
        else:
            request.org = None
        return self.get_response(request)
