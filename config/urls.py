# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

admin.site.site_header  = "Quản lý công việc"
admin.site.site_title   = "O³ Invest Admin"
admin.site.index_title  = "Trang điều khiển"

urlpatterns = [
    # Trang chủ → chuyển thẳng tới trang đăng nhập
    path("", lambda request: redirect("login", permanent=False)),

    # Ứng dụng
    path("", include("work.urls")),
    path("", include("apps.pages.urls")),

    # Auth
    path("login/",  auth_views.LoginView.as_view(
        template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),

    # Admin
    path("admin/", admin.site.urls),

    # Password flows
    path("password_reset/",              auth_views.PasswordResetView.as_view(), name="password_reset"),
    path("password_reset/done/",         auth_views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/",      auth_views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/",                  auth_views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("password_change/",             auth_views.PasswordChangeView.as_view(), name="password_change"),
    path("password_change/done/",        auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),
]

