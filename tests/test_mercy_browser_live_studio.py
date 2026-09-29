import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "cloud-backend" / "app" / "media_studio.py"
ADMIN = ROOT / "cloud-backend" / "app" / "static" / "admin.html"
DOCKER = ROOT / "cloud-backend" / "Dockerfile"

def test_media_studio_python_syntax():
    ast.parse(MEDIA.read_text(encoding="utf-8"))

def test_stream_key_not_returned_to_admin_browser():
    text = MEDIA.read_text(encoding="utf-8")
    assert 'data["stream_key"]' not in text
    assert 'data["stream_ready"]' in text

def test_publish_gateway_is_authenticated_and_csrf_guarded():
    text = MEDIA.read_text(encoding="utf-8")
    assert '@router.websocket("/api/admin/live/{live_id}/publish")' in text
    assert "_read_session(websocket)" in text
    assert 'websocket.query_params.get("csrf"' in text
    assert 'websocket.headers.get("origin")' in text
    assert 'websocket.headers.get("x-forwarded-host")' in text

def test_gateway_uses_server_side_ffmpeg_and_youtube_lifecycle():
    text = MEDIA.read_text(encoding="utf-8")
    assert 'asyncio.create_subprocess_exec(' in text
    assert '"ffmpeg"' in text
    assert '_wait_for_youtube_active(stream_id)' in text
    assert '_youtube_transition, broadcast_id, "live"' in text
    assert '_youtube_transition, broadcast_id, "complete"' in text

def test_admin_contains_integrated_live_controls_without_stream_key():
    text = ADMIN.read_text(encoding="utf-8")
    for required in (
        'id="livePreview"',
        'id="liveCameraSelect"',
        'id="liveMicSelect"',
        'id="liveMuteBtn"',
        'id="liveCameraBtn"',
        'id="liveFlipBtn"',
        'id="liveScreenBtn"',
        'id="liveGoBrowserBtn"',
        'id="liveEndBrowserBtn"',
        "new WebSocket(",
        "new MediaRecorder(",
    ):
        assert required in text
    assert "v.stream_key" not in text
    assert "Show encoder details" not in text

def test_runtime_image_contains_ffmpeg():
    text = DOCKER.read_text(encoding="utf-8")
    assert "apt-get install -y --no-install-recommends ffmpeg" in text
