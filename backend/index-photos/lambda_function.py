import json
import boto3
import urllib.parse
from datetime import datetime
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

print('Loading function')

region = 'us-east-1'  
service = 'es'

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key,
                   credentials.secret_key,
                   region, service,
                   session_token=credentials.token)

rekognition = boto3.client('rekognition')
s3 = boto3.client('s3')


es = Elasticsearch(
    hosts=[{'host': 'search-photo-2cazeomtw76yparwds4q3osswa.us-east-1.es.amazonaws.com', 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

def lambda_handler(event, context):
    # print("Received event: " + json.dumps(event, indent=2))
    print("Received event: " + json.dumps(event))

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        

        head = s3.head_object(Bucket=bucket, Key=key)
        custom_labels = head['Metadata'].get('customlabels', '')
        custom_labels = [x.strip() for x in custom_labels.split(',')] if custom_labels else []


        response = rekognition.detect_labels(
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxLabels=10
        )

        labels = [label['Name'].lower() for label in response['Labels']] + custom_labels
        print(labels)
        document = {
            'objectKey': key,
            'bucket': bucket,
            'createdTimestamp': datetime.now().isoformat(),
            'labels': labels
        }


        es.index(index="photo", body=document)
        

    return {
        'statusCode': 200,
        'body': json.dumps('Photo indexed successfully!')
    }


