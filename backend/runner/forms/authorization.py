from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from runner.services.captcha import (
    CaptchaConfigError,
    CaptchaValidationError,
    get_client_ip,
    is_captcha_enabled,
    verify_turnstile_token,
)


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'placeholder': 'Введите пароль'}),
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'placeholder': 'Повторите пароль'}),
    )

    ROLE_STUDENT = "student"
    ROLE_TEACHER = "teacher"
    ROLE_CHOICES = (
        (ROLE_STUDENT, "Студент/Ученик"),
        (ROLE_TEACHER, "Учитель"),
    )

    role = forms.ChoiceField(
        label="Роль",
        choices=ROLE_CHOICES,
        initial=ROLE_STUDENT,
        widget=forms.RadioSelect,
    )
    captcha_token = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Имя пользователя'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
        }

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('Пароли не совпадают')
        return password2

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1 and len(password1) < 8:
            raise ValidationError('Пароль должен быть не менее 8 символов')
        return password1

    def clean(self):
        cleaned_data = super().clean()

        if not is_captcha_enabled():
            return cleaned_data

        try:
            verify_turnstile_token(
                cleaned_data.get("captcha_token", ""),
                remote_ip=get_client_ip(self.request),
            )
        except CaptchaValidationError as exc:
            self.add_error("captcha_token", str(exc))
        except CaptchaConfigError:
            raise ValidationError("Капча временно недоступна. Попробуйте позже.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        role_value = self.cleaned_data.get('role', self.ROLE_STUDENT)
        if role_value == self.ROLE_TEACHER:
            user.is_staff = True
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(
        label='Имя пользователя',
        widget=forms.TextInput(attrs={'placeholder': 'Введите имя пользователя'})
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'placeholder': 'Введите пароль'})
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user is None:
                raise forms.ValidationError('Неверное имя пользователя или пароль')
            cleaned_data['user'] = user
        return cleaned_data
