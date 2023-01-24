FROM python:3.10-slim

WORKDIR /usr/src/app

EXPOSE 80

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "./run.py"]