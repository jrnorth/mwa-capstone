#!flask/bin/python3.4
from app.flask_app import app
from app import views, models

app.run(debug=True)
