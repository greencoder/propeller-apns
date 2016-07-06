import flask
import json

from flask import request
from flask import render_template
from flask import send_from_directory
from pystalkd import Beanstalkd

application = flask.Flask(__name__)
application.debug = True

conn = Beanstalkd.Connection()

TOKEN = '0d6d8d20-13c3-11e6-a148-3e1d05defe78'

@application.route('/post', methods=['POST'])
def post():

    if request.form.get('auth_token', None) != TOKEN:
        return 'Unauthorized', 401

    title = request.form.get('title')
    body = request.form.get('body')
    badge_count = request.form.get('badge', type=int)
    token = request.form.get('token')
    topic = request.form.get('topic')
    delay = request.form.get('delay', 0)

    payload = {
        'title': title,
        'body': body,
        'badge': badge_count,
        'token': token,
    }

    conn.use(topic)
    conn.put(body=json.dumps(payload), delay=delay)

    return json.dumps(payload)

@application.route('/log.txt')
def static_from_root():
    return send_from_directory(application.static_folder, request.path[1:])

@application.route('/form')
def form():
    if request.form.get('auth_token', None) != TOKEN:
        return 'Unauthorized', 401
    else:
        return render_template('form.html')

@application.route('/')
def index():
    return '<!-- Nothing to see here -->'

if __name__ == "__main__":
    application.run(host='0.0.0.0', port=8080)
