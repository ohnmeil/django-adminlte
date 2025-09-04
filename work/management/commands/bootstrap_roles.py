from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from work.models import Task


class Command(BaseCommand):
    help = "Create default groups and permissions for Task (NhanVien / TruongPhong / KiemToan / QuanTri)"

    def handle(self, *args, **kwargs):
        ct = ContentType.objects.get_for_model(Task)

        def require_perm(codename: str) -> Permission:
            p = Permission.objects.filter(codename=codename, content_type=ct).first()
            if not p:
                raise CommandError(
                    f"Permission '{codename}' chưa tồn tại cho Task.\n"
                    "→ Hãy thêm vào Task.Meta.permissions rồi chạy:\n"
                    "   python manage.py makemigrations && python manage.py migrate"
                )
            return p

        # Core (mặc định của Django model)
        view_task    = require_perm("view_task")
        add_task     = require_perm("add_task")
        change_task  = require_perm("change_task")
        delete_task  = Permission.objects.filter(codename="delete_task", content_type=ct).first()

        # Custom (cần khai báo trong Task.Meta.permissions)
        can_approve     = require_perm("can_approve")
        view_all_tasks  = require_perm("view_all_tasks")

        # Nhóm vai trò
        quantri_g, _   = Group.objects.get_or_create(name="QuanTri")       # admin
        truong_g, _    = Group.objects.get_or_create(name="TruongPhong")   # manager
        nv_g, _        = Group.objects.get_or_create(name="NhanVien")      # employee
        kiemtoan_g, _  = Group.objects.get_or_create(name="KiemToan")      # auditor (read-only all)

        # QuanTri: full perms trên Task
        quantri_g.permissions.set(Permission.objects.filter(content_type=ct))

        # NhanVien: thao tác cơ bản + cập nhật tiến độ (không phản hồi, không duyệt)
        nv_perms = [
            view_task, add_task, change_task,
            # Nếu bạn có model TaskUpdate/ManagerFeedback là model riêng,
            # hãy thêm view_* / add_* tương ứng ở đây.
        ]
        nv_g.permissions.set([p for p in nv_perms if p is not None])

        # TruongPhong: kế thừa NhanVien + duyệt + xem tất cả (+ delete nếu muốn)
        mgr_perms = [
            view_task, add_task, change_task,
            can_approve, view_all_tasks,
        ]
        if delete_task:
            mgr_perms.append(delete_task)
        truong_g.permissions.set([p for p in mgr_perms if p is not None])

        # KiemToan: chỉ xem tất cả (read-only)
        auditor_perms = [view_task, view_all_tasks]
        kiemtoan_g.permissions.set([p for p in auditor_perms if p is not None])

        self.stdout.write(self.style.SUCCESS("✅ Roles updated: NhanVien / TruongPhong / KiemToan / QuanTri"))

