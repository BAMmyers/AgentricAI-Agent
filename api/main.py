"""
AgentricAI API - Main Module
Consolidated entry point that imports from the single gateway module.

This module provides backward compatibility for legacy imports.
Use api.gateway for the full API implementation.
"""
# Import the consolidated gateway
from api.gateway import app, init_api


# Re-export for backward compatibility
__all__ = ['app', 'init_api']


def run_server():
    """Run the API server using the consolidated gateway."""
    import uvicorn
    from core.config import get_config
    
    config = get_config()
    uvicorn.run(
        app,
        host=config.host,
        port=config.api_port,
        log_level=config.log_level.lower()
    )


if __name__ == "__main__":
    run_server()
