import aws_cdk
from constructs import Construct
from aws_cdk import (
    SecretValue,
    Stack,
    aws_cognito as cognito,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_iam as iam,
    aws_amplify as amplify,
    aws_codebuild as codebuild,
    aws_bedrock as bedrock,
    CfnOutput,
    Duration,
    RemovalPolicy,
)

class MainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Cognito User Pool
        user_pool = cognito.UserPool(
            self, "AvaUserPool",
            user_pool_name="ava-user-pool",
            self_sign_up_enabled=True,
            sign_in_aliases={"username": True, "email": True},
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True)
            )
        )

        # Create app client
        user_pool_client = user_pool.add_client("ava-app-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True
            )
        )

        # Create Identity Pool
        identity_pool = cognito.CfnIdentityPool(
            self, "MyIdentityPool",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=user_pool_client.user_pool_client_id,
                    provider_name=user_pool.user_pool_provider_name,
                    server_side_token_check=True
                )
            ]
        )
        authenticated_role = iam.Role(
            self, "CognitoDefaultAuthenticatedRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": identity_pool.ref
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    }
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity"
            )
        )

        # Attach the IAM role to the identity pool
        cognito.CfnIdentityPoolRoleAttachment(
            self, "IdentityPoolRoleAttachment",
            identity_pool_id=identity_pool.ref,
            roles={
                "authenticated": authenticated_role.role_arn
            }
        )

        # Add necessary permissions to the authenticated role
        authenticated_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    # Add required permissions here
                    "execute-api:Invoke",
                    # Add other necessary permissions
                ],
                resources=["*"]  # Restrict this to specific resources in production
            )
        )

        # Create Lambda function
        lambda_role = iam.Role(
            self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add Bedrock, SQS, and DynamoDB permissions
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:*",
                    "sqs:*",
                    "dynamodb:*"
                ],
                resources=["*"]
            )
        )

        # Create DynamoDB table
        dynamodb_table = aws_cdk.aws_dynamodb.Table(
            self, "AvaDataTable",
            table_name="ava-chatbot-tracking-table",
            partition_key=aws_cdk.aws_dynamodb.Attribute(
                name="chatbot_request_id", 
                type=aws_cdk.aws_dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=aws_cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
        )
        # Create SQS Queue
        queue = aws_cdk.aws_sqs.Queue(
            self, "AvaQueue",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(14)
        )

        # Create main Lambda function
        lambda_function = lambda_.Function(
            self, "AvaLambdaFunction",
            function_name="ava-api-lambda-function",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda"),
            role=lambda_role,
            timeout=Duration.seconds(30),
            environment={
                "DYNAMODB_TABLE": dynamodb_table.table_name,
                "SQS_QUEUE_URL": queue.queue_url
            }
        )

        # Create queue processor Lambda function
        queue_handler_role = iam.Role(
            self, "QueueHandlerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        queue_handler_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )

        # Add SQS permissions
        queue_handler_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
                resources=[queue.queue_arn]
            )
        )

        # Add DynamoDB permissions
        queue_handler_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:ConditionCheckItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:GetItem"
                ],
                resources=[dynamodb_table.table_arn]
            )
        )
        queue_handler_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:Retrieve",
                "bedrock:RetrieveAndGenerate",
                "bedrock:InvokeModel",
                "bedrock:GetKnowledgeBase",
                "bedrock:ListKnowledgeBases",
                "bedrock:GenerateQuery"
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}:{self.account}:knowledge-base/*",
                f"arn:aws:bedrock:{self.region}::foundation-model/*"
            ]
        ))
        queue_handler_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel*",
                "bedrock:CreateInferenceProfile",
                "bedrock:GetInferenceProfile",
                "bedrock:ListInferenceProfiles",
                "bedrock:DeleteInferenceProfile",
                "bedrock:TagResource",
                "bedrock:UntagResource",
                "bedrock:ListTagsForResource"
            ],
            resources=[
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:*:*:inference-profile/*",
                "arn:aws:bedrock:*:*:application-inference-profile/*",
            ]
        ))
        
        

        queue_handler = lambda_.Function(
            self, "QueueHandlerFunction",
            function_name="ava-queue-worker-lambda-function",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="queue_handler.handler",
            code=lambda_.Code.from_asset("lambda"),
            role=queue_handler_role,
            timeout=Duration.seconds(30),
            environment={
                "DYNAMODB_TABLE": dynamodb_table.table_name,
                "SQS_QUEUE_URL": queue.queue_url
            }
        )

        # Add SQS trigger to queue handler Lambda
        queue_handler.add_event_source(
            aws_cdk.aws_lambda_event_sources.SqsEventSource(queue)
        )

        # Add DynamoDB permissions to main Lambda
        dynamodb_table.grant_write_data(lambda_function)
        dynamodb_table.grant_read_data(lambda_function)
        dynamodb_table.grant_read_data(queue_handler)

        # Add SQS permissions to main Lambda
        queue.grant_send_messages(lambda_function)

        # Create API Gateway
        api = apigateway.RestApi(
            self, "AvaApi",
            rest_api_name="ava-api",
            endpoint_types=[apigateway.EndpointType.REGIONAL],
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
                # access_log_destination=apigateway.LogGroupLogDestination(self.api_gateway_log_group),
                tracing_enabled=True
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS
            ),
        )
        api.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["execute-api:Invoke"],
                principals=[iam.ArnPrincipal("*")],
                resources=["execute-api/*"],
            )
        )
        # Create API Gateway integration
        api_integration = apigateway.LambdaIntegration(lambda_function, timeout=Duration.seconds(29))
        # Add Cognito Authorizer
        auth = apigateway.CognitoUserPoolsAuthorizer(
            self, "AvaAuthorizer",
            cognito_user_pools=[user_pool]
        )
        
        # Add routes
        knowledge_bases = api.root.add_resource("knowledge-bases")
        knowledge_bases.add_method(
            "GET",
            integration=api_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=auth
        )

        models = api.root.add_resource("models")
        models.add_method(
            "GET",
            apigateway.LambdaIntegration(lambda_function)
        )

        chatbot = api.root.add_resource("chatbot")
        chatbot.add_method(
            "GET",
            integration=api_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=auth
        )
        chatbot.add_method(
            "POST",
            integration=api_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=auth
        )   

        # Create separate API Gateway for Vue.js Chatbot (Regional/Public)
        vuejs_api = apigateway.RestApi(
            self, "AvaApiVueJs",
            rest_api_name="ava-api-vuejs",
            endpoint_types=[apigateway.EndpointType.REGIONAL],
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
                tracing_enabled=True
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"]
            ),
        )
        
        vuejs_api.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["execute-api:Invoke"],
                principals=[iam.ArnPrincipal("*")],
                resources=["execute-api/*"],
            )
        )

        # Create API Gateway integration for Vue.js API
        vuejs_api_integration = apigateway.LambdaIntegration(lambda_function, timeout=Duration.seconds(29))
        
        # Add Cognito Authorizer for Vue.js API
        vuejs_auth = apigateway.CognitoUserPoolsAuthorizer(
            self, "AvaVueJsAuthorizer",
            cognito_user_pools=[user_pool]
        )
        
        # Add Vue.js chatbot routes to the new API Gateway
        vuejs_knowledge_bases = vuejs_api.root.add_resource("knowledge-bases")
        vuejs_knowledge_bases.add_method(
            "GET",
            integration=vuejs_api_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=vuejs_auth
        )

        vuejs_models = vuejs_api.root.add_resource("models")
        vuejs_models.add_method(
            "GET",
            integration=vuejs_api_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=vuejs_auth
        )

        vuejs_chatbot = vuejs_api.root.add_resource("chatbot")
        vuejs_chatbot.add_method(
            "GET",
            integration=vuejs_api_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=vuejs_auth
        )
        vuejs_chatbot.add_method(
            "POST",
            integration=vuejs_api_integration,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=vuejs_auth
        )




        
        # Add endpoint with authorization
        # api.root.add_method(
        #     "POST",
        #     api_integration,
        #     authorization_type=apigateway.AuthorizationType.COGNITO,
        #     authorizer=auth,
        #     method_responses=[
        #         apigateway.MethodResponse(
        #             status_code="200",
        #             response_parameters={
        #                 'method.response.header.Access-Control-Allow-Origin': True,
        #                 'method.response.header.Access-Control-Allow-Headers': True,
        #                 'method.response.header.Access-Control-Allow-Methods': True
        #             }
        #         )
        #     ]
        # )

        # api.root.add_method(
        #     "GET",
        #     api_integration,
        #     authorization_type=apigateway.AuthorizationType.COGNITO,
        #     authorizer=auth,
        #     method_responses=[
        #         apigateway.MethodResponse(
        #             status_code="200",
        #             response_parameters={
        #                 'method.response.header.Access-Control-Allow-Origin': True,
        #                 'method.response.header.Access-Control-Allow-Headers': True,
        #                 'method.response.header.Access-Control-Allow-Methods': True
        #             }
        #         )
        #     ]
        # )
             

        # Create Amplify app
     
        # Output values
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        CfnOutput(self, "IdentityPoolId", value=identity_pool.ref)
        CfnOutput(self, "ApiUrl", value=api.url)
        CfnOutput(self, "VueJsApiUrl", value=vuejs_api.url)
   
     