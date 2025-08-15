import os
import zipfile
from django.http import HttpResponse
from django.utils.html import format_html
from django.contrib import admin
from .models import PastPaper, Profile


@admin.register(PastPaper)
class PastPaperAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'course_code', 'department', 'year', 'semester',
        'uploaded_at', 'download_count', 'user', 'file_link'
    )
    list_filter = ('department', 'year', 'semester')
    search_fields = ('title', 'course_code', 'department')
    ordering = ('-uploaded_at',)
    readonly_fields = ('download_count', 'uploaded_at', 'file_preview')
    actions = ['download_selected_as_zip']

    fieldsets = (
        ('Paper Information', {
            'fields': ('title', 'course_code', 'department', 'year', 'semester', 'file', 'file_preview')
        }),
        ('Uploader Information', {
            'fields': ('user',)
        }),
        ('Statistics', {
            'fields': ('download_count', 'uploaded_at')
        }),
    )

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View / Download</a>', obj.file.url)
        return "-"
    file_link.short_description = "File"

    def file_preview(self, obj):
        if obj.file and obj.file.url.lower().endswith('.pdf'):
            return format_html(
                '<iframe src="{}" width="100%" height="400px"></iframe>',
                obj.file.url
            )
        elif obj.file:
            return format_html('<a href="{}" target="_blank">Open File</a>', obj.file.url)
        return "No file uploaded"
    file_preview.short_description = "Preview"

    def download_selected_as_zip(self, request, queryset):
        """
        Bulk action to download selected files as a ZIP.
        """
        if not queryset.exists():
            self.message_user(request, "No files selected.", level='error')
            return

        # Create an in-memory zip
        zip_filename = "past_papers.zip"
        response = HttpResponse(content_type="application/zip")
        response['Content-Disposition'] = f'attachment; filename={zip_filename}'

        with zipfile.ZipFile(response, 'w') as zip_file:
            for paper in queryset:
                if paper.file and os.path.exists(paper.file.path):
                    zip_file.write(paper.file.path, os.path.basename(paper.file.path))

        return response

    download_selected_as_zip.short_description = "Download selected files as ZIP"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'university', 'profile_image')
    search_fields = ('user__username', 'university')
