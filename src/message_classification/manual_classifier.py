from src.utils.log import log_in_out
from src.message_classification.message_classification_logger import logger


class ManualMessageClassifier:
    def __init__(self):
        pass
    
    @log_in_out(logger=logger)
    def classify_whatsapp_message_is_lead(self, message_data) -> bool:
        return False
