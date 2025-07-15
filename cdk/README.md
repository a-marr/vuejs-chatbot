# Infrastructure Setup

This directory contains the AWS CDK infrastructure code for the Ava UI project.

## Prerequisites

- AWS CDK CLI
- Python 3.11 or later
- Node.js 14 or later

## Installation

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Deploy the stack:
```bash
cdk deploy
```

## Stack Components

- Cognito User Pool and Identity Pool for authentication
- API Gateway with Cognito authorization
- Lambda function with Bedrock knowledge base integration
- S3 bucket for Bedrock knowledge base storage
- Required IAM roles and policies

## Outputs

The stack will output:
- User Pool ID
- User Pool Client ID
- Identity Pool ID
- API Gateway URL

Use these values in your Vue.js application's environment variables.