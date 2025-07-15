import json
import os
import boto3
import logging
from botocore.exceptions import ClientError
import traceback


dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-agent')
bedrock_runtime = boto3.client('bedrock-agent-runtime')
bedrock_client = boto3.client('bedrock')
sqs = boto3.client('sqs')

logger = logging.getLogger()
logger.setLevel("INFO")
QUEUE_URL = os.environ.get('SQS_QUEUE_URL')
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])



def update_dynamodb_record(chatbot_request_id, response, status):
    
    try:
        # Update the item
        response = table.update_item(
            Key={
                'chatbot_request_id': chatbot_request_id
            },
            UpdateExpression='SET #status = :status, #result = :result',
            ExpressionAttributeNames={
                '#status': 'status',
                '#result': 'result'
            },
            ExpressionAttributeValues={
                ':status': status,
                ':result': response
            },
            ReturnValues="UPDATED_NEW"
        )
        return response
    except ClientError as e:
        print(f"Error updating record: {e.response['Error']['Message']}")
        raise

def handler(event, context):
    try:
        # Process SQS messages
        for sqs_record in event['Records']:
            print("SQS Record: " + json.dumps(sqs_record, indent=2))
            # Parse the message body
            message = json.loads(sqs_record['body'])
            chatbot_request_id = message['chatbot_request_id']
            # Read from DynamoDB table
            response = table.get_item(
                Key={
                    'chatbot_request_id': chatbot_request_id
                }
            )
            
            print(response)
            # Log the retrieved item
            if 'Item' in response:
                logger.info(f"Retrieved item from DynamoDB: {response['Item']}")
                payload = response['Item']['payload']
                
                message = payload['message']
                knowledgeBaseId = payload['knowledgeBaseId']
                textPromptTemplate = payload['textPromptTemplate']
                textInferenceConfig = payload['textInferenceConfig']
                modelArn = payload['modelArn']
                
                maxTokens =textInferenceConfig["maxTokens"]
                temperature = textInferenceConfig["temperature"]
                topP = textInferenceConfig["topP"]
                stopSequences = textInferenceConfig["stopSequences"]
                
                
                logger.info("=== Template Debug Information ===")
                logger.info(f"Custom template provided: {textPromptTemplate is not None}")
                if textPromptTemplate is not None:
                    logger.info(f"Custom template length: {len(textPromptTemplate)}")
                    logger.info(f"Custom template preview (first 100 chars): {textPromptTemplate[:100]}")
                
                print("ModelARN: "+ modelArn)
                print("knowledge_base_id: "+ knowledgeBaseId)
                print("Message: "+ message)
                
                # Call Bedrock Knowledge Base
                try:
                    kb_response = bedrock_runtime.retrieve_and_generate(
                        input={
                            'text': message
                        },
                        retrieveAndGenerateConfiguration={
                            'type': 'KNOWLEDGE_BASE',
                            'knowledgeBaseConfiguration': {
                                "knowledgeBaseId" :  knowledgeBaseId,
                                "modelArn": modelArn,
                                'retrievalConfiguration': {
                                    'vectorSearchConfiguration': {
                                        'numberOfResults': 10
                                    }
                                },
                                'generationConfiguration': {
                                    'promptTemplate': {
                                        'textPromptTemplate': textPromptTemplate if textPromptTemplate is not None else None
                                    },
                                    "inferenceConfig": { 
                                        "textInferenceConfig": { 
                                            # "maxTokens": int(maxTokens),
                                            "maxTokens": 4096,
                                                "temperature": float(temperature),
                                                "topP": float(topP),
                                                "stopSequences": stopSequences
                                        }
                                    }
                                }
                            }
                        }
                    )
                    
                    # Update DynamoDB with the response
                    update_dynamodb_record(chatbot_request_id, kb_response, 'success')
                    
                    # Delete the SQS message since processing was successful
                    sqs.delete_message(
                        QueueUrl=QUEUE_URL,
                        ReceiptHandle=sqs_record['receiptHandle']
                    )
                    
                except Exception as e:
                    traceback_str = traceback.format_exc()
                    print(traceback_str)
                    logger.error(f"Error processing request: {str(e)}")
                    update_dynamodb_record(chatbot_request_id, str(e), 'error')

                
    
            else:
                logger.info(f"No item found for chatbot_request_id: {message['chatbot_request_id']}")
                
        return {
            'statusCode': 200,
            'body': json.dumps('Messages processed successfully')
        }
        
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(traceback_str)
        logger.error(f"Error processing messages: {str(e)}")
        raise