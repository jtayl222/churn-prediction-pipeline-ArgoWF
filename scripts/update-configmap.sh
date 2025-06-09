#!/bin/bash
# update-configmap.sh for churn-prediction-pipeline

set -e

# Define the namespace
NAMESPACE="argowf" # Or your target namespace

# Define the ConfigMap name
CONFIGMAP_NAME="churn-pipeline-scripts"

# Define the output YAML file
OUTPUT_YAML="k8s/${CONFIGMAP_NAME}-configmap.yaml" # Storing k8s manifests in a k8s/ directory is common

# Ensure the output directory exists
mkdir -p "$(dirname "$OUTPUT_YAML")"

# Create/update the ConfigMap
# Add --from-file for each script you want to include.
# The key in the ConfigMap will be the filename (e.g., preprocessing.py).
kubectl create configmap "${CONFIGMAP_NAME}" \
  --from-file=preprocessing.py=scripts/preprocessing.py \
  --from-file=xgboost_script.py=scripts/xgboost_script.py \
  --from-file=evaluation_script.py=scripts/evaluation_script.py \
  --namespace="${NAMESPACE}" \
  --dry-run=client -o yaml | \
  grep -v "creationTimestamp" > "${OUTPUT_YAML}"

echo "ConfigMap ${CONFIGMAP_NAME} YAML updated successfully at ${OUTPUT_YAML}!"
echo "To apply, run: kubectl apply -f ${OUTPUT_YAML}"