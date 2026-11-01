import io
import os
import tempfile

import pandas as pd

from main import APP_VERSION, _get_map_config, _safe_excel_value, app, convert_coordinate


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


def test_healthz_ok():
    client = app.test_client()
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["version"] == APP_VERSION


def test_gcj02_bd09_known_values_and_roundtrip():
    client = app.test_client()

    resp = client.post(
        "/convert_single",
        json={
            "sourceType": "wgs84",
            "targetType": "gcj02",
            "lonX": 116.397428,
            "latY": 39.909230,
            "decimalPlaces": 8,
        },
    )
    assert resp.status_code == 200
    gcj = resp.get_json()["result"]
    assert abs(gcj["target"]["longitude"] - 116.40367163) < 1e-7
    assert abs(gcj["target"]["latitude"] - 39.91063351) < 1e-7

    resp = client.post(
        "/convert_single",
        json={
            "sourceType": "wgs84",
            "targetType": "bd09",
            "lonX": 116.397428,
            "latY": 39.909230,
            "decimalPlaces": 8,
        },
    )
    assert resp.status_code == 200
    bd = resp.get_json()["result"]
    assert abs(bd["target"]["longitude"] - 116.41004410) < 1e-7
    assert abs(bd["target"]["latitude"] - 39.91697286) < 1e-7
    assert 0 <= bd["map"]["distance_m"] < 1

    resp = client.post(
        "/convert_single",
        json={
            "sourceType": "gcj02",
            "lonX": 116.40367163,
            "latY": 39.91063351,
            "decimalPlaces": 8,
        },
    )
    assert resp.status_code == 200
    back = resp.get_json()["result"]
    assert back["target_type"] == "wgs84"
    assert abs(back["target"]["longitude"] - 116.397428) < 1e-6
    assert abs(back["target"]["latitude"] - 39.909230) < 1e-6


def test_cgcs2000_with_band_mismatch_is_rejected():
    client = app.test_client()
    resp = client.post(
        "/convert_single",
        json={
            "sourceType": "cgcs2000",
            "lonX": 4419624.3249,
            "latY": 38448475.8151,
            "bandNum": 39,
            "sourceWithBand": True,
        },
    )
    assert resp.status_code == 400
    assert "不一致" in resp.get_json()["message"]


def test_cgcs2000_missing_band_prefix_is_rejected():
    client = app.test_client()
    resp = client.post(
        "/convert_single",
        json={
            "sourceType": "cgcs2000",
            "lonX": 4419624.3249,
            "latY": 448475.8151,
            "bandNum": 39,
            "sourceWithBand": True,
        },
    )
    assert resp.status_code == 400
    assert "未包含带号" in resp.get_json()["message"]


def test_band_boundaries_and_invalid_band_type():
    client = app.test_client()
    resp = client.post(
        "/convert_single",
        json={
            "sourceType": "wgs84",
            "lonX": 136.5,
            "latY": 39.0,
            "bandType": "3°分带",
        },
    )
    assert resp.status_code == 400
    assert "超出" in resp.get_json()["message"]

    resp = client.post(
        "/convert_single",
        json={
            "sourceType": "wgs84",
            "lonX": 136.499,
            "latY": 39.0,
            "bandType": "3°分带",
            "withBand": True,
        },
    )
    assert resp.status_code == 200

    resp = client.post(
        "/convert_single",
        json={
            "sourceType": "wgs84",
            "lonX": 138.0,
            "latY": 39.0,
            "bandType": "6°分带",
        },
    )
    assert resp.status_code == 400

    resp = client.post(
        "/convert_single",
        json={"sourceType": "wgs84", "lonX": 116.397428, "latY": 39.90923, "bandType": "5°"},
    )
    assert resp.status_code == 400
    assert "bandType" in resp.get_json()["message"]


def test_convert_single_rejects_non_boolean_with_band():
    client = app.test_client()
    resp = client.post(
        "/convert_single",
        json={
            "sourceType": "wgs84",
            "lonX": 116.397428,
            "latY": 39.90923,
            "withBand": "not-a-bool",
        },
    )
    assert resp.status_code == 400
    assert "布尔" in resp.get_json()["message"]


def test_export_template_cgcs2000_has_correct_samples():
    client = app.test_client()
    resp = client.get("/export_template?type=csv&source=cgcs2000&bandType=3°分带&withBand=true")
    assert resp.status_code == 200
    df = pd.read_csv(io.BytesIO(resp.data))
    assert {"X坐标", "Y坐标", "带号", "备注（可选）"} <= set(df.columns)
    first = df.iloc[0]
    assert abs(float(first["X坐标"]) - 4419624.3249) < 0.001
    assert abs(float(first["Y坐标"]) - 39448475.8151) < 0.001
    assert int(first["带号"]) == 39


def test_batch_gcj02_to_wgs84():
    client = app.test_client()
    df = pd.DataFrame({"经度": [116.40367163], "纬度": [39.91063351]})
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    resp = client.post(
        "/convert_batch",
        data={
            "file": (buf, "gcj.csv"),
            "sourceType": "gcj02",
            "targetType": "wgs84",
            "withBand": "false",
            "decimalPlaces": "8",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["successCount"] == 1
    assert data["source_type"] == "gcj02"
    assert data["target_type"] == "wgs84"
    out = data["results"][0]["output"]
    lon, lat = [float(x) for x in out.split(",")]
    assert abs(lon - 116.397428) < 1e-6
    assert abs(lat - 39.909230) < 1e-6
    assert data["results"][0]["map"] is not None


def test_index_includes_map_config_and_local_assets():
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "window.MAP_CONFIG" in html
    assert "vendor/leaflet/leaflet.js" in html
    assert "vendor/bootstrap/bootstrap.bundle.min.js" in html
    assert "cdn.jsdelivr.net" not in html


def test_convert_coordinate_can_skip_map_data():
    result, err = convert_coordinate(
        "wgs84", 116.397428, 39.90923,
        "3°分带", True,
        target_type="gcj02",
        include_map=False,
    )
    assert err is None
    assert result["map"] is None


def test_convert_batch_preview_maps_first_50_rows():
    client = app.test_client()
    df = pd.DataFrame(
        {
            "经度": [116.397428 + (i % 10) * 0.01 for i in range(60)],
            "纬度": [39.90923 + (i // 10) * 0.01 for i in range(60)],
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
            "targetType": "gcj02",
            "decimalPlaces": "6",
        },
        content_type="multipart/form-data",
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 60
    assert data["successCount"] == 60
    assert len(data["results"]) == 50
    assert all(row["map"] is not None for row in data["results"])


def test_map_provider_defaults_to_tianditu(monkeypatch):
    monkeypatch.delenv("MAP_PROVIDER", raising=False)
    monkeypatch.delenv("TIANDITU_KEY", raising=False)
    config = _get_map_config()
    assert config["provider"] == "tianditu"
    assert config["enabled"] is True
    assert config["tile_crs"] == "wgs84"
    assert config["key_configured"] is False
    assert config["tianditu_key"] == ""


def test_map_provider_reads_tianditu_key(monkeypatch):
    monkeypatch.setenv("MAP_PROVIDER", "tianditu")
    monkeypatch.setenv("TIANDITU_KEY", "test-key")
    config = _get_map_config()
    assert config["provider"] == "tianditu"
    assert config["key_configured"] is True
    assert config["tianditu_key"] == "test-key"


def test_map_provider_can_be_disabled(monkeypatch):
    monkeypatch.setenv("MAP_PROVIDER", "none")
    monkeypatch.setenv("TIANDITU_KEY", "test-key")
    config = _get_map_config()
    assert config["provider"] == "none"
    assert config["enabled"] is False
    assert config["key_configured"] is False
    assert config["tianditu_key"] == ""


def test_legacy_map_providers_fall_back_to_tianditu(monkeypatch):
    for legacy in ("osm", "auto", "custom", "unknown"):
        monkeypatch.setenv("MAP_PROVIDER", legacy)
        config = _get_map_config()
        assert config["provider"] == "tianditu"
        assert config["enabled"] is True


def test_csp_only_allows_tianditu_when_enabled(monkeypatch):
    client = app.test_client()
    monkeypatch.setenv("MAP_PROVIDER", "tianditu")
    csp = client.get("/").headers["Content-Security-Policy"]
    assert "https://*.tianditu.gov.cn" in csp
    assert "openstreetmap" not in csp.lower()

    monkeypatch.setenv("MAP_PROVIDER", "none")
    csp = client.get("/").headers["Content-Security-Policy"]
    assert "tianditu.gov.cn" not in csp


def test_batch_extra_columns_do_not_overwrite_system_columns():
    client = app.test_client()
    csv = (
        "经度,纬度,转换状态,备注,备注（可选）\n"
        "116.397428,39.909230,自定义状态,额外备注,正式备注\n"
    )
    buf = io.BytesIO(csv.encode("utf-8-sig"))
    resp = client.post(
        "/convert_batch",
        data={
            "file": (buf, "extra.csv"),
            "sourceType": "wgs84",
            "targetType": "gcj02",
            "decimalPlaces": "6",
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    path = os.path.join(tempfile.gettempdir(), data["temp_file"])
    try:
        df = pd.read_excel(path, engine="openpyxl")
        row = df.iloc[0]
        assert row["转换状态"] == "成功"
        assert row["附加_转换状态"] == "自定义状态"
        assert row["备注"] == "正式备注"
        assert row["附加_备注"] == "额外备注"
        assert pd.isna(row["错误信息"])
    finally:
        os.unlink(path)


def test_safe_excel_value_blocks_formula_injection():
    assert _safe_excel_value("=1+1") == "'=1+1"
    assert _safe_excel_value("+1") == "'+1"
    assert _safe_excel_value("@cmd") == "'@cmd"
    assert _safe_excel_value("-123.45") == "-123.45"
    assert _safe_excel_value("-1+2") == "'-1+2"
    assert _safe_excel_value("  =SUM(A1)") == "'  =SUM(A1)"
