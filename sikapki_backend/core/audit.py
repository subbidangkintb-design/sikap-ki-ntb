"""Pencatatan perubahan data melalui Django Admin."""

from contextvars import ContextVar
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver

from .models import AdminAuditLog


_request_context = ContextVar('sikap_admin_request', default=None)


def set_request(request):
    return _request_context.set(request)


def reset_request(token):
    _request_context.reset(token)


def _admin_request():
    request = _request_context.get()
    if not request or not request.path.startswith('/admin/'):
        return None
    if not getattr(request.user, 'is_staff', False):
        return None
    return request


def _json_value(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray)):
        return f'<{len(value)} bytes>'
    if hasattr(value, 'name') and value.__class__.__name__ in {'FieldFile', 'ImageFieldFile'}:
        return value.name or ''
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _snapshot(instance):
    data = {}
    for field in instance._meta.concrete_fields:
        if field.name == 'id' or field.name.endswith('_ptr'):
            continue
        try:
            value = field.value_from_object(instance)
            if field.is_relation:
                value = getattr(instance, f'{field.name}_id', None)
            data[field.name] = _json_value(value)
        except Exception:
            continue
    return data


def _write_audit(request, instance, action, before, after):
    if isinstance(instance, AdminAuditLog):
        return
    before = before or {}
    after = after or {}
    fields = sorted({*before.keys(), *after.keys()})
    changed = [field for field in fields if before.get(field) != after.get(field)]
    if action == AdminAuditLog.Action.CREATE:
        changed = sorted(after.keys())
    elif action == AdminAuditLog.Action.DELETE:
        changed = sorted(before.keys())
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    ip = forwarded.split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')
    import hashlib
    ip_hash = hashlib.sha256(f'{settings.SECRET_KEY}:{ip}'.encode()).hexdigest() if ip else ''
    AdminAuditLog.objects.create(
        actor=request.user,
        action=action,
        model_label=instance._meta.label,
        object_id=str(instance.pk or ''),
        object_repr=str(instance)[:500],
        changed_fields=changed,
        before_data=before,
        after_data=after,
        ip_hash=ip_hash,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )


@receiver(pre_save, dispatch_uid='sikap_admin_audit_pre_save')
def capture_before_save(sender, instance, **kwargs):
    request = _admin_request()
    if not request or sender is AdminAuditLog:
        return
    old = None
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            pass
    instance._sikap_audit_before = _snapshot(old) if old else {}
    instance._sikap_audit_action = AdminAuditLog.Action.UPDATE if old else AdminAuditLog.Action.CREATE


@receiver(post_save, dispatch_uid='sikap_admin_audit_post_save')
def write_after_save(sender, instance, created, **kwargs):
    request = _admin_request()
    if not request or sender is AdminAuditLog:
        return
    action = AdminAuditLog.Action.CREATE if created else getattr(
        instance, '_sikap_audit_action', AdminAuditLog.Action.UPDATE,
    )
    _write_audit(request, instance, action, getattr(instance, '_sikap_audit_before', {}), _snapshot(instance))


@receiver(pre_delete, dispatch_uid='sikap_admin_audit_pre_delete')
def write_before_delete(sender, instance, **kwargs):
    request = _admin_request()
    if not request or sender is AdminAuditLog:
        return
    _write_audit(request, instance, AdminAuditLog.Action.DELETE, _snapshot(instance), {})
