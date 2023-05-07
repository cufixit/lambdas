include ./makefile.env

.DEFAULT_GOAL := help
LAMBDAS := $(shell ls functions)
LAYERS := $(shell ls layers)

.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Build
.PHONY: build
build: build-functions build-layers ## package all Lambda functions and layers

.PHONY: build-functions
build-functions: $(addprefix build/functions/,$(addsuffix .zip,$(LAMBDAS))) ## package all Lambda functions

.PHONY: build-layers
build-layers: $(addprefix build/layers/,$(addsuffix .zip,$(LAYERS))) ## package all Lambda layers

.PHONY: rebuild
rebuild: clean build ## repackage all Lambda functions

.PHONY: build-function-%
build-function-% build/functions/%.zip: functions/%/lambda_function.py functions/%/requirements.txt
	./package-function.sh $*

.PHONY: build-layer-%
build-layer-% build/layers/%.zip: layers/%/*.py layers/%/requirements.txt
	./package-layer.sh $*

##@ Deploy
.PHONY: deploy
deploy: deploy-functions deploy-layers ## deploy all packaged Lambda functions and layers to AWS

.PHONY: deploy-functions
deploy-functions: $(addprefix deploy-layer-,$(LAMBDAS)) ## deploy all packaged Lambda functions to AWS

.PHONY: deploy-layers
deploy-layers: $(addprefix deploy-layer-,$(LAYERS)) ## deploy all packaged Lambda layers to AWS

.PHONY: redeploy
redeploy: clean deploy ## repackage and deploy all Lambda functions to AWS

.PHONY: deploy-function-%
deploy-function-%: build/functions/%.zip
	aws lambda update-function-code --no-cli-pager --function-name $* --zip-file fileb://build/functions/$*.zip

.PHONY: deploy-layer-%
deploy-layer-%: build/layers/%.zip
	aws lambda publish-layer-version --no-cli-pager --layer-name $* --zip-file fileb://build/layers/$*.zip

##@ Upload
.PHONY: upload
upload: upload-functions upload-layers ## upload all packaged Lambda functions and layers to S3

.PHONY: upload-functions
upload-functions: $(addprefix upload-function-,$(LAMBDAS)) ## upload all packaged Lambda functions to S3

.PHONY: upload-layers
upload-layers: $(addprefix upload-layer-,$(LAYERS)) ## upload all packaged Lambda layers to S3

.PHONY: reupload
reupload: clean upload ## repackage and upload all Lambda functions to S3

.PHONY: upload-function-%
upload-function-%: build/functions/%.zip
	aws s3 cp build/functions/$*.zip s3://$(LAMBDA_CODE_SOURCE_BUCKET)/functions/$*.zip

.PHONY: upload-layer-%
upload-layer-%: build/layers/%.zip
	aws s3 cp build/layers/$*.zip s3://$(LAMBDA_CODE_SOURCE_BUCKET)/layers/$*.zip

##@ Cleanup
.PHONY: clean
clean: ## remove all temporary files
	find . -type d -name "__pycache__" | xargs rm -rf {};
	rm -f *.zip
	rm -rf ./build
	rm -rf ./functions/*/package