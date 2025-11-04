"""
Keep-alive utility for services that need to stay alive when disabled.

This module provides a reusable function for services that need to remain
active for health checks even when their main functionality is disabled
via feature flags.
"""

import threading
from src.utils.logger import logger
from src.utils.log import log_in_out

@log_in_out(logger)
def keep_alive_for_health_checks(service_name: str, feature_flag_name: str) -> None:
    """
    Keep the process alive for health checks when the service is disabled.
    
    This function runs an infinite loop that keeps the process alive
    while the health server continues to respond to health checks.
    
    Args:
        service_name: Name of the service (e.g., "Message miner", "Message classifier")
        feature_flag_name: Name of the feature flag that controls this service
    """
    logger.info(f"🚫 {service_name} is DISABLED by feature flag {feature_flag_name}")
    logger.info("🟢 Health server remains active for health checks")
    
    # Keep the process alive for health checks but don't start the service
    try:
        while True:
            threading.Event().wait(60)  # Sleep for 60 seconds
    except KeyboardInterrupt:
        logger.info("🛑 Health server shutting down")
