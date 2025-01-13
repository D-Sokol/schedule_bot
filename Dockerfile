FROM python:3.11-slim

WORKDIR /opt/schedule
COPY requirements.txt /opt/schedule
RUN pip3 install --no-cache-dir -r requirements.txt
# Install some default fonts, list of packages may change in the future
RUN apt update && apt install fonts-freefont-ttf && apt clean
COPY . /opt/schedule
ENTRYPOINT ["bash", "entrypoint.sh"]
