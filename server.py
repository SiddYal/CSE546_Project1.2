from flask import Flask, request, Response, jsonify
import boto3
import csv
from werkzeug.utils import secure_filename
import os
import time

app = Flask(__name__)

s3 = boto3.client('s3', region_name="us-east-1")
sqs = boto3.client('sqs', region_name="us-east-1")


in_bucket_name = '1222045786-in-bucket'
s3.create_bucket(Bucket=in_bucket_name)

out_bucket_name = '1222045786-out-bucket'
s3.create_bucket(Bucket=out_bucket_name)



request_queue_name = '1222045786-req-queue'
response_queue_name = '1222045786-resp-queue'

sqs.create_queue(QueueName=request_queue_name, Attributes={
    'MaximumMessageSize': '1024'
})
req_queueURL='https://sqs.us-east-1.amazonaws.com/912786613775/1222045786-req-queue'
sqs.create_queue(QueueName=response_queue_name, Attributes={
    'MaximumMessageSize': '1024'
})
res_queueURL='https://sqs.us-east-1.amazonaws.com/912786613775/1222045786-resp-queue'

def get_queue_length(queueURL):
    attrs = sqs.get_queue_attributes(QueueUrl=queueURL, AttributeNames=['ApproximateNumberOfMessages'])
    queue_size = int(attrs['Attributes'].get('ApproximateNumberOfMessages', 0))
    print(queue_size)
    return queue_size


@app.route('/', methods=['POST'])
def handle_post_request():
    if 'inputFile' not in request.files:
        return jsonify({'error': 'No file part with key "inputFile"'}), 400
    #print("check1")
    file = request.files['inputFile']
    #print("check2")
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    #print("check3")
    # Secure filename and save
    filename = secure_filename(file.filename)
    #print(type(filename))

    s3.upload_file(filename, in_bucket_name, filename)
    #print(f"File {filename} uploaded.")
    #print("check4")


    #Task 3: Forward face recognition requests to application tier.
    sqs.send_message(QueueUrl=req_queueURL, MessageBody=filename)

    #Temp: Call backend. Replace with controller.py 
    os.system(f"python .\\backend.py")
    


    #Task 4: Return the results to the HTTP Requests
    while get_queue_length(res_queueURL) <= 0:
        time.sleep(0.5)
    #print(get_queue_length())
    truncfilename, ext = os.path.splitext(filename)
    foundResp=False
    while foundResp==False:
        resp = sqs.receive_message(QueueUrl=res_queueURL, MaxNumberOfMessages=1)
        print(resp)
        print("Server received response")
        print(f"Number of messages received: {len(resp.get('Messages', []))}")

        print(f"Request Queue Size: {get_queue_length(req_queueURL)}")
        print(f"Response Queue Size: {get_queue_length(res_queueURL)}")

        if len(resp.get('Messages', [])) <= 0:
            time.sleep(0.5)
            continue
        message = resp.get("Messages", [])[0]
        # print(message)
        message_body = message["Body"]
        receipt_handle = message['ReceiptHandle']
        print(f"Message body: {message_body}")
        print(f"Receipt Handle: {receipt_handle}")

        filename=message_body
        print(filename)

        if truncfilename in message_body:
            foundResp = True
            #delete response from queue
            sqs.delete_message(QueueUrl=res_queueURL, ReceiptHandle=receipt_handle)
            print(message_body)
            return Response(message_body, mimetype="text/plain")
        


    

    return Response(f"{truncfilename}:{message_body}", mimetype="text/plain")

    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)