import sys
import os
from collections import deque
from typing import Optional

import pandas as pd

from src.db.db_interface import get_session_local
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.utils.log import log_in_out
from src.message_classification.message_classification_logger import logger
from src.message_classification.whatsapp_message_classifier import WhatsappMessageClassifier


class MessageAnalysisOrchestrator:
    """Main orchestrator class that coordinates message retrieval and classification."""
    
    def __init__(self, target_group_id: str = "120363028694435074@g.us", window_size: int = 5):
        self.target_group_id = target_group_id
        self.window_size = window_size
        self.classifier = WhatsappMessageClassifier()
    
    @log_in_out(logger=logger)
    def download_messages_dataframe(self, limit: int = 50, offset=0) -> pd.DataFrame:
        """Download messages only from the Laureles group ordered by time.

        Filters by whatsapp_group_id and is_real == True.
        The larger default limit supports building WINDOW_SIZE-message histories.
        """
        SessionLocal = get_session_local()
        session = SessionLocal()

        query = (
            session.query(
                WhatsAppMessage.id,
                WhatsAppMessage.message_id,
                WhatsAppMessage.raw_text,
                WhatsAppMessage.message_type,
                WhatsAppMessage.is_forwarded,
                WhatsAppMessage.timestamp,
                WhatsAppMessage.llm_processed,
                WhatsAppMessage.is_real,
                WhatsAppUser.whatsapp_id.label('user_whatsapp_id'),
                WhatsAppUser.display_name.label('user_display_name'),
                WhatsAppGroup.whatsapp_group_id.label('group_whatsapp_id'),
                WhatsAppGroup.group_name.label('group_name')
            )
            .join(WhatsAppUser, WhatsAppMessage.sender_id == WhatsAppUser.id)
            .join(WhatsAppGroup, WhatsAppMessage.group_id == WhatsAppGroup.id)
            .filter(WhatsAppMessage.is_real == True)
            .filter(WhatsAppGroup.whatsapp_group_id == self.target_group_id)
            .order_by(WhatsAppMessage.timestamp.asc(), WhatsAppMessage.id.asc())
            .offset(offset)
            .limit(limit)
        )

        result = query.all()

        data = []
        for row in result:
            data.append({
                'id': row.id,
                'message_id': row.message_id,
                'raw_text': row.raw_text,
                'message_type': row.message_type,
                'is_forwarded': row.is_forwarded,
                'timestamp': row.timestamp,
                'llm_processed': row.llm_processed,
                'is_real': row.is_real,
                'user_whatsapp_id': row.user_whatsapp_id,
                'user_display_name': row.user_display_name,
                'group_whatsapp_id': row.group_whatsapp_id,
                'group_name': row.group_name,
            })

        df = pd.DataFrame(data)
        session.close()
        return df
    
    @log_in_out(logger=logger)
    def classify_messages_loop(self, messages_df: pd.DataFrame) -> pd.DataFrame:
        """Classify messages using a sliding window approach."""
        messages_df = messages_df.copy()
        messages_df['is_lead'] = pd.NA
        messages_df['business_type'] = pd.NA

        window = deque(maxlen=self.window_size)
        for idx, row in messages_df.iterrows():
            if len(window) < self.window_size:
                window.append(row)
                continue

            context_rows = pd.DataFrame(list(window))
            
            # Use the ManualMessageClassifier to classify the message
            parsed = self.classifier.classify_message_with_history(
                message_id=str(row.get('message_id')),
                context_rows=context_rows,
                message_data=row.to_dict(),
                window_size=self.window_size
            )
            
            messages_df.at[idx, 'is_lead'] = bool(parsed.is_lead)
            messages_df.at[idx, 'business_type'] = (parsed.business_type or None)

            window.append(row)

        return messages_df
    
    @log_in_out(logger=logger)
    def run_analysis(self, limit: int = 11, offset: int=0) -> Optional[pd.DataFrame]:
        """Run the complete message analysis pipeline."""
        assert os.environ.get('OPENAI_API_KEY'), "OPENAI_API_KEY environment variable is required"
        
        pd.set_option('display.max_columns', None)
        messages_df = self.download_messages_dataframe(limit=limit, offset=offset)
        
        if messages_df.empty:
            logger.warning("No messages found for analysis")
            return None

        classified_df = self.classify_messages_loop(messages_df)
        
        logger.info(classified_df)
        logger.info(messages_df.columns)
        
        return classified_df


def main():
    orchestrator = MessageAnalysisOrchestrator()
    orchestrator.run_analysis(limit=20, offset=20)


if __name__ == "__main__":
    main()
