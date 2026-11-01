"""Flask 坐标转换服务入口。

模块职责：
- 校验单点/批量请求参数，统一坐标系别名与分带规则；
- 通过 PROJ/pyproj 完成 WGS84 与 CGCS2000 投影转换；
- 通过 geo_conversion 完成 GCJ02/BD09 偏移与反算；
- 处理 CSV/Excel/TXT 批量文件、模板下载和结果导出；
- 生成地图公开配置与 CSP 白名单。

坐标约定：
- 经纬度接口字段统一为 (lonX, latY)；
- CGCS2000 的 X 为北方向 Northing，Y 为东方向 Easting；
- 含带号时 Y 前两位必须等于带号。
"""

import glob
import io
import math
import os
import re
import tempfile
import time
from functools import lru_cache

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file
from pyproj import Transformer as PyProjTransformer

from geo_conversion import (
    bd09_to_wgs84,
    gcj02_to_wgs84,
    out_of_china,
    wgs84_to_bd09,
    wgs84_to_gcj02,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB
APP_VERSION = os.getenv("APP_VERSION", "dev").strip() or "dev"

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
# 通用配置
# ============================================================
TEMP_FILE_PREFIX = "coord_cvt_"
TEMP_FILE_MAX_AGE = 3600  # 秒
MAX_BATCH_ROWS = 20000
MAX_PREVIEW_ROWS = 50
MAX_DECIMAL_PLACES = 10
DEFAULT_MAP_PROVIDER = "tianditu"
ALLOWED_EXTENSIONS = {".xlsx", ".csv", ".txt"}

CRS_LABELS = {
    "wgs84": "WGS84",
    "cgcs2000": "CGCS2000",
    "gcj02": "GCJ02（火星）",
    "bd09": "BD09（百度）",
}
CRS_ALIASES = {
    "wgs84": "wgs84",
    "wgs-84": "wgs84",
    "wgs_84": "wgs84",
    "cgcs2000": "cgcs2000",
    "cgcs-2000": "cgcs2000",
    "cgcs_2000": "cgcs2000",
    "国家2000": "cgcs2000",
    "gcj02": "gcj02",
    "gcj-02": "gcj02",
    "gcj_02": "gcj02",
    "火星": "gcj02",
    "火星坐标": "gcj02",
    "bd09": "bd09",
    "bd-09": "bd09",
    "bd_09": "bd09",
    "百度": "bd09",
    "百度坐标": "bd09",
}
DEFAULT_TARGET = {
    "wgs84": "cgcs2000",
    "cgcs2000": "wgs84",
    "gcj02": "wgs84",
    "bd09": "wgs84",
}
SAMPLE_POINTS = [
    ("北京天安门", 116.397428, 39.909230),
    ("上海外滩", 121.473701, 31.230416),
    ("广州塔", 113.264385, 23.129110),
]


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
# 参数校验
# ============================================================
def _get_band_type(raw) -> str:
    """把 3/6 及其常见中文写法归一化为内部值 "3" 或 "6"。"""
    if raw is None:
        return "3"
    value = str(raw).strip()
    if value in {"3", "3°", "3度", "3°分带", "3度分带"}:
        return "3"
    if value in {"6", "6°", "6度", "6°分带", "6度分带"}:
        return "6"
    raise ValueError("bandType 仅支持 3°分带 或 6°分带")


def _normalize_crs(value, field: str = "sourceType") -> str:
    """把大小写、分隔符和中文别名归一化为内部 CRS key。"""
    if value is None:
        value = "wgs84"
    key = str(value).strip().lower()
    normalized = CRS_ALIASES.get(key)
    if not normalized:
        raise ValueError(f"{field} 仅支持 wgs84 / cgcs2000 / gcj02 / bd09")
    return normalized


def _resolve_target_type(source_type: str, target_type) -> str:
    """解析目标 CRS；缺省时保持旧版 source→target 兼容行为。"""
    if target_type is None or str(target_type).strip() == "":
        return DEFAULT_TARGET[source_type]
    return _normalize_crs(target_type, "targetType")


def _parse_bool(value, default: bool = False, field: str = "withBand") -> bool:
    """解析 JSON/表单布尔值，兼容 true/false、1/0、是/否。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on", "是"}:
            return True
        if normalized in {"false", "0", "no", "off", "否"}:
            return False
    raise ValueError(f"{field} 必须是布尔值")


def _parse_decimal_places(raw_value, default: int = 4) -> int:
    """把小数位数限制在 0~MAX_DECIMAL_PLACES，非法值抛出 ValueError。"""
    try:
        value = int(raw_value if raw_value is not None else default)
    except (TypeError, ValueError):
        raise ValueError("decimalPlaces 必须是整数")
    return max(0, min(value, MAX_DECIMAL_PLACES))


def _parse_optional_int(raw_value, field: str = "targetBandNum"):
    """解析可为空的整数参数（例如目标固定带号）。"""
    if raw_value is None or str(raw_value).strip() == "":
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} 必须是整数")
    if not value.is_integer():
        raise ValueError(f"{field} 必须是整数")
    return int(value)


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
                if not (73.5 <= lon < 136.5):
                    return None, f"经度 {lon}° 超出3°分带有效范围（73.5°~136.5°）"
                band_num_calc = int((lon + 1.5) // 3)
                cfg = CGCS2000_3DEG["with_band"] if with_band else CGCS2000_3DEG["no_band"]
            else:
                if not (72.0 <= lon < 138.0):
                    return None, f"经度 {lon}° 超出6°分带有效范围（72°~138°）"
                band_num_calc = int(lon // 6) + 1
                cfg = CGCS2000_6DEG["with_band"] if with_band else CGCS2000_6DEG["no_band"]

            info = next((x for x in cfg if x["band_num"] == band_num_calc), None)
            if not info:
                return None, f"未找到对应分带（带号：{band_num_calc}）"
            return info, None

        elif band_num is not None and band_type is not None and with_band is not None:
            bn_float = float(band_num)         # 兼容 Excel 读入的 float 带号
            if not bn_float.is_integer():
                return None, f"带号必须是整数（当前为 {band_num}）"
            bn = int(bn_float)
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
def _to_wgs84(source_type, value1, value2, band_type, source_with_band, band_num):
    """把源坐标统一转换为 WGS84 经纬度。"""
    try:
        v1 = float(value1)
        v2 = float(value2)
    except (TypeError, ValueError):
        raise ValueError("坐标值格式错误，请输入数字")

    if not (math.isfinite(v1) and math.isfinite(v2)):
        raise ValueError("坐标值必须是有限数字")

    if source_type == "wgs84":
        if not (-180 <= v1 <= 180):
            raise ValueError(f"经度 {v1}° 超出范围（-180°~180°）")
        if not (-90 <= v2 <= 90):
            raise ValueError(f"纬度 {v2}° 超出范围（-90°~90°）")
        return v1, v2, None

    if source_type == "cgcs2000":
        x_northing, y_easting = v1, v2
        if band_num is None:
            raise ValueError("国家2000转其他坐标时必须指定带号")
        band_info, err = get_band_info(
            band_type=band_type, with_band=source_with_band, band_num=band_num
        )
        if err:
            raise ValueError(err)

        # 含带号时，Y 的前两位必须与带号一致；不含带号时不能出现带号前缀。
        if source_with_band:
            if abs(y_easting) < 10_000_000:
                raise ValueError("Y 坐标未包含带号，请关闭“Y坐标含带号”或检查数据")
            prefix = int(abs(y_easting) // 1_000_000)
            if prefix != band_info["band_num"]:
                raise ValueError(
                    f"Y 坐标带号前缀 {prefix} 与带号参数 {band_info['band_num']} 不一致，请检查数据"
                )
        else:
            if abs(y_easting) >= 10_000_000:
                raise ValueError("Y 坐标疑似包含带号，请启用“Y坐标含带号”或检查数据")
            if not (0 <= abs(y_easting) <= 1_000_000):
                raise ValueError("不带带号的 Y 坐标应在 0~1,000,000 米范围内")

        tf = _get_transformer(band_info["epsg"], 4326)
        longitude, latitude = tf.transform(y_easting, x_northing)
        if not (math.isfinite(longitude) and math.isfinite(latitude)):
            raise ValueError("投影反算失败，请检查 X/Y 与带号是否匹配")
        if not (70 <= longitude <= 140):
            raise ValueError(f"转换后经度 {longitude}° 超出合理范围，请检查坐标与带号是否匹配")
        if not (-5 <= latitude <= 60):
            raise ValueError(f"转换后纬度 {latitude}° 超出合理范围，请检查坐标与带号是否匹配")

        half_width = 2.0 if band_type == "3" else 4.0
        if abs(longitude - band_info["central_lon"]) > half_width:
            raise ValueError(
                f"带号与坐标不匹配：反算经度 {longitude:.6f}° 距中央子午线 "
                f"{band_info['central_lon']}° 超过 {half_width}°"
            )
        return longitude, latitude, band_info

    if source_type in {"gcj02", "bd09"}:
        if out_of_china(v1, v2):
            raise ValueError("GCJ02/BD09 仅适用于中国范围（约 72°~138°E，0°~56°N）")
        if source_type == "gcj02":
            longitude, latitude = gcj02_to_wgs84(v1, v2)
        else:
            longitude, latitude = bd09_to_wgs84(v1, v2)
        return longitude, latitude, None

    raise ValueError(f"不支持的源坐标类型：{source_type}")


def _from_wgs84(target_type, longitude, latitude, band_type, target_with_band, target_band_num):
    """把 WGS84 经纬度转换为目标坐标。"""
    if target_type == "wgs84":
        return {
            "type": "wgs84",
            "longitude": longitude,
            "latitude": latitude,
        }, None
    if target_type in {"gcj02", "bd09"}:
        if out_of_china(longitude, latitude):
            raise ValueError("GCJ02/BD09 仅适用于中国范围（约 72°~138°E，0°~56°N）")
        if target_type == "gcj02":
            lon, lat = wgs84_to_gcj02(longitude, latitude)
        else:
            lon, lat = wgs84_to_bd09(longitude, latitude)
        return {
            "type": target_type,
            "longitude": lon,
            "latitude": lat,
        }, None

    if target_type == "cgcs2000":
        if target_band_num is not None:
            band_info, err = get_band_info(
                band_type=band_type, with_band=target_with_band, band_num=target_band_num
            )
            if err:
                raise ValueError(err)
            half_width = 2.0 if band_type == "3" else 4.0
            if abs(longitude - band_info["central_lon"]) > half_width:
                raise ValueError(
                    f"目标带号 {band_info['band_num']} 的中央子午线为 "
                    f"{band_info['central_lon']}°，与经度 {longitude:.6f}° 不匹配"
                )
        else:
            band_info, err = get_band_info(
                lon=longitude, band_type=band_type, with_band=target_with_band
            )
            if err:
                raise ValueError(err)

        tf = _get_transformer(4326, band_info["epsg"])
        easting, northing = tf.transform(longitude, latitude)
        if not (math.isfinite(easting) and math.isfinite(northing)):
            raise ValueError("投影正算失败，请检查经纬度与分带参数")
        return {
            "type": "cgcs2000",
            "x": northing,
            "y": easting,
            "band_num": band_info["band_num"],
            "central_lon": band_info["central_lon"],
        }, band_info

    raise ValueError(f"不支持的目标坐标类型：{target_type}")


def _haversine_m(lon1, lat1, lon2, lat2):
    """返回两个经纬度点之间的球面距离（米，WGS84 平均半径）。"""
    radius = 6371008.8
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def _map_point(longitude, latitude):
    """生成同一 WGS84 点的 wgs84/gcj02/bd09 三套地图坐标。"""
    gcj_lon, gcj_lat = wgs84_to_gcj02(longitude, latitude)
    bd_lon, bd_lat = wgs84_to_bd09(longitude, latitude)
    return {
        "wgs84": [round(longitude, 10), round(latitude, 10)],
        "gcj02": [round(gcj_lon, 10), round(gcj_lat, 10)],
        "bd09": [round(bd_lon, 10), round(bd_lat, 10)],
    }


def convert_coordinate(source_type, value1, value2,
                       band_type, with_band,
                       band_num=None, decimal_places: int = 4,
                       target_type=None, target_band_num=None,
                       source_with_band=None, target_with_band=None,
                       include_map: bool = True):
    """
    通用双向坐标转换。

    支持源/目标：wgs84 / cgcs2000（高斯投影）/ gcj02 / bd09。
    CGCS2000 输入时 value1=X(Northing)、value2=Y(Easting)，必须提供 band_num。
    CGCS2000 输出时默认按经度自动选带，也可以通过 target_band_num 固定带号。
    """
    try:
        source_type = _normalize_crs(source_type)
        target_type = _resolve_target_type(source_type, target_type)
        if source_with_band is None:
            source_with_band = with_band
        if target_with_band is None:
            target_with_band = with_band

        wgs_lon, wgs_lat, source_band = _to_wgs84(
            source_type, value1, value2, band_type, source_with_band, band_num
        )
        target_data, target_band = _from_wgs84(
            target_type, wgs_lon, wgs_lat, band_type, target_with_band, target_band_num
        )

        # 记录源坐标摘要
        source_data = {}
        if source_type == "cgcs2000":
            source_data = {
                "type": "cgcs2000",
                "x": round(float(value1), decimal_places),
                "y": round(float(value2), decimal_places),
                "band_num": source_band["band_num"],
                "central_lon": source_band["central_lon"],
            }
        else:
            source_data = {
                "type": source_type,
                "longitude": round(float(value1), decimal_places),
                "latitude": round(float(value2), decimal_places),
            }

        # 目标坐标格式化
        if target_data["type"] == "cgcs2000":
            x = round(target_data["x"], decimal_places)
            y = round(target_data["y"], decimal_places)
            target_out = {
                "type": "cgcs2000",
                "x": x,
                "y": y,
                "band_num": target_data["band_num"],
                "central_lon": target_data["central_lon"],
            }
            combined = f"{x:.{decimal_places}f}, {y:.{decimal_places}f}"
        else:
            lon = round(target_data["longitude"], decimal_places)
            lat = round(target_data["latitude"], decimal_places)
            target_out = {
                "type": target_data["type"],
                "longitude": lon,
                "latitude": lat,
            }
            combined = f"{lon:.{decimal_places}f}, {lat:.{decimal_places}f}"

        # 用于地图预览：把目标坐标再反算回 WGS84，得到真实的往返位置与误差。
        # 批量导出时仅前 50 条需要地图数据，可通过 include_map=False 跳过反算。
        map_data = None
        if include_map:
            if target_type == "cgcs2000":
                target_wgs_lon, target_wgs_lat, _ = _to_wgs84(
                    "cgcs2000", target_data["x"], target_data["y"],
                    band_type, target_with_band, target_data["band_num"],
                )
            elif target_type == "gcj02":
                target_wgs_lon, target_wgs_lat = gcj02_to_wgs84(
                    target_data["longitude"], target_data["latitude"]
                )
            elif target_type == "bd09":
                target_wgs_lon, target_wgs_lat = bd09_to_wgs84(
                    target_data["longitude"], target_data["latitude"]
                )
            else:
                target_wgs_lon, target_wgs_lat = (
                    target_data["longitude"], target_data["latitude"]
                )

            map_data = {
                "source": _map_point(wgs_lon, wgs_lat),
                "target": _map_point(target_wgs_lon, target_wgs_lat),
                "distance_m": round(
                    _haversine_m(wgs_lon, wgs_lat, target_wgs_lon, target_wgs_lat), 3
                ),
            }

        result = {
            "source_type": source_type,
            "target_type": target_type,
            "source": source_data,
            "target": target_out,
            "combined": combined,
            "map": map_data,
        }

        # 兼容旧版前端/接口字段
        if target_out["type"] == "cgcs2000":
            result.update({
                "type": "cgcs2000",
                "x": target_out["x"],
                "y": target_out["y"],
                "band_num": target_out["band_num"],
                "central_lon": target_out["central_lon"],
            })
        else:
            result.update({
                "type": target_out["type"],
                "longitude": target_out["longitude"],
                "latitude": target_out["latitude"],
            })
            if source_type == "cgcs2000" and source_band:
                result["band_num"] = source_band["band_num"]
                result["central_lon"] = source_band["central_lon"]

        if source_type == "cgcs2000" and source_band:
            result["source_band_num"] = source_band["band_num"]
            result["source_central_lon"] = source_band["central_lon"]
        if target_band:
            result["target_band_num"] = target_band["band_num"]
            result["target_central_lon"] = target_band["central_lon"]

        return result, None

    except ValueError as e:
        return None, str(e)
    except Exception as e:
        return None, f"转换失败：{e}"


# ============================================================
# 在线地图配置（前端公开配置，不含服务端密钥）
# ============================================================
def _get_map_config():
    """读取天地图配置，生成可安全暴露给前端的公开配置。"""
    provider = os.getenv("MAP_PROVIDER", DEFAULT_MAP_PROVIDER).strip().lower()
    if provider not in {"tianditu", "none"}:
        provider = "tianditu"

    tianditu_key = os.getenv("TIANDITU_KEY", "").strip()
    enabled = provider == "tianditu"

    return {
        "provider": provider,
        "enabled": enabled,
        "tile_crs": "wgs84",
        "tianditu_key": tianditu_key if enabled else "",
        "key_configured": bool(enabled and tianditu_key),
        "label": "天地图" if enabled else "无",
    }


def _map_origins():
    """返回天地图需要加入 CSP 的 origin 列表。"""
    config = _get_map_config()
    origins = set()
    if config["provider"] == "tianditu":
        origins.add("https://*.tianditu.gov.cn")
    return origins


@app.context_processor
def _inject_app_context():
    """向模板注入地图配置和运行版本。"""
    return {"map_config": _get_map_config(), "app_version": APP_VERSION}


@app.errorhandler(413)
def _handle_request_too_large(error):
    return jsonify({
        "status": "error",
        "message": "上传内容超过 10MB 限制，请拆分文件后重试",
    }), 413


@app.errorhandler(500)
def _handle_internal_error(error):
    return jsonify({
        "status": "error",
        "message": "服务器内部错误，请稍后重试",
    }), 500


@app.after_request
def _add_security_headers(response):
    origins = sorted(_map_origins())
    img_src = " ".join(["'self'", "data:", "blob:"] + origins)
    connect_src = " ".join(["'self'"] + origins)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        f"img-src {img_src}; "
        f"connect-src {connect_src}; "
        "font-src 'self' data:; "
        "base-uri 'self'; form-action 'self'; frame-ancestors 'self'"
    )
    response.headers.setdefault("Content-Security-Policy", csp)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    return response


# ============================================================
# 路由
# ============================================================
@app.route("/")
def index():
    """渲染单页前端。"""
    return render_template("index.html")


@app.route("/convert_single", methods=["POST"])
def convert_single():
    """
    单点转换接口
    前端字段映射：
      WGS84/GCJ02/BD09：lonX=经度, latY=纬度
      CGCS2000：lonX=X(Northing), latY=Y(Easting), bandNum=带号
      targetType 可选；不传时保持旧行为（wgs84↔cgcs2000）
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "请求体必须为 JSON 对象"}), 400

    try:
        source_type = _normalize_crs(data.get("sourceType", "wgs84"))
        target_type = _resolve_target_type(source_type, data.get("targetType"))
        band_type = _get_band_type(data.get("bandType", "3°分带"))
        with_band = _parse_bool(data.get("withBand"), False)
        source_with_band = _parse_bool(data.get("sourceWithBand"), with_band, "sourceWithBand")
        target_with_band = _parse_bool(data.get("targetWithBand"), with_band, "targetWithBand")
        decimal_places = _parse_decimal_places(data.get("decimalPlaces", 4))
        target_band_num = _parse_optional_int(data.get("targetBandNum"))
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    result, error = convert_coordinate(
        source_type=source_type,
        value1=data.get("lonX"),
        value2=data.get("latY"),
        band_type=band_type,
        with_band=with_band,
        band_num=data.get("bandNum"),
        decimal_places=decimal_places,
        target_type=target_type,
        target_band_num=target_band_num,
        source_with_band=source_with_band,
        target_with_band=target_with_band,
    )

    if error:
        return jsonify({"status": "error", "message": error}), 400
    return jsonify({"status": "success", "result": result})


def _sample_rows(source_type, band_type, with_band):
    """生成模板示例行，按源 CRS 输出对应列名和示例值。"""
    rows = []
    for name, lon, lat in SAMPLE_POINTS:
        if source_type == "wgs84":
            rows.append({"经度": lon, "纬度": lat, "备注（可选）": name})
        elif source_type in {"gcj02", "bd09"}:
            result, error = convert_coordinate(
                "wgs84", lon, lat, band_type, with_band,
                decimal_places=8, target_type=source_type,
                include_map=False,
            )
            if error:
                raise ValueError(error)
            rows.append({
                "经度": result["longitude"],
                "纬度": result["latitude"],
                "备注（可选）": name,
            })
        else:
            result, error = convert_coordinate(
                "wgs84", lon, lat, band_type, with_band,
                decimal_places=4, target_type="cgcs2000",
                target_with_band=with_band, include_map=False,
            )
            if error:
                raise ValueError(error)
            rows.append({
                "X坐标": result["x"],
                "Y坐标": result["y"],
                "带号": result["band_num"],
                "备注（可选）": name,
            })
    return rows


@app.route("/export_template")
def export_template():
    """下载空白导入模板（按源坐标系生成正确示例值）"""
    fmt = request.args.get("type", "xlsx").strip().lower()
    if fmt not in {"xlsx", "csv", "txt"}:
        return jsonify({"status": "error", "message": "模板格式仅支持 xlsx/csv/txt"}), 400

    try:
        source_type = _normalize_crs(request.args.get("source", "wgs84"), "source")
        target_type = _resolve_target_type(source_type, request.args.get("target"))
        band_type = _get_band_type(request.args.get("bandType", "3°分带"))
        with_band = _parse_bool(request.args.get("withBand"), True)
        rows = _sample_rows(source_type, band_type, with_band)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    df = pd.DataFrame(rows)
    base_name = f"{CRS_LABELS[source_type]}转{CRS_LABELS[target_type]}模板"

    buf = io.BytesIO()
    if fmt == "xlsx":
        df.to_excel(buf, index=False, engine="openpyxl")
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{base_name}.xlsx"
    elif fmt == "csv":
        df.to_csv(buf, index=False, encoding="utf-8-sig")
        mime = "text/csv"
        filename = f"{base_name}.csv"
    else:
        df.to_csv(buf, index=False, encoding="utf-8-sig")
        mime = "text/plain"
        filename = f"{base_name}.txt"

    buf.seek(0)
    return send_file(buf, mimetype=mime, as_attachment=True, download_name=filename)


def _read_dataframe(raw: bytes, ext: str) -> pd.DataFrame:
    """读取上传的 xlsx/csv/txt；CSV 自动尝试常见中文编码。"""
    buf = io.BytesIO(raw)
    if ext == ".xlsx":
        return pd.read_excel(buf, engine="openpyxl")

    last_error = None
    for encoding in ("utf-8-sig", "gb18030", "gbk"):
        try:
            buf.seek(0)
            return pd.read_csv(buf, encoding=encoding, sep=None, engine="python")
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise ValueError("无法读取文件")


def _cell_value(value):
    """把 pandas/numpy 标量转换为可 JSON/Excel 序列化的 Python 值。"""
    if pd.isna(value):
        return ""
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _safe_excel_value(value):
    """防止 Excel/CSV 公式注入，同时保留普通负数。"""
    if isinstance(value, str):
        stripped = value.lstrip()
        if stripped[:1] in {"=", "+", "@"}:
            return "'" + value
        if stripped.startswith("-") and not re.match(r"^-\d+(?:\.\d+)?$", stripped):
            return "'" + value
    return value


def _extra_column_names(extra_cols, reserved):
    """为额外列生成不冲突的导出列名，冲突时加“附加_”前缀。"""
    mapping = {}
    used = set(reserved)
    for col in extra_cols:
        base = str(col)
        name = base
        if name in used:
            name = f"附加_{base}"
            suffix = 2
            while name in used:
                name = f"附加_{base}_{suffix}"
                suffix += 1
        mapping[col] = name
        used.add(name)
    return mapping


def _build_export_rows(results, source_type, target_type, extra_cols):
    """把批量结果整理为导出表，保留额外列并避免覆盖系统列。"""
    rows_out = []
    labels = {"wgs84": "WGS84", "cgcs2000": "国家2000", "gcj02": "GCJ02", "bd09": "BD09"}
    reserved = {
        "序号", "源X坐标", "源Y坐标", "源带号",
        "目标X坐标", "目标Y坐标", "目标带号", "目标中央子午线",
        "源坐标系", "目标坐标系", "转换状态", "备注", "错误信息",
    }
    for label in labels.values():
        reserved.update({
            f"源{label}经度", f"源{label}纬度",
            f"目标{label}经度", f"目标{label}纬度",
        })
    extra_names = _extra_column_names(extra_cols, reserved)
    for item in results:
        ok = item["status"] == "成功"
        detail = item.get("detail") or {}
        original = item.get("original", {})

        if source_type == "cgcs2000":
            source_cols = {
                "源X坐标": original.get("x", ""),
                "源Y坐标": original.get("y", ""),
                "源带号": original.get("band_num", ""),
            }
        else:
            source_cols = {
                f"源{labels[source_type]}经度": original.get("lon", ""),
                f"源{labels[source_type]}纬度": original.get("lat", ""),
            }

        if target_type == "cgcs2000":
            target_cols = {
                "目标X坐标": detail.get("x", "") if ok else "",
                "目标Y坐标": detail.get("y", "") if ok else "",
                "目标带号": detail.get("band_num", "") if ok else "",
                "目标中央子午线": detail.get("central_lon", "") if ok else "",
            }
        else:
            target_cols = {
                f"目标{labels[target_type]}经度": detail.get("longitude", "") if ok else "",
                f"目标{labels[target_type]}纬度": detail.get("latitude", "") if ok else "",
            }

        row = {"序号": item["index"]}
        row.update(source_cols)
        row.update(target_cols)
        row.update({
            "源坐标系": labels[source_type],
            "目标坐标系": labels[target_type],
            "转换状态": item["status"],
            "备注": _safe_excel_value(item.get("note", "")),
            "错误信息": item.get("message", ""),
        })
        for col in extra_cols:
            row[extra_names[col]] = _safe_excel_value(
                original.get("extra", {}).get(col, "")
            )
        rows_out.append(row)
    return rows_out


@app.route("/convert_batch", methods=["POST"])
def convert_batch():
    """批量转换接口（支持 WGS84 / CGCS2000 / GCJ02 / BD09 任意组合）"""
    _cleanup_old_temp_files()

    try:
        decimal_places = _parse_decimal_places(request.form.get("decimalPlaces", 4))
        source_type = _normalize_crs(request.form.get("sourceType", "wgs84"), "sourceType")
        target_type = _resolve_target_type(source_type, request.form.get("targetType"))
        band_type = _get_band_type(request.form.get("bandType", "3°分带"))
        with_band = _parse_bool(request.form.get("withBand"), False)
        source_with_band = _parse_bool(request.form.get("sourceWithBand"), with_band, "sourceWithBand")
        target_with_band = _parse_bool(request.form.get("targetWithBand"), with_band, "targetWithBand")
        target_band_num = _parse_optional_int(request.form.get("targetBandNum"))
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "未上传文件"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"status": "error", "message": "未选择文件"}), 400

    try:
        raw = file.read()
        if not raw:
            return jsonify({"status": "error", "message": "上传文件为空"}), 400
        name = file.filename.lower().strip()
        ext = os.path.splitext(name)[1]
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({
                "status": "error",
                "message": "不支持的文件格式，请上传 .xlsx / .csv / .txt",
            }), 400

        df = _read_dataframe(raw, ext)
        if df.empty:
            return jsonify({"status": "error", "message": "文件内容为空"}), 400
        if len(df) > MAX_BATCH_ROWS:
            return jsonify({
                "status": "error",
                "message": f"单次最多支持 {MAX_BATCH_ROWS} 行，当前为 {len(df)} 行",
            }), 400

        df.columns = [str(col).strip() for col in df.columns]
        duplicated = df.columns[df.columns.duplicated()].tolist()
        if duplicated:
            return jsonify({
                "status": "error",
                "message": f"文件包含重复列名：{', '.join(duplicated)}",
            }), 400

        if source_type == "wgs84":
            need = ["经度", "纬度"]
        elif source_type == "cgcs2000":
            need = ["X坐标", "Y坐标", "带号"]
        else:
            need = ["经度", "纬度"]

        missing = [c for c in need if c not in df.columns]
        if missing:
            return jsonify({
                "status": "error",
                "message": f"文件缺少必要列：{', '.join(missing)}，当前列名：{list(df.columns)}",
            }), 400

        note_col = next((c for c in ["备注（可选）", "备注"] if c in df.columns), None)
        extra_cols = [c for c in df.columns if c not in need and c != note_col]

        col_pos = {col: i for i, col in enumerate(df.columns)}
        note_idx = col_pos[note_col] if note_col else None
        extra_indices = [(col, col_pos[col]) for col in extra_cols]

        results = []
        for row_no, values in enumerate(df.itertuples(index=False, name=None), start=1):
            input_info = f"第 {row_no} 行"
            note = ""
            original = {}
            include_map = row_no <= MAX_PREVIEW_ROWS

            try:
                if note_idx is not None:
                    raw_note = values[note_idx]
                    note = str(raw_note) if pd.notna(raw_note) else ""
                original["extra"] = {
                    col: _cell_value(values[pos]) for col, pos in extra_indices
                }

                if source_type == "cgcs2000":
                    x_v = values[col_pos["X坐标"]]
                    y_v = values[col_pos["Y坐标"]]
                    bn_r = values[col_pos["带号"]]
                    if pd.isna(x_v) or pd.isna(y_v) or pd.isna(bn_r):
                        raise ValueError("X坐标、Y坐标或带号为空")
                    bn_float = float(bn_r)
                    if not bn_float.is_integer():
                        raise ValueError("带号必须为整数")
                    bn_v = int(bn_float)
                    input_info = f"X={x_v}, Y={y_v}, 带号={bn_v}"
                    original.update({"x": float(x_v), "y": float(y_v), "band_num": bn_v})
                    result, err = convert_coordinate(
                        "cgcs2000", x_v, y_v,
                        band_type, with_band,
                        band_num=bn_v, decimal_places=decimal_places,
                        target_type=target_type, target_band_num=target_band_num,
                        source_with_band=source_with_band,
                        target_with_band=target_with_band,
                        include_map=include_map,
                    )
                else:
                    lon_v = values[col_pos["经度"]]
                    lat_v = values[col_pos["纬度"]]
                    if pd.isna(lon_v) or pd.isna(lat_v):
                        raise ValueError("经度或纬度为空")
                    input_info = f"{lon_v}, {lat_v}"
                    original.update({"lon": float(lon_v), "lat": float(lat_v)})
                    result, err = convert_coordinate(
                        source_type, lon_v, lat_v,
                        band_type, with_band,
                        decimal_places=decimal_places,
                        target_type=target_type, target_band_num=target_band_num,
                        source_with_band=source_with_band,
                        target_with_band=target_with_band,
                        include_map=include_map,
                    )

                if err:
                    results.append({
                        "index": row_no, "input": input_info, "output": "",
                        "status": "失败", "message": err, "note": note,
                        "detail": None, "original": original, "map": None,
                    })
                else:
                    results.append({
                        "index": row_no, "input": input_info,
                        "output": result["combined"],
                        "status": "成功", "message": "", "note": note,
                        "detail": result, "original": original,
                        "map": result.get("map"),
                    })
            except Exception as ex:
                results.append({
                    "index": row_no, "input": input_info, "output": "",
                    "status": "失败", "message": f"处理错误: {ex}", "note": note,
                    "detail": None, "original": original, "map": None,
                })

        rows_out = _build_export_rows(results, source_type, target_type, extra_cols)
        export_df = pd.DataFrame(rows_out)
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".xlsx", prefix=TEMP_FILE_PREFIX
        )
        export_df.to_excel(tmp, index=False, engine="openpyxl")
        tmp.close()

        success_n = sum(1 for r in results if r["status"] == "成功")
        preview = [
            {k: r[k] for k in ("index", "input", "output", "status", "message", "note", "map")}
            for r in results[:MAX_PREVIEW_ROWS]
        ]

        return jsonify({
            "status": "success",
            "results": preview,
            "total": len(results),
            "successCount": success_n,
            "failCount": len(results) - success_n,
            "temp_file": os.path.basename(tmp.name),
            "source_type": source_type,
            "target_type": target_type,
            "source_label": CRS_LABELS[source_type],
            "target_label": CRS_LABELS[target_type],
        })

    except pd.errors.EmptyDataError:
        return jsonify({"status": "error", "message": "文件为空或格式不正确"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"处理文件时出错: {e}"}), 400


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

        real_dir = os.path.realpath(tempfile.gettempdir())
        real_path = os.path.realpath(os.path.join(real_dir, safe))
        if not real_path.startswith(real_dir + os.sep):
            return jsonify({"status": "error", "message": "非法路径"}), 403

        if not os.path.exists(real_path):
            return jsonify({
                "status": "error",
                "message": "文件不存在或已过期，请重新执行批量转换",
            }), 404

        return send_file(
            real_path,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="坐标转换结果.xlsx",
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"导出失败: {e}"}), 400


@app.route("/healthz", methods=["GET"])
def healthz():
    """Container/runtime health probe endpoint."""
    return jsonify({"status": "ok", "version": APP_VERSION}), 200


# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    _cleanup_old_temp_files()
    app.run(host="0.0.0.0", port=5000, debug=False)
