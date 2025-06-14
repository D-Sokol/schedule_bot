alembic upgrade head
source .venv/bin/activate
python3 data/nats/initial_setup.py
upload-images data/images/
schedule-bot
