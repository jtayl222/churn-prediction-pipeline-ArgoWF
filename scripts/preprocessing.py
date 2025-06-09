import pandas as pd
from sklearn.preprocessing import LabelEncoder # Keep if used, though current script doesn't use it for final encoding
from sklearn.model_selection import train_test_split
import argparse
import os
import mlflow
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main(args):
    # --- MLflow Setup ---
    # It's good practice to set the tracking URI via an environment variable
    # or have it configured globally for your MLflow server.
    # Defaulting here for standalone script execution, but override in your Argo workflow.
    mlflow_tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000") # Replace with your MLflow server URI
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    
    try:
        mlflow.set_experiment(args.mlflow_experiment_name)
        logger.info(f"Using MLflow experiment: {args.mlflow_experiment_name}")
    except Exception as e:
        logger.error(f"Could not set MLflow experiment '{args.mlflow_experiment_name}': {e}")
        # Fallback or create if not exists (more robust)
        try:
            logger.info(f"Attempting to create MLflow experiment: {args.mlflow_experiment_name}")
            mlflow.create_experiment(args.mlflow_experiment_name)
            mlflow.set_experiment(args.mlflow_experiment_name)
        except Exception as e_create:
            logger.error(f"Failed to create or set MLflow experiment: {e_create}")
            # Decide if you want to proceed without MLflow or raise error
            # For now, we'll try to proceed, but logging might fail.

    with mlflow.start_run(run_name="preprocessing_run") as run:
        run_id = run.info.run_id
        logger.info(f"MLflow Run ID: {run_id}")
        logger.info(f"MLflow Tracking URI: {mlflow.get_tracking_uri()}")
        logger.info(f"MLflow Artifact URI: {mlflow.get_artifact_uri()}")

        # Log parameters
        mlflow.log_param("input_data_path", args.input_data_path)
        mlflow.log_param("test_split_ratio", args.test_split_ratio)
        mlflow.log_param("random_state", args.random_state)
        mlflow.log_param("output_train_path", args.output_train_path)
        mlflow.log_param("output_test_path", args.output_test_path)

        # --- Original Data Processing Logic (with minor adjustments for paths) ---
        logger.info(f"Reading data from: {args.input_data_path}")
        df = pd.read_csv(args.input_data_path)
        
        logger.info("Dropping 'customerID' column.")
        df = df.drop(['customerID'], axis=1)
        
        logger.info("Converting 'TotalCharges' to numeric and filling NaNs with 0.")
        df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce').fillna(0)

        # Original script's LabelEncoder loop - this encodes all object columns.
        # This is different from the one-hot encoding in the more detailed script I provided earlier.
        # Sticking to the user's original logic here.
        le = LabelEncoder()
        logger.info("Label encoding object type columns.")
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = le.fit_transform(df[col])

        X = df.drop('Churn', axis=1)
        y = df['Churn']
        
        logger.info(f"Splitting data with test_size={args.test_split_ratio} and random_state={args.random_state}")
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=args.test_split_ratio, random_state=args.random_state)

        train_df = pd.concat([y_train.reset_index(drop=True), X_train.reset_index(drop=True)], axis=1)
        test_df = pd.concat([y_test.reset_index(drop=True), X_test.reset_index(drop=True)], axis=1)
        
        # Ensure output directories exist
        os.makedirs(os.path.dirname(args.output_train_path), exist_ok=True)
        os.makedirs(os.path.dirname(args.output_test_path), exist_ok=True)

        logger.info(f"Saving training data to: {args.output_train_path}")
        train_df.to_csv(args.output_train_path, index=False)
        
        logger.info(f"Saving test data to: {args.output_test_path}")
        test_df.to_csv(args.output_test_path, index=False)

        # --- Log processed data as MLflow artifacts ---
        logger.info("Logging processed train.csv and test.csv as MLflow artifacts.")
        mlflow.log_artifact(args.output_train_path, artifact_path="processed_data")
        mlflow.log_artifact(args.output_test_path, artifact_path="processed_data")
        
        mlflow.set_tag("preprocessing_status", "completed")
        logger.info("Preprocessing script finished successfully.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Preprocess churn data and log to MLflow.")
    parser.add_argument('--input-data-path', type=str, default='/opt/ml/processing/input/WA_Fn-UseC_-Telco-Customer-Churn.csv', help='Path to the input CSV file.')
    parser.add_argument('--output-train-path', type=str, default='/opt/ml/processing/output/train/train.csv', help='Path to save the processed training data.')
    parser.add_argument('--output-test-path', type=str, default='/opt/ml/processing/output/test/test.csv', help='Path to save the processed test data.')
    parser.add_argument('--test-split-ratio', type=float, default=0.2, help='Ratio for train-test split.')
    parser.add_argument('--random-state', type=int, default=42, help='Random state for train-test split.')
    parser.add_argument('--mlflow-experiment-name', type=str, default="Churn_Prediction_Experiment", help="Name of the MLflow experiment.")
    
    args = parser.parse_args()
    main(args)
