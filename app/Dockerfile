FROM python:3.11.3-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt /app
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

HEALTHCHECK --interval=5s --timeout=5s --retries=3  CMD wget localhost:8000/api/health -q -O - > /dev/null 2>&1

EXPOSE 8000

CMD ["python", "main.py", "--env", "prod"]