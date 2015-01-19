web: gunicorn --pythonpath eorlive_prototype run_app:app --log-file=- & sh background.sh
init: cd eorlive_prototype;python -m app.manage db init
migrate: cd eorlive_prototype;python -m app.manage db migrate
upgrade: cd eorlive_prototype;python -m app.manage db upgrade
