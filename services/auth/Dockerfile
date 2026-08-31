# Одинаковый шаблон для всех сервисов — см. services/warehouse/Dockerfile как канонический источник.
# копируется в каждый services/<name>/Dockerfile с одинаковым содержимым.
# Контекст сборки — корень репозитория (нужен доступ к libs/common), см. infra/docker-compose.yml.
FROM python:3.12-slim

WORKDIR /app

# Сначала зависимости — для кэша слоёв Docker при доработке кода
COPY services/auth/pyproject.toml services/auth/poetry.lock* /app/
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction

COPY libs /app/libs
COPY services/auth/app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
