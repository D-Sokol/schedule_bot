alembic upgrade head
python3 data/nats/initial_setup.py
python3 upload_images.py data/images/
python3 main.py
