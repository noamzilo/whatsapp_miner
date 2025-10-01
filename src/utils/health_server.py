"""
Lightweight FastAPI health server for container health checks.
Runs in a background thread to avoid blocking the main application.
"""
import threading
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from typing import Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


def create_health_app(service_name: str, health_check_fn: Optional[Callable] = None) -> FastAPI:
    """
    Create a minimal FastAPI app with health endpoint.
    
    Args:
        service_name: Name of the service (for logging/identification)
        health_check_fn: Optional function to call for deep health checks (e.g., DB validation)
    
    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title=f"{service_name} Health API",
        description="Health check endpoint for container orchestration",
        version="1.0.0",
        docs_url=None,  # Disable docs in production
        redoc_url=None,
    )
    
    @app.get("/health")
    async def health_check():
        """
        Health check endpoint for Docker health checks and load balancers.
        Returns 200 OK if the service is healthy, 503 if unhealthy.
        """
        result = {
            "service": service_name,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # If app provided a health check function, call it
        if health_check_fn:
            try:
                health_check_fn()  # App validates its own state (e.g., DB connection)
                result["checks"] = "passed"
            except Exception as e:
                result["status"] = "unhealthy"
                result["checks"] = "failed"
                result["error"] = str(e)
                logger.warning(f"Health check failed for {service_name}: {e}")
                return JSONResponse(status_code=503, content=result)
        
        return result
    
    @app.get("/")
    async def root():
        """Root endpoint redirects to health."""
        return {"message": f"{service_name} is running", "health_endpoint": "/health"}
    
    return app


def start_health_server(
    service_name: str,
    health_check_fn: Optional[Callable] = None,
    port: int = 8000,
    host: str = "0.0.0.0"
) -> Optional[threading.Thread]:
    """
    Start health check server in a background daemon thread.
    
    Args:
        service_name: Name of the service
        health_check_fn: Optional function to call for deep health checks
        port: Port to listen on (default: 8000)
        host: Host to bind to (default: 0.0.0.0)
    
    Returns:
        Thread object running the server, or None if failed to start
    """
    app = create_health_app(service_name, health_check_fn)
    
    def run_server():
        """Run uvicorn server (blocking call)."""
        try:
            logger.info(f"🏥 Starting health server for {service_name} on {host}:{port}")
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="error",  # Quiet, only log errors
                access_log=False,   # No access logs for health checks
            )
        except Exception as e:
            logger.error(f"❌ Health server failed: {e}")
    
    # Start server in daemon thread (won't block shutdown)
    thread = threading.Thread(
        target=run_server,
        name=f"health-server-{service_name}",
        daemon=True
    )
    thread.start()
    
    logger.info(f"✅ Health server thread started for {service_name} on port {port}")
    return thread

