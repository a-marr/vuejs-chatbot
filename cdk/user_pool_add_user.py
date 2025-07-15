from constructs import Construct
from aws_cdk import (
    aws_cognito as cognito,
    custom_resources as cr,
)

class UserPoolAddUser(Construct):
    def __init__(self, scope: Construct, id: str, *, 
                 user_pool: cognito.IUserPool,
                 username: str,
                 password: str,
                 attributes: list[dict[str, str]] = None,
                 group_name: str = None):
        """
        Create a Cognito User Pool User with optional group attachment
        
        Args:
            scope: CDK Construct scope
            id: Construct ID
            user_pool: Cognito User Pool
            username: Username for the new user
            password: Password for the new user
            attributes: Optional list of user attributes [{"Name": "name", "Value": "value"}]
            group_name: Optional group to add the user to
        """
        super().__init__(scope, id)

        # Create the user inside the Cognito user pool using Lambda backed AWS Custom resource
        admin_create_user = cr.AwsCustomResource(
            self, 'AwsCustomResource-CreateUser',
            on_create=cr.AwsSdkCall(
                service='CognitoIdentityServiceProvider',
                action='adminCreateUser',
                parameters={
                    'UserPoolId': user_pool.user_pool_id,
                    'Username': username,
                    'MessageAction': 'SUPPRESS',
                    'TemporaryPassword': password,
                    'UserAttributes': attributes or [],
                    'Permanent': True
                },
                physical_resource_id=cr.PhysicalResourceId.of(f'AwsCustomResource-CreateUser-{username}')
            ),
            on_update=cr.AwsSdkCall(
                service='CognitoIdentityServiceProvider',
                action='adminUpdateUserAttributes',
                parameters={
                    'UserPoolId': user_pool.user_pool_id,
                    'Username': username,
                    'UserAttributes': attributes or [],
                    'Permanent': True
                },
                physical_resource_id=cr.PhysicalResourceId.of(f'AwsCustomResource-CreateUser-{username}')
            ),
            on_delete=cr.AwsSdkCall(
                service='CognitoIdentityServiceProvider',
                action='adminDeleteUser',
                parameters={
                    'UserPoolId': user_pool.user_pool_id,
                    'Username': username,
                }
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            install_latest_aws_sdk=True
        )
        admin_set_user = cr.AwsCustomResource(
            self, 'AwsCustomResource-SetUser',
            on_create=cr.AwsSdkCall(
                service='CognitoIdentityServiceProvider',
                action='adminSetUserPassword',
                parameters={
                    'UserPoolId': user_pool.user_pool_id,
                    'Username': username,
                    'MessageAction': 'SUPPRESS',
                    'Password': password,
                    'Permanent': True
                },
                physical_resource_id=cr.PhysicalResourceId.of(f'AwsCustomResource-SetUser-{username}')
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
            install_latest_aws_sdk=True
		)
        admin_set_user.node.add_dependency(admin_create_user)

        # If a Group Name is provided, also add the user to this Cognito UserPool Group
        if group_name:
            user_to_group_attachment = cognito.CfnUserPoolUserToGroupAttachment(
                self, 'AttachUserToGroup',
                user_pool_id=user_pool.user_pool_id,
                group_name=group_name,
                username=username
            )
            user_to_group_attachment.node.add_dependency(admin_create_user)
            user_to_group_attachment.node.add_dependency(admin_set_user)
            user_to_group_attachment.node.add_dependency(user_pool)
