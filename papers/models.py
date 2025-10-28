# models.py - Enhanced models for better admin integration
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import os


def user_profile_image_path(instance, filename):
    """Generate upload path for papers"""
    return f'papers/{instance.department}/{instance.year}/{instance.semester}/{filename}'


class PastPaper(models.Model):
    SEMESTER_CHOICES = [
        ('Fall', 'Fall'),
        ('Spring', 'Spring'),
        ('Summer', 'Summer'),
    ]
    
    DEPARTMENT_CHOICES = [
        ('Computer Science', 'Computer Science'),
        ('Mathematics', 'Mathematics'),
        ('Physics', 'Physics'),
        ('Chemistry', 'Chemistry'),
        ('Biology', 'Biology'),
        ('Engineering', 'Engineering'),
        ('Business', 'Business'),
    ]

    title = models.CharField(max_length=200)
    course_code = models.CharField(max_length=20)
    department = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES)
    year = models.IntegerField()
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    file = models.FileField(upload_to=user_profile_image_path)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-uploaded_at']
        unique_together = ['title', 'course_code', 'year', 'semester']
        verbose_name = 'Past Paper'
        verbose_name_plural = 'Past Papers'

    def __str__(self):
        return f"{self.course_code} - {self.title} ({self.year} {self.semester})"

    def get_filename(self):
        """Get clean filename"""
        if self.file:
            return os.path.basename(self.file.name)
        return ""

    def increment_download_count(self):
        """Increment download count"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class PastPaperAttachment(models.Model):
    past_paper = models.ForeignKey(PastPaper, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(upload_to=user_profile_image_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def get_filename(self):
        if self.file:
            return os.path.basename(self.file.name)
        return ""
    
    def __str__(self):
        return f"{self.past_paper.title} - {self.get_filename()}"



class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    university = models.CharField(max_length=200, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'




class Download(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='downloads')
    paper = models.ForeignKey(PastPaper, on_delete=models.CASCADE, related_name='user_downloads')
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-downloaded_at']
        unique_together = ['user', 'paper']  # Prevent duplicate downloads from being recorded

    def __str__(self):
        return f"{self.user.username} downloaded {self.paper.title}"