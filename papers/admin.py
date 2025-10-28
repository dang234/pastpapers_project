import os
import zipfile
from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.html import format_html
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe
from django.db import transaction
from django.template.response import TemplateResponse
import logging

from .models import PastPaper, PastPaperAttachment, Profile

logger = logging.getLogger(__name__)


class BulkUploadForm(forms.Form):
    """Form for bulk upload functionality"""
    department = forms.ChoiceField(
        choices=[
            ('', 'Select Department'),
            ('Computer Science', 'Computer Science'),
            ('Mathematics', 'Mathematics'),
            ('Physics', 'Physics'),
            ('Chemistry', 'Chemistry'),
            ('Biology', 'Biology'),
            ('Engineering', 'Engineering'),
            ('Business', 'Business'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    year = forms.ChoiceField(
        choices=[(str(year), str(year)) for year in range(2015, 2026)],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    semester = forms.ChoiceField(
        choices=[
            ('', 'Select Semester'),
            ('Fall', 'Fall'),
            ('Spring', 'Spring'),
            ('Summer', 'Summer'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


# ADD this inline for multiple files
class PastPaperAttachmentInline(admin.TabularInline):
    model = PastPaperAttachment
    extra = 2  # Show 2 empty file upload fields
    fields = ('file',)
    verbose_name = "Additional File"
    verbose_name_plural = "Additional Files (Upload multiple files here)"


@admin.register(PastPaper)
class PastPaperAdmin(admin.ModelAdmin):
    # ADD the inline to your existing admin
    inlines = [PastPaperAttachmentInline]
    
    # Keep all your existing configurations
    list_display = (
        'title', 'course_code', 'department', 'year', 'semester',
        'uploaded_at', 'download_count', 'user', 'file_link', 'file_size', 'total_files'
    )
    list_filter = ('department', 'year', 'semester', 'uploaded_at')
    search_fields = ('title', 'course_code', 'department', 'user__username')
    ordering = ('-uploaded_at',)
    readonly_fields = ('download_count', 'uploaded_at', 'file_preview', 'file_size')
    actions = ['download_selected_as_zip', 'reset_download_count']
    list_per_page = 25

    fieldsets = (
        ('Paper Information', {
            'fields': ('title', 'course_code', 'department', 'year', 'semester', 'file', 'file_preview')
        }),
        ('Uploader Information', {
            'fields': ('user',)
        }),
        ('Statistics', {
            'fields': ('download_count', 'uploaded_at', 'file_size')
        }),
    )

    # Keep all your existing methods and ADD this new one
    def total_files(self, obj):
        """Show total number of files (main + attachments)"""
        count = 1 if obj.file else 0
        count += obj.attachments.count()
        return f"{count} file{'s' if count != 1 else ''}"
    total_files.short_description = "Total Files"

    def get_urls(self):
        """Add bulk upload URL to admin"""
        urls = super().get_urls()
        custom_urls = [
            path('bulk-upload/', self.bulk_upload_view, name='papers_pastpaper_bulk_upload'),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        """Add bulk upload button to changelist view"""
        extra_context = extra_context or {}
        extra_context['bulk_upload_url'] = reverse('admin:papers_pastpaper_bulk_upload')
        return super().changelist_view(request, extra_context)

    def bulk_upload_view(self, request):
        """Handle bulk upload functionality"""
        if request.method == 'POST':
            form = BulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                success_count, error_messages = self.process_bulk_upload(request, form)
                
                if success_count > 0:
                    messages.success(request, f'Successfully uploaded {success_count} papers!')
                
                for error in error_messages:
                    messages.error(request, error)
                
                if success_count > 0 and not error_messages:
                    return HttpResponseRedirect(reverse('admin:papers_pastpaper_changelist'))
        else:
            form = BulkUploadForm()

        context = {
            'form': form,
            'title': 'Bulk Upload Papers',
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request),
        }
        
        return TemplateResponse(request, 'admin/bulk_upload.html', context)

    def process_bulk_upload(self, request, form):
        """Process the bulk upload"""
        department = form.cleaned_data['department']
        year = int(form.cleaned_data['year'])
        semester = form.cleaned_data['semester']
        files = request.FILES.getlist('files')
        
        success_count = 0
        error_messages = []
        
        if not files:
            error_messages.append('No files were uploaded.')
            return success_count, error_messages

        course_codes = request.POST.getlist('course_codes[]')
        titles = request.POST.getlist('titles[]')
        
        if len(files) != len(course_codes) or len(files) != len(titles):
            error_messages.append('Mismatch between files and metadata.')
            return success_count, error_messages

        try:
            with transaction.atomic():
                for i, file in enumerate(files):
                    if not file.name.lower().endswith('.pdf'):
                        error_messages.append(f'File "{file.name}" is not a PDF.')
                        continue
                    
                    course_code = course_codes[i].strip() if i < len(course_codes) else ''
                    title = titles[i].strip() if i < len(titles) else file.name.replace('.pdf', '')
                    
                    if not course_code:
                        error_messages.append(f'Course code missing for file "{file.name}".')
                        continue
                    
                    if PastPaper.objects.filter(
                        title=title, 
                        course_code=course_code, 
                        year=year,
                        semester=semester
                    ).exists():
                        error_messages.append(f'Duplicate paper: "{title}".')
                        continue
                    
                    PastPaper.objects.create(
                        title=title,
                        course_code=course_code,
                        department=department,
                        year=year,
                        semester=semester,
                        file=file,
                        user=request.user
                    )
                    
                    success_count += 1
                    logger.info(f"Bulk uploaded: {title} by {request.user.username}")
        
        except Exception as e:
            error_messages.append(f'Error during upload: {str(e)}')
            logger.error(f"Bulk upload error: {str(e)}")
        
        return success_count, error_messages

    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank" class="button">View / Download</a>', 
                obj.file.url
            )
        return "-"
    file_link.short_description = "File"

    def file_size(self, obj):
        """Display file size in human readable format"""
        if obj.file:
            try:
                size = obj.file.size
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024.0:
                        return f"{size:.1f} {unit}"
                    size /= 1024.0
                return f"{size:.1f} TB"
            except:
                return "Unknown"
        return "-"
    file_size.short_description = "File Size"

    def file_preview(self, obj):
        if obj.file and obj.file.url.lower().endswith('.pdf'):
            return format_html(
                '''
                <div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0;">
                    <iframe src="{}" width="100%" height="400px" frameborder="0"></iframe>
                    <p><a href="{}" target="_blank" class="button">Open in New Tab</a></p>
                </div>
                ''',
                obj.file.url, obj.file.url
            )
        elif obj.file:
            return format_html('<a href="{}" target="_blank" class="button">Open File</a>', obj.file.url)
        return "No file uploaded"
    file_preview.short_description = "Preview"

    def download_selected_as_zip(self, request, queryset):
        """Bulk action to download selected files as ZIP - ENHANCED to include attachments"""
        if not queryset.exists():
            self.message_user(request, "No files selected.", level=messages.ERROR)
            return

        zip_filename = "past_papers.zip"
        response = HttpResponse(content_type="application/zip")
        response['Content-Disposition'] = f'attachment; filename={zip_filename}'

        with zipfile.ZipFile(response, 'w') as zip_file:
            for paper in queryset:
                # Add main file
                if paper.file and os.path.exists(paper.file.path):
                    filename = f"{paper.course_code}_{paper.year}_{paper.semester}_{paper.title}.pdf"
                    filename = filename.replace('/', '_').replace('\\', '_')
                    zip_file.write(paper.file.path, filename)
                
                # Add attachment files
                for attachment in paper.attachments.all():
                    if attachment.file and os.path.exists(attachment.file.path):
                        filename = f"{paper.course_code}_{paper.year}_{paper.semester}_{paper.title}_attachment_{attachment.id}.pdf"
                        filename = filename.replace('/', '_').replace('\\', '_')
                        zip_file.write(attachment.file.path, filename)

        self.message_user(request, f"Downloaded files from {queryset.count()} papers as ZIP.")
        return response
    download_selected_as_zip.short_description = "Download selected files as ZIP"

    def reset_download_count(self, request, queryset):
        """Reset download count for selected papers"""
        count = queryset.update(download_count=0)
        self.message_user(request, f"Reset download count for {count} papers.")
    reset_download_count.short_description = "Reset download count"

    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'university', 'profile_image', 'created_at')
    search_fields = ('user__username', 'university')
    list_filter = ('university', 'created_at')
    readonly_fields = ('created_at',)

    def profile_image(self, obj):
        if obj.profile_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%;" />',
                obj.profile_image.url
            )
        return "No image"
    profile_image.short_description = "Image"


admin.site.site_header = "Past Papers Admin"
admin.site.site_title = "Past Papers Admin"
admin.site.index_title = "Welcome to Past Papers Administration"