from django.contrib import admin
from .models.problem import Problem
from .models.problem_data import ProblemData

class ProblemDataInline(admin.StackedInline):
    model = ProblemData
    extra = 1  # количество пустых форм для добавления
    fields = ('train_csv', 'test_csv', 'metric')  # какие поля показывать
    show_change_link = True  # ссылка на редактирование отдельно

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    inlines = [ProblemDataInline]
