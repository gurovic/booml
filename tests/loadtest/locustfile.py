"""
Нагрузочные тесты для BOOML API (бэкенд на порту 8100)
"""

from locust import HttpUser, task, between


class BOOMLUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Сначала получаем CSRF-токен
        csrf_response = self.client.get("/backend/csrf-token/")
        csrf_token = csrf_response.json().get("csrfToken")

        # Устанавливаем заголовки
        self.client.headers.update({
            "X-CSRFToken": csrf_token,
            "Referer": "http://localhost:8100",
        })

        # Теперь логинимся
        response = self.client.post("/backend/login/", json={
            "username": "a",
            "password": "aaaaaaaa"
        })

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                self.access_token = data["tokens"]["access"]
                self.client.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })

    @task(5)
    def home_page(self):
        self.client.get("/")

    @task(4)
    def login_page(self):
        self.client.get("/login/")

    @task(4)
    def register_page(self):
        self.client.get("/register/")

    @task(1)
    def failed_login(self):
        self.client.post("/backend/login/", json={
            "username": "a",
            "password": "wrong_password"
        })

    @task(3)
    def course_page(self):
        self.client.get("/course/12/")

    @task(3)
    def search(self):
        self.client.get("/backend/search/?q=A&type/")


class UnauthorizedUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def home_page(self):
        self.client.get("/")

    @task(2)
    def login_page(self):
        self.client.get("/login/")

    @task(2)
    def register_page(self):
        self.client.get("/register/")