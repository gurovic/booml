from django import forms


class SubmissionUploadForm(forms.Form):
    """
    Простая форма для загрузки файла с решениями.

    Валидация синхронизирована с DRF-сериализатором, который используется
    API-эндпоинтом создания Submission: ограничение на размер файла и требование
    расширения .csv.
    """

    MAX_FILE_MB = 50

    file = forms.FileField(label="Файл с решением (CSV)")

    def __init__(self, *args, **kwargs):
        self.max_file_mb = kwargs.pop("max_file_mb", self.MAX_FILE_MB)
        super().__init__(*args, **kwargs)

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if uploaded.size > self.max_file_mb * 1024 * 1024:
            raise forms.ValidationError(f"Файл слишком большой (> {self.max_file_mb}MB)")

        filename = (getattr(uploaded, "name", "") or "").lower()
        if not filename.endswith(".csv"):
            raise forms.ValidationError("Ожидается CSV файл (.csv)")

        return uploaded
