from django.contrib import admin
from .models import Task, Department, UserProfile, TaskUpdate, ManagerFeedback

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "department")
    list_filter  = ("department",)
    search_fields = ("user__username", "user__first_name", "user__last_name")

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title","department","assigned_by","assignee","progress","status","approver","approved_at")
    list_filter  = ("department","status","assigned_by","assignee")
    search_fields = ("title","assignee__username","approver__username")

@admin.register(TaskUpdate)
class TaskUpdateAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "progress", "created_at")
    list_filter = ("user", "task")

@admin.register(ManagerFeedback)
class ManagerFeedbackAdmin(admin.ModelAdmin):
    list_display = ("task", "manager", "created_at")
    list_filter = ("manager", "task")
