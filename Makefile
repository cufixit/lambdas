include ./makefile.env

.DEFAULT_GOAL := help
LAMBDAS := $(shell ls functions)

.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Build
.PHONY: build
build: $(addprefix build/,$(addsuffix .zip,$(LAMBDAS))) ## package all Lambda functions

.PHONY: rebuild
rebuild: clean build ## repackage all Lambda functions

.PHONY: build-%
build-% build/%.zip: functions/%/lambda_function.py functions/%/requirements.txt
	./package.sh $*

##@ Deploy
.PHONY: deploy
deploy: $(addprefix deploy-,$(LAMBDAS)) ## deploy all packaged Lambda functions to AWS

.PHONY: redeploy
redeploy: clean deploy ## repackage and deploy all Lambda functions to AWS

.PHONY: deploy-%
deploy-%: build/%.zip
	aws lambda update-function-code --no-cli-pager --function-name $* --zip-file fileb://build/$*.zip

##@ Upload
.PHONY: upload
upload: $(addprefix upload-,$(LAMBDAS)) ## upload all packaged Lambda functions to S3

.PHONY: reupload
reupload: clean upload ## repackage and upload all Lambda functions to S3

.PHONY: upload-%
upload-%: build/%.zip
	aws s3 cp build/$*.zip s3://$(LAMBDA_CODE_SOURCE_BUCKET)/functions/$*.zip

##@ Cleanup
.PHONY: clean
clean: ## remove all temporary files
	find . -type d -name "__pycache__" | xargs rm -rf {};
	rm -f *.zip
	rm -rf ./build
	rm -rf ./functions/*/package