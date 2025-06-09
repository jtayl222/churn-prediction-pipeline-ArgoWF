import xgboost as xgb
import pandas as pd
import os
import logging
from sklearn.metrics import accuracy_score, roc_auc_score
import json
import argparse # Added for MLflow experiment name
import mlflow # Added for MLflow
import mlflow.xgboost # Added for MLflow XGBoost integration

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # Argument for MLflow experiment name
    parser.add_argument('--mlflow-experiment-name', type=str, default="Churn_Prediction_XGBoost", help="Name of the MLflow experiment.")
    # Optional: Add arguments for data paths if you want to override SageMaker defaults when not in SageMaker
    parser.add_argument('--train-data-path', type=str, default='/opt/ml/processing/input/data/train/train.csv')
    parser.add_argument('--valid-data-path', type=str, default='/opt/ml/processing/input/data/validation/test.csv')
    parser.add_argument('--model-output-path', type=str, default='/opt/ml/processing/model/xgboost-model') # SageMaker model path
    parser.add_argument('--metrics-output-path', type=str, default='/opt/ml/processing/output/metrics.json') # SageMaker metrics path

    args = parser.parse_args()

    logger.info("Starting XGBoost training script.")

    # --- MLflow Setup ---
    mlflow_tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000") # Replace with your MLflow server URI
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    
    try:
        mlflow.set_experiment(args.mlflow_experiment_name)
        logger.info(f"Using MLflow experiment: {args.mlflow_experiment_name}")
    except Exception as e:
        logger.error(f"Could not set MLflow experiment '{args.mlflow_experiment_name}': {e}")
        try:
            logger.info(f"Attempting to create MLflow experiment: {args.mlflow_experiment_name}")
            mlflow.create_experiment(args.mlflow_experiment_name)
            mlflow.set_experiment(args.mlflow_experiment_name)
        except Exception as e_create:
            logger.error(f"Failed to create or set MLflow experiment: {e_create}")


    with mlflow.start_run(run_name="xgboost_training_run") as run:
        run_id = run.info.run_id
        logger.info(f"MLflow Run ID: {run_id}")
        logger.info(f"MLflow Tracking URI: {mlflow.get_tracking_uri()}")
        logger.info(f"MLflow Artifact URI: {mlflow.get_artifact_uri()}")

        # Load training data
        logger.info(f"Loading training data from {args.train_data_path}")
        train_data = pd.read_csv(args.train_data_path)
        X_train = train_data.iloc[:, 1:]
        y_train = train_data.iloc[:, 0]
        logger.info(f"Training data loaded. Shape: {train_data.shape}")

        # Load validation data
        logger.info(f"Loading validation data from {args.valid_data_path}")
        valid_data = pd.read_csv(args.valid_data_path)
        X_valid = valid_data.iloc[:, 1:]
        y_valid = valid_data.iloc[:, 0]
        logger.info(f"Validation data loaded. Shape: {valid_data.shape}")

        # Define hyperparameters, reading from SageMaker env vars or defaults
        hp_max_depth = int(float(os.environ.get('SM_HP_MAX_DEPTH', 5)))
        hp_eta = float(os.environ.get('SM_HP_ETA', 0.2))
        hp_min_child_weight = float(os.environ.get('SM_HP_MIN_CHILD_WEIGHT', 1))
        hp_subsample = float(os.environ.get('SM_HP_SUBSAMPLE', 0.8))
        hp_num_round = int(os.environ.get('SM_HP_NUM_ROUND', 100)) # SageMaker often passes num_round

        model_params = {
            'max_depth': hp_max_depth,
            'eta': hp_eta,
            'min_child_weight': hp_min_child_weight,
            'subsample': hp_subsample,
            'objective': 'binary:logistic',
            'n_estimators': hp_num_round, # XGBClassifier uses n_estimators
            'use_label_encoder': False # Suppress warning for newer XGBoost
        }
        
        # Log parameters to MLflow
        logger.info(f"Logging parameters to MLflow: {model_params}")
        mlflow.log_params({
            'max_depth': hp_max_depth,
            'eta': hp_eta,
            'min_child_weight': hp_min_child_weight,
            'subsample': hp_subsample,
            'num_round': hp_num_round, # Logged as num_round for consistency with SM
            'objective': 'binary:logistic'
        })
        mlflow.log_param("train_data_path", args.train_data_path)
        mlflow.log_param("valid_data_path", args.valid_data_path)


        # Initialize XGBoost model
        logger.info("Initializing XGBoost model with hyperparameters.")
        # XGBClassifier uses n_estimators instead of num_round directly in constructor
        model = xgb.XGBClassifier(
            max_depth=hp_max_depth,
            eta=hp_eta,
            min_child_weight=hp_min_child_weight,
            subsample=hp_subsample,
            objective='binary:logistic',
            n_estimators=hp_num_round, # Use n_estimators here
            use_label_encoder=False # Suppress warning
        )
        logger.info("XGBoost model initialized.")

        # Train the model
        logger.info("Starting model training.")
        model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
        logger.info("Model training completed.")

        # Save the model (SageMaker conventional path) - kept for compatibility
        logger.info(f"Saving the trained model to SageMaker path: {args.model_output_path}")
        os.makedirs(os.path.dirname(args.model_output_path), exist_ok=True)
        model.save_model(args.model_output_path)
        logger.info("Model saved to SageMaker path successfully.")

        # Log model with MLflow
        logger.info("Logging model with MLflow.")
        mlflow.xgboost.log_model(
            xgb_model=model,
            artifact_path="xgboost-churn-model", # This will be a directory in MLflow artifacts
            input_example=X_train.head(), # Optional: for signature inference
            signature=mlflow.models.infer_signature(X_train, model.predict(X_train)) # Optional
        )
        logger.info("Model logged to MLflow successfully.")

        # Evaluate the model
        logger.info("Evaluating the model on validation data.")
        y_pred = model.predict(X_valid)
        y_pred_proba = model.predict_proba(X_valid)[:, 1]
        accuracy = accuracy_score(y_valid, y_pred)
        auc = roc_auc_score(y_valid, y_pred_proba)
        logger.info(f"Model evaluation completed. Accuracy: {accuracy:.4f}, AUC: {auc:.4f}")

        # Log metrics to MLflow
        logger.info("Logging metrics to MLflow.")
        mlflow.log_metric("validation_accuracy", accuracy)
        mlflow.log_metric("validation_auc", auc)

        # Print metrics in the format expected by SageMaker HPO - kept for compatibility
        print(f"validation:accuracy: {accuracy}")
        print(f"validation:auc: {auc}")

        # Save metrics to file (SageMaker conventional path) - kept for compatibility
        logger.info(f"Saving evaluation metrics to SageMaker path: {args.metrics_output_path}")
        os.makedirs(os.path.dirname(args.metrics_output_path), exist_ok=True)
        metrics_content = {'accuracy': accuracy, 'auc': auc}
        with open(args.metrics_output_path, 'w') as f:
            json.dump(metrics_content, f)
        logger.info("Metrics saved to SageMaker path successfully.")
        
        mlflow.set_tag("training_status", "completed")
        logger.info("XGBoost training script finished.")
