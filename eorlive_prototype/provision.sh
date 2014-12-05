#!/usr/bin/env bash
echo ---provision.sh---

apt-get update
apt-get install -y python-virtualenv python3-dev libpq-dev

cd /mnt/eorlive_prototype

sudo virtualenv --python=/usr/bin/python3.4 flask
flask/bin/pip install flask
flask/bin/pip install requests
flask/bin/pip install Flask-SQLAlchemy
flask/bin/pip install Flask-Migrate
flask/bin/pip install Flask-Login
flask/bin/pip install requests-futures
flask/bin/pip install psycopg2

flask/bin/python3.4 -m app.manage db upgrade

crontab crontab

./run.py
