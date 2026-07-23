from rest_framework import permissions

from .models import UserProfile


STAFF_ROLES = {
    UserProfile.Role.SUPERADMIN,
    UserProfile.Role.PETUGAS,
    UserProfile.Role.VERIFIKATOR,
}


def has_sikap_staff_role(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not user.is_staff:
        return False

    try:
        return user.profile.role in STAFF_ROLES
    except UserProfile.DoesNotExist:
        return False


class IsSIKAPStaff(permissions.BasePermission):
    """Restrict sensitive service records to registered SIKAP-KI staff."""

    message = 'Akses hanya tersedia untuk petugas SIKAP-KI yang berwenang.'

    def has_permission(self, request, view):
        return has_sikap_staff_role(request.user)


class IsSIKAPStaffOrReadOnly(permissions.BasePermission):
    """Allow public reads while limiting content changes to authorized staff."""

    message = 'Perubahan konten hanya dapat dilakukan oleh petugas SIKAP-KI.'

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return has_sikap_staff_role(request.user)
