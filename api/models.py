from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.contenttypes.models import ContentType

# Create your models here.

class CustomUser(AbstractUser):
    """Custom user model extending Django's AbstractUser"""
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Reading history stored as JSON
    reading_history = models.JSONField(default=list, blank=True)
    # Library stored as JSON (manga IDs)
    library = models.JSONField(default=list, blank=True)
    # Last read timestamp
    last_read_at = models.DateTimeField(null=True, blank=True)
    # Total read count (explicitly stored)
    total_read_count = models.IntegerField(default=0)
    # Reading streak
    reading_streak = models.IntegerField(default=0)
    # Reading days (array of date strings)
    reading_days = models.JSONField(default=list, blank=True)
    # Last streak update
    last_streak_update = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'custom_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        permissions = [
            ('can_read_manga', 'Can read manga'),
            ('can_download_manga', 'Can download manga'),
            ('can_manage_users', 'Can manage users'),
            ('can_access_admin_panel', 'Can access admin panel'),
        ]

    def __str__(self):
        return self.email

    @property
    def total_read(self):
        """Return total number of manga read"""
        return self.total_read_count

    @property
    def last_read_date(self):
        """Return last read date formatted"""
        if self.last_read_at:
            return self.last_read_at.strftime('%Y-%m-%d')
        return 'Never'

# Create groups and assign permissions
def setup_groups_and_permissions():
    """Create default groups and assign permissions"""
    # Create groups
    readers_group, _ = Group.objects.get_or_create(name='Readers')
    admin_group, _ = Group.objects.get_or_create(name='Admin')

    # Get content type for CustomUser
    user_content_type = ContentType.objects.get_for_model(CustomUser)

    # Get or create custom permissions
    read_perm, _ = Permission.objects.get_or_create(
        codename='can_read_manga',
        content_type=user_content_type,
        defaults={'name': 'Can read manga'}
    )
    download_perm, _ = Permission.objects.get_or_create(
        codename='can_download_manga',
        content_type=user_content_type,
        defaults={'name': 'Can download manga'}
    )
    manage_users_perm, _ = Permission.objects.get_or_create(
        codename='can_manage_users',
        content_type=user_content_type,
        defaults={'name': 'Can manage users'}
    )
    admin_panel_perm, _ = Permission.objects.get_or_create(
        codename='can_access_admin_panel',
        content_type=user_content_type,
        defaults={'name': 'Can access admin panel'}
    )

    # Assign permissions to Readers group
    readers_group.permissions.add(read_perm, download_perm)

    # Assign all permissions to Admin group
    admin_group.permissions.add(read_perm, download_perm, manage_users_perm, admin_panel_perm)

    return readers_group, admin_group
