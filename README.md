# Churn Prediction Pipeline with Argo Workflows and MLflow

This project demonstrates a churn prediction machine learning pipeline orchestrated by Argo Workflows on Kubernetes, with MLflow integration for experiment tracking and model management.

## Prerequisites

*   A running Kubernetes cluster (e.g., k3s, Minikube, EKS, GKE, AKS).
*   `kubectl` configured to interact with your cluster.
*   Argo Workflows installed in your cluster (e.g., in the `argowf` namespace).
*   An MLflow Tracking Server accessible from your Kubernetes cluster.
*   A PersistentVolumeClaim (PVC) available for storing data (e.g., `churn-data-pvc`).
*   Docker installed and configured if you need to rebuild and push custom images.

## Setup and Deployment

### 1. Prepare Data and Persistent Volume

Ensure your `WA_Fn-UseC_-Telco-Customer-Churn.csv` dataset is available. The following steps assume you'll copy it to a PVC.

```bash
# Apply the PersistentVolumeClaim manifest (if not already created)
# Ensure k8s/pvc.yaml defines your 'churn-data-pvc'
kubectl apply -f k8s/pvc.yaml

# (Optional) Verify PVC status
kubectl -n argowf describe pvc churn-data-pvc

# Create a temporary pod to copy data to the PVC
# Ensure k8s/copy-file-pod.yaml defines the 'copy-file-pod'
kubectl apply -f k8s/copy-file-pod.yaml

kubectl -n argowf exec -it copy-file-pod -- bash
  mkdir /opt/ml/processing/input
  exit

# Wait for the pod to be running, then copy the data
# Adjust the source path to your local CSV file
kubectl cp ../churn-prediction-pipeline/data/WA_Fn-UseC_-Telco-Customer-Churn.csv argowf/copy-file-pod:/opt/ml/processing/input/WA_Fn-UseC_-Telco-Customer-Churn.csv -n argowf

# (Optional) Clean up the copy pod
kubectl delete pod copy-file-pod -n argowf
```

### 2. (Optional) Rebuild and Push Docker Images

If you've made changes to the Python environments or need to include specific dependencies not present in the base images:

```bash
# Ensure Dockerfiles are in the project root
docker build -t jtayl22/preprocess:0.23-3 -f Dockerfile.preprocess .
docker build -t jtayl22/xgboost:1.5-2 -f Dockerfile.xgboost .

# Push images to your container registry
docker push jtayl22/preprocess:0.23-3
docker push jtayl22/xgboost:1.5-2
```
*Note: The provided `argowf.yaml` now includes `pip install` commands for dependencies as a fallback if they are not in the base images.*

### 3. Update and Apply Kubernetes Manifests

The Python scripts for preprocessing and training are managed via a ConfigMap.

```bash
# Run the script to generate/update the ConfigMap YAML from your Python scripts
bash scripts/update-configmap.sh

# Apply the generated ConfigMap to your cluster
kubectl apply -f k8s/churn-pipeline-scripts-configmap.yaml -n argowf

# Apply RBAC configuration (if not already applied)
# Ensure k8s/rbac.yaml contains your service account, role, and rolebinding
kubectl apply -f k8s/rbac.yaml -n argowf

# Verify RBAC components (optional)
kubectl -n argowf get serviceaccount argo-workflow
kubectl -n argowf get role workflow-role
kubectl -n argowf get rolebinding workflow-binding
```

### 4. Submit the Argo Workflow

Ensure your `argowf.yaml` is updated to:
*   Reference the `churn-pipeline-scripts` ConfigMap.
*   Pass the correct arguments to `preprocessing.py` and `xgboost_script.py`.
*   Set the `MLFLOW_TRACKING_URI` environment variable for the workflow steps.

```bash
# Delete existing workflow if needed (optional, good for clean runs)
argo -n argowf delete churn-pipeline

# Submit the workflow
argo submit -n argowf argowf.yaml
```

## Workflow Management and Monitoring

```bash
# List workflows
argo -n argowf list

# Get details of a specific workflow
argo -n argowf get churn-pipeline

# View logs for the entire workflow (or follow with -f)
argo -n argowf logs churn-pipeline
argo -n argowf logs -f churn-pipeline

# Access Argo UI (optional)
# kubectl -n argowf port-forward svc/argo-server 2746:2746 # If your service is argo-server
# # Open http://localhost:2746
```

**Useful CLI Commands:**

**Argo Workflows:**
*   `argo -n argowf list`: List all workflows in the `argowf` namespace.
*   `argo -n argowf get <workflow-name>`: Get the status and details of a specific workflow (e.g., `argo -n argowf get churn-pipeline`).
*   `argo -n argowf logs <workflow-name>`: View logs for all pods in a workflow.
*   `argo -n argowf logs -f <workflow-name>`: Follow logs for all pods in a workflow.
*   `argo -n argowf logs <pod-name>`: View logs for a specific pod within a workflow (e.g., `argo -n argowf logs churn-pipeline-preprocess-xxxx`).
*   `argo -n argowf delete <workflow-name>`: Delete a workflow.
*   `argo -n argowf submit <workflow-yaml-file>`: Submit a new workflow.
*   `argo -n argowf submit --watch <workflow-yaml-file>`: Submit and watch a workflow's progress.
*   `argo -n argowf resubmit <workflow-name>`: Resubmit a workflow.
*   `argo -n argowf retry <workflow-name>`: Retry a failed workflow from the point of failure.

**Kubernetes (`kubectl` - for deeper inspection):**
*   `kubectl -n argowf get pods`: List pods in the `argowf` namespace (useful to find specific pod names for `argo logs`).
*   `kubectl -n argowf describe pod <pod-name>`: Get detailed information about a pod, including events (very useful for debugging pod startup issues).
*   `kubectl -n argowf logs <pod-name>`: Get logs directly from a pod (sometimes `argo logs` might miss early container setup logs).
*   `kubectl -n argowf get cm churn-pipeline-scripts -o yaml`: View the content of your scripts ConfigMap.
*   `kubectl -n argowf get secret minio-credentials-wf -o yaml`: View the (base64 encoded) content of your MinIO credentials secret.

**MLflow CLI (less frequently used for day-to-day, GUI is primary):**
```bash
# Set the MLflow Tracking URI to your MLflow server
export MLFLOW_TRACKING_URI="http://192.168.1.85:30800"

# Search for experiments.
mlflow experiments search

# List runs for a specific experiment.
mlflow runs list --experiment-id "Churn_Prediction_Experiment"
```
## Troubleshooting

```bash
# Check workflow events
kubectl -n argowf get events --field-selector involvedObject.name=churn-pipeline

# Check specific step pod logs (replace <pod-suffix> with actual suffix)
# kubectl -n argowf logs churn-pipeline-preprocess-<pod-suffix>
# kubectl -n argowf logs churn-pipeline-train-<pod-suffix>

# Retry a failed workflow
argo -n argowf retry churn-pipeline

# Debug: Check if data files exist on PVC after preprocessing
# (Using the copy-file-pod temporarily if needed, or inspect via a debug pod)
# kubectl apply -f k8s/copy-file-pod.yaml # If deleted earlier
# kubectl -n argowf exec -it copy-file-pod -- find /opt/ml/processing -name "*.csv"
# kubectl -n argowf exec -it copy-file-pod -- ls -la /opt/ml/processing/output/train/
# kubectl -n argowf exec -it copy-file-pod -- ls -la /opt/ml/processing/output/test/
# kubectl delete pod copy-file-pod -n argowf # Clean up
```

## MLflow Integration

MLflow is a core component of this MLOps pipeline, used for managing the machine learning lifecycle.

**Key MLflow Features Used in This Project:**

*   **MLflow Tracking:**
    *   **Purpose:** To log and compare parameters, code versions, metrics, and output files (artifacts) from machine learning experiments.
    *   **Benefit:** Enables reproducibility of experiments, easy comparison of different model versions or hyperparameter settings, and a historical record of all training runs.
    *   **Usage:**
        *   The `preprocessing.py` script logs its parameters (like test split ratio) and the processed `train.csv` and `test.csv` files as artifacts.
        *   The `xgboost_script.py` logs hyperparameters (e.g., `max_depth`, `eta`), evaluation metrics (e.g., accuracy, AUC), and the trained XGBoost model itself as an artifact.
        *   Each script execution within the Argo workflow creates a new "run" under a defined "experiment" in MLflow (e.g., "Churn_Prediction_Experiment", "Churn_Prediction_XGBoost").

*   **MLflow Models (Implicitly via Artifact Logging):**
    *   **Purpose:** A convention for packaging machine learning models in multiple "flavors" that can be understood by downstream tools.
    *   **Benefit:** Simplifies model deployment and interoperability. By logging the XGBoost model using `mlflow.xgboost.log_model()`, it's stored in a standard format.
    *   **Usage:** The trained XGBoost model is logged, making it available for later inspection, sharing, or deployment through MLflow-compatible serving tools.

*   **MLflow UI:**
    *   **Purpose:** A web interface to visually browse experiments, compare runs, view logged metrics, parameters, and artifacts.
    *   **Benefit:** Provides an intuitive way to analyze experiment results without digging through logs or files manually.
    *   **Usage:** After the pipeline runs, you can access the MLflow UI (e.g., at `http://192.168.1.85:30800`) to see the details of the "Churn_Prediction_Experiment" and "Churn_Prediction_XGBoost" experiments and their respective runs.

**Benefits of Using MLflow in this Pipeline:**

*   **Reproducibility:** Easily track what code, data, and parameters were used to produce a specific model.
*   **Experiment Management:** Systematically organize and compare different training runs.
*   **Collaboration:** Share experiment results and models with team members.
*   **Foundation for Model Deployment:** Logged models are ready for deployment using MLflow's serving capabilities or other compatible tools.

**Accessing MLflow Data:**

*   **UI:** The primary way to interact with logged data is through the MLflow UI, accessible at your MLflow server's address (e.g., `http://192.168.1.85:30800`).
*   **CLI:** For programmatic access or quick checks (see "MLflow CLI" commands section).
*   **APIs:** MLflow provides Python, R, and Java APIs for more advanced programmatic interaction.

*Ensure your MLflow Tracking Server is running and accessible from the Kubernetes cluster.*
*The `MLFLOW_TRACKING_URI` environment variable in `argowf.yaml` must point to your MLflow server (e.g., `http://mlflow.mlflow.svc.cluster.local:5000`).*
*Experiments (`Churn_Prediction_Experiment`, `Churn_Prediction_XGBoost`) will be created in MLflow if they don't already exist.*
*Parameters, metrics, and the trained XGBoost model will be logged to MLflow for each run.*

## Model Deployment with Seldon Core

After successful training and evaluation, the pipeline can automatically deploy the trained XGBoost model as a REST API endpoint using Seldon Core.

### Prerequisites for Seldon Deployment

*   Seldon Core installed in your Kubernetes cluster.
*   The `argo-workflow` service account must have permissions to manage `SeldonDeployment` resources in the `argowf` namespace. Apply `k8s/seldon-rbac.yaml`:
    ```bash
    kubectl apply -f k8s/seldon-rbac.yaml
    ```
*   A ConfigMap containing the SeldonDeployment template must exist:
    ```bash
    kubectl create configmap seldon-churn-template --from-file=k8s/seldon-churn-deployment-template.yaml -n argowf
    ```
    (This step might be automated or handled differently in a production setup, e.g., by including the template directly in the Argo workflow or using a Helm chart).

### Deployment Process

1.  The `train` step in the Argo workflow trains the model and logs it to MLflow, outputting the MLflow model URI.
2.  The `deploy-seldon-model` step takes this URI.
3.  It uses a template (`k8s/seldon-churn-deployment-template.yaml`, made available via the `seldon-churn-template` ConfigMap) and injects the model URI into it.
4.  It then applies this manifest using `kubectl apply`, creating a `SeldonDeployment` named `churn-xgboost-model`.
5.  Seldon Core provisions the necessary pods and services to serve the model. The model artifacts are pulled from the S3/MinIO location specified by the model URI, using credentials from the `minio-credentials-wf` secret.

### Accessing the Deployed Model

Once the `SeldonDeployment` is ready, you can find its service. Seldon typically creates a service for each predictor.
```bash
kubectl get svc -n argowf | grep churn-xgboost-model
# Look for a service like churn-xgboost-model-default-churn-classifier or similar

# If you have an Ingress controller (like Nginx, Traefik) or a service mesh (like Istio with a gateway)
# configured to expose Seldon services, you'll use its external IP/port.
# Otherwise, for testing within the cluster or via port-forward:
kubectl port-forward svc/churn-xgboost-model-default-churn-classifier 9000:9000 -n argowf # Port 9000 is common for the component's HTTP endpoint
```

Then you can send prediction requests. For a Seldon model, the payload format is specific.
Example using `curl` (assuming port-forward is active on port 9000 to the component service):
```bash
curl -X POST -H "Content-Type: application/json" -d '{
    "data": {
        "ndarray": [[/* feature_vector_1 */], [/* feature_vector_2 */]]
    }
}' http://localhost:9000/api/v1.0/predictions
```
Replace `[[/* feature_vector_1 */]]` with actual numeric data matching your model's input features.

You can also use the `seldon-core-api-tester` tool if you have it.

### Seldon Core CLI Commands (kubectl)

Here are some useful `kubectl` commands for interacting with Seldon Core resources:

*   **List SeldonDeployments:**
    ```bash
    kubectl get seldondeployments -n argowf
    ```

*   **Describe a SeldonDeployment (shows status, events, and configuration):**
    ```bash
    kubectl describe seldondeployment <seldon-deployment-name> -n argowf
    # e.g., kubectl describe seldondeployment churn-xgboost-model -n argowf
    ```

*   **Get the YAML definition of a SeldonDeployment:**
    ```bash
    kubectl get seldondeployment <seldon-deployment-name> -n argowf -o yaml
    ```

*   **Delete a SeldonDeployment (this will remove the model server and associated resources):**
    ```bash
    kubectl delete seldondeployment <seldon-deployment-name> -n argowf
    ```

*   **Check logs of the Seldon model server pods:**
    First, find the pod name:
    ```bash
    kubectl get pods -n argowf -l seldon-deployment-id=<seldon-deployment-name>
    # e.g., kubectl get pods -n argowf -l seldon-deployment-id=churn-xgboost-model
    ```
    Then, view logs (replace `<pod-name>` and `<container-name>`):
    ```bash
    # Logs for the model initializer (rclone)
    kubectl logs <pod-name> -n argowf -c <graph-component-name>-model-initializer
    # e.g., kubectl logs churn-xgboost-model-default-0-churn-classifier-xxxx -n argowf -c churn-classifier-model-initializer

    # Logs for the main model server container
    kubectl logs <pod-name> -n argowf -c <graph-component-name>
    # e.g., kubectl logs churn-xgboost-model-default-0-churn-classifier-xxxx -n argowf -c churn-classifier
    ```
    *(The exact container names can be found by describing the pod: `kubectl describe pod <pod-name> -n argowf`)*

*   **Check Seldon Controller Manager logs (for debugging Seldon Core itself):**
    (Assuming Seldon is installed in `seldon-system` namespace)
    ```bash
    kubectl logs -n seldon-system -l control-plane=seldon-controller-manager -f
    ```