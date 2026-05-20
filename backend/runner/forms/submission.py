from django import forms


class SubmissionUploadForm(forms.Form):
    """
    Простая форма для загрузки файла с решениями.

    Валидация синхронизирована с DRF-сериализатором, который используется
    API-эндпоинтом создания Submission: ограничение на размер файла и требование
    расширения .csv.
    """

    MAX_FILE_MB = 50

    file = forms.FileField(label="Файл с решением (CSV)", required=False)
    raw_text = forms.CharField(label="Текстовый ответ", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        self.max_file_mb = kwargs.pop("max_file_mb", self.MAX_FILE_MB)
        self.supports_text = kwargs.pop("supports_text", False)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        file_obj = cleaned_data.get("file")
        raw_text = (cleaned_data.get("raw_text") or "").strip()

        if self.supports_text:
            if not raw_text:
                self.add_error("raw_text", "Введите текстовый ответ")
            cleaned_data["raw_text"] = raw_text
        else:
            if not file_obj:
                self.add_error("file", "Загрузите CSV файл")

        return cleaned_data

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if uploaded.size > self.max_file_mb * 1024 * 1024:
            raise forms.ValidationError(f"Файл слишком большой (> {self.max_file_mb}MB)")

        filename = (getattr(uploaded, "name", "") or "").lower()
        if not filename.endswith(".csv"):
            raise forms.ValidationError("Ожидается CSV файл (.csv)")

        return uploaded
