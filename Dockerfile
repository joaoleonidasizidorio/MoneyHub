FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Criar pasta para uploads temporários e estáticos
RUN mkdir -p /app/uploads && chmod 777 /app/uploads
RUN mkdir -p /app/static/uploads/avatars && chmod 777 /app/static/uploads/avatars

EXPOSE 5001

CMD ["python", "app.py"]
