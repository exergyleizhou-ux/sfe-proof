FROM python:3.12-slim
WORKDIR /app
COPY backend/pyproject.toml .
RUN pip install --no-cache-dir .
COPY backend/app app
COPY backend/alembic alembic
COPY backend/alembic.ini .
COPY seed /seed
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
