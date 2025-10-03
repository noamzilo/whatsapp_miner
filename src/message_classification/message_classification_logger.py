from src.utils.log import get_logger, setup_logger
from src.paths import logs_root

setup_logger(log_location=str(logs_root / "message_classification"))
logger = get_logger("message_classification")
