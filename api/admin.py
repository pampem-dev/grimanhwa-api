from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Manga, Chapter, Page

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


@admin.register(Manga)
class MangaAdmin(admin.ModelAdmin):
    list_display = ['title', 'chapter_count', 'rating', 'status', 'last_updated', 'created_at']
    list_filter = ['status', 'created_at', 'last_updated']
    search_fields = ['title', 'url']
    ordering = ['-last_updated']
    readonly_fields = ['created_at', 'last_updated']

    fieldsets = (
        ('Basic Info', {'fields': ('title', 'url', 'cover_url')}),
        ('Stats', {'fields': ('rating', 'chapter_count', 'status')}),
        ('Details', {'fields': ('description', 'alternative_titles')}),
        ('Timestamps', {'fields': ('created_at', 'last_updated')}),
    )


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['manga', 'number', 'title', 'is_locked', 'created_at']
    list_filter = ['is_locked', 'created_at', 'manga']
    search_fields = ['title', 'chapter_id', 'manga__title']
    ordering = ['-manga', '-number']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Basic Info', {'fields': ('manga', 'chapter_id', 'title', 'number')}),
        ('Details', {'fields': ('url', 'is_locked')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ['chapter', 'page_number', 'image_url', 'created_at']
    list_filter = ['created_at', 'chapter']
    search_fields = ['chapter__title', 'image_url']
    ordering = ['chapter', 'page_number']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Basic Info', {'fields': ('chapter', 'page_number', 'image_url')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )