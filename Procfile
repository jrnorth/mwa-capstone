web: gunicorn --pythonpath eorlive_prototype app.flask_app:app --log-file=-
init: cd eorlive_prototype;python -m app.manage db init
migrate: cd eorlive_prototype;python -m app.manage db migrate
upgrade: cd eorlive_prototype;python -m app.manage db upgrade
