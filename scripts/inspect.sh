#!/bin/bash

set -x

kubectl -n argowf get all

# Watch the new workflow
argo get -n argowf churn-pipeline

# Check workflow events
kubectl -n argowf get events --field-selector involvedObject.name=churn-pipeline

# Check specific step logs
argo -n argowf logs churn-pipeline --container preprocess
argo -n argowf logs churn-pipeline --container train
argo -n argowf logs churn-pipeline --container evaluate


# Get logs from specific workflow steps (correct syntax)
argo -n argowf logs churn-pipeline --container main | grep -v "Requirement already satisfied" | tail -20

# Or get logs from specific pods
for pod in $(kubectl -n argowf get pods -l workflows.argoproj.io/workflow=churn-pipeline -o jsonpath='{.items[*].metadata.name}'); do
    echo "Logs for pod: $pod"
    kubectl -n argowf logs $pod --container main | grep -v "Requirement already satisfied" | tail -20
done

# Get all workflow logs
argo -n argowf logs churn-pipeline | grep -v "Requirement already satisfied"  | tail -20
