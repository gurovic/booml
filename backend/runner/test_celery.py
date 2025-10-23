from celery import Celery

app = Celery('test_celery', broker='redis://localhost:6379/0', backend='redis://localhost:6379/1')

@app.task
def add(x, y):
    return x + y

if __name__ == '__main__':
    result = add.delay(4, 6)
    print("Задача отправлена! Ждём результат...")
    print("Результат:", result.get(timeout=10))
