from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class PastPaper(models.Model):
    title = models.CharField(max_length=200)
    course_code = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    year = models.CharField(max_length=10)
    semester = models.CharField(max_length=10)
    file = models.FileField(upload_to='papers/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    download_count = models.PositiveIntegerField(default=0)  # NEW FIELD

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # this field


    def __str__(self):
        return f"{self.course_code} - {self.title}"

    def increment_download_count(self):
        self.download_count += 1
        self.save(update_fields=['download_count'])


        

def user_profile_image_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/profile_images/user_<id>/<filename>
    return f'profile_images/user_{instance.user.id}/{filename}'

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = models.ImageField(upload_to=user_profile_image_path, blank=True, null=True)
    bio = models.TextField(blank=True)
    university = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user.username
    


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
