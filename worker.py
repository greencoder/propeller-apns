import argparse
import datetime
import json
import logging
import os
import socket
import sys

from apns2.client import APNsClient
from apns2.payload import Payload
from apns2.payload import PayloadAlert

from apns2.errors import ConnectionException
from apns2.errors import APNsException

from pystalkd.Beanstalkd import Connection
from pystalkd.Beanstalkd import SocketError
from pystalkd.Beanstalkd import DeadlineSoon

CUR_DIR = os.path.dirname(os.path.realpath(__file__))

# Configure Logging
logger = logging.getLogger('Propeller Worker')
logger.setLevel(logging.DEBUG)
logfile_path = os.path.join(CUR_DIR, 'log.txt')

# Configure file logging
fh = logging.FileHandler(logfile_path)
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('%(asctime)s\t%(message)s'))
logger.addHandler(fh)

# Configure stdout logging
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s\t%(message)s'))
logger.addHandler(ch)

# Read command-line arguments
argparser = argparse.ArgumentParser()
argparser.add_argument('--cert', dest='cert_file', help='Location of the .pem certificate file', required=True)
argparser.add_argument('--topic', dest='topic', help='Bundle ID for the app (e.g. com.apple.exampleapp)', required=True)
argparser.add_argument('--server', dest='server', help='Mock, Sandbox, or Production Server', required=True)
args = argparser.parse_args()

# Verify the certificate file exists
if not os.path.exists(os.path.abspath(args.cert_file)):
    logging.error('Error! Could not find certificate file: %s' % args.cert_file)
    sys.exit()
else:
    cert_filepath = os.path.abspath(args.cert_file)

# Verify they passed a valid server
if args.server.lower() not in ('sandbox', 'production', 'mock'):
    logging.error('Error! Server must be either "sandbox", "production", or "mock".')
    sys.exit()
else:
    server_name = args.server.lower()

# Create the beanstalkd connection
try:
    bean_conn = Connection()
except SocketError as err:
    logging.error('Error connecting to Beanstalkd server: %s' % err)
    sys.exit()

# Set the beanstalk tube to watch based on the topic
bean_conn.watch(args.topic)

# Set the default timeout for the socket
socket.setdefaulttimeout(15)

# We want to know every time the server restarts
logger.info('Starting propeller worker')

# Create the persistent http/2 connection to Apple
client = APNsClient(cert_filepath, server=server_name)

# Start a run loop to listen for jobs
while True:

    # Get the job
    try:
        job = bean_conn.reserve()
    except DeadlineSoon as err:
        logger.error('Beanstalkd Deadline Error: %s' % err)
        sys.exit()

    logger.info('Received a job with ID: %s' % job.job_id)
    sys.stdout.flush()

    data = json.loads(job.body)

    token = data['token']
    title = data['title']
    body = data['body']
    badge = data['badge']

    alert = PayloadAlert(title=title, body=body)
    payload = Payload(alert=alert.dict(), sound=None, badge=badge)

    # Todo: 
    # There is almost nothing here in terms of error handling code
    # except for some rudamentary exception catching. At a minimum,
    # there needs to be handling for invalid tokens.

    try:
        result_code = client.send_notification(token, payload, topic=args.topic)
        logger.info('Job result status code: %s' % result_code)
        job.delete()
    except (TimeoutError, ConnectionException) as err:
        job.release()
        logger.error('Connection error sending notification: %s' % err)
        logger.error('Restarting worker to re-establish connection')
        sys.exit()
    except APNsException as err:
        job.release()
        logging.error('Error sending notification: %s (%s)' % type(err))
        logging.error('Error type: %s' % type(err))
        logging.error('Restarting worker to re-establish connection')
        sys.exit()

