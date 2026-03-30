FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ARG GIT_SHA=unknown
RUN echo "build=${GIT_SHA}" > /app/.buildstamp

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501", "--server.headless", "true", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false", "--browser.gatherUsageStats", "false"]
