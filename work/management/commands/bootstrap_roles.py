from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from work.models import Task

class Command(BaseCommand):
    help = "Create default groups and permissions for Task"

    def handle(self, *args, **kwargs):
        ct = ContentType.objects.get_for_model(Task)
        perms = {
            'view': Permission.objects.get(codename='view_task', content_type=ct),
            'add': Permission.objects.get(codename='add_task', content_type=ct),
            'change': Permission.objects.get(codename='change_task', content_type=ct),
            'approve': Permission.objects.get(codename='can_approve', content_type=ct),
        }

        admin_g, _ = Group.objects.get_or_create(name='QuanTri')
        truong_g, _ = Group.objects.get_or_create(name='TruongPhong')
        nv_g, _     = Group.objects.get_or_create(name='NhanVien')

        admin_g.permissions.set(Permission.objects.filter(content_type=ct))  # full Task perms
        truong_g.permissions.set([perms['view'], perms['change'], perms['approve']])
        nv_g.permissions.set([perms['view'], perms['add'], perms['change']])

        self.stdout.write(self.style.SUCCESS('✅ Groups & permissions ready.'))

