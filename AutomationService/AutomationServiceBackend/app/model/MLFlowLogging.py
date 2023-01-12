from qanary_helpers.logging import MLFlowLogger
import logging
import os


class MLFlowLoggerFactory:
    ml_logger = None

    @staticmethod
    def connect_logger():
        # MLFlowLogger data
        if os.getenv("MLFLOW_URI"):
            mlflow_uri = os.environ['MLFLOW_URI']
        if os.getenv("USE_SFTP"):
            use_sftp = os.getenv("USE_SFTP", 'False').lower() in ('true', '1', 't')
        if os.getenv("MLFLOW_HOST"):
            ssh_host = os.environ["MLFLOW_HOST"]
        if os.getenv("MLFLOW_PORT"):
            ssh_port = os.environ["MLFLOW_PORT"]

        try:
            MLFlowLoggerFactory.ml_logger = MLFlowLogger(mlflow_uri, use_sftp, ssh_host, ssh_port)
            logging.info("MLFlowLogger was successfully initialized with the given arguments.")
        except Exception as e:
            logging.info("MLFlowLogger arguments are missing, wrong or there is no active MLFlow service running. The logger will not be used. Please check the environment-files (one in /app, one in root folder) if this is not intended.")
            return None
            #logging.warning("Optional MLFlowLogger arguments not given or invalid (uri, etc.); using default and "
            #                "connecting to http://localhost:5000. This likely won't work with Docker.")
            #logging.error(e)
            #MLFlowLoggerFactory.ml_logger = MLFlowLogger()

    @staticmethod
    def get_ml_logger() -> MLFlowLogger:
        if MLFlowLoggerFactory.ml_logger is None:
            MLFlowLoggerFactory.connect_logger()
        
        return MLFlowLoggerFactory.ml_logger
