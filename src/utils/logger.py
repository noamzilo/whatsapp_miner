from src.utils.log import setup_logger, get_logger
from src.paths import logs_root

setup_logger(log_location=str(logs_root / "whatsapp_miner"))
logger = get_logger("whatsapp_miner")

