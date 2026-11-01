"""中国常用坐标加密/偏移算法。

实现 WGS84、GCJ02（国测局/火星坐标）、BD09（百度坐标）之间的转换。
这些算法属于工程近似实现，适用于可视化与一般业务校验；高精度生产场景
应以官方 SDK / 测绘成果为准。算法公式参考公开实现 coordTransform_py /
eviltransform，不包含任何官方保密参数。
"""

from __future__ import annotations

import math

_A = 6378245.0
_EE = 0.00669342162296594323
_X_PI = math.pi * 3000.0 / 180.0


def out_of_china(lon: float, lat: float) -> bool:
    """粗略判断是否在中国范围之外（GCJ02/BD09 只在中国范围内有意义）。"""
    return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _transform_lat(x: float, y: float) -> float:
    """GCJ02 纬度偏移经验多项式。"""
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320.0 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(x: float, y: float) -> float:
    """GCJ02 经度偏移经验多项式。"""
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lon: float, lat: float) -> tuple[float, float]:
    """WGS84 → GCJ02；中国范围外原样返回。"""
    if out_of_china(lon, lat):
        return lon, lat
    dlat = _transform_lat(lon - 105.0, lat - 35.0)
    dlng = _transform_lng(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - _EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtmagic) * math.pi)
    dlng = (dlng * 180.0) / (_A / sqrtmagic * math.cos(radlat) * math.pi)
    return lon + dlng, lat + dlat


def gcj02_to_wgs84(lon: float, lat: float) -> tuple[float, float]:
    """迭代反解，往返精度优于 1e-9 度。"""
    if out_of_china(lon, lat):
        return lon, lat
    wgs_lon, wgs_lat = lon, lat
    for _ in range(20):
        gcj_lon, gcj_lat = wgs84_to_gcj02(wgs_lon, wgs_lat)
        d_lon = gcj_lon - lon
        d_lat = gcj_lat - lat
        if abs(d_lon) < 1e-10 and abs(d_lat) < 1e-10:
            break
        wgs_lon -= d_lon
        wgs_lat -= d_lat
    return wgs_lon, wgs_lat


def gcj02_to_bd09(lon: float, lat: float) -> tuple[float, float]:
    """GCJ02 → BD09（百度坐标偏移）。"""
    z = math.sqrt(lon * lon + lat * lat) + 0.00002 * math.sin(lat * _X_PI)
    theta = math.atan2(lat, lon) + 0.000003 * math.cos(lon * _X_PI)
    return z * math.cos(theta) + 0.0065, z * math.sin(theta) + 0.006


def bd09_to_gcj02(lon: float, lat: float) -> tuple[float, float]:
    """BD09 → GCJ02。"""
    x = lon - 0.0065
    y = lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * _X_PI)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * _X_PI)
    return z * math.cos(theta), z * math.sin(theta)


def wgs84_to_bd09(lon: float, lat: float) -> tuple[float, float]:
    """WGS84 → BD09（先转 GCJ02 再转 BD09）。"""
    return gcj02_to_bd09(*wgs84_to_gcj02(lon, lat))


def bd09_to_wgs84(lon: float, lat: float) -> tuple[float, float]:
    """BD09 → WGS84（先转 GCJ02 再迭代反解）。"""
    return gcj02_to_wgs84(*bd09_to_gcj02(lon, lat))


def to_wgs84(lon: float, lat: float, source_type: str) -> tuple[float, float]:
    """按源 CRS 把坐标统一转换为 WGS84。"""
    if source_type == "wgs84":
        return lon, lat
    if source_type == "gcj02":
        return gcj02_to_wgs84(lon, lat)
    if source_type == "bd09":
        return bd09_to_wgs84(lon, lat)
    raise ValueError(f"不支持的加密坐标类型：{source_type}")


def from_wgs84(lon: float, lat: float, target_type: str) -> tuple[float, float]:
    """按目标 CRS 把 WGS84 转换为目标坐标。"""
    if target_type == "wgs84":
        return lon, lat
    if target_type == "gcj02":
        return wgs84_to_gcj02(lon, lat)
    if target_type == "bd09":
        return wgs84_to_bd09(lon, lat)
    raise ValueError(f"不支持的加密坐标类型：{target_type}")
