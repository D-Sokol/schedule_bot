source .venv/bin/activate
alembic upgrade head
python3 data/nats/initial_setup.py
upload-images data/images/
schedule-bot
