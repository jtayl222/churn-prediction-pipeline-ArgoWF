# here

```bash

kubectl apply -f pvc.yaml

kubectl -n argowf describe  pvc churn-data-pv

kubectl apply -f copy-file-pod.yaml

kubectl -n argowf exec -it copy-file-pod -- bash

kubectl cp  ../churn-prediction-pipeline/data/WA_Fn-UseC_-Telco-Customer-Churn.csv  argowf/copy-file-pod:/opt/ml/processing/input/WA_Fn-UseC_-Telco-Customer-Churn.csv

```

## Rebuild and Deploy

```bash
# Rebuild Docker images with MLflow
docker build -t jtayl22/sklearn:0.23-3 -f Dockerfile.sklearn .
docker build -t jtayl22/xgboost:1.5-2 -f Dockerfile.xgboost .

# Push images
docker push jtayl22/sklearn:0.23-3
docker push jtayl22/xgboost:1.5-2

# Update ConfigMap
kubectl apply -f config-map.yaml

# Apply workflow
kubectl apply -f argowf.yaml
```

## RBAS

```bash
# Apply RBAC configuration
kubectl apply -f rbac.yaml

# Verify the service account was created
kubectl -n argowf get serviceaccount argo-workflow

# Verify the role and rolebinding
kubectl -n argowf get role workflow-role
kubectl -n argowf get rolebinding workflow-binding

# Apply the updated workflow
kubectl apply -f argowf.yaml

# Submit the workflow
argo submit -n argowf argowf.yaml
```

## Churn Prediction Pipeline

```bash
argo -n argowf list
argo -n argowf get churn-pipeline
argo -n argowf logs churn-pipeline
 ```