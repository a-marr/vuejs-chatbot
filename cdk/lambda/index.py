import decimal
import json
from datetime import datetime, date
from time import time, struct_time, mktime
import decimal 
import os
import boto3
import logging
import uuid
from typing import Dict, Any
from botocore.exceptions import ClientError
from typing import Dict, Optional
import traceback

logger = logging.getLogger()
logger.setLevel("INFO")

sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-agent')
bedrock_runtime = boto3.client('bedrock-agent-runtime')
bedrock_client = boto3.client('bedrock')

QUEUE_URL = os.environ.get('SQS_QUEUE_URL')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

  

prompt_template = open('prompt_template.txt', 'r').read()

def submit_to_queue(payload: Dict[str, Any]) -> Dict[str, str]:
    try:
        chatbot_request_id = str(uuid.uuid4())
        status = "processing"
        
        item = {
            'chatbot_request_id': chatbot_request_id,
            'status': status,
            'payload': payload,
            'result': ""
        }
        table.put_item(Item=item)
        message = {
            'chatbot_request_id': chatbot_request_id,
        }
        
        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        print("Message created: "+ response["MessageId"])
        
        return {
            'chatbot_request_id': chatbot_request_id
        }
        
    except ClientError as e:
        traceback_str = traceback.format_exc()
        print(traceback_str)
        print(f"Error putting item: {e.response['Error']['Message']}")
        return {
            'success': False,
            'error': str(e)
        }    
        
def print_table_info():
    response = table.meta.client.describe_table(TableName=os.environ['DYNAMODB_TABLE'])
    print("Table Key Schema:")
    for key in response['Table']['KeySchema']:
        print(f"- {key['AttributeName']} ({key['KeyType']})")
    
def get_record(chatbot_request_id: str) -> Optional[Dict[str, any]]:
    try:
        print_table_info()
        response = table.get_item(
            Key={
                'chatbot_request_id': str(chatbot_request_id)
            },
            ConsistentRead=True  # Optional: ensures you get the latest version
        )    
        
        if 'Item' in response:
            # Use get() method to safely access dictionary keys
            item = response['Item']
            record = {
                'chatbot_request_id': item.get('chatbot_request_id'),
                'status': item.get('status'),
                'payload': item.get('payload'),
                'result': item.get('result')
            }
            
            # If status is success, delete the record after retrieving it
            if record['status'] != 'processing':
                try:
                    delete_record(chatbot_request_id)
                except Exception as e:
                    logger.warning(f"Failed to delete completed record {chatbot_request_id}: {str(e)}")
            
            return record
        else:
            return None
            
    except ClientError as e:
        traceback_str = traceback.format_exc()
        print(traceback_str)
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"Error getting record: {error_code}: {error_message}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise
    
def delete_record(chatbot_request_id: str) -> Dict[str, any]:
    try:
        # Delete the item and get the old values
        response = table.delete_item(
            Key={
                'chatbot_request_id': chatbot_request_id
            },
            ReturnValues='ALL_OLD'  # This will return the item that was deleted
        )
        
        # Check if an item was actually deleted
        if 'Attributes' in response:
            deleted_item = {
                'chatbot_request_id': response['Attributes']['chatbot_request_id'],
                'status': response['Attributes']['status'],
                'payload': response['Attributes']['payload'],
                'result': response['Attributes']['result']
            }
            
            return {
                'success': True,
                'message': 'Record deleted successfully',
                'deleted_item': deleted_item
            }
        else:
            return {
                'success': False,
                'message': 'Record not found',
                'deleted_item': None
            }
            
    except ClientError as e:
        traceback_str = traceback.format_exc()
        print(traceback_str)
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"Error deleting record: {error_code}: {error_message}")
        return {
            'success': False,
            'message': f"Failed to delete record: {error_message}",
            'error': error_code
        }
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(traceback_str)
        print(f"Unexpected error: {str(e)}")
        return {
            'success': False,
            'message': f"Unexpected error: {str(e)}",
            'error': 'UnexpectedError'
        }
    
def extract_guid(url):
    try:
        if '?' not in url:
            return None
        
        # Remove any trailing slashes or whitespace
        guid = url.split('?')[1].strip('/')
        
        # Optional: Validate the GUID format if needed
        if not guid:
            return None
            
        return guid
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(traceback_str)
        print(f"Error extracting GUID: {str(e)}")
        return None

def handler(event, context):
    # Get the HTTP method from the event
    http_method = event['httpMethod']
    path = event.get('path')
    
    # Set CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Allow-Methods': 'GET,PUT'
    }
    
    try:
        if http_method == 'GET' and path == '/knowledge-bases':
            filtered_knowledge_bases = []
            knowledge_bases = bedrock.list_knowledge_bases()
            logger.info(knowledge_bases)
            for kb in knowledge_bases.get('knowledgeBaseSummaries', []):
                get_knowledge_base_response = bedrock.get_knowledge_base(
                    knowledgeBaseId=kb['knowledgeBaseId']
                )
                tags_response = bedrock_client.list_tags_for_resource(
                    resourceArn=get_knowledge_base_response['knowledgeBase']['knowledgeBaseArn']
                )
                tags = tags_response.get('tags', {})
                if tags.get('public') == 'visible':
                    filtered_knowledge_bases.append({
                        'id': kb['knowledgeBaseId'],
                        'name': kb['name']
                    })

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'knowledgeBases': filtered_knowledge_bases
                })
            }
        if http_method == 'GET' and path == '/models':
            available_models = [
                {
                    'modelArn': 'arn:aws:bedrock:us-east-1:509399601784:inference-profile/us.anthropic.claude-3-opus-20240229-v1:0',
                    'modelName': 'Claude 3 Opus'
                }
                ,
                {
                    'modelArn': 'arn:aws:bedrock:us-east-1:509399601784:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0',
                    'modelName': 'Claude 3.5 Haiku'
                },
                {
                    'modelArn': 'arn:aws:bedrock:us-east-1:509399601784:inference-profile/us.anthropic.claude-3-5-sonnet-20241022-v2:0',
                    'modelName': 'Claude 3.5 Sonnet v2'
                },
                {
                    'modelArn': 'arn:aws:bedrock:us-east-1:509399601784:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0',
                    'modelName': 'Claude 3.7 Sonnet v1'
                }


            ]
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(available_models)
            }
            
        elif http_method == "GET" and path == "/chatbot":
            query_params = event.get('queryStringParameters', {})
            print("getting information for request: " + str(query_params))

            if query_params and 'url' in query_params:
                print("Found URL in request")

                chatbot_request_id = query_params['url']
                print("Found chatbot_request_id in request: " + chatbot_request_id)
                record = get_record(chatbot_request_id)
                if record:
                    return {
                        'statusCode': 200,
                        'headers': headers,
                        'body': json.dumps(record, cls=CustomJSONEncoder)
                    }
                else:
                    print("No record found DynamoDB record: " + chatbot_request_id)

                 

            
        elif http_method == 'POST' and path == "/chatbot":
            body = json.loads(event['body'])
            message = body.get('message', '')
            knowledgeBaseId = body.get('knowledgeBaseId')
            textPromptTemplate = body.get('textPromptTemplate')
            textInferenceConfig = body.get('textInferenceConfig')
            modelArn = body.get('modelArn') 
            
            print("Body: "+ json.dumps(body))
            # model_arn = 'us.anthropic.claude-3-opus-20240229-v1:0'
            
            # Add detailed logging for debugging template flow
            logger.info("=== Template Debug Information ===")
            logger.info(f"Custom template provided: {textPromptTemplate is not None}")
            if textPromptTemplate is not None:
                logger.info(f"Custom template length: {len(textPromptTemplate)}")
                logger.info(f"Custom template preview (first 100 chars): {textPromptTemplate[:100]}")
            
            print("ModelARN: "+ modelArn)
            print("knowledge_base_id: "+ knowledgeBaseId)
            print("Message: "+ message)

            # Validate knowledge base ID is provided
            if not knowledgeBaseId:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'knowledgeBaseId is required in the request body'
                    })
                }

            # Use custom template if provided, otherwise use default
            template = textPromptTemplate if textPromptTemplate else open('prompt_template.txt', 'r').read()
            
            # Log which template is being used and its content
            logger.info("=== Final Template Information ===")
            logger.info(f"Using custom template: {textPromptTemplate is not None}")
            logger.info(f"Template length: {len(template)}")
            logger.info(f"Template preview (first 100 chars): {template[:100]}")
            logger.info("=== End Template Information ===")
            
            createdRecord = submit_to_queue({
                'message': message,
                'knowledgeBaseId': knowledgeBaseId,
                'textPromptTemplate': template,
                'textInferenceConfig': textInferenceConfig,
                'modelArn': modelArn
                })

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(createdRecord)
            }
        else:
            return {
                'statusCode': 405,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Method not allowed'
                })
            }
            
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(traceback_str)
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': str(e)
            })
        }
        
    
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return str(o)
        if isinstance(o, date):
            return str(o)
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, struct_time):
            return datetime.fromtimestamp(mktime(o))
        # Any other serializer if needed
        return super(CustomJSONEncoder, self).default(o)