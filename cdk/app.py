#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.main_stack import MainStack

APP_NAME = "ava"


app = cdk.App()
MainStack(app, f"{APP_NAME}-ui-stack",
    stack_name=f"{APP_NAME}-ui-stack",
    description=f"Infrastructure stack for {APP_NAME} UI",
    tags={
        'app': APP_NAME,
        'environment': 'prod'  # You might want to make this configurable
    }
)
app.synth()