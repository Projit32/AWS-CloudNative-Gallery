import shutil
from os import remove

import boto3
import os

s3 = boto3.resource("s3")

def zip_folder_with_shutil(source_folder, output_path):
   shutil.make_archive(output_path, 'zip', source_folder)
   print("Done Zipping")

def upload_file_to_s3(file_path, s3_bucket, s3_key):
   s3.Bucket(s3_bucket).upload_file(file_path, s3_key)
   print("Done Upload")

def delete_file(file_path):
   os.remove(file_path)


if __name__ == "__main__":

   source = "G:\\image-gallery-aws\\Lambda-Layer\\API registry Layer\\src\\"
   zip_path = "G:\\image-gallery-aws\\Lambda-Layer\\APIRegistryLayer"
   zip_folder_with_shutil(source, zip_path)
   upload_file_to_s3(zip_path+".zip", "aws-sam-cli-managed-default-samclisourcebucket-zkhbofflf4v1", "layer/ApiRegistry.zip")
   remove(zip_path+".zip")