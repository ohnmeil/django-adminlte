from django.db import models, transaction
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


# =========================
# Department / UserProfile
# =========================

class Department(models.Model):
    name = models.CharField("Tên phòng ban", max_length=120, unique=True)
    code = models.CharField("Mã phòng ban", max_length=30, unique=True, blank=True, null=True)
    description = models.TextField("Mô tả", blank=True, null=True)
    is_active = models.BooleanField("Hoạt động", default=True)

    class Meta:
        verbose_name = "Phòng ban"
        verbose_name_plural = "Phòng ban"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["name"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('admin:work_department_change', args=[self.id])


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Phòng ban"
    )
    phone = models.CharField("Số điện thoại", max_length=15, blank=True, null=True)
    position = models.CharField("Chức vụ", max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Hồ sơ người dùng"
        verbose_name_plural = "Hồ sơ người dùng"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["department"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.department.name if self.department else 'Chưa có phòng ban'}"


# Gộp tạo & lưu profile vào 1 signal để tránh double trigger
@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    # Tạo nếu thiếu
    if created:
        UserProfile.objects.create(user=instance)
        return
    # Nếu đã có, đảm bảo vẫn save để trigger on_update cần thiết (nhẹ)
    if hasattr(instance, "profile"):
        instance.profile.save()


# =====
# Task
# =====

class Task(models.Model):
    class Status(models.TextChoices):
        NEW = 'NEW', '🆕 Chưa bắt đầu'
        DOING = 'DOING', '🚀 Đang thực hiện'
        PENDING = 'PENDING', '⏳ Chờ phê duyệt'
        DONE = 'DONE', '✅ Đã hoàn thành'
        CANCELLED = 'CANCELLED', '❌ Đã hủy'

    class Priority(models.TextChoices):
        LOW = 'LOW', '📌 Thấp'
        MEDIUM = 'MEDIUM', '📝 Trung bình'
        HIGH = 'HIGH', '🔥 Cao'
        URGENT = 'URGENT', '⚡ Khẩn cấp'

    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Phòng ban", db_index=True
    )
    title = models.CharField("Tên công việc", max_length=255)
    content = models.TextField("Nội dung công việc", blank=True)
    priority = models.CharField(
        "Độ ưu tiên", max_length=10, choices=Priority.choices, default=Priority.MEDIUM, db_index=True
    )

    assigned_by = models.ForeignKey(
        User, related_name='assigned_tasks', on_delete=models.PROTECT, verbose_name="Người giao việc", db_index=True
    )
    assignee = models.ForeignKey(
        User, related_name='tasks', on_delete=models.PROTECT, verbose_name="Người phụ trách", db_index=True
    )
    supporters = models.ManyToManyField(
        User, related_name='supporting_tasks', blank=True, verbose_name="Người hỗ trợ"
    )

    progress = models.PositiveIntegerField("% hoàn thành", default=0,
                                           validators=[MinValueValidator(0), MaxValueValidator(100)])
    status = models.CharField("Trạng thái", max_length=10, choices=Status.choices, default=Status.NEW, db_index=True)

    deadline = models.DateTimeField("Hạn hoàn thành", null=True, blank=True, db_index=True)
    estimated_hours = models.PositiveIntegerField("Giờ ước tính", null=True, blank=True)

    approver = models.ForeignKey(
        User, related_name='approved_tasks', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Người phê duyệt", db_index=True
    )
    approved_at = models.DateTimeField("Thời gian phê duyệt", null=True, blank=True)

    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True, db_index=True)

    class Meta:
        verbose_name = "Công việc"
        verbose_name_plural = "Công việc"
        # Giữ nguyên 2 quyền custom như bạn yêu cầu
        permissions = [
            ('can_approve', 'Có thể phê duyệt công việc'),
            ('view_all_tasks', 'Có thể xem tất cả công việc (read-only)'),
        ]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["assignee", "status"]),
            models.Index(fields=["department", "status"]),
            models.Index(fields=["deadline", "status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse('task_list')

    def save(self, *args, **kwargs):
        """
        - Cho phép DONE != 100% (giữ nguyên nghiệp vụ).
        - Nếu đã có approver và status=DONE mà chưa có approved_at -> set approved_at.
        - Không tự ép trạng thái dựa trên % ở đây (đã xử lý trong TaskUpdate hoặc view).
        """
        if self.status == self.Status.DONE and self.approver and not self.approved_at:
            self.approved_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_overdue(self) -> bool:
        if self.deadline:
            # timezone-aware compare
            now = timezone.localtime(timezone.now())
            dl = timezone.localtime(self.deadline)
            return now > dl and self.status not in (self.Status.DONE, self.Status.CANCELLED)
        return False

    @property
    def days_until_deadline(self):
        if self.deadline:
            delta = timezone.localtime(self.deadline) - timezone.localtime(timezone.now())
            return delta.days
        return None


# ==============
# TaskUpdate / Feedback
# ==============

class TaskUpdate(models.Model):
    """Bản cập nhật tiến độ của nhân viên cho công việc."""
    task = models.ForeignKey(
        Task, related_name='updates', on_delete=models.CASCADE, verbose_name="Công việc"
    )
    user = models.ForeignKey(
        User, related_name='task_updates', on_delete=models.CASCADE, verbose_name="Người cập nhật"
    )
    content = models.TextField("Nội dung cập nhật", blank=True, null=True)
    progress = models.PositiveIntegerField(
        "% hoàn thành", default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    created_at = models.DateTimeField("Thời gian cập nhật", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Cập nhật công việc"
        verbose_name_plural = "Cập nhật công việc"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["task", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"Cập nhật #{self.id} - {self.task.title} - {self.progress}%"

    def save(self, *args, **kwargs):
        """
        Sau khi lưu bản cập nhật:
        - Đồng bộ progress vào Task nếu thay đổi.
        - Nếu Task chưa DONE:
          + progress >= 100  -> PENDING (chờ duyệt)
          + 0 < progress < 100 -> DOING
          + progress == 0 -> NEW
        - Chỉ update các field thay đổi (update_fields) để tối ưu truy vấn.
        """
        with transaction.atomic():
            super().save(*args, **kwargs)
            task = self.task

            fields_to_update = []

            # Đồng bộ % hoàn thành
            if task.progress != self.progress:
                task.progress = self.progress
                fields_to_update.append('progress')

            # Cập nhật trạng thái nếu chưa DONE
            if task.status != Task.Status.DONE:
                if self.progress >= 100 and task.status != Task.Status.PENDING:
                    task.status = Task.Status.PENDING
                    fields_to_update.append('status')
                elif 0 < self.progress < 100 and task.status != Task.Status.DOING:
                    task.status = Task.Status.DOING
                    fields_to_update.append('status')
                elif self.progress == 0 and task.status != Task.Status.NEW:
                    task.status = Task.Status.NEW
                    fields_to_update.append('status')

            if fields_to_update:
                task.updated_at = timezone.now()
                fields_to_update.append('updated_at')
                task.save(update_fields=fields_to_update)


class ManagerFeedback(models.Model):
    """Phản hồi của quản lý cho công việc."""
    task = models.ForeignKey(
        Task, related_name='manager_feedbacks', on_delete=models.CASCADE, verbose_name="Công việc"
    )
    manager = models.ForeignKey(
        User, related_name='manager_feedbacks', on_delete=models.CASCADE, verbose_name="Quản lý"
    )
    content = models.TextField("Nội dung phản hồi")
    created_at = models.DateTimeField("Thời gian phản hồi", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Phản hồi quản lý"
        verbose_name_plural = "Phản hồi quản lý"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["task", "created_at"]),
            models.Index(fields=["manager", "created_at"]),
        ]

    def __str__(self):
        return f"Phản hồi từ {self.manager.username} cho {self.task.title}"

