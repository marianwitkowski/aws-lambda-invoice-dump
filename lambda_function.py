import datetime
import boto3
from io import BytesIO
import zipfile
import os


def send_ses(url):
    client = boto3.client('ses')
    from_email = os.environ["SES_EMAIL_IDENTITY"]

    email_message = {
        'Body': {
            'Html': {
                'Charset': 'utf-8',
                'Data': f"Archiwum faktur do pobrania z {url} ",
            },
        },
        'Subject': {
            'Charset': 'utf-8',
            'Data': "Pozdrowienia z firmy XYZ sp. z o.o.",
        },
    }

    ses_response = client.send_email(
        Destination={
            'ToAddresses': [os.environ["SES_EMAIL_DEST"]],
        },
        Message=email_message,
        Source=from_email,
    )
    print(f"ses response id received: {ses_response['MessageId']}.")


def create_zip_dump(bucket_name, bucket_file_path, output_fn):
    s3 = boto3.resource('s3')

    response = {}
    bucket = s3.Bucket(bucket_name)
    files_collection = bucket.objects.filter(Prefix=bucket_file_path).all()
    archive = BytesIO()

    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zip_archive:
        for file in files_collection:
            with zip_archive.open(file.key, 'w') as file1:
                file1.write(file.get()['Body'].read())

    archive.seek(0)
    s3.Object(bucket_name, bucket_file_path + '/' + output_fn + '.zip').upload_fileobj(archive)
    archive.close()

    expiry = int(os.environ["EXPIRY_HOURS"]) * 3600
    s3_client = boto3.client('s3')
    url = s3_client.generate_presigned_url('get_object',
                                           Params={'Bucket': bucket_name,
                                                   'Key': '' + bucket_file_path + '/' + output_fn + '.zip'},
                                           ExpiresIn=expiry)

    return url


def lambda_handler(event, context):
    full_month = f"{datetime.date.today().month:02d}"
    dump_url = create_zip_dump("invoices-company", full_month, f"dump-{full_month}")
    send_ses(dump_url)
    return "{}"
