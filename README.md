# Lambda Functions

To set up a new Lambda function, create a new subdirectory under `functions/` with the name of the Lambda, and create a `lambda_function.py` and `requirements.txt` within it. For example:

```shell
mkdir -p functions/<lambda-name>
touch functions/<lambda-name>/lambda_function.py
touch functions/<lambda-name>/requirements.txt
```

Run `make build` to build and package all Lambda functions and their dependencies. Alternatively, to package a specific Lambda function, run

```shell
make build-<lambda-name>
```

Run `make upload` to upload all packaged Lambda functions to the code source S3 bucket, where the Lambda deployment packages will be fetched from when they are first created through CloudFormation. Alternatively, to upload a specific Lambda function, run

```shell
make upload-<lambda-name>
```

Run `make deploy` to deploy all packaged Lambda functions to AWS. Alternatively, to deploy a specific Lambda function, run

```shell
make deploy-<lambda-name>
```

Run `make clean` to remove all temporary files generated in the build process.
