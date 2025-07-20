FROM python:3.11-slim

WORKDIR /opt/schedule

# Enable RU names for weekdays, month etc
RUN apt update && apt install -y locales && echo 'ru_RU.UTF-8 UTF-8' >>/etc/locale.gen && locale-gen
# Install some default fonts, list of packages may change in the future
RUN apt update && apt install -y fonts-freefont-ttf && apt clean

COPY pyproject.toml .
COPY uv.lock .
RUN pip install --root-user-action=ignore --no-cache uv && uv sync --no-install-project --no-dev --group deploy --no-cache --locked --active --no-managed-python

# Enables subcommands
COPY src src
COPY LICENSE .
COPY README.md .
RUN uv sync --no-dev --frozen --active --no-managed-python

# Required for correct entrypoint launch.
COPY alembic .
COPY alembic.ini .
COPY entrypoint.sh .
COPY data/nats/initial_setup.py ./data/nats/

ENTRYPOINT ["bash", "entrypoint.sh"]
