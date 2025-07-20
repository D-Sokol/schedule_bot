FROM python:3.11-slim

WORKDIR /opt/schedule

# Enable RU names for weekdays, month etc
RUN apt update && apt install -y locales && echo 'ru_RU.UTF-8 UTF-8' >>/etc/locale.gen && locale-gen
# Install some default fonts, list of packages may change in the future
RUN apt update && apt install -y fonts-freefont-ttf && apt clean

COPY pyproject.toml .
COPY uv.lock .
RUN pip install --root-user-action=ignore --no-cache uv && uv sync --no-install-project --no-dev --no-cache --locked --active --no-managed-python

COPY src/ src/
RUN uv sync --no-dev --frozen --active --no-managed-python
COPY entrypoint.sh .

ENTRYPOINT ["bash", "entrypoint.sh"]
