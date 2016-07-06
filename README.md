# propeller-apns

A Python 3 gateway server for sending Apple Push Notifications with HTTP/2.

## Overview

This project uses the [hyper](https://github.com/Lukasa/hyper) library to maintain a persistent connection to Apple's HTTP/2 servers.  A worker processes jobs from a [beanstalkd](https://github.com/kr/beanstalkd) work queue and sends them to Apple's servers. An optional [Flask](http://flask.pocoo.org/) web server provides a HTTP interface to the queue.

*Note: It might be possible to run this project with Python 2.7.x, but I was unable to get it working and used Python 3.4.*

## Usage

By default, the worker talks to the beanstalkd queue on its standard port `11300`. Make sure beanstalkd is running, then start your worker:
```
$ python worker.py --cert=<path/to/certificate.pem> --server=<sandbox|production> --topic=<com.example.bundleid>
````

Arguments:
1. `--cert`: Path to the .pem certificate file (see "Generating Certificates" below)
1. `--server`: Which Apple server, `production` or `sandbox`, to use (only use production from your App Store version)
1. `--topic`: The bundle identifier of your application

*Note: Passing the `topic` allows you to target multiple applications from a single installation, since each application requires its own persistent connection. It is possible to run multiple workers with the same topic to increase your throughput.*

## Connection Maintenance

Trying to send messages asynchronously to APNS via persistent connection is difficult because Apple can close the connection at any time without warning. 

The high-level `hyper` library used to create the HTTP/2 connection does not currently have support to notify you when a connection has been closed, so you'll only find out when you try to send a message and it doesn't complete.

Rather than write complex reconnection logic, I took the easy way out on this and manage the worker with [Supervisor](http://supervisord.org/). If there is an error sending a message, the job is released back into the queue and the process terminates. Supervisor then automatically restarts the process which creates a new APNs connection and resumes processing the queue.

This strategy has worked very well in production so far. (I see the server restart about every 4-10 days) It's also respectful to Apple's servers and does not try to reestablish a closed connection until a message needs to be sent.

## HTTP API

If you want to use the HTTP API, start the optional web server:
```
$ python server.py
```

This web server allows you to queue jobs via HTTP POST. Use the following parameters:

1. `auth_token`: (string) The secret auth token you defined in [server.py](../blob/master/server.py#L15)
1. `title`: (string) The title of your notification
1. `body`: (string) The body of your notification
1. `badge`: (integer, optional) The badge count to display
1. `token`: (string) The device token to send the message to
1. `topic`: (string) The bundle identifier (see below)
1. `delay`: (integer, optional) Number of seconds to wait before the message shoudl be sent (great for queueing future messages)

*Note: If you are running multiple workers for different applications, you can use this API to queue messages to target the appropriate worker.*

There is an HTML form included with the web server for testing/diagnostic purposes, but it's not protected out of the box. **Do not leave it enabled without protecting it!**

## Generating Certificates

You must generate a `.pem` certificate file from the `.p12` that Apple provides. Apple provides a helpful guide to [Creating a Universal Push Notification Client SSL Certificate](https://developer.apple.com/library/ios/documentation/IDEs/Conceptual/AppDistributionGuide/AddingCapabilities/AddingCapabilities.html#//apple_ref/doc/uid/TP40012582-CH26-SW11)

Following the steps in Apple's guide, generate the production HTTP/2 Cert (use Apple Push Notification service SSL (Sandbox & Production) under Production)

In Keychain Assistant on your Mac, click on "My Certificates" on the left, then select the Apple Push Services item and its associated key as `certificate.p12`. (or you can name it what you want)

Convert the `.p12` file to a .`pem` file:
```
$ openssl pkcs12 -in certificate.p12 -out certificate.pem -nodes`
```

If you have a passphrase, remove it:
```
$ openssl rsa -in certificate.pem -out certificate_nopass.pem && mv certificate_nopass.pem certificate.pem
```

## Notes on Using Beanstalkd

I chose Beanstalk because it is easy to use and I have experience with it from previous projects. I also like its ability to delay message sending. I did not choose Redis because I wanted the ability to easily release a job back into the queue if there is an error.

[Disque](https://github.com/antirez/disque) looks like an interesting project, but since I didn't have any experience with it, I didn't choose it.

## Notes on Token Registration

This app *intentionally* does not handle the registration and persistence of client device tokens. You will need your own mechanism to accept and manage tokens from clients.

While this functionality could be written into the Flask web server, I wanted to keep this project as clean and simple as possible. (Following the concept of microservices)

Whatever you use, it will probably be pretty easy to integrate with this gateway server since you can insert your messages into the work queue directly. This also gives you the flexibility to write the token registration piece in any language you desire.

## Todo

1. Add support for the `apns-expiration` header 
1. Add more error handling when sending messages via the worker

## Feedback and Contribution

If you have feedback or suggestions, I'd love to hear them. Pull requests gladly accepted, especially for things that help handle sending errors. (something I haven't gotten to yet)

## Credit

This project was based, in part, on the great work in [PyAPNs2](https://github.com/Pr0Ger/PyAPNs2)
