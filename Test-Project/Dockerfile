FROM python:3.13.0a6-alpine3.19

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

ENV PORT=5000

ENTRYPOINT ["python", "app.py"]