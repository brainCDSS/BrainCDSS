from apps.accounts.api.permissions import (
    SystemAdminPermission,
)


class AuditReadPermission(
    SystemAdminPermission
):
    message = "AUDIT_ACCESS_FORBIDDEN"
