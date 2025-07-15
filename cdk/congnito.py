from aws_cdk import (
    Duration,
    aws_cognito as cognito,
    aws_ssm as ssm,
        RemovalPolicy,
)
from constructs import Construct

from infrastructure.user_pool_add_user import UserPoolAddUser

class CognitoConstruct(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        
        self.user_pool = cognito.UserPool(self, "AVAUserPool",
            user_pool_name="ava-user-pool",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=True
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True)
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        self.user_pool_client = self.user_pool.add_client("AVAWebClient",
            access_token_validity=Duration.minutes(60),
            id_token_validity=Duration.days(1),
            refresh_token_validity=Duration.days(1),
            auth_flows=cognito.AuthFlow(admin_user_password=True, user_password=True),

            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=True
                ),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE],
                callback_urls=["http://localhost:3000"]
            ),
        )        

        self.group  = cognito.UserPoolGroup(self, "AdminGroup",
            group_name="admins",
            description="Group for admins",
            user_pool=self.user_pool
        )

        user = UserPoolAddUser(
            self, "admin",
            user_pool=self.user_pool,
            username="admin",
            password="Qwerty!234",
            attributes=[
                {"Name": "email", "Value": "admin@amazon.com"},
                {"Name": "email_verified", "Value": "true"}
            ],
            group_name="admins"
        )

        self.user_pool_id = ssm.StringParameter(self, "AVA UserPoolId",
            parameter_name="/ava/auth/user-pool-id",
            string_value=self.user_pool.user_pool_id,
        )

        self.client_id = ssm.StringParameter(self, "AVA UserPoolClientId",
            parameter_name="/ava/auth/client-id",
            string_value=self.user_pool_client.user_pool_client_id,
        )
