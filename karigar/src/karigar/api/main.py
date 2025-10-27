"""
KARIGAR FastAPI Backend
Main API server for the multi-agent artisan platform
"""

from fastapi import FastAPI, HTTPException, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import uuid

from ..config.settings import settings
from ..schemas.models import init_db, get_session
from ..orchestrators.workflow_orchestrator import (
    workflow_orchestrator,
    WorkflowType,
)
from ..tools import tool_registry

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.api_debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and register tools"""
    logger.info("Starting KARIGAR API...")
    try:
        init_db(settings.database_url)
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")

    logger.info(f"✓ {len(tool_registry.tools)} tools registered")
    logger.info(f"✓ Workflow orchestrator ready with {len(workflow_orchestrator.workflow_definitions)} workflows")
    logger.info(f"API running on {settings.api_host}:{settings.api_port}")


# ==================== Request Models ====================

class ArtisanOnboardingRequest(BaseModel):
    """Artisan onboarding request"""
    name: str
    craft_type: str
    location: str
    experience_years: int
    has_portfolio: bool = False
    has_website: bool = False
    has_social_media: bool = False


class OrderRequest(BaseModel):
    """Customer order request"""
    customer_name: str
    customer_email: str
    customer_phone: str
    description: str
    quantity: int
    timeline_days: int = 30
    estimated_cost: float


class MaterialNeedRequest(BaseModel):
    """Material sourcing request"""
    artisan_id: str
    materials: Dict[str, Dict[str, Any]]


# ==================== Health Check ====================

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "running",
            "database": "connected",
            "tools": len(tool_registry.tools),
            "workflows": len(workflow_orchestrator.workflow_definitions)
        }
    }


# ==================== Artisan Onboarding ====================

@app.post("/api/artisan/onboard", tags=["Artisan"])
async def onboard_artisan(request: ArtisanOnboardingRequest):
    """
    Onboard a new artisan
    Triggers: IntakeAgent -> SupplierAgent workflow
    """
    try:
        artisan_id = f"artisan_{uuid.uuid4().hex[:8]}"

        artisan_data = {
            "id": artisan_id,
            "name": request.name,
            "craft_type": request.craft_type,
            "location": request.location,
            "experience_years": request.experience_years,
            "has_portfolio": request.has_portfolio,
            "has_website": request.has_website,
            "has_social_media": request.has_social_media,
        }

        # Execute onboarding workflow
        result = await workflow_orchestrator.onboard_artisan(artisan_data)

        logger.info(f"✓ Artisan {artisan_id} onboarded successfully")

        return {
            "status": "success",
            "artisan_id": artisan_id,
            "workflow": result
        }

    except Exception as e:
        logger.error(f"Onboarding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Order Management ====================

@app.post("/api/order/create", tags=["Order"])
async def create_order(artisan_id: str, request: OrderRequest):
    """
    Create a customer order
    Triggers: CommitAgent -> SupplierAgent workflow
    """
    try:
        order_id = f"order_{uuid.uuid4().hex[:12]}"

        order_data = {
            "order_id": order_id,
            "customer_name": request.customer_name,
            "customer_email": request.customer_email,
            "customer_phone": request.customer_phone,
            "description": request.description,
            "quantity": request.quantity,
            "timeline_days": request.timeline_days,
            "estimated_cost": request.estimated_cost,
        }

        # Execute order fulfillment workflow
        result = await workflow_orchestrator.fulfill_order(order_data, artisan_id)

        logger.info(f"✓ Order {order_id} created for artisan {artisan_id}")

        return {
            "status": "success",
            "order_id": order_id,
            "artisan_id": artisan_id,
            "workflow": result
        }

    except Exception as e:
        logger.error(f"Order creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Supplier Management ====================

@app.post("/api/supplier/search", tags=["Supplier"])
async def search_suppliers(artisan_id: str, request: MaterialNeedRequest):
    """
    Search for suppliers for artisan's material needs
    Uses SupplierAgent
    """
    try:
        # Execute supplier search
        result = await tool_registry.execute(
            "supplier_search",
            material_name=list(request.materials.keys())[0],
            location="India",
            quantity=list(request.materials.values())[0].get("quantity", 10)
        )

        logger.info(f"✓ Supplier search completed for artisan {artisan_id}")

        return {
            "status": "success",
            "artisan_id": artisan_id,
            "results": result.to_dict() if result else None
        }

    except Exception as e:
        logger.error(f"Supplier search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Workflow Management ====================

@app.get("/api/workflows", tags=["Workflow"])
async def list_workflows():
    """List all available workflows"""
    return {
        "workflows": workflow_orchestrator.list_workflow_types()
    }


@app.get("/api/workflows/{workflow_id}", tags=["Workflow"])
async def get_workflow_status(workflow_id: str):
    """Get status of a workflow"""
    workflow = workflow_orchestrator.get_workflow_status(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {
        "workflow": workflow
    }


@app.get("/api/artisan/{artisan_id}/workflows", tags=["Workflow"])
async def get_artisan_workflows(artisan_id: str):
    """Get all workflows for an artisan"""
    workflows = workflow_orchestrator.get_artisan_workflows(artisan_id)

    return {
        "artisan_id": artisan_id,
        "workflows": workflows,
        "count": len(workflows)
    }


# ==================== Tools Management ====================

@app.get("/api/tools", tags=["Tools"])
async def list_tools():
    """List all available tools"""
    return {
        "tools": tool_registry.list_tools(),
        "total": len(tool_registry.tools)
    }


@app.post("/api/tools/{tool_name}/execute", tags=["Tools"])
async def execute_tool(tool_name: str, params: Dict[str, Any]):
    """Execute a tool directly"""
    try:
        result = await tool_registry.execute(tool_name, **params)

        return {
            "tool": tool_name,
            "success": result.success,
            "data": result.data,
            "message": result.message,
            "execution_time": result.execution_time
        }

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Analytics ====================

@app.get("/api/analytics/summary", tags=["Analytics"])
async def get_analytics_summary():
    """Get system analytics summary"""
    return {
        "total_workflows": len(workflow_orchestrator.workflows),
        "total_tools": len(tool_registry.tools),
        "timestamp": datetime.utcnow().isoformat()
    }


# ==================== WebSocket (Real-time Updates) ====================

@app.websocket("/ws/workflow/{workflow_id}")
async def websocket_workflow_updates(websocket: WebSocket, workflow_id: str):
    """
    WebSocket endpoint for real-time workflow updates
    Clients can subscribe to workflow progress
    """
    await websocket.accept()

    try:
        workflow = workflow_orchestrator.get_workflow_status(workflow_id)

        if not workflow:
            await websocket.send_json({
                "error": "Workflow not found"
            })
            await websocket.close()
            return

        # Send initial state
        await websocket.send_json({
            "type": "workflow_state",
            "workflow_id": workflow_id,
            "state": workflow.get("state"),
            "timestamp": datetime.utcnow().isoformat()
        })

        # Keep connection open for updates
        while True:
            # This would be replaced with actual updates from queue
            import asyncio
            await asyncio.sleep(5)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


# ==================== Error Handling ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ==================== Root ====================

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "service": "KARIGAR - Multi-Agent Artisan Platform",
        "version": settings.api_version,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": "/docs"
    }


# Export app for production servers
__all__ = ["app"]
