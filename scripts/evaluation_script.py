import xgboost as xgb
import pandas as pd
import os
import logging
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score, f1_score
import json
import argparse
import mlflow

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def evaluate_model(model_path, valid_data_path, metrics_output_path, mlflow_experiment_name, training_run_id=None):
    """
    Loads a trained model, evaluates it on validation data, and logs metrics.
    """
    logger.info(f"Starting model evaluation.")
    logger.info(f"MLflow Experiment Name: {mlflow_experiment_name}")
    if training_run_id:
        logger.info(f"Associated Training MLflow Run ID: {training_run_id}")

    # --- MLflow Setup ---
    # MLFLOW_TRACKING_URI and S3 credentials should be set as environment variables in the Argo workflow
    try:
        mlflow.set_experiment(mlflow_experiment_name)
        logger.info(f"Using MLflow experiment: {mlflow_experiment_name}")
    except Exception as e:
        logger.error(f"Could not set MLflow experiment '{mlflow_experiment_name}': {e}")
        # Attempt to create if not exists
        try:
            logger.info(f"Attempting to create MLflow experiment: {mlflow_experiment_name}")
            mlflow.create_experiment(mlflow_experiment_name)
            mlflow.set_experiment(mlflow_experiment_name)
        except Exception as e_create:
            logger.error(f"Failed to create or set MLflow experiment: {e_create}")
            # Decide if you want to proceed without MLflow or raise error

    # Start a new MLflow run for evaluation, or use the parent training run if ID is provided
    # For simplicity here, we'll create a new run.
    # To nest it under the training run, you'd use:
    # with mlflow.start_run(run_id=training_run_id, nested=True, run_name="evaluation") if training_run_id else mlflow.start_run(run_name="evaluation_run") as run:
    
    # For now, let's create a distinct evaluation run, but tag it if training_run_id is available
    with mlflow.start_run(run_name="model_evaluation_run") as run:
        eval_run_id = run.info.run_id
        logger.info(f"Evaluation MLflow Run ID: {eval_run_id}")
        if training_run_id:
            mlflow.set_tag("training_run_id", training_run_id)
        mlflow.log_param("model_path", model_path)
        mlflow.log_param("validation_data_path", valid_data_path)

        # Load the trained model
        logger.info(f"Loading model from {model_path}")
        try:
            model = xgb.XGBClassifier()
            model.load_model(model_path)
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            mlflow.set_tag("evaluation_status", "failed_model_load")
            raise

        # Load validation data
        logger.info(f"Loading validation data from {valid_data_path}")
        try:
            valid_data = pd.read_csv(valid_data_path)
            X_valid = valid_data.iloc[:, 1:]  # Assuming first column is target
            y_valid = valid_data.iloc[:, 0]
            logger.info(f"Validation data loaded. Shape: X_valid {X_valid.shape}, y_valid {y_valid.shape}")
        except Exception as e:
            logger.error(f"Failed to load validation data from {valid_data_path}: {e}")
            mlflow.set_tag("evaluation_status", "failed_data_load")
            raise

        # Make predictions
        logger.info("Making predictions on validation data.")
        try:
            y_pred_proba = model.predict_proba(X_valid)[:, 1]
            y_pred = model.predict(X_valid)
        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            mlflow.set_tag("evaluation_status", "failed_prediction")
            raise

        # Calculate metrics
        logger.info("Calculating evaluation metrics.")
        try:
            accuracy = accuracy_score(y_valid, y_pred)
            auc = roc_auc_score(y_valid, y_pred_proba)
            precision = precision_score(y_valid, y_pred, zero_division=0)
            recall = recall_score(y_valid, y_pred, zero_division=0)
            f1 = f1_score(y_valid, y_pred, zero_division=0)

            metrics = {
                "accuracy": accuracy,
                "auc": auc,
                "precision": precision,
                "recall": recall,
                "f1_score": f1
            }
            logger.info(f"Evaluation Metrics: {metrics}")

            # Log metrics to MLflow
            logger.info("Logging metrics to MLflow.")
            mlflow.log_metrics(metrics)

            # Print metrics for Argo logs / SageMaker HPO compatibility
            print(f"validation:accuracy: {accuracy}")
            print(f"validation:auc: {auc}")
            print(f"validation:precision: {precision}")
            print(f"validation:recall: {recall}")
            print(f"validation:f1_score: {f1}")

            # Save metrics to JSON file
            logger.info(f"Saving evaluation metrics to {metrics_output_path}")
            os.makedirs(os.path.dirname(metrics_output_path), exist_ok=True)
            with open(metrics_output_path, 'w') as f:
                json.dump(metrics, f, indent=4)
            logger.info("Metrics saved successfully.")
            mlflow.log_artifact(metrics_output_path, artifact_path="evaluation_results")
            mlflow.set_tag("evaluation_status", "completed")

        except Exception as e:
            logger.error(f"Error during metrics calculation or logging: {e}")
            mlflow.set_tag("evaluation_status", "failed_metrics_calculation")
            raise

    logger.info("Model evaluation script finished.")
    return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Evaluate a trained XGBoost model.")
    parser.add_argument('--model-path', type=str, required=True,
                        help='Path to the trained XGBoost model file (e.g., /opt/ml/processing/model/xgboost-model).')
    parser.add_argument('--valid-data-path', type=str, required=True,
                        help='Path to the validation data CSV file (e.g., /opt/ml/processing/output/test/test.csv).')
    parser.add_argument('--metrics-output-path', type=str, required=True,
                        help='Path to save the evaluation metrics JSON file (e.g., /opt/ml/processing/output/evaluation_metrics.json).')
    parser.add_argument('--mlflow-experiment-name', type=str, default="Churn_Prediction_XGBoost", # Or a new one like "Churn_Model_Evaluation"
                        help='Name of the MLflow experiment to log metrics to.')
    parser.add_argument('--training-run-id', type=str, default=None, required=False,
                        help='(Optional) MLflow Run ID of the training job to associate this evaluation with.')
    
    args = parser.parse_args()

    # Ensure MLFLOW_TRACKING_URI is set in the environment by Argo workflow
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        logger.warning("MLFLOW_TRACKING_URI environment variable not set. MLflow logging might fail or use local tracking.")

    evaluate_model(
        model_path=args.model_path,
        valid_data_path=args.valid_data_path,
        metrics_output_path=args.metrics_output_path,
        mlflow_experiment_name=args.mlflow_experiment_name,
        training_run_id=args.training_run_id
    )