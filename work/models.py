from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone


class Department(models.Model):
    name = models.CharField("Tên phòng ban", max_length=120, unique=True)
    code = models.CharField("Mã phòng ban", max_length=30, unique=True, blank=True, null=True)
    description = models.TextField("Mô tả", blank=True, null=True)
    is_active = models.BooleanField("Hoạt động", default=True)

    class Meta:
        verbose_name = "Phòng ban"
        verbose_name_plural = "Phòng ban"
        ordering = ["name"]

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

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.department.name if self.department else 'Chưa có phòng ban'}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()


class Task(models.Model):
    STATUS_CHOICES = [
        ('NEW', '🆕 Chưa bắt đầu'),
        ('DOING', '🚀 Đang thực hiện'),
        ('PENDING', '⏳ Chờ phê duyệt'),
        ('DONE', '✅ Đã hoàn thành'),
        ('CANCELLED', '❌ Đã hủy'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', '📌 Thấp'),
        ('MEDIUM', '📝 Trung bình'),
        ('HIGH', '🔥 Cao'),
        ('URGENT', '⚡ Khẩn cấp'),
    ]

    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Phòng ban"
    )
    title = models.CharField("Tên công việc", max_length=255)
    content = models.TextField("Nội dung công việc", blank=True)
    priority = models.CharField(
        "Độ ưu tiên", max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM'
    )

    assigned_by = models.ForeignKey(
        User, related_name='assigned_tasks', on_delete=models.PROTECT, verbose_name="Người giao việc"
    )
    assignee = models.ForeignKey(
        User, related_name='tasks', on_delete=models.PROTECT, verbose_name="Người phụ trách"
    )
    supporters = models.ManyToManyField(
        User, related_name='supporting_tasks', blank=True, verbose_name="Người hỗ trợ"
    )

    progress = models.PositiveIntegerField("% hoàn thành", default=0)
    status = models.CharField("Trạng thái", max_length=10, choices=STATUS_CHOICES, default='NEW')

    deadline = models.DateTimeField("Hạn hoàn thành", null=True, blank=True)
    estimated_hours = models.PositiveIntegerField("Giờ ước tính", null=True, blank=True)

    approver = models.ForeignKey(
        User, related_name='approved_tasks', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Người phê duyệt"
    )
    approved_at = models.DateTimeField("Thời gian phê duyệt", null=True, blank=True)

    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Cập nhật lúc", auto_now=True)

    class Meta:
        verbose_name = "Công việc"
        verbose_name_plural = "Công việc"
        permissions = [('can_approve', 'Có thể phê duyệt công việc'),('view_all_tasks', 'Có thể xem tất cả công việc (read-only)'),]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse('task_list')

    def save(self, *args, **kwargs):
        """
        Cho phép DONE != 100%.
        Khi đã có approver và status=DONE mà chưa có approved_at -> set approved_at.
        Không tự ép trạng thái dựa trên % ở đây (đã xử lý trong TaskUpdate hoặc view).
        """
        if self.status == 'DONE' and self.approver and not self.approved_at:
            self.approved_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        if self.deadline:
            return timezone.now() > self.deadline and self.status not in ('DONE', 'CANCELLED')
        return False

    @property
    def days_until_deadline(self):
        if self.deadline:
            delta = self.deadline - timezone.now()
            return delta.days
        return None


class TaskUpdate(models.Model):
    """Bản cập nhật tiến độ của nhân viên cho công việc."""
    task = models.ForeignKey(
        Task, related_name='updates', on_delete=models.CASCADE, verbose_name="Công việc"
    )
    user = models.ForeignKey(
        User, related_name='task_updates', on_delete=models.CASCADE, verbose_name="Người cập nhật"
    )
    content = models.TextField("Nội dung cập nhật", blank=True, null=True)
    progress = models.PositiveIntegerField("% hoàn thành", default=0)
    created_at = models.DateTimeField("Thời gian cập nhật", auto_now_add=True)

    class Meta:
        verbose_name = "Cập nhật công việc"
        verbose_name_plural = "Cập nhật công việc"
        ordering = ['-created_at']

    def __str__(self):
        return f"Cập nhật #{self.id} - {self.task.title} - {self.progress}%"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        task = self.task

        fields_to_update = []
        if task.progress != self.progress:
            task.progress = self.progress
            fields_to_update.append('progress')

        # Nếu chưa DONE thì cập nhật trạng thái:
        if task.status != 'DONE':
            if self.progress >= 100:
                if task.status != 'PENDING':
                    task.status = 'PENDING'
                    fields_to_update.append('status')
            elif self.progress > 0:
                if task.status != 'DOING':
                    task.status = 'DOING'
                    fields_to_update.append('status')
            else:
                if task.status != 'NEW':
                    task.status = 'NEW'
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
    created_at = models.DateTimeField("Thời gian phản hồi", auto_now_add=True)

    class Meta:
        verbose_name = "Phản hồi quản lý"
        verbose_name_plural = "Phản hồi quản lý"
        ordering = ['-created_at']

    def __str__(self):
        return f"Phản hồi từ {self.manager.username} cho {self.task.title}"

