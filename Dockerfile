FROM python:3.11-slim

WORKDIR /opt/schedule
COPY requirements.txt /opt/schedule
RUN pip3 install --no-cache-dir -r requirements.txt
# Enable RU names for weekdays, month etc
RUN apt update && apt install -y locales && echo 'ru_RU.UTF-8 UTF-8' >>/etc/locale.gen && locale-gen
# Install some default fonts, list of packages may change in the future
RUN apt update && apt install -y fonts-freefont-ttf && apt clean
COPY . /opt/schedule
ENTRYPOINT ["bash", "entrypoint.sh"]
