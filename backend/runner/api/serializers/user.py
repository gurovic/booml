from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import serializers

from ...models.profile import Profile
from .submissions import SubmissionReadSerializer


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'full_name', 'role')

    def get_full_name(self, obj):
        return f"{obj.last_name} {obj.first_name}".strip() or obj.username

    def get_role(self, obj):
        if obj.is_staff:
            return 'teacher'
        return 'student'


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('user', 'username', 'email', 'first_name', 'last_name',
                  'full_name', 'role', 'avatar', 'avatar_url')

    def get_full_name(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}".strip() or obj.user.username

    def get_role(self, obj):
        if obj.user.is_staff:
            return 'teacher'
        return 'student'

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class ProfileDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    recent_submissions = serializers.SerializerMethodField()
    activity_heatmap = serializers.SerializerMethodField()
    ACTIVITY_HEATMAP_DAYS = 365

    class Meta:
        model = Profile
        fields = ('user', 'username', 'email', 'first_name', 'last_name',
                  'full_name', 'role', 'avatar', 'avatar_url',
                  'recent_submissions', 'activity_heatmap')

    def get_full_name(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}".strip() or obj.user.username

    def get_role(self, obj):
        if obj.user.is_staff:
            return 'teacher'
        return 'student'

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    def get_recent_submissions(self, obj):
        submissions = obj.user.submissions.all().order_by('-submitted_at')[:4]
        return SubmissionReadSerializer(submissions, many=True, context=self.context).data

    def _resolve_activity_level(self, count, max_count):
        if count <= 0:
            return 0
        if max_count <= 1:
            return 4

        ratio = count / max_count
        if ratio >= 0.75:
            return 4
        if ratio >= 0.5:
            return 3
        if ratio >= 0.25:
            return 2
        return 1

    def _calculate_streaks(self, days):
        best_streak = 0
        rolling_streak = 0

        for day in days:
            if day['count'] > 0:
                rolling_streak += 1
                best_streak = max(best_streak, rolling_streak)
            else:
                rolling_streak = 0

        current_streak = 0
        for day in reversed(days):
            if day['count'] > 0:
                current_streak += 1
            else:
                break

        return current_streak, best_streak

    def get_activity_heatmap(self, obj):
        today = timezone.localdate()
        current_year = today.year

        joined_at = getattr(obj.user, 'date_joined', None)
        if joined_at is not None:
            if timezone.is_aware(joined_at):
                registration_year = timezone.localtime(joined_at).year
            else:
                registration_year = joined_at.year
        else:
            registration_year = current_year
        registration_year = min(registration_year, current_year)

        available_years = list(range(registration_year, current_year + 1))
        requested_year = self.context.get('activity_year')
        is_year_mode = isinstance(requested_year, int) and requested_year in available_years

        selected_year = requested_year if is_year_mode else None
        period_type = 'year' if is_year_mode else 'rolling_365'

        if is_year_mode:
            start_date = date(selected_year, 1, 1)
            end_date = date(selected_year, 12, 31)
            if selected_year == current_year:
                end_date = today
        else:
            end_date = today
            start_date = end_date - timedelta(days=self.ACTIVITY_HEATMAP_DAYS - 1)

        submissions_by_day = (
            obj.user.submissions
            .filter(submitted_at__date__gte=start_date, submitted_at__date__lte=end_date)
            .annotate(day=TruncDate('submitted_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        counts_by_day = {item['day']: int(item['count']) for item in submissions_by_day}

        days = []
        total_submissions = 0
        active_days = 0
        max_count = 0

        current_date = start_date
        while current_date <= end_date:
            count = counts_by_day.get(current_date, 0)
            total_submissions += count
            if count > 0:
                active_days += 1
                max_count = max(max_count, count)
            days.append({
                'date': current_date.isoformat(),
                'count': count,
            })
            current_date += timedelta(days=1)

        for day in days:
            day['level'] = self._resolve_activity_level(day['count'], max_count)

        current_streak, best_streak = self._calculate_streaks(days)

        return {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'period_type': period_type,
            'selected_year': selected_year,
            'available_years': available_years,
            'total_submissions': total_submissions,
            'active_days': active_days,
            'max_count': max_count,
            'current_streak': current_streak,
            'best_streak': best_streak,
            'days': days,
        }
