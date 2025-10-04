import sys

print(f"path[0]={sys.path[0]}")



import pandas as pd
from typing import List, Dict, Any
from sqlalchemy.orm import sessionmaker

from src.db.db_interface import get_session_local
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.message_classification.manual_classifier import ManualMessageClassifier
from src.utils.log import log_in_out
from src.message_classification.message_classification_logger import logger


@log_in_out(logger=logger)
def download_messages_dataframe(limit: int = 50) -> pd.DataFrame:
    SessionLocal = get_session_local()
    session = SessionLocal()
    
    query = session.query(
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
    ).join(
        WhatsAppUser, WhatsAppMessage.sender_id == WhatsAppUser.id
    ).join(
        WhatsAppGroup, WhatsAppMessage.group_id == WhatsAppGroup.id
    ).filter(
        WhatsAppMessage.is_real == True
    ).filter(
        WhatsAppMessage.id >= 1
    ).order_by(
        WhatsAppMessage.id.asc()
    ).limit(limit)
    
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
            'group_name': row.group_name
        })
    
    df = pd.DataFrame(data)
    session.close()
    return df


@log_in_out(logger=logger)
def classify_messages_loop(messages_df: pd.DataFrame) -> pd.DataFrame:
    classifier = ManualMessageClassifier()
    messages_df['is_lead'] = False
    
    for index, row in messages_df.iterrows():
        message_data = row.to_dict()
        is_lead = classifier.classify_whatsapp_message_is_lead(message_data)
        messages_df.at[index, 'is_lead'] = is_lead
    
    return messages_df


@log_in_out(logger=logger)
def main():

    messages_df = download_messages_dataframe(limit=50)
    
    if messages_df.empty:
        return
    
    classified_df = classify_messages_loop(messages_df)

    logger.info(classified_df)


if __name__ == "__main__":

    main()
