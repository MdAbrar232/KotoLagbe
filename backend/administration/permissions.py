from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Only logged-in staff users may use the administration API."""

    message = "Administrator access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)
