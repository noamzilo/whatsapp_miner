from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from src.db.db_interface import get_session_local
from src.db.models.whatsapp_message import WhatsAppMessage
from src.db.models.whatsapp_user import WhatsAppUser
from src.db.models.whatsapp_group import WhatsAppGroup
from src.db.models.tagger import Tagger
from src.db.models.message_tag import MessageTag
from src.db.models.lead_category import LeadCategory
from src.utils.log import log_in_out
from src.utils.logger import logger


COLORS = {
    'reset': '\033[0m',
    'blue': '\033[94m',
    'cyan': '\033[96m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'red': '\033[91m',
    'bold': '\033[1m',
    'gray': '\033[90m',
}

MESSAGE_COLORS = [
    '\033[48;5;234m',
    '\033[48;5;235m',
]


class InteractiveTagger:
    def __init__(self):
        self.session: Session = get_session_local()()
        self.human_tagger = self._get_or_create_human_tagger()
        self.untagged_messages = []
        self.current_index = 0
        
    @log_in_out(logger=logger)
    def _get_or_create_human_tagger(self) -> Tagger:
        tagger = self.session.query(Tagger).filter_by(
            tagger_type_id=1,
            identifier='human_tagger'
        ).first()
        
        if not tagger:
            tagger = Tagger(tagger_type_id=1, identifier='human_tagger')
            self.session.add(tagger)
            self.session.commit()
        
        return tagger
    
    @log_in_out(logger=logger)
    def _load_untagged_messages(self, limit: int = 100):
        tagged_message_ids = self.session.query(MessageTag.message_id).filter_by(
            tagger_id=self.human_tagger.id
        ).subquery()
        
        messages = (
            self.session.query(
                WhatsAppMessage.id,
                WhatsAppMessage.message_id,
                WhatsAppMessage.raw_text,
                WhatsAppMessage.timestamp,
                WhatsAppMessage.group_id,
                WhatsAppMessage.sender_id,
                WhatsAppMessage.quoted_message_id,
                WhatsAppUser.display_name.label('user_display_name'),
                WhatsAppGroup.group_name
            )
            .join(WhatsAppUser, WhatsAppMessage.sender_id == WhatsAppUser.id)
            .join(WhatsAppGroup, WhatsAppMessage.group_id == WhatsAppGroup.id)
            .filter(WhatsAppMessage.is_real == True)
            .filter(~WhatsAppMessage.id.in_(tagged_message_ids))
            .order_by(WhatsAppMessage.timestamp.asc())
            .limit(limit)
            .all()
        )
        
        self.untagged_messages = [
            {
                'id': m.id,
                'message_id': m.message_id,
                'raw_text': m.raw_text,
                'timestamp': m.timestamp,
                'group_id': m.group_id,
                'sender_id': m.sender_id,
                'quoted_message_id': m.quoted_message_id,
                'user_display_name': m.user_display_name,
                'group_name': m.group_name,
            }
            for m in messages
        ]
    
    @log_in_out(logger=logger)
    def _get_context_messages(self, current_msg: Dict[str, Any], count: int = 10) -> List[Dict[str, Any]]:
        context = (
            self.session.query(
                WhatsAppMessage.id,
                WhatsAppMessage.raw_text,
                WhatsAppMessage.timestamp,
                WhatsAppMessage.quoted_message_id,
                WhatsAppUser.display_name.label('user_display_name')
            )
            .join(WhatsAppUser, WhatsAppMessage.sender_id == WhatsAppUser.id)
            .filter(WhatsAppMessage.group_id == current_msg['group_id'])
            .filter(WhatsAppMessage.timestamp < current_msg['timestamp'])
            .filter(WhatsAppMessage.is_real == True)
            .order_by(WhatsAppMessage.timestamp.desc())
            .limit(count)
            .all()
        )
        
        context_list = [
            {
                'id': c.id,
                'raw_text': c.raw_text,
                'timestamp': c.timestamp,
                'quoted_message_id': c.quoted_message_id,
                'user_display_name': c.user_display_name,
            }
            for c in reversed(context)
        ]
        
        return context_list
    
    @log_in_out(logger=logger)
    def _get_quoted_message(self, quoted_id: Optional[int]) -> Optional[str]:
        if not quoted_id:
            return None
        
        quoted = self.session.query(WhatsAppMessage.raw_text).filter_by(id=quoted_id).first()
        return quoted.raw_text if quoted else None
    
    def _display_message(self, msg: Dict[str, Any], color_idx: int, is_current: bool = False):
        bg_color = MESSAGE_COLORS[color_idx % len(MESSAGE_COLORS)]
        timestamp_str = msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        sender = msg['user_display_name'] or 'Unknown'
        text = msg['raw_text']
        
        prefix = f"{COLORS['bold']}{COLORS['green']}>>> CURRENT <<< {COLORS['reset']}" if is_current else ""
        
        quoted_text = self._get_quoted_message(msg.get('quoted_message_id'))
        quoted_display = ""
        if quoted_text:
            quoted_display = f"\n{bg_color}{COLORS['gray']}  [Quoted: {quoted_text[:60]}...]{COLORS['reset']}"
        
        print(f"{bg_color}{prefix}[{timestamp_str}] {sender}: {text}{quoted_display}{COLORS['reset']}")
    
    def _display_current_message_with_context(self):
        if not self.untagged_messages or self.current_index >= len(self.untagged_messages):
            print(f"{COLORS['red']}No more messages to tag!{COLORS['reset']}")
            return
        
        current_msg = self.untagged_messages[self.current_index]
        context = self._get_context_messages(current_msg, count=10)
        
        print("\n" + "="*80)
        print(f"{COLORS['cyan']}Message {self.current_index + 1}/{len(self.untagged_messages)}{COLORS['reset']}")
        print(f"{COLORS['cyan']}Group: {current_msg['group_name']}{COLORS['reset']}")
        print("="*80)
        
        for i, ctx_msg in enumerate(context):
            self._display_message(ctx_msg, i, False)
        
        self._display_message(current_msg, len(context), True)
        
        print("\n" + "-"*80)
        print(f"{COLORS['yellow']}Commands: y=lead | n=not lead | u=lead no category | s=skip | p=previous | j <id>=jump | q=quit{COLORS['reset']}")
        print("-"*80)
    
    @log_in_out(logger=logger)
    def _get_all_categories(self) -> List[LeadCategory]:
        return self.session.query(LeadCategory).order_by(LeadCategory.name).all()
    
    def _prompt_for_category(self) -> Optional[int]:
        categories = self._get_all_categories()
        
        print(f"\n{COLORS['cyan']}Available categories:{COLORS['reset']}")
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat.name}")
        print(f"  0. Skip category")
        
        while True:
            choice = input(f"{COLORS['yellow']}Enter category number: {COLORS['reset']}").strip()
            if choice == '0':
                return None
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(categories):
                    return categories[idx].id
            except ValueError:
                pass
            print(f"{COLORS['red']}Invalid choice. Try again.{COLORS['reset']}")
    
    @log_in_out(logger=logger)
    def _save_tag(self, message_id: int, is_lead: bool, category_id: Optional[int] = None):
        tag = MessageTag(
            message_id=message_id,
            is_lead=is_lead,
            lead_category_id=category_id,
            tagger_id=self.human_tagger.id,
            confidence_score=1.0
        )
        self.session.add(tag)
        self.session.commit()
    
    @log_in_out(logger=logger)
    def run(self):
        self._load_untagged_messages(limit=1000)
        
        if not self.untagged_messages:
            print(f"{COLORS['green']}All messages are already tagged!{COLORS['reset']}")
            return
        
        print(f"{COLORS['green']}Loaded {len(self.untagged_messages)} untagged messages{COLORS['reset']}")
        
        while self.current_index < len(self.untagged_messages):
            self._display_current_message_with_context()
            
            command = input(f"{COLORS['bold']}> {COLORS['reset']}").strip().lower()
            
            if command == 'q':
                print(f"{COLORS['green']}Exiting...{COLORS['reset']}")
                break
            
            elif command == 'y':
                category_id = self._prompt_for_category()
                if category_id is None:
                    print(f"{COLORS['yellow']}Skipping - no category selected{COLORS['reset']}")
                    continue
                self._save_tag(self.untagged_messages[self.current_index]['id'], True, category_id)
                print(f"{COLORS['green']}Tagged as LEAD{COLORS['reset']}")
                self.current_index += 1
            
            elif command == 'n':
                self._save_tag(self.untagged_messages[self.current_index]['id'], False, None)
                print(f"{COLORS['green']}Tagged as NOT LEAD{COLORS['reset']}")
                self.current_index += 1
            
            elif command == 'u':
                self._save_tag(self.untagged_messages[self.current_index]['id'], True, None)
                print(f"{COLORS['green']}Tagged as LEAD (no category){COLORS['reset']}")
                self.current_index += 1
            
            elif command == 's':
                print(f"{COLORS['yellow']}Skipped{COLORS['reset']}")
                self.current_index += 1
            
            elif command == 'p':
                if self.current_index > 0:
                    self.current_index -= 1
                else:
                    print(f"{COLORS['red']}Already at first message{COLORS['reset']}")
            
            elif command.startswith('j '):
                try:
                    jump_id = int(command[2:])
                    for i, msg in enumerate(self.untagged_messages):
                        if msg['id'] == jump_id:
                            self.current_index = i
                            print(f"{COLORS['green']}Jumped to message {jump_id}{COLORS['reset']}")
                            break
                    else:
                        print(f"{COLORS['red']}Message ID {jump_id} not found in untagged messages{COLORS['reset']}")
                except ValueError:
                    print(f"{COLORS['red']}Invalid message ID{COLORS['reset']}")
            
            else:
                print(f"{COLORS['red']}Unknown command{COLORS['reset']}")
        
        self.session.close()
        print(f"{COLORS['green']}Done!{COLORS['reset']}")


if __name__ == "__main__":
    tagger = InteractiveTagger()
    tagger.run()

