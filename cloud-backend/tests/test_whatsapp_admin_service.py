"""Security contracts for WhatsApp admin routes.

Integration tests against PostgreSQL and Meta sandbox remain required.
"""
from app.whatsapp_admin_service import router as admin_router
from app.whatsapp_ministry import router as webhook_router


def test_owner_only_routes_require_admin():
    from app.cms_admin import require_admin
    protected = [r for r in admin_router.routes if r.path.endswith(
        ("/notifications", "/acknowledge", "/homily-drafts")) or
        "/notifications/" in r.path]
    assert len(protected) == 3
    for route in protected:
        assert any(dep.call is require_admin for dep in route.dependant.dependencies)


def test_homily_endpoint_not_public_webhook():
    assert not any("homily-drafts" in r.path for r in webhook_router.routes)
    assert any(r.path.endswith("/homily-drafts") and "POST" in r.methods
               for r in admin_router.routes)
