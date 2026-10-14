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


def test_all_whatsapp_admin_routes_require_session_and_writes_have_csrf_guard():
    """Protect owner inbox, takeover, notification acknowledgment, and drafts."""
    from app.cms_admin import require_admin
    from app import whatsapp_ministry, whatsapp_admin_service
    import inspect

    routes = [route for router in (whatsapp_ministry.router,
                                   whatsapp_admin_service.router)
              for route in router.routes if "/admin/" in route.path]
    assert len(routes) >= 6
    for route in routes:
        assert any(dep.call is require_admin for dep in route.dependant.dependencies), route.path
        if route.methods & {"POST", "PUT", "PATCH", "DELETE"}:
            source = inspect.getsource(route.endpoint)
            assert "_require_write_guard(request, session)" in source, route.path


def test_whatsapp_admin_has_no_data_deletion_endpoint():
    """Retention cleanup requires a separate approved maintenance procedure."""
    from app import whatsapp_ministry, whatsapp_admin_service
    for router in (whatsapp_ministry.router, whatsapp_admin_service.router):
        for route in router.routes:
            if "/admin/" in route.path:
                assert "DELETE" not in route.methods, route.path
