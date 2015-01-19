web: gunicorn --pythonpath eorlive_prototype app.flask_app:app --log-file=-
init: python -m app.manage db init
migrate: python -m app.manage db migrate
upgrade: python -m app.manage db upgrade
