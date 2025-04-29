import json
import boto3
from elasticsearch import Elasticsearch
from elasticsearch.connection import RequestsHttpConnection
from requests_aws4auth import AWS4Auth

region = 'us-east-1'
service = 'es'

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    region,
    service,
    session_token=credentials.token
)

es = Elasticsearch(
    hosts=[{'host': 'search-photo-2cazeomtw76yparwds4q3osswa.us-east-1.es.amazonaws.com', 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

STOPWORDS = {'me', 'i', 'want', 'to', 'see', 'show', 'photos', 'pictures', 'with', 'of', 'and'}

def extract_keywords(transcript):
    words = transcript.lower().split()
    return [word for word in words if word not in STOPWORDS]

def lambda_handler(event, context):
    print("Event:", json.dumps(event))

    query = event.get("queryStringParameters", {}).get("q", "")
    if not query:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing query parameter'}),
            'headers': {'Access-Control-Allow-Origin': '*'},
            'origin_event': json.dumps(event)
        }


    lex = boto3.client('lexv2-runtime')

    lex_response = lex.recognize_text(
        botId='S6IWFAORFV',      
        botAliasId='TSTALIASID', 
        localeId='en_US',           
        sessionId='searchuser',     
        text=query
    )

    print("Lex response:", json.dumps(lex_response))


    transcript = lex_response.get('inputTranscript', '')

    if not transcript and lex_response.get('interpretations'):
        transcript = lex_response['interpretations'][0].get('inputTranscript', '')

    if not transcript:
        transcript = query

    keywords = extract_keywords(transcript)
    print("Extracted keywords:", keywords)

    if not keywords:
        return {
            'statusCode': 200,
            'body': json.dumps([]),
            'headers': {'Access-Control-Allow-Origin': '*'}
        }

    must_clauses = [{"match": {"labels": keyword}} for keyword in keywords]
    es_query = {
        "query": {
            "bool": {
                "should": must_clauses
            }
        }
    }

    results = es.search(index="photo", body=es_query)
    hits = results['hits']['hits']


    # photos = []
    # for hit in hits:
    #     source = hit["_source"]
    #     photo_url = f"https://{source['bucket']}.s3.amazonaws.com/{source['objectKey']}"
    #     photos.append({
    #         "objectKey": source["objectKey"],
    #         "bucket": source["bucket"],
    #         "url": photo_url
    #     })
    photos = []
    seen_urls = set()

    for hit in hits:
        source = hit["_source"]
        photo_url = f"https://{source['bucket']}.s3.amazonaws.com/{source['objectKey']}"
        
        if photo_url in seen_urls:
            continue
        
        seen_urls.add(photo_url)
        photos.append({
            "objectKey": source["objectKey"],
            "bucket": source["bucket"],
            "url": photo_url
        })

    return {
        'statusCode': 200,
        'body': json.dumps(photos),
        'headers': {'Access-Control-Allow-Origin': '*'}
    }
