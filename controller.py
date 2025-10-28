#!/usr/bin/env python3
import boto3
import time

# === CONFIGURATION ===
req_queue_name = "1222045786-req-queue"
app_instance_name = "app-tier-instance"
MAX_INSTANCES = 15
POLL_INTERVAL = 10

# === AWS CLIENTS ===
ec2 = boto3.client('ec2', region_name="us-east-1")
sqs = boto3.client('sqs', region_name="us-east-1")

req_queueURL='https://sqs.us-east-1.amazonaws.com/912786613775/1222045786-req-queue'

# === Helper Functions ===
def get_queue_length():
    attrs = sqs.get_queue_attributes(QueueUrl=req_queueURL, AttributeNames=['ApproximateNumberOfMessages'])
    return int(attrs['Attributes'].get('ApproximateNumberOfMessages', 0))

def get_app_instances():
    filters = [{'Name': 'tag:Name', 'Values': [f"{app_instance_name}-*"]}]
    resp = ec2.describe_instances(Filters=filters)
    running, stopped = [], []

    for r in resp['Reservations']:
        for inst in r['Instances']:
            state = inst['State']['Name']
            instance_id = inst['InstanceId']
            if state == 'running':
                running.append(instance_id)
            elif state == 'stopped':
                stopped.append(instance_id)
    return running, stopped

def start_instances(instance_ids):
    if instance_ids:
        print(f"Starting instances: {instance_ids}")
        ec2.start_instances(InstanceIds=instance_ids)

def stop_instances(instance_ids):
    if instance_ids:
        print(f"Stopping instances: {instance_ids}")
        ec2.stop_instances(InstanceIds=instance_ids)

# === Main Scaling Loop ===
def main():
    while True:
        try:
            num_messages = get_queue_length()
            running, stopped = get_app_instances()
            running_count = len(running)
            stopped_count = len(stopped)

            #print(f"\n[Controller Status]")
            #print(f"Queue messages: {num_messages}")
            #print(f"Running instances: {running_count}")
            #print(f"Stopped instances: {stopped_count}")

            # Scale down (no requests)
            if num_messages == 0:
                if running_count > 0:
                    #print("No messages in queue → stopping all running instances.")
                    stop_instances(running)
                else:
                    print("System idle. Nothing to do.")
            
            # Scale up or down based on queue
            else:
                desired_instances = min(num_messages, MAX_INSTANCES)
                if running_count < desired_instances:
                    num_to_start = min(desired_instances - running_count, stopped_count)
                    if num_to_start > 0:
                        instances_to_start = stopped[:num_to_start]
                        start_instances(instances_to_start)
                    else:
                        print("No stopped instances available to start.")
                elif running_count > desired_instances:
                    num_to_stop = running_count - desired_instances
                    instances_to_stop = running[:num_to_stop]
                    stop_instances(instances_to_stop)
                else:
                    print("Instance count matches demand. No action taken.")
            
            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print(f"[ERROR] {str(e)}")
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
