import hashlib
from django.db import transaction
from django.utils import timezone
from .models import AuditLog


def _digest(prev, e):
    parts = [prev, e.time.isoformat(), e.user_id, e.username, e.action, e.document_id, e.result, e.detail, e.ip]
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def _ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[-1].strip() if xff else request.META.get("REMOTE_ADDR")


def log(request, action, doc_id=None, result="allowed", detail=""):
    u = request.user if request.user.is_authenticated else None
    with transaction.atomic():
        last = AuditLog.objects.select_for_update().order_by("-id").first()
        prev = last.hash if last else ""
        e = AuditLog(time=timezone.now(), user_id=u.id if u else None,
                     username=u.username if u else "", action=action,
                     document_id=doc_id, result=result, detail=str(detail)[:300],
                     ip=_ip(request), prev_hash=prev)
        e.hash = _digest(prev, e)
        e.save()


def verify_chain():
    """Returns None if intact, else the id of the first bad row."""
    prev = ""
    for e in AuditLog.objects.order_by("id").iterator():
        if e.prev_hash != prev or e.hash != _digest(prev, e):
            return e.id
        prev = e.hash
    return None
