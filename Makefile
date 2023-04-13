.DEFAULT_GOAL := help

.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Build
.PHONY: build
build: handle-new-report ## package all Lambda functions

.PHONY: handle-new-report
handle-new-report: handle-new-report.zip ## package handle-new-report Lambda function

.PHONY: rebuild
rebuild: clean build ## repackage all Lambda functions

handle-new-report.zip: handle-new-report/lambda_function.py handle-new-report/requirements.txt
	./package.sh handle-new-report

##@ Deploy
.PHONY: deploy
deploy: deploy-handle-new-report ## deploy all packaged Lambda functions to AWS

.PHONY: deploy-handle-new-report
deploy-handle-new-report: handle-new-report.zip ## deploy packaged handle-new-report Lambda code to AWS
	aws lambda update-function-code --no-cli-pager --function-name handle-new-report --zip-file fileb://handle-new-report.zip

.PHONY: redeploy
redeploy: clean deploy ## repackage and deploy all Lambda functions

##@ Cleanup
.PHONY: clean
clean: ## remove all temporary files
	find . -type d -name "__pycache__" | xargs rm -rf {};
	rm -f *.zip
	rm -rf */package