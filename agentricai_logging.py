import datetime
import logging
import os

class AgentricAILogger:
    def __init__(self):
        self.logger = logging.getLogger('AgentricAILogger')
        self.logger.setLevel(logging.INFO)

        # Create logs directory if it doesn't exist
        log_dir = r"C:\Program Files\AgentricAI\Logs"
        os.makedirs(log_dir, exist_ok=True)

        # Create file handler which logs even debug messages
        fh = logging.FileHandler(os.path.join(log_dir, 'agentricai.log'))
        fh.setLevel(logging.DEBUG)

        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)

        self.logger.addHandler(fh)

    def log(self, message):
        self.logger.info(message)

# Usage example
logger = AgentricAILogger()
logger.log("AgentricAI logging initialized.")
