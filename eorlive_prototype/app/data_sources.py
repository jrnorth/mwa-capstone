from flask import render_template, request, g, make_response
import psycopg2
import os
from app.flask_app import app
from app import db_utils

@app.route('/get_tables', methods = ['POST'])
def get_tables():
    if g.user is not None and g.user.is_authenticated():
        hostname = request.form['hostname']
        database = request.form['database']

        try:
            db_conn = psycopg2.connect(database=database, host=hostname,
                user=os.environ['MWA_DB_USERNAME'], password=os.environ['MWA_DB_PW'])
        except Exception as e:
            return "Can't connect to database"

        table_tuples = db_utils.send_query(db_conn, """SELECT table_name
                                                    FROM information_schema.tables
                                                    WHERE table_schema='public'
                                                    ORDER BY table_name""").fetchall()

        db_conn.close()

        return render_template("table_list.html", table_tuples=table_tuples)
    else:
        return make_response("You must be logged in to use this feature.", 401)

@app.route('/get_columns', methods = ['POST'])
def get_columns():
    if g.user is not None and g.user.is_authenticated():
        hostname = request.form['hostname']
        database = request.form['database']
        table = request.form['table']

        try:
            db_conn = psycopg2.connect(database=database, host=hostname,
                user=os.environ['MWA_DB_USERNAME'], password=os.environ['MWA_DB_PW'])
        except Exception as e:
            return "Can't connect to database"

        column_tuples = db_utils.send_query(db_conn, """SELECT column_name
                                                    FROM information_schema.columns
                                                    WHERE table_name = '{}'
                                                    AND numeric_precision IS NOT NULL""".format(table)).fetchall()

        db_conn.close()

        return render_template("column_list.html", column_tuples=column_tuples)
    else:
        return make_response("You must be logged in to use this feature.", 401);
