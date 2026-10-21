from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.businesses import router as businesses_router
from app.routers.products import router as products_router
from app.routers.orders import router as orders_router
from app.routers.customers import router as customers_router
from app.routers.webhooks import router as webhooks_router
from app.routers.whatsapp import router as whatsapp_router
from app.routers.conversations import router as conversations_router
from app.routers.media import router as media_router
from app.routers.team import router as team_router

__all__ = [
    "health_router",
    "auth_router",
    "businesses_router",
    "products_router",
    "orders_router",
    "customers_router",
    "webhooks_router",
    "whatsapp_router",
    "conversations_router",
    "media_router",
    "team_router",
]
