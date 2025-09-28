from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return '/static/images/default-avatar.png'
