from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

# Register your models here.
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'is_active', 'is_staff', 'created_at', 'total_read_count', 'history_size', 'library_size']
    list_filter = ['is_active', 'is_staff', 'created_at']
    search_fields = ['email', 'username']
    ordering = ['-created_at']

    fieldsets = UserAdmin.fieldsets + (
        ('Reading Stats', {'fields': ('total_read_count', 'history_size', 'library_size', 'reading_history', 'library', 'last_read_at')}),
        (None, {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ['created_at', 'updated_at', 'total_read_count', 'history_size', 'library_size']

    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('email',)}),
    )

    def history_size(self, obj):
        return len(obj.reading_history) if obj.reading_history else 0
    history_size.short_description = 'History Size'

    def library_size(self, obj):
        return len(obj.library) if obj.library else 0
    library_size.short_description = 'Library Size'