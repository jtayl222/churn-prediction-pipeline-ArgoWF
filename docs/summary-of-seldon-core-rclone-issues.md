# Summary of Seldon Core Rclone and Model Serving Issues Encountered

This document summarizes the challenges and resolutions encountered while configuring Seldon Core to download a model from a MinIO S3-compatible store using `rclone` and serve it.

## 1. Initial Goal: Model Download from MinIO

The primary goal was to have a SeldonDeployment download an XGBoost model, saved by an MLflow pipeline, from a MinIO bucket and serve it.

## 2. Challenge: Rclone Configuration for MinIO

Seldon Core's default storage initializer uses `rclone`. Standard `rclone` often requires a configuration file (`rclone.conf`) to define remotes, especially for S3-compatible providers like MinIO that need a specific endpoint URL.

### Attempt 1: Custom InitContainer with `rclone.conf` VolumeMount

*   **Approach:**
    *   Create a Kubernetes `ConfigMap` (`rclone-config`) containing a valid `rclone.conf` for MinIO.
    *   Define a custom `initContainer` in the `SeldonDeployment`'s `componentSpecs`.
    *   Mount the `rclone-config` `ConfigMap` as a volume into the custom `initContainer` at `/root/.config/rclone/rclone.conf`.
    *   The custom `initContainer` would execute an `rclone copy` command.
    *   Explicitly define an `emptyDir` volume named `churn-classifier-provision-location` in `componentSpecs.spec.volumes` for the model.
*   **Problem Encountered:**
    *   `Deployment.apps "churn-xgboost-model-default-0-churn-classifier" is invalid: spec.template.spec.volumes[...].name: Duplicate value: "churn-classifier-provision-location"`
    *   **Reason:** Seldon Core, when a `modelUri` is specified for a graph component, automatically creates an `emptyDir` volume named `<component-name>-provision-location` for its *own* default model initializer. Explicitly defining a volume with the same name caused a conflict.
*   **Resolution (Partial):**
    *   Removed the explicit definition of `churn-classifier-provision-location` from `componentSpecs.spec.volumes`. The `volumeMounts` in the custom initContainer and main container would then refer to the Seldon-managed volume.

### Attempt 2: Custom InitContainer - Accessing `modelUri`

*   **Problem Encountered:**
    *   The custom `initContainer` needed the `modelUri` (e.g., `s3://mlflow-artifacts/...`) to pass to its `rclone copy` command.
    *   It was discovered that Seldon Core does **not** automatically pass the `graph.modelUri` as an environment variable to custom `initContainers` defined in `componentSpecs`.
*   **Considered Workaround:**
    *   Pass the `modelUri` (after Argo placeholder replacement) as an explicit environment variable to the custom `initContainer` within the `SeldonDeployment` template. This would work but adds complexity and potential redundancy if Seldon's default initializer also runs.

## 3. Solution Path: Leveraging Seldon's Default Initializer with Environment Variables

*   **Discovery:** Seldon Core's `rclone-storage-initializer` (the default one) can be configured entirely through environment variables, following the pattern `RCLONE_CONFIG_<REMOTE_NAME>_<CONFIG_KEY>=<VALUE>`. This is the idiomatic Seldon way to handle custom S3 providers.
*   **Approach:**
    1.  **Modify `minio-credentials-wf` Secret:**
        *   The Kubernetes `Secret` referenced by `envSecretRefName` in the `SeldonDeployment`'s graph node (`churn-classifier`) was updated.
        *   Instead of (or in addition to) generic `AWS_ACCESS_KEY_ID`, etc., it was populated with `rclone`-specific keys for an S3 remote (Seldon's initializer defaults to using a remote named `s3` if the `modelUri` starts with `s3://`):
            *   `RCLONE_CONFIG_S3_TYPE="s3"`
            *   `RCLONE_CONFIG_S3_PROVIDER="Minio"`
            *   `RCLONE_CONFIG_S3_ENV_AUTH="false"`
            *   `RCLONE_CONFIG_S3_ACCESS_KEY_ID="minioadmin"`
            *   `RCLONE_CONFIG_S3_SECRET_ACCESS_KEY="minioadmin123"`
            *   `RCLONE_CONFIG_S3_ENDPOINT="http://minio.minio.svc.cluster.local:9000"`
    2.  **Simplify `SeldonDeployment` Template:**
        *   Removed the custom `initContainer` entirely.
        *   Removed the `rclone-config` `ConfigMap` and its associated `volumeMounts`.
        *   Relied solely on Seldon's default initContainer, which would now be correctly configured by the environment variables from the `minio-credentials-wf` secret.
*   **Outcome - Model Download Success:**
    *   Seldon's default `churn-classifier-model-initializer` initContainer started.
    *   Logs showed: `NOTICE: Config file "/.rclone.conf" not found - using defaults`. This is benign because the environment variables successfully configured the `s3` remote for rclone.
    *   The model artifacts were successfully downloaded from MinIO to `/mnt/models`.

## 4. Subsequent Challenge: `XGBoostServer` Fails to Load Model (`model.bst` not found)

*   **Problem Encountered:**
    *   After the model successfully downloaded, the main `churn-classifier` container (running `seldonio/xgboostserver:1.17.1`) failed to become ready.
    *   The `seldon-container-engine` logs showed readiness probe failures: `dial tcp [::1]:9000: connect: connection refused`.
    *   Logs from the `churn-classifier` container revealed the root cause:
        ```
        xgboost.core.XGBoostError: ... LocalFileSystem::Open "/mnt/models/model.bst": No such file or directory
        ```
*   **Reason:**
    *   The MLflow pipeline saved the XGBoost model as `model.xgb`.
    *   The `seldonio/xgboostserver` by default was trying to load a model file named `model.bst` from the `MLSERVER_MODEL_URI` (`/mnt/models`).
*   **Attempted Resolution:** Specifying `model_file_name` parameter for `XGBOOST_SERVER`.
    *   Added a `parameters` section to the `SeldonDeployment` graph node:
        ```yaml
        parameters:
        - name: model_file_name
          type: STRING
          value: "model.xgb"
        ```

## 5. Challenge: `XGBoostServer` Constructor `TypeError`

*   **Problem Encountered:**
    *   With the `model_file_name` parameter added, the `churn-classifier` container failed to start with a new error:
        ```
        Traceback (most recent call last):
          File "/opt/conda/bin/seldon-core-microservice", line 8, in <module>
            sys.exit(main())
          File "/opt/conda/lib/python3.8/site-packages/seldon_core/microservice.py", line 619, in main
            user_object = user_class(**parameters)
        TypeError: __init__() got an unexpected keyword argument 'model_file_name'
        ```
*   **Reason:**
    *   The `XGBoostServer` class in `seldonio/xgboostserver:1.17.1` does not accept `model_file_name` as a parameter in its `__init__` constructor.
    *   It hardcodes the model file name it looks for (typically `model.bst`) inside its `load()` method.

## 6. Resolution Path: Switching to `MLFLOW_SERVER`
*   Changed the `implementation` in the `SeldonDeployment` from `XGBOOST_SERVER` to `MLFLOW_SERVER`.
*   Removed the `parameters` section for `model_file_name`, as `MLFLOW_SERVER` interrogates the `MLmodel` file to determine model details.
*   **Modification to `seldon-churn-deployment-template.yaml`:**
    ```yaml
    # ...
    predictors:
    - graph:
        implementation: MLFLOW_SERVER # Changed from XGBOOST_SERVER
        modelUri: MODEL_ARTIFACT_URI_PLACEHOLDER
        name: churn-classifier
        envSecretRefName: minio-credentials-wf
        # Parameters for model_file_name removed
      name: default
    # ...
    ```
*   **Expected Outcome (at the time of switching):**
    *   The `MLFLOW_SERVER` will correctly parse the `MLmodel` file located in `/mnt/models` (downloaded by the rclone initContainer).
    *   It will identify and load the `model.xgb` file as specified in the `MLmodel` artifact.
    *   The `churn-classifier` container should start successfully, and the pod should become ready.

## 7. Current Challenge & Resolution: `MLFLOW_SERVER` OOMKilled During Conda Environment Creation

*   **Symptoms:**
    *   The `churn-classifier-model-initializer` (rclone initContainer) **completes successfully**.
    *   The main `churn-classifier` container (running `MLFLOW_SERVER`) starts, begins creating the Conda environment, and then the pod goes into `CrashLoopBackOff`.
    *   `kubectl describe pod <pod_name>` reveals the `churn-classifier` container's `lastState` as:
        ```yaml
        lastState:
          terminated:
            exitCode: 137
            reason: OOMKilled
        ```
*   **Reason:** The Conda environment creation process for the specified `conda.yaml` requires more memory than the container's defined limit (which was previously 4Gi). `exitCode: 137` signifies an OOMKill.
*   **Solution:**
    1.  **Increase Memory Limits:** Modify the `seldon-churn-deployment-template.yaml` to provide a higher memory limit to the `churn-classifier` container. For example, increase from `4Gi` to `6Gi` or `8Gi`.
        ```yaml
        # k8s/seldon-churn-deployment-template.yaml
        # ...
              resources:
                requests:
                  cpu: "1"
                  memory: 2Gi # Or adjust as needed
                limits:
                  cpu: "2"
                  memory: 6Gi # Example of increased limit
        # ...
        ```
    2.  Re-apply the `SeldonDeployment`.
*   **Status:** Actively testing with increased memory limits.


## 8. Current Challenge: `MLFLOW_SERVER` Container Terminates with Exit Code 143 (SIGTERM)

*   **Symptoms:**
    *   The `churn-classifier-model-initializer` (rclone initContainer) **completes successfully**.
    *   The main `churn-classifier` container (running `MLFLOW_SERVER` with increased memory limits, e.g., 8Gi) starts, begins creating the Conda environment, and then the pod goes into `CrashLoopBackOff`.
    *   `kubectl describe pod <pod_name>` (or `get pod <pod_name> -o yaml`) shows the `churn-classifier` container's `lastState` as:
        ```yaml
        lastState:
          terminated:
            exitCode: 143 # Indicates termination by SIGTERM
            reason: Error # Not OOMKilled in this instance
        ```
*   **Reasoning for Exit Code 143:**
    *   This exit code (128 + 15) typically means the process received a `SIGTERM` signal.
    *   This can be due to:
        *   **Liveness/Readiness Probe Failures:** If the MLflow server doesn't become healthy (i.e., listening on its port) within the probe's configured timeouts and thresholds, Kubernetes will send `SIGTERM`.
        *   **Application Error:** The MLflow server application itself might be encountering an error during startup (e.g., Conda environment creation failure, model loading failure) that causes it to terminate or not start its HTTP/TCP listeners.
*   **Troubleshooting Steps in Progress:**
    1.  **Analyze `churn-classifier` Logs:** Obtain detailed logs from the `churn-classifier` container (using `kubectl logs ... --previous` or `kubectl logs ... -f`) to identify any Python tracebacks, Conda errors, or MLflow/MLServer errors occurring before termination. This is the highest priority.
    2.  **Review and Adjust Probes:**
        *   The current probes (TCP check on port 9000) might be too aggressive if Conda environment creation is lengthy.
        *   Consider increasing `initialDelaySeconds` for both liveness and readiness probes in `seldon-churn-deployment-template.yaml` (e.g., to `120s` or `180s`) to allow more time for startup.
*   **Status:** Actively trying to capture detailed application logs and considering probe adjustments.


## 9. Challenge: `MLFLOW_SERVER` Conda Environment Creation Exceeds Probe Timeouts

*   **Symptoms:**
    *   The `SeldonDeployment` applies correctly, and the model pod starts.
    *   The `churn-classifier-model-initializer` (rclone initContainer) **completes successfully**.
    *   The main `churn-classifier` container (running `MLFLOW_SERVER`) starts and begins creating the Conda environment. Logs show:
        ```
        INFO:root:Creating Conda environment 'mlflow' from conda.yaml
        Collecting package metadata (repodata.json): ...working...
        ```
    *   The container never progresses past this "Collecting package metadata" step before being terminated.
    *   Pod events show liveness probe failures, and the container `lastState` often indicates `exitCode: 143` (SIGTERM).
    *   This occurs even with increased `initialDelaySeconds` for probes (e.g., 180s for liveness, 120s for readiness) and increased memory (8Gi).
*   **Reason:**
    *   The process of creating the Conda environment from `conda.yaml` is taking longer than the `initialDelaySeconds` of the liveness probe.
    *   When the liveness probe fails repeatedly because the server hasn't started listening on its port (due to being stuck in Conda setup), Kubernetes sends a `SIGTERM` to the container, causing it to restart.
*   **Troubleshooting & Next Steps:**
    1.  **Drastically Increase Liveness Probe `initialDelaySeconds` (Diagnostic):** Temporarily set `initialDelaySeconds` to a very high value (e.g., 600s or 900s) in `seldon-churn-deployment-template.yaml` to see if the Conda environment creation can complete given enough time.
    2.  **Inspect and Simplify `conda.yaml`:**
        *   Review for overly complex dependencies or a large number of packages.
        *   Ensure package versions are pinned.
        *   Test `conda env create -f conda.yaml` locally to benchmark creation time.
    3.  **Pre-bake Conda Environment into Custom Docker Image (Recommended Long-Term Fix):** If Conda setup is inherently slow, build a custom Docker image where the Conda environment is created during the image build process. This makes pod startup much faster.
    4.  **Investigate Network (If Applicable):** Check for slow network access to Conda channels from within the pod if other steps don't resolve the issue.
*   **Status:** The primary hypothesis is that Conda environment creation time is the bottleneck. Testing with significantly increased probe delays.


## 10. SUCCESS! `MLFLOW_SERVER` Pod Healthy and Serving

*   **Outcome:**
    *   By significantly increasing the `livenessProbe.initialDelaySeconds` (e.g., to 600s), the `MLFLOW_SERVER` container (`churn-classifier`) had enough time to complete the lengthy Conda environment creation process.
    *   The pod (`churn-xgboost-model-default-0-churn-classifier-...`) is now `READY 2/2` and in a `Running` state.
    *   The Seldon Core microservice and gunicorn servers for REST and metrics have started successfully.
*   **Logs Confirm Startup Sequence:**
    1.  Conda environment creation from `conda.yaml` completes.
    2.  Pip dependencies from a `requirements.txt` (likely for `seldon-core`) are installed.
    3.  The `mlflow` Conda environment is activated.
    4.  `MLFlowServer` is imported and starts, listening on ports 9000 (HTTP) and 6000 (metrics).
*   **New Observation: Dependency Version Mismatches:**
    *   The server logs show warnings from `mlflow.pyfunc`:
        ```
        WARNING mlflow.pyfunc: Detected one or more mismatches between the model's dependencies and the current Python environment:
         - mlflow (current: 2.5.0, required: mlflow==2.17.2)
         - pandas (current: 2.0.0, required: pandas==2.0.3)
        ```
    *   This indicates that the environment created at runtime (influenced by both the model's `conda.yaml` and potentially a `requirements.txt` used by `seldon-core`) has different versions of `mlflow` and `pandas` than those recorded when the model was originally logged.

## Next Steps & Refinements

1.  **Address Dependency Mismatches (Recommended):**
    *   **Goal:** Ensure the runtime environment precisely matches the model's training/logging environment for maximum reliability.
    *   **Investigate:** Determine if the conflicting versions (e.g., `mlflow==2.5.0`) are introduced by the `requirements.txt` used by `seldon-core` within the `MLFLOW_SERVER` image.
    *   **Option 1: Align Model's `conda.yaml`:** Ensure the `conda.yaml` in your MLflow model artifact has strictly pinned versions for all dependencies, including `mlflow` itself.
    *   **Option 2: Pre-bake Environment (Most Robust):** Create a custom Docker image. First, build the Conda environment from your model's exact `conda.yaml`. Then, install any additional Seldon-required packages into that environment. This provides full control.
2.  **Optimize `initialDelaySeconds`:**
    *   Now that the server starts, the `initialDelaySeconds` for the liveness probe can likely be reduced from the diagnostic value (e.g., 600s) to a more practical one. Experiment to find the lowest reliable value. However, if the Conda/pip installation is inherently long, pre-baking the environment is a better fix than overly long probe delays.
3.  **Testing:** Thoroughly test the model endpoint to ensure it behaves as expected despite the version mismatch warnings (if not immediately addressed).

## Key Takeaways (Updated)

1.  **SUCCESSFUL DEPLOYMENT!** The main hurdles have been overcome.
2.  **Probe Delays are Critical for Long Startups:** `initialDelaySeconds` must accommodate all startup tasks, including lengthy environment setups.
3.  **Dependency Management is Key:** Mismatches between training and serving environments can lead to subtle issues. Strive for identical environments. MLflow's environment tracking is helpful, but runtime overrides (e.g., from server framework dependencies) need to be managed.
4.  **Pre-baking Environments is a Best Practice:** For complex or slow-to-build environments, pre-installing them in a custom Docker image significantly improves pod startup time and reliability.
5.  **YAML Structure is Critical.**
6.  **Exit Codes are Informative.**
7.  **Application Logs are Crucial.**
8.  **InitContainer vs. Main Container.**
9.  **Conda Environment Creation is Resource-Intensive.**
10. **Prefer Seldon's Default Initializer for Rclone:** For `rclone`-based model downloads, leverage Seldon Core's default storage initializer. Configure it using `RCLONE_CONFIG_<REMOTE_NAME>_*` environment variables sourced from a secret via `envSecretRefName`.
11. **Use the Right Server for Your Model Format (`MLFLOW_SERVER` for MLflow models).** For models logged with MLflow, `MLFLOW_SERVER` is generally the most suitable pre-packaged Seldon server as it understands MLflow's conventions. For other formats, check the specific server's documentation (e.g., `XGBOOST_SERVER`, `SKLEARN_SERVER`) for how it expects models to be named/structured and what parameters it accepts.
12. **Constructor Signatures Matter:** Parameters defined in the SeldonDeployment graph are passed as keyword arguments to the server class's `__init__` method. If the server class doesn't accept these arguments, a `TypeError` will occur.
13. **Iterative Debugging:** Use `kubectl logs` extensively on both initContainers and main containers. `kubectl describe pod` is also crucial for understanding pod events, volume mounts, and environment variables.