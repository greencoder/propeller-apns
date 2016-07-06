import hyper
import json
import sys

from apns2.errors import APNsException
from apns2.errors import ConnectionException

class APNsClient(object):
    
    def __init__(self, cert_file, server='mock'):

        if server == 'production':
            server_hostname = 'api.push.apple.com'
            server_port = 2197
        elif server == 'sandbox':
            server_hostname = 'api.development.push.apple.com'
            server_port = 443
        else:
            server_hostname = 'localhost'
            server_port = 8443
            
        ssl_context = hyper.tls.init_context()
        ssl_context.load_verify_locations(cafile=cert_file)
        ssl_context.load_cert_chain(cert_file)

        self.__connection = hyper.HTTP20Connection(server_hostname, server_port, 
            ssl_context=ssl_context, force_proto='h2', secure=True)


    def send_notification(self, token_hex, notification, topic):

        json_payload = json.dumps(notification.dict(), ensure_ascii=False, separators=(',', ':'))
        json_payload = json_payload.encode('utf-8')

        headers = {
            'apns-priority': '10',
            'apns-topic': topic,
        }

        url = '/3/device/{}'.format(token_hex)

        stream_id = self.__connection.request('POST', url, json_payload, headers)
        response = self.__connection.get_response(stream_id)
        
        if response:
            status_code = response.status
        else:
            status_code = None

        # Temporarily removing exception handling to better diagnose connection errors
        # This will be added back in one I'm familiar with what the errors are, I don't
        # want to just keep handling them naievely

        # The remote server could close the connection at any time
        # try:
        #     stream_id = self.__connection.request('POST', url, json_payload, headers)
        #     response = self.__connection.get_response(stream_id)
        #     status_code = response.status
        # except ConnectionRefusedError as err:
        #     sys.stdout.write('Connection Refused')
        #     raise ConnectionException(err)
        #     status_code = None
        # except Exception as err:
        #     raise APNsException(err)
        #     status_code = None
        # if status_code != 200:
        #     raw_data = response.read().decode('utf-8')
        #     data = json.loads(raw_data)
        #     raise Exception(data['reason'], response.status)
        
        return status_code
