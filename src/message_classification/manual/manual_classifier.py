from typing import Dict, Any
import pandas as pd
from src.utils.log import log_in_out
from src.message_classification.message_classification_logger import logger


class ManualMessageClassifier:
    def __init__(self):
        pass
    
    @log_in_out(logger=logger)
    def classify_whatsapp_message_is_lead(self, message_data: Dict[str, Any]) -> bool:
        return False
    
    @log_in_out(logger=logger)
    def classify_message_batch(self, messages_df: pd.DataFrame) -> pd.DataFrame:
        messages_df['is_lead'] = messages_df.apply(
            lambda row: self.classify_whatsapp_message_is_lead(row.to_dict()), 
            axis=1
        )
        return messages_df
