from .models import Grant

OWNER_ACTIONS = {"read", "edit", "delete", "share"}


def can(user, document, action):
    """The ONLY place that decides document access. Default is deny."""
    if not user.is_authenticated or not user.is_active:
        return False
    if document.owner_id == user.id:
        return action in OWNER_ACTIONS
    grant = Grant.objects.filter(document=document, user=user).first()
    if grant is None:
        return False
    if grant.level == Grant.Level.EDIT:
        return action in {"read", "edit"}
    if grant.level == Grant.Level.READ:
        return action == "read"
    return False