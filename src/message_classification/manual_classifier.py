from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from joblib import Memory

from src.utils.log import log_in_out
from src.message_classification.message_classification_logger import logger
from src.paths import cache_root
from src.message_classification.pydantic_models import LeadDecision
from src.utils.llm.schema_builder import SchemaBuilder


class ManualMessageClassifier:
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
    
    def _format_context_block(self, context_rows) -> str:
        """Format context rows into a readable conversation block"""
        lines = []
        for _, r in context_rows.iterrows():
            author = r.get('user_display_name') or r.get('user_whatsapp_id') or 'unknown'
            text = (r.get('raw_text') or '').strip()
            lines.append(f"{author}: {text}")
        return "\n".join(lines)
    
    @log_in_out(logger=logger)
    def classify_message_with_history(self, message_id: str, context_rows, current_message, window_size: int = 5) -> LeadDecision:
        """Classify a message with its conversation history using LangChain structured output"""
        
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
        current_author = current_message.get('user_display_name') or current_message.get('user_whatsapp_id') or 'unknown'
        current_text = (current_message.get('raw_text') or '').strip()
        
        user_prompt = (
            f"Context (previous {window_size} messages):\n" + context_block + "\n\n" +
            f"Current message from {current_author}: {current_text}"
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
        """Get cached classification or compute and cache it"""
        # Create a cached function that only uses message_id as the cache key
        @self._memory.cache
        def _cached_classify_by_message_id(msg_id: str) -> LeadDecision:
            return self._classify_single_message_with_history(
                message_id=msg_id,
                system_instructions=system_instructions,
                user_prompt=user_prompt
            )
        
        # Call the cached function with only message_id
        return _cached_classify_by_message_id(message_id)
