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


# Create/update the MinIO credentials secret for Seldon
echo "Creating/Updating MinIO credentials secret 'minio-credentials-wf' with rclone specific keys..."
kubectl create secret generic minio-credentials-wf \
  --from-literal=RCLONE_CONFIG_S3_TYPE="s3" \
  --from-literal=RCLONE_CONFIG_S3_PROVIDER="Minio" \
  --from-literal=RCLONE_CONFIG_S3_ENV_AUTH="false" \
  --from-literal=RCLONE_CONFIG_S3_ACCESS_KEY_ID="${MINIO_ROOT_USER}" \
  --from-literal=RCLONE_CONFIG_S3_SECRET_ACCESS_KEY="${MINIO_ROOT_PASSWORD}" \
  --from-literal=RCLONE_CONFIG_S3_ENDPOINT="http://minio.minio.svc.cluster.local:9000" \
  -n "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# For reference, also include the AWS specific keys if other components might still expect them,
# though for rclone via Seldon's default initializer, the RCLONE_CONFIG_ vars are primary.
# If you are sure nothing else needs the AWS_ prefixed vars from this secret, you can omit the next command.
echo "Creating/Updating MinIO credentials secret 'minio-credentials-wf' with AWS prefixed keys (for compatibility)..."
kubectl create secret generic minio-credentials-aws-compat \
  --from-literal=AWS_ACCESS_KEY_ID="${MINIO_ROOT_USER}" \
  --from-literal=AWS_SECRET_ACCESS_KEY="${MINIO_ROOT_PASSWORD}" \
  --from-literal=MLFLOW_S3_ENDPOINT_URL="http://minio.minio.svc.cluster.local:9000" \
  --from-literal=AWS_ENDPOINT_URL="http://minio.minio.svc.cluster.local:9000" \
  -n "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
# Note: Seldon's envSecretRefName will only pull from ONE secret.
# If you need both sets of vars, they must be in the *same* secret referenced by envSecretRefName.
# Let's put them all in minio-credentials-wf for simplicity if Seldon merges them,
# or prioritize RCLONE_CONFIG vars.
# For now, the first secret creation for minio-credentials-wf with RCLONE_ vars is the critical one.
# You might need to merge these if Seldon doesn't overlay them from multiple secrets or if other tools need AWS_ vars from the *same* secret.

# Safer approach: Put all needed variables in the single 'minio-credentials-wf' secret.
# Seldon's default initializer will primarily look for RCLONE_CONFIG_S3_*,
# but other tools might use AWS_*.

set -x

kubectl delete secret minio-credentials-wf -n "${NAMESPACE}" --ignore-not-found=true # Delete to recreate with all keys
echo "Recreating MinIO credentials secret 'minio-credentials-wf' with ALL rclone and AWS keys..."
kubectl create secret generic minio-credentials-wf \
  --from-literal=RCLONE_CONFIG_S3_TYPE="s3" \
  --from-literal=RCLONE_CONFIG_S3_PROVIDER="Minio" \
  --from-literal=RCLONE_CONFIG_S3_ENV_AUTH="false" \
  --from-literal=RCLONE_CONFIG_S3_ACCESS_KEY_ID="${MINIO_ROOT_USER}" \
  --from-literal=RCLONE_CONFIG_S3_SECRET_ACCESS_KEY="${MINIO_ROOT_PASSWORD}" \
  --from-literal=RCLONE_CONFIG_S3_ENDPOINT="http://minio.minio.svc.cluster.local:9000" \
  --from-literal=AWS_ACCESS_KEY_ID="${MINIO_ROOT_USER}" \
  --from-literal=AWS_SECRET_ACCESS_KEY="${MINIO_ROOT_PASSWORD}" \
  --from-literal=MLFLOW_S3_ENDPOINT_URL="http://minio.minio.svc.cluster.local:9000" \
  --from-literal=AWS_ENDPOINT_URL="http://minio.minio.svc.cluster.local:9000" \
  -n "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

kubectl get secret generic minio-credentials-wf -o yaml -n "${NAMESPACE}" 