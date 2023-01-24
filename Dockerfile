FROM python:3.10-slim

WORKDIR /usr/src/app

EXPOSE 80

COPY . .
COPY run.sh

RUN pip install --no-cache-dir -r requirements.txt
RUN chmod a+x run.sh

CMD ["./run.sh"]