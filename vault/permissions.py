from .models import Permission


def is_owner(user, doc):
    return user.is_authenticated and not doc.is_deleted and doc.owner_id == user.id


def can_access(user, doc, action):  # action: "read" or "edit"
    if not user.is_authenticated or doc.is_deleted:
        return False
    if doc.owner_id == user.id:
        return True
    p = Permission.objects.filter(document=doc, user=user).first()
    if not p:
        return False
    return p.can_read if action == "read" else p.can_edit
