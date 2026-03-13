from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from pyproj import Transformer as PyProjTransformer
from functools import lru_cache
import io
import os
import re
import time
import glob
import tempfile

app = Flask(__name__)

# ============================================================
# 权威 EPSG 编码配置
# ============================================================
CGCS2000_3DEG = {
    "no_band": [
        {"band_num": 25, "central_lon": 75.0,  "epsg": 4534},
        {"band_num": 26, "central_lon": 78.0,  "epsg": 4535},
        {"band_num": 27, "central_lon": 81.0,  "epsg": 4536},
        {"band_num": 28, "central_lon": 84.0,  "epsg": 4537},
        {"band_num": 29, "central_lon": 87.0,  "epsg": 4538},
        {"band_num": 30, "central_lon": 90.0,  "epsg": 4539},
        {"band_num": 31, "central_lon": 93.0,  "epsg": 4540},
        {"band_num": 32, "central_lon": 96.0,  "epsg": 4541},
        {"band_num": 33, "central_lon": 99.0,  "epsg": 4542},
        {"band_num": 34, "central_lon": 102.0, "epsg": 4543},
        {"band_num": 35, "central_lon": 105.0, "epsg": 4544},
        {"band_num": 36, "central_lon": 108.0, "epsg": 4545},
        {"band_num": 37, "central_lon": 111.0, "epsg": 4546},
        {"band_num": 38, "central_lon": 114.0, "epsg": 4547},
        {"band_num": 39, "central_lon": 117.0, "epsg": 4548},
        {"band_num": 40, "central_lon": 120.0, "epsg": 4549},
        {"band_num": 41, "central_lon": 123.0, "epsg": 4550},
        {"band_num": 42, "central_lon": 126.0, "epsg": 4551},
        {"band_num": 43, "central_lon": 129.0, "epsg": 4552},
        {"band_num": 44, "central_lon": 132.0, "epsg": 4553},
        {"band_num": 45, "central_lon": 135.0, "epsg": 4554},
    ],
    "with_band": [
        {"band_num": 25, "central_lon": 75.0,  "epsg": 4513},
        {"band_num": 26, "central_lon": 78.0,  "epsg": 4514},
        {"band_num": 27, "central_lon": 81.0,  "epsg": 4515},
        {"band_num": 28, "central_lon": 84.0,  "epsg": 4516},
        {"band_num": 29, "central_lon": 87.0,  "epsg": 4517},
        {"band_num": 30, "central_lon": 90.0,  "epsg": 4518},
        {"band_num": 31, "central_lon": 93.0,  "epsg": 4519},
        {"band_num": 32, "central_lon": 96.0,  "epsg": 4520},
        {"band_num": 33, "central_lon": 99.0,  "epsg": 4521},
        {"band_num": 34, "central_lon": 102.0, "epsg": 4522},
        {"band_num": 35, "central_lon": 105.0, "epsg": 4523},
        {"band_num": 36, "central_lon": 108.0, "epsg": 4524},
        {"band_num": 37, "central_lon": 111.0, "epsg": 4525},
        {"band_num": 38, "central_lon": 114.0, "epsg": 4526},
        {"band_num": 39, "central_lon": 117.0, "epsg": 4527},
        {"band_num": 40, "central_lon": 120.0, "epsg": 4528},
        {"band_num": 41, "central_lon": 123.0, "epsg": 4529},
        {"band_num": 42, "central_lon": 126.0, "epsg": 4530},
        {"band_num": 43, "central_lon": 129.0, "epsg": 4531},
        {"band_num": 44, "central_lon": 132.0, "epsg": 4532},
        {"band_num": 45, "central_lon": 135.0, "epsg": 4533},
    ]
}

CGCS2000_6DEG = {
    "with_band": [
        {"band_num": 13, "central_lon": 75.0,  "epsg": 4491},
        {"band_num": 14, "central_lon": 81.0,  "epsg": 4492},
        {"band_num": 15, "central_lon": 87.0,  "epsg": 4493},
        {"band_num": 16, "central_lon": 93.0,  "epsg": 4494},
        {"band_num": 17, "central_lon": 99.0,  "epsg": 4495},
        {"band_num": 18, "central_lon": 105.0, "epsg": 4496},
        {"band_num": 19, "central_lon": 111.0, "epsg": 4497},
        {"band_num": 20, "central_lon": 117.0, "epsg": 4498},
        {"band_num": 21, "central_lon": 123.0, "epsg": 4499},
        {"band_num": 22, "central_lon": 129.0, "epsg": 4500},
        {"band_num": 23, "central_lon": 135.0, "epsg": 4501},
    ],
    "no_band": [
        {"band_num": 13, "central_lon": 75.0,  "epsg": 4502},
        {"band_num": 14, "central_lon": 81.0,  "epsg": 4503},
        {"band_num": 15, "central_lon": 87.0,  "epsg": 4504},
        {"band_num": 16, "central_lon": 93.0,  "epsg": 4505},
        {"band_num": 17, "central_lon": 99.0,  "epsg": 4506},
        {"band_num": 18, "central_lon": 105.0, "epsg": 4507},
        {"band_num": 19, "central_lon": 111.0, "epsg": 4508},
        {"band_num": 20, "central_lon": 117.0, "epsg": 4509},
        {"band_num": 21, "central_lon": 123.0, "epsg": 4510},
        {"band_num": 22, "central_lon": 129.0, "epsg": 4511},
        {"band_num": 23, "central_lon": 135.0, "epsg": 4512},
    ]
}


# ============================================================
# Transformer 缓存（always_xy=True 统一轴序）
# ============================================================
@lru_cache(maxsize=128)
def _get_transformer(from_epsg: int, to_epsg: int) -> PyProjTransformer:
    """
    always_xy=True 保证：
      地理CRS  → 输入/输出顺序为 (经度, 纬度)
      投影CRS  → 输入/输出顺序为 (Easting, Northing)
    """
    return PyProjTransformer.from_crs(
        f"EPSG:{from_epsg}",
        f"EPSG:{to_epsg}",
        always_xy=True
    )


# ============================================================
# 临时文件管理
# ============================================================
TEMP_FILE_PREFIX = "coord_cvt_"
TEMP_FILE_MAX_AGE = 3600  # 秒


def _cleanup_old_temp_files():
    """清理超过 1 小时的应用临时文件"""
    pattern = os.path.join(tempfile.gettempdir(), f"{TEMP_FILE_PREFIX}*.xlsx")
    now = time.time()
    for fp in glob.glob(pattern):
        try:
            if now - os.path.getmtime(fp) > TEMP_FILE_MAX_AGE:
                os.unlink(fp)
        except OSError:
            pass


# ============================================================
# 分带信息查询
# ============================================================
def get_band_info(lon=None, band_type=None, with_band=None, band_num=None):
    """
    方式1: 通过经度自动计算 → 传入 lon, band_type, with_band
    方式2: 直接指定带号     → 传入 band_num, band_type, with_band
    返回: (band_info_dict, None) 或 (None, error_str)
    """
    try:
        if lon is not None and band_type is not None and with_band is not None:
            lon = float(lon)
            if band_type == "3":
                if not (73.5 <= lon <= 136.5):
                    return None, f"经度 {lon}° 超出3°分带有效范围（73.5°~136.5°）"
                band_num_calc = int((lon + 1.5) // 3)
                cfg = CGCS2000_3DEG["with_band"] if with_band else CGCS2000_3DEG["no_band"]
            else:
                if not (72.0 <= lon <= 138.0):
                    return None, f"经度 {lon}° 超出6°分带有效范围（72°~138°）"
                band_num_calc = int(lon // 6) + 1
                cfg = CGCS2000_6DEG["with_band"] if with_band else CGCS2000_6DEG["no_band"]

            info = next((x for x in cfg if x["band_num"] == band_num_calc), None)
            if not info:
                return None, f"未找到对应分带（带号：{band_num_calc}）"
            return info, None

        elif band_num is not None and band_type is not None and with_band is not None:
            bn = int(float(band_num))          # 兼容 Excel 读入的 float 带号
            if band_type == "3":
                cfg = CGCS2000_3DEG["with_band"] if with_band else CGCS2000_3DEG["no_band"]
            else:
                cfg = CGCS2000_6DEG["with_band"] if with_band else CGCS2000_6DEG["no_band"]

            info = next((x for x in cfg if x["band_num"] == bn), None)
            if not info:
                valid = [x["band_num"] for x in cfg]
                return None, (
                    f"未找到分带信息（{band_type}°分带，带号：{bn}）。"
                    f"有效带号范围：{min(valid)}~{max(valid)}"
                )
            return info, None

        return None, "参数不足，无法获取分带信息"

    except Exception as e:
        return None, f"分带计算错误：{e}"


# ============================================================
# 核心转换函数
# ============================================================
def convert_coordinate(source_type: str, value1, value2,
                       band_type: str, with_band: bool,
                       band_num=None, decimal_places: int = 4):
    """
    双向坐标转换

    中国测绘惯例：
        X = Northing（北方向，数值约 0~6,000,000）
        Y = Easting （东方向；含带号时 = 带号×1,000,000 + Easting）

    always_xy=True 轴序约定：
        地理CRS 输入/输出 → (经度, 纬度)
        投影CRS 输入/输出 → (Easting, Northing)

    Args:
        source_type:   'wgs84' 或 'cgcs2000'
        value1:        WGS84→经度；CGCS2000→X坐标(Northing)
        value2:        WGS84→纬度；CGCS2000→Y坐标(Easting)
        band_num:      CGCS2000→WGS84 时必须提供
    """
    try:
        v1 = float(value1)
        v2 = float(value2)
    except (TypeError, ValueError):
        return None, "坐标值格式错误，请输入数字"

    try:
        if source_type == 'wgs84':
            # ── WGS84(经纬度) → CGCS2000(高斯投影) ──────────────
            longitude, latitude = v1, v2

            if not (0 <= latitude <= 54):
                return None, f"纬度 {latitude}° 超出范围（0°~54°）"

            band_info, err = get_band_info(lon=longitude, band_type=band_type, with_band=with_band)
            if err:
                return None, err

            # (lon, lat) → (Easting, Northing)
            tf = _get_transformer(4326, band_info["epsg"])
            easting, northing = tf.transform(longitude, latitude)

            # 中国惯例：X=Northing, Y=Easting
            x = round(northing, decimal_places)
            y = round(easting,  decimal_places)

            return {
                "type":       "cgcs2000",
                "x":          x,
                "y":          y,
                "band_num":   band_info["band_num"],
                "central_lon": band_info["central_lon"],
                "combined":   f"{x:.{decimal_places}f}, {y:.{decimal_places}f}",
            }, None

        elif source_type == 'cgcs2000':
            # ── CGCS2000(高斯投影) → WGS84(经纬度) ──────────────
            x_northing = v1
            y_easting  = v2

            if band_num is None:
                return None, "国家2000转经纬度时必须指定带号"

            band_info, err = get_band_info(band_type=band_type, with_band=with_band, band_num=band_num)
            if err:
                return None, err

            # (Easting, Northing) → (lon, lat)
            tf = _get_transformer(band_info["epsg"], 4326)
            longitude, latitude = tf.transform(y_easting, x_northing)

            longitude = round(longitude, decimal_places)
            latitude  = round(latitude,  decimal_places)

            if not (70 <= longitude <= 140):
                return None, f"转换后经度 {longitude}° 超出合理范围，请检查坐标与带号是否匹配"
            if not (-5 <= latitude <= 60):
                return None, f"转换后纬度 {latitude}° 超出合理范围，请检查坐标与带号是否匹配"

            return {
                "type":       "wgs84",
                "longitude":  longitude,
                "latitude":   latitude,
                "band_num":   band_info["band_num"],
                "central_lon": band_info["central_lon"],
                "combined":   f"{longitude:.{decimal_places}f}, {latitude:.{decimal_places}f}",
            }, None

        else:
            return None, f"不支持的源类型：{source_type}"

    except Exception as e:
        return None, f"转换失败：{e}"


# ============================================================
# 路由
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")   # 修复：原为 'index-old'


@app.route("/convert_single", methods=["POST"])
def convert_single():
    """
    单点转换接口
    前端字段映射：
      WGS84  模式：lonX=经度,  latY=纬度
      CGCS模式：lonX=X(Northing), latY=Y(Easting), bandNum=带号
    """
    data = request.get_json(force=True)

    source_type    = data.get("sourceType", "wgs84")
    band_type_raw  = data.get("bandType", "3°分带")
    band_type      = "3" if band_type_raw == "3°分带" else "6"
    with_band      = bool(data.get("withBand", False))
    decimal_places = max(0, min(int(data.get("decimalPlaces", 4)), 10))

    result, error = convert_coordinate(
        source_type    = source_type,
        value1         = data.get("lonX"),      # WGS84→经度 / CGCS2000→X(Northing)
        value2         = data.get("latY"),      # WGS84→纬度 / CGCS2000→Y(Easting)
        band_type      = band_type,
        with_band      = with_band,
        band_num       = data.get("bandNum"),   # 仅 CGCS2000→WGS84 时有效
        decimal_places = decimal_places,
    )

    if error:
        return jsonify({"status": "error", "message": error})
    return jsonify({"status": "success", "result": result})


@app.route("/export_template")
def export_template():
    """下载空白导入模板"""
    fmt         = request.args.get("type",   "xlsx")
    source_type = request.args.get("source", "wgs84")

    if source_type == "wgs84":
        df = pd.DataFrame({
            "经度": [116.397428, 121.473701, 113.264385],
            "纬度": [39.909230,  31.230416,  23.129110],
            "备注（可选）": ["北京天安门", "上海外滩", "广州塔"],
        })
        base_name = "WGS84转国家2000模板"
    else:
        # 真实坐标：3°分带含带号
        # 北京天安门(116.397428°E, 39.909230°N) → 带39: X≈4426952, Y≈39449898
        # 上海外滩  (121.473701°E, 31.230416°N) → 带40: X≈3456878, Y≈40639224
        # 广州塔    (113.264385°E, 23.129110°N) → 带38: X≈2560229, Y≈38370569
        df = pd.DataFrame({
            "X坐标": [4426952.4132, 3456877.5924, 2560229.1108],
            "Y坐标": [39449898.0916, 40639224.3187, 38370568.7462],
            "带号":  [39, 40, 38],
            "备注（可选）": ["北京天安门", "上海外滩", "广州塔"],
        })
        base_name = "国家2000转WGS84模板"

    buf = io.BytesIO()
    if fmt == "xlsx":
        df.to_excel(buf, index=False, engine="openpyxl")
        mime     = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{base_name}.xlsx"
    elif fmt == "csv":
        df.to_csv(buf, index=False, encoding="utf-8-sig")
        mime     = "text/csv"
        filename = f"{base_name}.csv"
    else:
        df.to_csv(buf, index=False, encoding="utf-8-sig")
        mime     = "text/plain"
        filename = f"{base_name}.txt"

    buf.seek(0)
    return send_file(buf, mimetype=mime, as_attachment=True, download_name=filename)


@app.route("/convert_batch", methods=["POST"])
def convert_batch():
    """批量转换接口"""
    _cleanup_old_temp_files()

    decimal_places = max(0, min(int(request.form.get("decimalPlaces", 4)), 10))

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "未上传文件"})
    file = request.files["file"]
    if not file.filename:
        return jsonify({"status": "error", "message": "未选择文件"})

    source_type   = request.form.get("sourceType", "wgs84")
    band_type_raw = request.form.get("bandType", "3°分带")
    band_type     = "3" if band_type_raw == "3°分带" else "6"
    with_band     = request.form.get("withBand", "false").lower() == "true"

    try:
        # 读入内存，规避 SpooledTemporaryFile seekable 问题
        raw  = file.read()
        buf  = io.BytesIO(raw)
        name = file.filename.lower()

        if name.endswith(".xlsx"):
            df = pd.read_excel(buf, engine="openpyxl")
        elif name.endswith(".csv"):
            df = pd.read_csv(buf, encoding="utf-8-sig")
        elif name.endswith(".txt"):
            df = pd.read_csv(buf, sep=",", encoding="utf-8-sig")
        else:
            return jsonify({"status": "error", "message": "不支持的文件格式，请上传 .xlsx / .csv / .txt"})

        if df.empty:
            return jsonify({"status": "error", "message": "文件内容为空"})

        # 去除列名首尾空格
        df.columns = df.columns.str.strip()

        # 校验必要列
        if source_type == "wgs84":
            need = ["经度", "纬度"]
        else:
            need = ["X坐标", "Y坐标", "带号"]

        missing = [c for c in need if c not in df.columns]
        if missing:
            return jsonify({
                "status":  "error",
                "message": f"文件缺少必要列：{', '.join(missing)}，当前列名：{list(df.columns)}"
            })

        has_note = "备注（可选）" in df.columns

        # ── 批量转换循环 ─────────────────────────────────────
        results = []
        for idx, row in df.iterrows():
            input_info = f"第 {idx + 1} 行"
            note       = ""
            original   = {}

            try:
                if has_note:
                    raw_n = row["备注（可选）"]
                    note  = str(raw_n) if pd.notna(raw_n) else ""

                if source_type == "wgs84":
                    lon_v = row["经度"]
                    lat_v = row["纬度"]
                    if pd.isna(lon_v) or pd.isna(lat_v):
                        raise ValueError("经度或纬度为空")
                    input_info = f"{lon_v}, {lat_v}"
                    original   = {"lon": float(lon_v), "lat": float(lat_v)}
                    result, err = convert_coordinate(
                        "wgs84", lon_v, lat_v,
                        band_type, with_band,
                        decimal_places=decimal_places,
                    )
                else:
                    x_v  = row["X坐标"]
                    y_v  = row["Y坐标"]
                    bn_r = row["带号"]
                    if pd.isna(x_v) or pd.isna(y_v) or pd.isna(bn_r):
                        raise ValueError("X坐标、Y坐标或带号为空")
                    bn_v = int(float(bn_r))          # 兼容 float 带号
                    input_info = f"X={x_v}, Y={y_v}, 带号={bn_v}"
                    original   = {"x": float(x_v), "y": float(y_v), "band_num": bn_v}
                    result, err = convert_coordinate(
                        "cgcs2000", x_v, y_v,
                        band_type, with_band,
                        band_num=bn_v, decimal_places=decimal_places,
                    )

                if err:
                    results.append({
                        "index": idx + 1, "input": input_info, "output": "",
                        "status": "失败", "message": err, "note": note,
                        "detail": None, "original": original,
                    })
                else:
                    results.append({
                        "index": idx + 1, "input": input_info,
                        "output": result["combined"],
                        "status": "成功", "message": "", "note": note,
                        "detail": result, "original": original,
                    })

            except Exception as ex:
                results.append({
                    "index": idx + 1, "input": input_info, "output": "",
                    "status": "失败", "message": f"处理错误: {ex}", "note": note,
                    "detail": None, "original": original,
                })

        # ── 构建导出 DataFrame ────────────────────────────────
        rows_out = []
        for item in results:
            ok = item["status"] == "成功"
            d  = item.get("detail") or {}
            o  = item.get("original", {})

            if source_type == "wgs84":
                rows_out.append({
                    "序号":           item["index"],
                    "WGS84经度":      o.get("lon", ""),
                    "WGS84纬度":      o.get("lat", ""),
                    "国家2000 X坐标": d.get("x", "")          if ok else "",
                    "国家2000 Y坐标": d.get("y", "")          if ok else "",
                    "带号":           d.get("band_num", "")   if ok else "",
                    "中央子午线":     d.get("central_lon", "") if ok else "",
                    "转换状态":       item["status"],
                    "备注":           item["note"],
                    "错误信息":       item["message"],
                })
            else:
                rows_out.append({
                    "序号":           item["index"],
                    "国家2000 X坐标": o.get("x", ""),
                    "国家2000 Y坐标": o.get("y", ""),
                    "带号":           o.get("band_num", ""),
                    "WGS84经度":      d.get("longitude", "")  if ok else "",
                    "WGS84纬度":      d.get("latitude", "")   if ok else "",
                    "中央子午线":     d.get("central_lon", "") if ok else "",
                    "转换状态":       item["status"],
                    "备注":           item["note"],
                    "错误信息":       item["message"],
                })

        export_df = pd.DataFrame(rows_out)
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".xlsx", prefix=TEMP_FILE_PREFIX
        )
        export_df.to_excel(tmp, index=False, engine="openpyxl")
        tmp.close()

        # 仅返回预览（前50条），统计数来自全量
        success_n = sum(1 for r in results if r["status"] == "成功")
        preview   = [
            {k: r[k] for k in ("index", "input", "output", "status", "message", "note")}
            for r in results[:50]
        ]

        return jsonify({
            "status":       "success",
            "results":      preview,
            "total":        len(results),
            "successCount": success_n,
            "failCount":    len(results) - success_n,
            "temp_file":    os.path.basename(tmp.name),
            "source_type":  source_type,
        })

    except pd.errors.EmptyDataError:
        return jsonify({"status": "error", "message": "文件为空或格式不正确"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"处理文件时出错: {e}"})


@app.route("/export_results/<filename>")
def export_results(filename):
    """导出批量转换结果文件（含路径遍历防护）"""
    try:
        safe = os.path.basename(filename)
        pattern = re.compile(
            r"^" + re.escape(TEMP_FILE_PREFIX) + r"[a-zA-Z0-9_\-]+\.xlsx$"
        )
        if not pattern.match(safe):
            return jsonify({"status": "error", "message": "非法文件名"}), 400

        real_dir  = os.path.realpath(tempfile.gettempdir())
        real_path = os.path.realpath(os.path.join(real_dir, safe))
        if not real_path.startswith(real_dir + os.sep):
            return jsonify({"status": "error", "message": "非法路径"}), 403

        if not os.path.exists(real_path):
            return jsonify({
                "status":  "error",
                "message": "文件不存在或已过期，请重新执行批量转换"
            }), 404

        return send_file(
            real_path,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="坐标转换结果.xlsx",
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"导出失败: {e}"})


# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    _cleanup_old_temp_files()
    app.run(debug=True)