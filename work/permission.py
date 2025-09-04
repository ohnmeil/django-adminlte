# work/permissions.py

def is_approver(user):
    """Quản lý thực sự: superuser hoặc có quyền can_approve."""
    return user.is_superuser or user.has_perm("work.can_approve")

def same_dept(user, task):
    """User cùng phòng ban với task? (dựa vào profile.department)"""
    udept = getattr(getattr(user, "profile", None), "department", None)
    return bool(udept and task.department_id and udept.id == task.department_id)

def can_view_task(user, task):
    """
    Ai được xem task?
    - Admin / Approver
    - Người giao / Người được giao
    - Supporter
    - Cùng phòng ban
    """
    if user.is_superuser or is_approver(user):
        return True
    if task.assigned_by_id == user.id or task.assignee_id == user.id:
        return True
    if task.supporters.filter(id=user.id).exists():
        return True
    if same_dept(user, task):
        return True
    return False

def can_edit_task(user, task):
    """Sửa task: approver hoặc người giao (khi task CHƯA DONE)."""
    if is_approver(user):
        return True
    if task.assigned_by_id == user.id and task.status != "DONE":
        return True
    return False

def can_delete_task(user, task):
    """Xóa task: approver hoặc người giao (khi task CHƯA DONE)."""
    if is_approver(user):
        return True
    if task.assigned_by_id == user.id and task.status != "DONE":
        return True
    return False

def can_update_progress(user, task):
    """Cập nhật tiến độ: chỉ assignee hoặc approver."""
    return task.assignee_id == user.id or is_approver(user)

def can_set_deadline(user, task):
    """Sửa deadline: approver | người giao | người được giao."""
    return is_approver(user) or task.assigned_by_id == user.id or task.assignee_id == user.id

