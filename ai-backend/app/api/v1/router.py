"""Agregador de rotas da v1."""

from fastapi import APIRouter

from . import admin, analyze_context, auth, fictional_data, validate_prescription

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(admin.router)
router.include_router(analyze_context.router)
router.include_router(validate_prescription.router)
router.include_router(fictional_data.router)
