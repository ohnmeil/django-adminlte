from datetime import datetime
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden

from .forms import (
    TaskForm, ProgressForm, TaskUpdateForm, ManagerFeedbackForm, DeadlineForm
)
from .models import Task, TaskUpdate, ManagerFeedback


def _is_manager(user):
    """Quản lý: superuser, staff hoặc có quyền can_approve."""
    return user.is_superuser or user.is_staff or user.has_perm("work.can_approve")

@login_required
def task_list(request):
    tab = request.GET.get('tab', 'dang')
    dept = request.GET.get('dept', 'my')

    # quyền xem tất cả (hoặc quản lý/staff/superuser)
    can_view_all = (
        request.user.has_perm('work.view_all_tasks') or
        request.user.has_perm('work.can_approve') or
        request.user.is_staff or
        request.user.is_superuser
    )
    readonly_mode = (dept == 'all' and not request.user.has_perm('work.can_approve'))

    mapping = {
        'xong': 'DONE',
        'dang': 'DOING',
        'cho': 'PENDING',
        'chua': 'NEW',
        'tat': None,
    }
    status = mapping.get(tab, 'DOING')

    qs = Task.objects.select_related(
        'department', 'assigned_by', 'assignee', 'approver'
    ).prefetch_related('supporters', 'updates', 'manager_feedbacks')

    if status:
        qs = qs.filter(status=status)

    if dept == 'all':
        if not can_view_all:
            # fallback nếu không có quyền
            dept = 'my'
            # lọc theo phòng ban của user / hoặc chỉ task được giao
            user_dept = getattr(getattr(request.user, 'profile', None), 'department', None)
            if user_dept:
                qs = qs.filter(department=user_dept)
            else:
                qs = qs.filter(assignee=request.user)
        # else: xem tất cả -> không lọc theo phòng ban
    else:
        # 'my' -> phòng ban của tôi (hoặc chỉ task được giao nếu chưa có phòng ban)
        user_dept = getattr(getattr(request.user, 'profile', None), 'department', None)
        if user_dept:
            qs = qs.filter(department=user_dept)
        else:
            qs = qs.filter(assignee=request.user)

    qs = qs.order_by('-created_at')

    return render(request, 'work/task_list.html', {
        'tasks': qs,
        'tab': tab,
        'dept': dept,
        'can_view_all': can_view_all,
        'readonly_mode': readonly_mode,
    })




# =========================================================
# CREATE / EDIT
# =========================================================
@login_required
def create_task(request):
    if request.method == "POST":
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.assigned_by = request.user

            if not _is_manager(request.user):
                if hasattr(request.user, "profile") and request.user.profile.department:
                    task.department = request.user.profile.department
                else:
                    messages.error(
                        request,
                        "Bạn chưa được gán vào phòng ban nào. Vui lòng liên hệ quản lý.",
                    )
                    return render(
                        request,
                        "work/task_form.html",
                        {"form": form, "title": "Tạo công việc"},
                    )

                # nhân viên không set DONE trực tiếp
                if task.status == "DONE":
                    task.status = "PENDING"

            # chuẩn hóa deadline -> aware
            if task.deadline and timezone.is_naive(task.deadline):
                task.deadline = timezone.make_aware(
                    task.deadline, timezone.get_current_timezone()
                )

            task.save()
            form.save_m2m()
            messages.success(request, f"Đã tạo công việc '{task.title}' thành công!")
            return redirect("task_list")
        else:
            messages.error(request, "Vui lòng kiểm tra lại thông tin nhập.")
    else:
        initial = {}
        if (
            not _is_manager(request.user)
            and hasattr(request.user, "profile")
            and request.user.profile.department
        ):
            initial["department"] = request.user.profile.department
        form = TaskForm(initial=initial, user=request.user)

    return render(
        request, "work/task_form.html", {"form": form, "title": "Tạo công việc mới"}
    )


@login_required
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if not (_is_manager(request.user) or task.assigned_by_id == request.user.id):
        raise PermissionDenied("Bạn không có quyền sửa công việc này.")

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)

            if not _is_manager(request.user):
                obj.department = task.department
                if obj.status == "DONE":
                    obj.status = "PENDING"

            if obj.deadline and timezone.is_naive(obj.deadline):
                obj.deadline = timezone.make_aware(
                    obj.deadline, timezone.get_current_timezone()
                )

            obj.save()
            form.save_m2m()
            messages.success(
                request, f"Đã cập nhật công việc '{task.title}' thành công!"
            )
            return redirect("task_list")
        else:
            messages.error(request, "Vui lòng kiểm tra lại thông tin nhập.")
    else:
        form = TaskForm(instance=task, user=request.user)

    return render(
        request,
        "work/task_form.html",
        {"form": form, "title": f"Sửa công việc: {task.title}"},
    )


# =========================================================
# APPROVE / DELETE
# =========================================================
@login_required
@permission_required("work.can_approve", raise_exception=True)
def approve_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == "POST":
        task.status = "DONE"  # DONE không ép = 100%
        task.approver = request.user
        task.approved_at = timezone.now()
        task.save(update_fields=["status", "approver", "approved_at", "updated_at"])
        messages.success(request, f"Đã phê duyệt công việc '{task.title}'!")
    return redirect("task_list")


@login_required
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if not (request.user.has_perm("work.can_approve") or task.assigned_by_id == request.user.id):
        raise PermissionDenied("Bạn không có quyền xóa công việc này.")

    if request.method == "POST":
        title = task.title
        task.delete()
        messages.success(request, f"Đã xóa công việc '{title}' thành công!")
        return redirect("task_list")

    return render(request, "work/task_confirm_delete.html", {"task": task})


# =========================================================
# PROGRESS & FEEDBACK
# =========================================================
@login_required
def update_progress(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if task.assignee != request.user and not _is_manager(request.user):
        raise PermissionDenied("Bạn không có quyền cập nhật tiến độ công việc này.")

    if request.method == "POST":
        form = ProgressForm(request.POST)
        if form.is_valid():
            upd = TaskUpdate.objects.create(
                task=task,
                user=request.user,
                progress=form.cleaned_data["progress"],
                content=form.cleaned_data.get("content", ""),
            )

            if task.status != "DONE":
                new_progress = upd.progress
                if new_progress >= 100:
                    task.status = "PENDING"
                elif new_progress > 0:
                    task.status = "DOING"
                else:
                    task.status = "NEW"
                task.progress = new_progress
                task.updated_at = timezone.now()
                task.save(update_fields=["progress", "status", "updated_at"])

            messages.success(request, "Đã cập nhật tiến độ thành công!")
            return redirect("task_list")
        else:
            messages.error(request, "Vui lòng kiểm tra lại thông tin nhập.")
    else:
        form = ProgressForm(initial={"progress": task.progress})

    updates = task.updates.all().select_related("user").order_by("-created_at")
    feedbacks = task.manager_feedbacks.all().select_related("manager").order_by(
        "-created_at"
    )

    return render(
        request,
        "work/update_progress.html",
        {"task": task, "form": form, "updates": updates, "feedbacks": feedbacks},
    )


@login_required
@permission_required("work.can_approve", raise_exception=True)
def manager_feedback(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if request.method == "POST":
        form = ManagerFeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.task = task
            fb.manager = request.user
            fb.save()

            task.updated_at = timezone.now()
            task.save(update_fields=["updated_at"])

            messages.success(request, "Đã gửi phản hồi thành công!")
            return redirect("task_list")
        else:
            messages.error(request, "Vui lòng nhập nội dung phản hồi.")
    else:
        form = ManagerFeedbackForm()

    feedbacks = task.manager_feedbacks.all().select_related("manager").order_by(
        "-created_at"
    )

    return render(
        request,
        "work/manager_feedback.html",
        {"task": task, "feedbacks": feedbacks, "form": form},
    )


@login_required
def task_updates(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if task.assignee != request.user and not _is_manager(request.user):
        raise PermissionDenied("Bạn không có quyền xem lịch sử cập nhật công việc này.")

    updates = task.updates.select_related("user").all().order_by("-created_at")

    if request.method == "POST":
        if task.assignee != request.user and not _is_manager(request.user):
            return HttpResponseForbidden("Bạn không có quyền cập nhật công việc này.")

        form = TaskUpdateForm(request.POST)
        if form.is_valid():
            upd = form.save(commit=False)
            upd.task = task
            upd.user = request.user
            upd.save()

            if task.status != "DONE":
                new_progress = upd.progress
                if new_progress >= 100:
                    task.status = "PENDING"
                elif new_progress > 0:
                    task.status = "DOING"
                else:
                    task.status = "NEW"
                task.progress = new_progress
                task.updated_at = timezone.now()
                task.save(update_fields=["progress", "status", "updated_at"])

            messages.success(request, "Đã cập nhật tiến độ thành công!")
            return redirect("task_list")
        else:
            messages.error(request, "Vui lòng kiểm tra lại thông tin nhập.")
    else:
        form = TaskUpdateForm(initial={"progress": task.progress})

    return render(
        request, "work/task_updates.html", {"task": task, "updates": updates, "form": form}
    )


# =========================================================
# DEADLINE (có giờ)
# =========================================================
@login_required
def update_deadline(request, pk):
    """
    Cập nhật deadline (ngày & giờ).
    Quyền: quản lý HOẶC người giao việc HOẶC người được giao.
    """
    task = get_object_or_404(Task, pk=pk)

    if not (
        _is_manager(request.user)
        or task.assigned_by_id == request.user.id
        or task.assignee_id == request.user.id
    ):
        raise PermissionDenied("Bạn không có quyền sửa deadline công việc này.")

    if request.method == "POST":
        form = DeadlineForm(request.POST, instance=task)
        if form.is_valid():
            dl = form.cleaned_data.get("deadline")
            if dl:
                if timezone.is_naive(dl):
                    dl = timezone.make_aware(dl, timezone.get_current_timezone())
                task.deadline = dl
            else:
                task.deadline = None

            task.updated_at = timezone.now()
            task.save(update_fields=["deadline", "updated_at"])
            messages.success(request, "Đã cập nhật deadline thành công.")
            return redirect("task_list")
        else:
            messages.error(request, "Vui lòng kiểm tra lại deadline.")
    else:
        initial = {}
        if task.deadline:
            local_dt = timezone.localtime(task.deadline)
            initial["deadline"] = local_dt.strftime("%Y-%m-%dT%H:%M")
        form = DeadlineForm(instance=task, initial=initial)

    return render(
        request, "work/deadline_form.html", {"form": form, "task": task, "title": "Cập nhật deadline"}
    )

