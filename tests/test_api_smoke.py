import io
import pandas as pd

from main import app


def test_convert_single_wgs84_success():
    client = app.test_client()
    resp = client.post(
        "/convert_single",
        json={
            "sourceType": "wgs84",
            "lonX": 116.397428,
            "latY": 39.90923,
            "bandType": "3°分带",
            "withBand": True,
            "decimalPlaces": 4,
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["result"]["type"] == "cgcs2000"


def test_convert_single_rejects_bad_source_type():
    client = app.test_client()
    resp = client.post(
        "/convert_single",
        json={
            "sourceType": "bad-type",
            "lonX": 116.397428,
            "latY": 39.90923,
        },
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"


def test_export_template_rejects_bad_format():
    client = app.test_client()
    resp = client.get("/export_template?type=exe&source=wgs84")
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"


def test_convert_batch_rejects_too_many_rows(monkeypatch):
    client = app.test_client()

    app_module = __import__("main")
    monkeypatch.setattr(app_module, "MAX_BATCH_ROWS", 1)

    df = pd.DataFrame(
        {
            "经度": [116.397428, 121.473701],
            "纬度": [39.90923, 31.230416],
        }
    )
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    resp = client.post(
        "/convert_batch",
        data={
            "file": (buf, "test.csv"),
            "sourceType": "wgs84",
            "bandType": "3°分带",
            "withBand": "false",
            "decimalPlaces": "4",
        },
        content_type="multipart/form-data",
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "最多支持" in data["message"]
