"""
Telegram Web App API routes for partners.
Main router that combines all sub-routers.
"""
from fastapi import APIRouter

# Import all sub-routers
from . import auth, documents, documents_detail, document_exports, partner, partner_balance, orders, products

router = APIRouter(prefix="/api/telegram-webapp", tags=["telegram-webapp"])

# Include all sub-routers
router.include_router(auth.router)
router.include_router(documents.router)
router.include_router(documents_detail.router)
router.include_router(document_exports.router)
router.include_router(partner.router)
router.include_router(partner_balance.router)
router.include_router(orders.router)
router.include_router(products.router)
