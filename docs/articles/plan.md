# Plan

You've got a solid plan for evolving this project and creating valuable content! Let's refine those steps and consider how they build your MLOps expertise and interview talking points.

**Understanding Your Current xgboost_script.py (from the active editor):**

*   This script is very much in the style of a typical **Amazon SageMaker training script**.
    *   It reads hyperparameters from environment variables prefixed with `SM_HP_`.
    *   It expects data in specific input channel paths (`/opt/ml/processing/input/data/...`).
    *   It saves the model to `/opt/ml/processing/model/`.
    *   It prints metrics in a specific format for SageMaker's HPO to capture.
*   This is perfectly valid for running within SageMaker or emulating that environment.
*   It's a good example of a "direct file-based" approach.

**Your Proposed Plan - Refined:**

Here's a breakdown of your ideas with some MLOps considerations:

**Phase 1: Foundational Exploration & Quick Wins (JupyterHub)**

*   **(1) Copy existing functionality into a Jupyter Notebook and run on JupyterHub in the cluster.**
    *   **Goal:** Rapid iteration, data exploration, initial model development, and demonstrating a user-facing interactive environment within your Kubernetes cluster.
    *   **MLOps Angle:**
        *   **Interactive Development Environment:** Showcases how data scientists/ML engineers can work within the k8s ecosystem.
        *   **Reproducibility (Notebooks):** Discuss challenges (hidden state, out-of-order execution) and best practices (clear all outputs, run all, version control notebooks).
        *   **Transition to Automation:** This notebook becomes the *source* or *prototype* for the automated pipeline steps.
    *   **Implementation:**
        *   Install JupyterHub on your k3s cluster (if not already done).
        *   Adapt your xgboost_script.py logic into a notebook.
        *   Mount the PVC (where your data resides) into the JupyterLab user pods so the notebook can access `train.csv` and `test.csv`.
        *   Manually define hyperparameters or use widgets.
        *   Save the model and metrics to the PVC from the notebook.
    *   **Interview Evidence:** "I set up JupyterHub on Kubernetes to provide an interactive environment for ML development. I prototyped the churn model training in a notebook, ensuring it could access data from our shared storage (PVC), before automating it in a pipeline."

**Phase 2: Building a Robust MLOps Pipeline (Homelab-MLOps-Demo Approach)**

*   **(2) Convert existing Python into a `homelab-mlops-demo` Approach.**
    *   **Goal:** Implement a more mature MLOps pipeline with centralized tracking, model packaging, and artifact management using MLflow and an S3-compatible backend (MinIO).
    *   **MLOps Angle:** This is the core of demonstrating best practices.
        *   **Centralized Experiment Tracking:** All runs logged to MLflow.
        *   **Model Registry (via MLflow):** Packaged models versioned and potentially promoted through stages.
        *   **Artifact Storage:** Models, datasets (if versioned), and other large files stored in MinIO.
        *   **Pipeline Orchestration:** Argo Workflows calls scripts that interact with MLflow.
    *   **Implementation:**
        *   **Set up MLflow Tracking Server and MinIO** in your k3s cluster (as per the `homelab-mlops-demo`). Ensure they are configured to work together.
        *   **Modify your Python scripts (preprocessing, training, evaluation):**
            *   Remove SageMaker-specific environment variable usage (`SM_HP_`) for hyperparameters; pass them as script arguments or use MLflow's parameter logging.
            *   Remove SageMaker-specific file paths; use paths appropriate for your Argo workflow and PVC structure, or better yet, log datasets as MLflow artifacts and have downstream steps consume them via MLflow.
            *   **Crucially, integrate MLflow:**
                *   `mlflow.start_run()`
                *   `mlflow.log_param()`, `mlflow.log_metric()`
                *   `mlflow.xgboost.log_model()` (or the appropriate flavor for your model) to log the *packaged model* to the MLflow server (which then stores it in MinIO).
                *   In evaluation, load the model *from MLflow* using its run ID or model URI.
        *   **Update argowf.yaml:**
            *   Ensure steps have access to the MLflow Tracking Server URL.
            *   Pass necessary credentials for MinIO if MLflow needs them directly (though usually, the MLflow server handles S3 interaction).
    *   **Interview Evidence:** "I evolved the initial file-based pipeline into a more robust MLOps system. I deployed an MLflow Tracking Server and MinIO for object storage. The Argo pipeline now logs experiments, parameters, metrics, and packaged models to MLflow, with artifacts stored in MinIO. This provides centralized tracking, model versioning, and improved reproducibility, aligning with industry best practices."

**Phase 3: Comparative Analysis & Content Creation**

*   **(3) Track any divergences so that the AWS repo can be a valid comparison.**
    *   **Goal:** Create a compelling article/blog post comparing a self-hosted Kubernetes-based MLOps pipeline with a managed AWS SageMaker pipeline for the same churn prediction task.
    *   **MLOps Angle:** Demonstrates deep understanding of different MLOps ecosystems, their trade-offs, and the ability to adapt solutions.
    *   **Implementation:**
        *   **Keep your original SageMaker-compatible `churn-prediction-pipeline` repo as is.** This is your AWS baseline.
        *   Your new Kubernetes/MLflow pipeline (from Phase 2) is the self-hosted comparison.
        *   **Document meticulously:**
            *   **Setup:** What infrastructure is needed for each? (k3s cluster, MLflow, MinIO vs. SageMaker IAM roles, S3 buckets, SageMaker SDK).
            *   **Code Changes:** Highlight how the training/evaluation scripts differ (e.g., `SM_HP_` vs. script args, `mlflow.log_model` vs. `model.save_model` to `/opt/ml/model`).
            *   **Orchestration:** Argo Workflows YAML vs. SageMaker Pipelines Python SDK.
            *   **Experiment Tracking:** MLflow UI/API vs. SageMaker Experiments.
            *   **Model Registry:** MLflow Model Registry vs. SageMaker Model Registry.
            *   **Cost:** Discuss potential cost differences (self-managed infra vs. pay-as-you-go AWS services).
            *   **Flexibility & Control:** Kubernetes offers more, SageMaker offers more managed convenience.
            *   **Learning Curve/Operational Overhead.**
    *   **Interview Evidence:** "I conducted a comparative analysis of implementing the same churn prediction pipeline on AWS SageMaker versus a self-hosted Kubernetes stack using Argo, MLflow, and MinIO. My article details the architectural differences, code adaptations, and trade-offs in terms of cost, flexibility, and operational overhead. This demonstrates my ability to evaluate and implement MLOps solutions across different platforms."

**Key Considerations for Best Practices & Interview Value:**

*   **Git for Everything:** All code, Kubernetes manifests, Argo workflows, and even the article draft should be in Git.
*   **Infrastructure as Code (IaC) - Bonus:** If you can define your k3s MLflow/MinIO setup using something like Helm charts or Kustomize, that's a big plus.
*   **CI/CD - Bonus:** A simple CI/CD pipeline (e.g., GitHub Actions) to build Docker images or deploy Argo workflows.
*   **Clear READMEs:** Each repo should clearly explain its purpose, setup, and how to run it.

This structured approach will not only give you excellent projects for your portfolio but also deep insights into MLOps principles, which will be invaluable in interviews. Good luck!