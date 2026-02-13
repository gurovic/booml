from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ROLE_STUDENT = "student"
    ROLE_TEACHER = "teacher"
    ROLE_CHOICES = (
        (ROLE_STUDENT, "Студент/Ученик"),
        (ROLE_TEACHER, "Учитель"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        primary_key=True
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student'
    )

    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
