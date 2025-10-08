import sys

print(f"path[0]={sys.path[0]}")



import os
from collections import deque

import pandas as pd

from src.db.db_interface import get_session_local
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.utils.log import log_in_out
from src.message_classification.message_classification_logger import logger
from src.message_classification.whatsapp_message_classifier import WhatsappMessageClassifier

# Number of previous messages to include in the classification context window
WINDOW_SIZE = 5

@log_in_out(logger=logger)
def download_messages_dataframe(limit: int = 50) -> pd.DataFrame:
    """Download messages only from the Laureles group ordered by time.

    Filters by whatsapp_group_id == "120363028694435074@g.us" and is_real == True.
    The larger default limit supports building WINDOW_SIZE-message histories.
    """
    SessionLocal = get_session_local()
    session = SessionLocal()

    target_group_id = "120363028694435074@g.us"

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
        .filter(WhatsAppGroup.whatsapp_group_id == target_group_id)
        .order_by(WhatsAppMessage.timestamp.asc(), WhatsAppMessage.id.asc())
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
def classify_messages_loop(messages_df: pd.DataFrame, classifier: WhatsappMessageClassifier) -> pd.DataFrame:
    messages_df = messages_df.copy()
    messages_df['is_lead'] = pd.NA
    messages_df['business_type'] = pd.NA

    window = deque(maxlen=WINDOW_SIZE)
    for idx, row in messages_df.iterrows():
        if len(window) < WINDOW_SIZE:
            window.append(row)
            continue

        context_rows = pd.DataFrame(list(window))
        
        # Use the ManualMessageClassifier to classify the message
        parsed = classifier.classify_message_with_history(
            message_id=str(row.get('message_id')),
            context_rows=context_rows,
            current_message=row,
            window_size=WINDOW_SIZE
        )
        
        messages_df.at[idx, 'is_lead'] = bool(parsed.is_lead)
        messages_df.at[idx, 'business_type'] = (parsed.business_type or None)

        window.append(row)

    return messages_df


@log_in_out(logger=logger)
def main():
    assert os.environ.get('OPENAI_API_KEY')

    pd.set_option('display.max_columns', None)
    messages_df = download_messages_dataframe(limit=11)
    
    if messages_df.empty:
        return

    # Initialize the classifier
    classifier = WhatsappMessageClassifier()
    
    # Classify messages using the new classifier
    classified_df = classify_messages_loop(messages_df, classifier)

    logger.info(classified_df)
    logger.info(messages_df.columns)


if __name__ == "__main__":

    main()
