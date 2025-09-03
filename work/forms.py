from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Task, TaskUpdate, ManagerFeedback


def is_manager(user):
    return user.is_superuser or user.is_staff or user.has_perm("work.can_approve")


class _BootstrapFormMixin:
    """Thêm class form-control + placeholder tự động cho mọi field."""
    def _beautify(self):
        for name, f in self.fields.items():
            w = f.widget
            # không override HiddenInput
            if isinstance(w, forms.HiddenInput):
                continue
            css = w.attrs.get("class", "")
            if "form-control" not in css and not isinstance(w, (forms.CheckboxInput,)):
                w.attrs["class"] = (css + " form-control").strip()
            # placeholder theo label
            w.attrs.setdefault("placeholder", f.label)


# Định dạng datetime-local: 2025-08-28T13:30
DATETIME_LOCAL_FORMATS = ['%Y-%m-%dT%H:%M']


class DeadlineForm(forms.ModelForm):
    deadline = forms.DateTimeField(
        label="Deadline (ngày & giờ)",
        required=False,
        input_formats=DATETIME_LOCAL_FORMATS,
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": "form-control", "step": 60}
        ),
        help_text="Chọn ngày & giờ kết thúc."
    )

    class Meta:
        model = Task
        fields = ["deadline"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hiển thị deadline theo local time vào input datetime-local
        if self.instance and self.instance.pk and self.instance.deadline:
            local_dt = timezone.localtime(self.instance.deadline)
            self.initial['deadline'] = local_dt.strftime(DATETIME_LOCAL_FORMATS[0])


class TaskForm(_BootstrapFormMixin, forms.ModelForm):
    # Ghi đè deadline để dùng datetime-local trong form create/edit
    deadline = forms.DateTimeField(
        label="Deadline (ngày & giờ)",
        required=False,
        input_formats=DATETIME_LOCAL_FORMATS,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "step": 60})
    )
    estimated_hours = forms.IntegerField(
        label="Giờ ước tính",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"step": 1})
    )

    class Meta:
        model = Task
        fields = [
            "department", "title", "content", "assignee", "supporters",
            "progress", "status", "deadline", "estimated_hours", "priority"
        ]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self._beautify()

        # Hiển thị deadline lên input datetime-local (local time)
        if self.instance and self.instance.pk and self.instance.deadline:
            local_dt = timezone.localtime(self.instance.deadline)
            self.initial['deadline'] = local_dt.strftime(DATETIME_LOCAL_FORMATS[0])

        # Nhân viên: không cho set DONE trực tiếp
        if user and not is_manager(user):
            allowed = [
                ("NEW", "🆕 Chưa bắt đầu"),
                ("DOING", "🚀 Đang thực hiện"),
                ("PENDING", "⏳ Chờ phê duyệt"),
            ]
            self.fields["status"].choices = allowed

            user_dept = getattr(getattr(user, "profile", None), "department", None)
            if user_dept:
                self.fields["assignee"].queryset = User.objects.filter(profile__department=user_dept)
                self.fields["supporters"].queryset = User.objects.filter(profile__department=user_dept)

                # Ẩn field phòng ban, auto set theo user
                self.fields["department"].widget = forms.HiddenInput()
                if not self.instance.pk:
                    self.initial["department"] = user_dept


class ProgressForm(forms.Form):
    content = forms.CharField(
        label="Nội dung cập nhật",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control"})
    )
    progress = forms.IntegerField(
        label="% hoàn thành",
        min_value=0, max_value=100, required=True,
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )


class TaskUpdateForm(forms.ModelForm):
    class Meta:
        model = TaskUpdate
        fields = ["content", "progress"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 3, "class": "form-control", "placeholder": "Nhập cập nhật..."
            }),
            "progress": forms.NumberInput(attrs={
                "class": "form-control", "min": 0, "max": 100
            }),
        }


class ManagerFeedbackForm(forms.ModelForm):
    class Meta:
        model = ManagerFeedback
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 3, "class": "form-control", "placeholder": "Nhập phản hồi..."
            }),
        }

