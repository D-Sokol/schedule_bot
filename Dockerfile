FROM python:3.11-slim

WORKDIR /opt/schedule
COPY requirements.txt /opt/schedule
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . /opt/schedule
ENTRYPOINT ["bash", "entrypoint.sh"]
