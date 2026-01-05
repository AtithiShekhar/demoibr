import boto3

def check_boto3_version():
    version = boto3.__version__
    print(f"📦 boto3 version: {version}")