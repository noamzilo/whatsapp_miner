import csv
from collections import deque
from typing import List, Dict, Any

import pandas as pd

from src.db.db_interface import get_session_local
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.db.models.tagger import Tagger
from src.db.models.message_tag import MessageTag
from src.db.models.lead_category import LeadCategory
from src.utils.log import log_in_out
from src.utils.logger import logger
from src.message_classification.whatsapp_message_classifier import WhatsappMessageClassifier
from src.message_classification.message_classification_config import ACTIVE_MODEL_NAME


class AutoTaggingOrchestrator:
    def __init__(self, num_leads: int = 10, num_not_leads: int = 10, window_size: int = 5):
        self.num_leads = num_leads
        self.num_not_leads = num_not_leads
        self.window_size = window_size
        self.classifier = WhatsappMessageClassifier()
        self.session = get_session_local()()
        self.model_tagger = self._get_or_create_model_tagger()
        self.human_tagger = self._get_human_tagger()
    
    @log_in_out(logger=logger)
    def _get_human_tagger(self) -> Tagger:
        return self.session.query(Tagger).filter_by(
            tagger_type_id=1,
            identifier='human_tagger'
        ).first()
    
    @log_in_out(logger=logger)
    def _get_or_create_model_tagger(self) -> Tagger:
        tagger = self.session.query(Tagger).filter_by(
            tagger_type_id=2,
            identifier=ACTIVE_MODEL_NAME
        ).first()
        
        if not tagger:
            tagger = Tagger(tagger_type_id=2, identifier=ACTIVE_MODEL_NAME)
            self.session.add(tagger)
            self.session.commit()
        
        return tagger
    
    @log_in_out(logger=logger)
    def _load_human_tagged_messages(self) -> pd.DataFrame:
        human_tags_subquery = self.session.query(
            MessageTag.message_id,
            MessageTag.is_lead,
            MessageTag.lead_category_id
        ).filter_by(tagger_id=self.human_tagger.id).subquery()
        
        leads_query = (
            self.session.query(
                WhatsAppMessage.id,
                WhatsAppMessage.message_id,
                WhatsAppMessage.raw_text,
                WhatsAppMessage.message_type,
                WhatsAppMessage.is_forwarded,
                WhatsAppMessage.timestamp,
                WhatsAppMessage.group_id,
                WhatsAppUser.whatsapp_id.label('user_whatsapp_id'),
                WhatsAppUser.display_name.label('user_display_name'),
                WhatsAppGroup.whatsapp_group_id.label('group_whatsapp_id'),
                WhatsAppGroup.group_name.label('group_name'),
                human_tags_subquery.c.is_lead.label('human_is_lead'),
                human_tags_subquery.c.lead_category_id.label('human_category_id')
            )
            .join(WhatsAppUser, WhatsAppMessage.sender_id == WhatsAppUser.id)
            .join(WhatsAppGroup, WhatsAppMessage.group_id == WhatsAppGroup.id)
            .join(human_tags_subquery, WhatsAppMessage.id == human_tags_subquery.c.message_id)
            .filter(WhatsAppMessage.is_real == True)
            .filter(human_tags_subquery.c.is_lead == True)
            .order_by(WhatsAppMessage.timestamp.asc())
            .limit(self.num_leads)
        )
        
        not_leads_query = (
            self.session.query(
                WhatsAppMessage.id,
                WhatsAppMessage.message_id,
                WhatsAppMessage.raw_text,
                WhatsAppMessage.message_type,
                WhatsAppMessage.is_forwarded,
                WhatsAppMessage.timestamp,
                WhatsAppMessage.group_id,
                WhatsAppUser.whatsapp_id.label('user_whatsapp_id'),
                WhatsAppUser.display_name.label('user_display_name'),
                WhatsAppGroup.whatsapp_group_id.label('group_whatsapp_id'),
                WhatsAppGroup.group_name.label('group_name'),
                human_tags_subquery.c.is_lead.label('human_is_lead'),
                human_tags_subquery.c.lead_category_id.label('human_category_id')
            )
            .join(WhatsAppUser, WhatsAppMessage.sender_id == WhatsAppUser.id)
            .join(WhatsAppGroup, WhatsAppMessage.group_id == WhatsAppGroup.id)
            .join(human_tags_subquery, WhatsAppMessage.id == human_tags_subquery.c.message_id)
            .filter(WhatsAppMessage.is_real == True)
            .filter(human_tags_subquery.c.is_lead == False)
            .order_by(WhatsAppMessage.timestamp.asc())
            .limit(self.num_not_leads)
        )
        
        leads = leads_query.all()
        not_leads = not_leads_query.all()
        
        combined = leads + not_leads
        
        data = []
        for row in combined:
            data.append({
                'id': row.id,
                'message_id': row.message_id,
                'raw_text': row.raw_text,
                'message_type': row.message_type,
                'is_forwarded': row.is_forwarded,
                'timestamp': row.timestamp,
                'group_id': row.group_id,
                'user_whatsapp_id': row.user_whatsapp_id,
                'user_display_name': row.user_display_name,
                'group_whatsapp_id': row.group_whatsapp_id,
                'group_name': row.group_name,
                'human_is_lead': row.human_is_lead,
                'human_category_id': row.human_category_id,
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('timestamp').reset_index(drop=True)
        return df
    
    @log_in_out(logger=logger)
    def _get_context_for_message(self, message_row: pd.Series) -> List[Dict[str, Any]]:
        context = (
            self.session.query(
                WhatsAppMessage.raw_text,
                WhatsAppUser.display_name.label('user_display_name'),
                WhatsAppMessage.timestamp
            )
            .join(WhatsAppUser, WhatsAppMessage.sender_id == WhatsAppUser.id)
            .filter(WhatsAppMessage.group_id == message_row['group_id'])
            .filter(WhatsAppMessage.timestamp < message_row['timestamp'])
            .filter(WhatsAppMessage.is_real == True)
            .order_by(WhatsAppMessage.timestamp.desc())
            .limit(10)
            .all()
        )
        
        return [
            {
                'raw_text': c.raw_text,
                'user_display_name': c.user_display_name,
                'timestamp': c.timestamp
            }
            for c in reversed(context)
        ]
    
    @log_in_out(logger=logger)
    def _format_context_messages(self, context: List[Dict[str, Any]]) -> str:
        lines = []
        for msg in context:
            timestamp = msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            sender = msg['user_display_name'] or 'Unknown'
            text = msg['raw_text']
            lines.append(f"[{timestamp}] {sender}: {text}")
        return "\n".join(lines)
    
    @log_in_out(logger=logger)
    def classify_messages_loop(self, messages_df: pd.DataFrame) -> List[Dict[str, Any]]:
        results = []
        
        for idx, row in messages_df.iterrows():
            context = self._get_context_for_message(row)
            context_df = pd.DataFrame(context) if context else pd.DataFrame()
            
            if len(context_df) < self.window_size:
                context_rows = context_df
            else:
                context_rows = context_df.iloc[-self.window_size:]
            
            parsed = self.classifier.classify_message_with_history(
                message_id=str(row['message_id']),
                context_rows=context_rows,
                message_data=row.to_dict(),
                window_size=self.window_size
            )
            
            context_formatted = self._format_context_messages(context)
            
            results.append({
                'message_id': row['id'],
                'message_text': row['raw_text'],
                'context_messages': context_formatted,
                'human_is_lead': row['human_is_lead'],
                'model_is_lead': parsed.is_lead,
                'human_category_id': row['human_category_id'],
                'model_category': parsed.business_type,
            })
        
        return results
    
    @log_in_out(logger=logger)
    def _get_category_name(self, category_id: int) -> str:
        if not category_id:
            return None
        cat = self.session.query(LeadCategory.name).filter_by(id=category_id).first()
        return cat.name if cat else None
    
    @log_in_out(logger=logger)
    def _save_model_tags(self, results: List[Dict[str, Any]]):
        for result in results:
            model_category_id = None
            if result['model_is_lead'] and result['model_category']:
                cat = self.session.query(LeadCategory).filter_by(name=result['model_category']).first()
                if not cat:
                    cat = LeadCategory(name=result['model_category'])
                    self.session.add(cat)
                    self.session.commit()
                model_category_id = cat.id
            
            tag = MessageTag(
                message_id=result['message_id'],
                is_lead=result['model_is_lead'],
                lead_category_id=model_category_id,
                tagger_id=self.model_tagger.id,
                confidence_score=1.0
            )
            self.session.add(tag)
        
        self.session.commit()
    
    @log_in_out(logger=logger)
    def _export_to_csv(self, results: List[Dict[str, Any]], filename: str = 'classification_results.csv'):
        enriched_results = []
        for result in results:
            human_category = self._get_category_name(result['human_category_id'])
            enriched_results.append({
                'message_id': result['message_id'],
                'message_text': result['message_text'],
                'context_messages': result['context_messages'],
                'human_is_lead': result['human_is_lead'],
                'model_is_lead': result['model_is_lead'],
                'human_category': human_category,
                'model_category': result['model_category'],
                'match': result['human_is_lead'] == result['model_is_lead'],
                'category_match': human_category == result['model_category'] if result['human_is_lead'] and result['model_is_lead'] else None
            })
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if enriched_results:
                writer = csv.DictWriter(f, fieldnames=enriched_results[0].keys())
                writer.writeheader()
                writer.writerows(enriched_results)
        
        return enriched_results
    
    @log_in_out(logger=logger)
    def _display_tabular_results(self, csv_results: List[Dict[str, Any]]):
        print("\n" + "="*120)
        print(f"{'Message ID':<12} | {'Text Preview':<30} | {'Human':<10} | {'Model':<10} | {'Match':<7} | {'Cat Match':<10}")
        print("="*120)
        
        for result in csv_results:
            text_preview = result['message_text'][:30] + '...' if len(result['message_text']) > 30 else result['message_text']
            human_tag = 'lead' if result['human_is_lead'] else 'not_lead'
            model_tag = 'lead' if result['model_is_lead'] else 'not_lead'
            match_symbol = '✓' if result['match'] else '✗ WRONG'
            
            cat_match = ''
            if result['category_match'] is not None:
                cat_match = '✓' if result['category_match'] else '✗'
            else:
                cat_match = '-'
            
            print(f"{result['message_id']:<12} | {text_preview:<30} | {human_tag:<10} | {model_tag:<10} | {match_symbol:<7} | {cat_match:<10}")
        
        print("="*120)
        
        total = len(csv_results)
        correct = sum(1 for r in csv_results if r['match'])
        accuracy = (correct / total * 100) if total > 0 else 0
        
        print(f"\nAccuracy: {correct}/{total} ({accuracy:.1f}%)")
    
    @log_in_out(logger=logger)
    def run(self):
        messages_df = self._load_human_tagged_messages()
        
        if messages_df.empty:
            logger.warning("No human-tagged messages found")
            return
        
        logger.info(f"Loaded {len(messages_df)} human-tagged messages")
        
        results = self.classify_messages_loop(messages_df)
        
        self._save_model_tags(results)
        logger.info("Saved model tags to database")
        
        csv_results = self._export_to_csv(results)
        logger.info("Exported results to classification_results.csv")
        
        self._display_tabular_results(csv_results)
        
        self.session.close()


def main():
    orchestrator = AutoTaggingOrchestrator(num_leads=5, num_not_leads=5)
    orchestrator.run()


if __name__ == "__main__":
    main()
