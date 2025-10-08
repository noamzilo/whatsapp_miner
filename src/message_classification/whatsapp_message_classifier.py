from typing import Optional, Dict, Any
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from joblib import Memory

from src.utils.log import log_in_out
from src.message_classification.message_classification_logger import logger
from src.paths import cache_root
from src.message_classification.pydantic_models import LeadDecision
from src.utils.llm.schema_builder import SchemaBuilder


class WhatsappMessageClassifier:
    def __init__(self):
        # Schema validation happens automatically at import time
        self.client = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
        self.structured_model = self.client.with_structured_output(LeadDecision)
        self.schema_builder = SchemaBuilder()
        
        # Configure on-disk cache for single-message+history classifications
        self._cache_dir = cache_root / 'manual_classifier'
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory = Memory(location=str(self._cache_dir), verbose=0)
    
    
    def _generate_schema_instructions(self) -> str:
        schema_fields = self.schema_builder.generate_schema_instructions(LeadDecision)
        return f"Respond with a JSON object containing these fields:\n{schema_fields}"
    
    def _format_context_block(self, context_rows: pd.DataFrame) -> str:
        """Format context rows into a readable conversation block"""
        lines = []
        for _, r in context_rows.iterrows():
            author = r.get('user_display_name') or r.get('user_whatsapp_id') or 'unknown'
            text = r.get('raw_text', '').strip()
            lines.append(f"{author}: {text}")
        return "\n".join(lines)
    
    @log_in_out(logger=logger)
    def classify_message_with_history(self, message_id: str, context_rows: pd.DataFrame, message_data: Dict[str, Any], window_size: int = 5, preview_length: int = 100) -> LeadDecision:
        """Classify a message with its conversation history using LangChain structured output"""
        
        message_text = message_data.get('raw_text', '').strip()
        message_preview = message_text[:preview_length] + ('...' if len(message_text) > preview_length else '')
        logger.info(f"Classifying message {message_id}: {message_preview}")
        
        system_instructions = (
            f"You are a small business owner that goes over whatsapp-group messages "
            f"in order to find leads for small businesses in the groups. "
            f"Many times, people in the group are looking for a specific business to fulfill a need. "
            f"A lead must show clear purchase-seeking intent AND specify a clear business type that could fulfill it. "
            f"Examples of leads: 'Looking for a dentist', 'Anyone know a good nail salon?', 'I need a Spanish teacher'. "
            f"Use only the supplied context of the previous {window_size} messages and the current message. "
            f"\n\n{self._generate_schema_instructions()}"
        )
        
        context_block = self._format_context_block(context_rows)
        current_author = message_data.get('user_display_name') or message_data.get('user_whatsapp_id') or 'unknown'
        message_text = message_data.get('raw_text', '').strip()
        
        user_prompt = (
            f"Context (previous {window_size} messages):\n" + context_block + "\n\n" +
            f"Current message from {current_author}: {message_text}"
        )
        
        return self._get_cached_classification(
            message_id=message_id,
            system_instructions=system_instructions,
            user_prompt=user_prompt,
        )
    
    def _classify_single_message_with_history(self, *, message_id: str, system_instructions: str, user_prompt: str) -> LeadDecision:
        """Cached method to classify a single message with history using LangChain"""
        messages = [
            SystemMessage(content=system_instructions),
            HumanMessage(content=user_prompt)
        ]
        
        result = self.structured_model.invoke(messages)
        return result
    
    def _get_cached_classification(self, message_id: str, system_instructions: str, user_prompt: str) -> LeadDecision:
        cache_hit = True
        
        def _classify_with_tracking(msg_id: str) -> LeadDecision:
            nonlocal cache_hit
            cache_hit = False
            logger.info(f"Cache MISS for message {msg_id} - computing new classification")
            return self._classify_single_message_with_history(
                message_id=msg_id,
                system_instructions=system_instructions,
                user_prompt=user_prompt
            )
        
        cached_classify = self._memory.cache(_classify_with_tracking)
        result = cached_classify(message_id)
        
        if cache_hit:
            logger.info(f"Cache HIT for message {message_id}")
        
        return result
