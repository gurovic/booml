from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
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

    gpu_access = models.BooleanField(
        default=False,
    )

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


def teacher_request_upload_path(instance, filename):
    return f"teacher_requests/user_{instance.user_id}/{filename}"


class TeacherAccessRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_PENDING, "На проверке"),
        (STATUS_APPROVED, "Одобрена"),
        (STATUS_REJECTED, "Отклонена"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="teacher_access_requests",
    )
    proof = models.FileField(upload_to=teacher_request_upload_path)
    comment = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    review_comment = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="reviewed_teacher_access_requests",
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Заявка на права учителя"
        verbose_name_plural = "Заявки на права учителя"

    def __str__(self):
        return f"{self.user.username} - {self.status}"

    def approve(self, reviewer=None, comment=None):
        self.status = self.STATUS_APPROVED
        self.reviewed_by = reviewer
        if comment is not None:
            self.review_comment = comment
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "review_comment", "reviewed_at", "updated_at"])

        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

        profile, _ = Profile.objects.get_or_create(user=self.user)
        profile.role = Profile.ROLE_TEACHER
        profile.save(update_fields=["role"])

    def reject(self, reviewer=None, comment=None):
        self.status = self.STATUS_REJECTED
        self.reviewed_by = reviewer
        if comment is not None:
            self.review_comment = comment
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "review_comment", "reviewed_at", "updated_at"])


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
