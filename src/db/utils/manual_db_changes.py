import sys
import os
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from src.db.db_interface import get_db_session
from src.db.dal import get_total_messages_count, get_processed_messages_count, get_unprocessed_messages_count, update_messages_to_unprocessed
from src.message_classification.message_classification_logger import logger
from src.env_var_injection import database_url

logger.info(f"[DEBUG] SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER: {os.getenv('SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER')}")
logger.info(f"[DEBUG] SUPABASE_DATABASE_CONNECTION_STRING: {os.getenv('SUPABASE_DATABASE_CONNECTION_STRING')}")
logger.info(f"[DEBUG] SUPABASE_DATABASE_CONNECTION_STRING_DIRECT: {os.getenv('SUPABASE_DATABASE_CONNECTION_STRING_DIRECT')}")
logger.info(f"[DEBUG] database_url from env_var_injection: {database_url}")


@dataclass
class ProcessingStats:
    total_messages: int
    processed_messages: int
    unprocessed_messages: int
    processed_percentage: float


@dataclass
class ResetResult:
    affected_count: int
    updated_count: int
    success: bool
    message: str


class ManualDbChanges:
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._should_close_session = session is None
    
    def __enter__(self):
        if self._session is None:
            self._session = get_db_session().__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_session and self._session is not None:
            self._session.close()
            self._session = None
    
    def reset_llm_processed_flag(self, dry_run: bool = False) -> ResetResult:
        try:
            affected_count = get_processed_messages_count(self._session)
            logger.info(f"Found {affected_count} messages with llm_processed=true")
            
            if dry_run:
                logger.info("DRY RUN: No changes made")
                return ResetResult(
                    affected_count=affected_count,
                    updated_count=0,
                    success=True,
                    message="DRY RUN: No changes made"
                )
            
            if affected_count == 0:
                logger.info("No messages need to be reset")
                return ResetResult(
                    affected_count=0,
                    updated_count=0,
                    success=True,
                    message="No messages need to be reset"
                )
            
            updated_count = update_messages_to_unprocessed(self._session)
            self._session.commit()
            logger.info(f"Reset llm_processed flag for {updated_count} messages")
            
            remaining_count = get_processed_messages_count(self._session)
            if remaining_count == 0:
                message = "All messages now have llm_processed=false"
                logger.info(message)
            else:
                message = f"{remaining_count} messages still have llm_processed=true"
                logger.warning(message)
            
            return ResetResult(
                affected_count=affected_count,
                updated_count=updated_count,
                success=True,
                message=message
            )
        except Exception as e:
            logger.error(f"Error resetting llm_processed flag: {e}")
            self._session.rollback()
            return ResetResult(
                affected_count=0,
                updated_count=0,
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def get_llm_processed_stats(self) -> ProcessingStats:
        try:
            total_count = get_total_messages_count(self._session)
            processed_count = get_processed_messages_count(self._session)
            unprocessed_count = get_unprocessed_messages_count(self._session)
            processed_percentage = (processed_count / total_count * 100) if total_count > 0 else 0
            
            stats = ProcessingStats(
                total_messages=total_count,
                processed_messages=processed_count,
                unprocessed_messages=unprocessed_count,
                processed_percentage=processed_percentage
            )
            
            logger.info(f"Stats: {stats.total_messages} total, {stats.processed_messages} processed ({stats.processed_percentage:.1f}%)")
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise


# Convenience functions for backward compatibility
def reset_llm_processed_flag(session: Optional[Session] = None, dry_run: bool = False) -> ResetResult:
    with ManualDbChanges(session) as manager:
        return manager.reset_llm_processed_flag(dry_run)


def get_llm_processed_stats(session: Optional[Session] = None) -> ProcessingStats:
    with ManualDbChanges(session) as manager:
        return manager.get_llm_processed_stats()


if __name__ == "__main__":
    
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        dry_run = len(sys.argv) > 2 and sys.argv[2] == "--dry-run"
        print(f"Resetting llm_processed flag (dry_run={dry_run})")
        affected = reset_llm_processed_flag(dry_run=dry_run)
        print(f"Affected {affected} messages")
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        print("Getting llm_processed statistics...")
        stats = get_llm_processed_stats()
        print(f"Stats: {stats}")
    else:
        print("Usage:")
        print("  python -m src.db.utils.manual_db_changes reset [--dry-run]")
        print("  python -m src.db.utils.manual_db_changes stats")
