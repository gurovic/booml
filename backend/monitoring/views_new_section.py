class HistoricalMetricsView(APIView):
    """
    View to provide historical system metrics for charts
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Генерируем исторические данные для графиков
        # В реальном приложении здесь будет логика получения данных из базы данных
        
        # Временные метки за последние 30 минут (с шагом 5 минут)
        timestamps = []
        now = datetime.now()
        for i in range(7):
            timestamps.append((now - timedelta(minutes=i*5)).isoformat())

        # Генерируем случайные данные для CPU, памяти и диска
        cpu_data = [random.randint(20, 90) for _ in range(7)]
        memory_data = [random.randint(30, 85) for _ in range(7)]
        disk_data = [random.randint(10, 70) for _ in range(7)]

        # Формируем ответ
        historical_metrics = {
            'timestamps': timestamps[::-1],  # Обратный порядок (от старых к новым)
            'cpu_history': cpu_data[::-1],
            'memory_history': memory_data[::-1],
            'disk_history': disk_data[::-1],
        }

        return Response(historical_metrics)