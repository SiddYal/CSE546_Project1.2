from flask import Flask, request, Response, jsonify
import boto3
import csv
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

s3 = boto3.client('s3', region_name="us-east-1")
sdb = boto3.client('sdb', region_name="us-east-1")

sqs = boto3.client('sqs', region_name="us-east-1")

in_bucket_name = '1222045786-in-bucket'
out_bucket_name = '1222045786-out-bucket'
#s3.create_bucket(Bucket=bucket_name)

db_name = '1222045786-simpleDB'
#sdb.delete_domain(DomainName=db_name)
#sdb.create_domain(DomainName=db_name)

request_queue_name = '1222045786-req-queue'
response_queue_name = '1222045786-resp-queue'

req_queueURL='https://sqs.us-east-1.amazonaws.com/912786613775/1222045786-req-queue'
res_queueURL='https://sqs.us-east-1.amazonaws.com/912786613775/1222045786-resp-queue'

#Retrieve request from request queue

#request = sqs.receive_message(request_queue_name)
request = sqs.receive_message(QueueUrl=req_queueURL, MaxNumberOfMessages=1)
print("Backend Received Request")
#print(request)
print(f"Number of messages received: {len(request.get('Messages', []))}")

message = request.get("Messages", [])[0]
# print(message)
message_body = message["Body"]
receipt_handle = message['ReceiptHandle']
print(f"Message body: {message_body}")
print(f"Receipt Handle: {receipt_handle}")
# delete taken request from the request queue
print("Deleting message from request queue")
sqs.delete_message(QueueUrl=req_queueURL, ReceiptHandle=receipt_handle)

filename=message_body
#print(filename)

#new_save = os.path.join('/tmp/', filename)

s3.download_file(in_bucket_name, filename, 'temppic.jpg')
print("success?")

command = f"python .\\face_recognition.py .\{message_body}"
print(command)
os.system(command)
result = os.popen(command).read()
print(f"Result: {result}")


truncfilename, ext = os.path.splitext(filename)
s3.put_object(Body=result, Bucket=out_bucket_name, Key=truncfilename)
resp = f"{truncfilename}:{result}"
sqs.send_message(QueueUrl=res_queueURL, MessageBody=resp)
