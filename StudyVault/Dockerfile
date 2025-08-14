FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p static

EXPOSE 3000 5000

ENV PYTHONUNBUFFERED=1
ENV MONGODB_URL=mongodb://mongo:27017/

CMD ["python", "main.py"]
