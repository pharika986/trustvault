import os
import uuid
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from .audit import log, verify_chain
from .models import AuditLog, Document, Permission, User
from .permissions import can_access, is_owner

MAX_SIZE = 5 * 1024 * 1024
ALLOWED = {
    "pdf": [b"%PDF"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "docx": [b"PK\x03\x04"],
    "txt": None,
}


def role_required(*roles):
    def deco(view):
        @login_required
        @wraps(view)
        def wrapper(request, *a, **k):
            if request.user.role not in roles:
                log(request, "role_denied", None, "denied", request.path)
                raise Http404
            return view(request, *a, **k)
        return wrapper
    return deco


def get_doc_or_404(request, doc_id, action, log_action):
    doc = Document.objects.filter(id=doc_id).first()
    if not doc or not can_access(request.user, doc, action):
        log(request, log_action, doc_id, "denied")
        raise Http404
    return doc


def get_owned_doc_or_404(request, doc_id, log_action):
    doc = Document.objects.filter(id=doc_id).first()
    if not doc or not is_owner(request.user, doc):
        log(request, log_action, doc_id, "denied")
        raise Http404
    return doc


def validate_upload(f):
    name = os.path.basename(f.name)
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext == "jpeg":
        ext = "jpg"
    if ext not in ALLOWED:
        return None, "File type not allowed (pdf, docx, png, jpg, txt only)"
    if f.size == 0 or f.size > MAX_SIZE:
        return None, "File is empty or larger than 5 MB"
    head = f.read(16)
    f.seek(0)
    sigs = ALLOWED[ext]
    if sigs and not any(head.startswith(s) for s in sigs):
        return None, "File content does not match its extension"
    if ext == "txt":
        try:
            f.read().decode("utf-8")
        except UnicodeDecodeError:
            return None, "Text file must be UTF-8"
        f.seek(0)
    return name[:200], None


@login_required
def index(request):
    docs = Document.objects.filter(is_deleted=False).filter(
        Q(owner=request.user) | Q(grants__user=request.user, grants__can_read=True)
    ).distinct()
    g = request.GET
    if g.get("q"):
        docs = docs.filter(name__icontains=g["q"])
    if g.get("category"):
        docs = docs.filter(category__icontains=g["category"])
    if g.get("owner"):
        docs = docs.filter(owner__username__icontains=g["owner"])
    d_from, d_to = parse_date(g.get("from", "")), parse_date(g.get("to", ""))
    if d_from:
        docs = docs.filter(uploaded_at__date__gte=d_from)
    if d_to:
        docs = docs.filter(uploaded_at__date__lte=d_to)
    return render(request, "vault/index.html", {"docs": docs.select_related("owner").order_by("-uploaded_at")})


@role_required("owner")
def upload(request):
    if request.method == "POST":
        f = request.FILES.get("file")
        if not f:
            messages.error(request, "Choose a file")
        else:
            clean, err = validate_upload(f)
            if err:
                log(request, "upload", None, "denied", err)
                messages.error(request, err)
            else:
                settings.PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
                stored = uuid.uuid4().hex
                with open(settings.PRIVATE_DIR / stored, "wb") as out:
                    for chunk in f.chunks():
                        out.write(chunk)
                doc = Document.objects.create(
                    name=clean, category=request.POST.get("category", "").strip()[:100],
                    owner=request.user, stored_name=stored, size=f.size)
                log(request, "upload", doc.id, "allowed", clean)
                return redirect("index")
    return render(request, "vault/upload.html")


@login_required
def download(request, doc_id):
    doc = get_doc_or_404(request, doc_id, "read", "download")
    path = settings.PRIVATE_DIR / doc.stored_name
    if not path.is_file():
        log(request, "download", doc.id, "denied", "file missing on disk")
        raise Http404
    log(request, "download", doc.id, "allowed", doc.name)
    resp = FileResponse(open(path, "rb"), as_attachment=True, filename=doc.name)
    resp["X-Content-Type-Options"] = "nosniff"
    return resp


@login_required
def edit(request, doc_id):
    doc = get_doc_or_404(request, doc_id, "edit", "edit")
    if request.method == "POST":
        old = f"{doc.name} | {doc.category}"
        name = request.POST.get("name", "").strip()[:200]
        if name:
            doc.name = name
        doc.category = request.POST.get("category", "").strip()[:100]
        doc.save()
        log(request, "edit", doc.id, "allowed", f"{old} -> {doc.name} | {doc.category}")
        return redirect("index")
    return render(request, "vault/edit.html", {"doc": doc})


@login_required
@require_POST
def delete(request, doc_id):
    doc = get_owned_doc_or_404(request, doc_id, "delete")
    doc.is_deleted = True
    doc.save()
    log(request, "delete", doc.id, "allowed", doc.name)
    return redirect("index")


@login_required
def share(request, doc_id):
    doc = get_owned_doc_or_404(request, doc_id, "share")
    if request.method == "POST":
        target = User.objects.filter(username=request.POST.get("username", "").strip(), is_active=True).first()
        level = request.POST.get("level")
        if not target or target.id == request.user.id or level not in ("read", "edit"):
            messages.error(request, "Pick a valid other user and a level")
        else:
            Permission.objects.update_or_create(
                document=doc, user=target,
                defaults={"can_read": True, "can_edit": level == "edit", "granted_by": request.user})
            log(request, "grant", doc.id, "allowed", f"{target.username}:{level}")
            messages.success(request, f"Shared with {target.username} ({level})")
    return render(request, "vault/share.html", {"doc": doc, "grants": doc.grants.select_related("user")})


@login_required
@require_POST
def revoke(request, doc_id, user_id):
    doc = get_owned_doc_or_404(request, doc_id, "revoke")
    p = Permission.objects.filter(document=doc, user_id=user_id).select_related("user").first()
    if p:
        detail = p.user.username
        p.delete()
        log(request, "revoke", doc.id, "allowed", detail)
    return redirect("share", doc_id=doc.id)


@role_required("admin")
def activity(request):
    g = request.GET
    logs = AuditLog.objects.all()
    if g.get("user"):
        logs = logs.filter(username__icontains=g["user"])
    if g.get("action"):
        logs = logs.filter(action=g["action"])
    if g.get("result") in ("allowed", "denied"):
        logs = logs.filter(result=g["result"])
    if g.get("doc"):
        try:
            logs = logs.filter(document_id=uuid.UUID(g["doc"]))
        except ValueError:
            pass
    recent = AuditLog.objects.filter(time__gte=timezone.now() - timedelta(hours=1))
    flagged = list(recent.filter(result="denied").values("username", "ip").annotate(n=Count("id")).filter(n__gte=3))
    heavy = list(recent.filter(action="download", result="allowed").values("username").annotate(n=Count("id")).filter(n__gte=10))
    chain = None
    if g.get("verify"):
        bad = verify_chain()
        chain = "Audit chain intact" if bad is None else f"TAMPERED: chain breaks at row {bad}"
    return render(request, "vault/activity.html",
                  {"logs": logs.order_by("-id")[:200], "flagged": flagged, "heavy": heavy, "chain": chain})
