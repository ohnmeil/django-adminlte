from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [
    path("", views.task_list, name="index"),
    path("tien-do-thuc-hien/", views.task_list, name="task_list"),
    path("task/create/", views.create_task, name="create_task"),
    path("task/<int:pk>/edit/", views.edit_task, name="edit_task"),
    path("task/<int:pk>/approve/", views.approve_task, name="approve_task"),
    path("task/<int:pk>/delete/", views.delete_task, name="delete_task"),
    # cập nhật tiến độ + xem lịch sử
    path("task/<int:pk>/progress/", views.update_progress, name="update_progress"),

    # quản lý phản hồi
    path("task/<int:pk>/feedback/", views.manager_feedback, name="manager_feedback"),
    # mới thêm
    path("task/<int:pk>/updates/", views.task_updates, name="task_updates"),
    path('tasks/<int:pk>/deadline/', views.update_deadline, name='update_deadline'),
    path("calendar/", TemplateView.as_view(template_name="pages/calendar.html"), name="calendar"),
]

