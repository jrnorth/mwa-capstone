from flask import render_template, flash, redirect, session, url_for, request, g, jsonify
from app import app
import requests
import json

@app.route('/')
@app.route('/index')
def index():
	return render_template('index.html')

@app.route('/get_observations', methods = ['POST'])
def get_observations():
	starttime = int(request.form['starttime'])
	endtime = int(request.form['endtime'])
	session['starttime'] = starttime
	session['endtime'] = endtime

	requestURL = 'http://ngas01.ivec.org/metadata/find'

	params = {'projectid': 'G0009', 'mintime': starttime, 'maxtime': endtime}

	data = requests.get(requestURL, params=params)

	return jsonify({'observations': json.loads(data.text)})