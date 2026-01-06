from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import numpy as np
from pyproj import Transformer as PyProjTransformer
import io
import os
import tempfile

app = Flask(__name__)

# 权威EPSG编码配置（保持不变）
CGCS2000_3DEG = {
    "no_band": [
        {"band_num": 25, "central_lon": 75.0, "epsg": 4534},
        {"band_num": 26, "central_lon": 78.0, "epsg": 4535},
        {"band_num": 27, "central_lon": 81.0, "epsg": 4536},
        {"band_num": 28, "central_lon": 84.0, "epsg": 4537},
        {"band_num": 29, "central_lon": 87.0, "epsg": 4538},
        {"band_num": 30, "central_lon": 90.0, "epsg": 4539},
        {"band_num": 31, "central_lon": 93.0, "epsg": 4540},
        {"band_num": 32, "central_lon": 96.0, "epsg": 4541},
        {"band_num": 33, "central_lon": 99.0, "epsg": 4542},
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
        {"band_num": 25, "central_lon": 75.0, "epsg": 4513},
        {"band_num": 26, "central_lon": 78.0, "epsg": 4514},
        {"band_num": 27, "central_lon": 81.0, "epsg": 4515},
        {"band_num": 28, "central_lon": 84.0, "epsg": 4516},
        {"band_num": 29, "central_lon": 87.0, "epsg": 4517},
        {"band_num": 30, "central_lon": 90.0, "epsg": 4518},
        {"band_num": 31, "central_lon": 93.0, "epsg": 4519},
        {"band_num": 32, "central_lon": 96.0, "epsg": 4520},
        {"band_num": 33, "central_lon": 99.0, "epsg": 4521},
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
        {"band_num": 13, "central_lon": 75.0, "epsg": 4491},
        {"band_num": 14, "central_lon": 81.0, "epsg": 4492},
        {"band_num": 15, "central_lon": 87.0, "epsg": 4493},
        {"band_num": 16, "central_lon": 93.0, "epsg": 4494},
        {"band_num": 17, "central_lon": 99.0, "epsg": 4495},
        {"band_num": 18, "central_lon": 105.0, "epsg": 4496},
        {"band_num": 19, "central_lon": 111.0, "epsg": 4497},
        {"band_num": 20, "central_lon": 117.0, "epsg": 4498},
        {"band_num": 21, "central_lon": 123.0, "epsg": 4499},
        {"band_num": 22, "central_lon": 129.0, "epsg": 4500},
        {"band_num": 23, "central_lon": 135.0, "epsg": 4501},
    ],
    "no_band": [
        {"band_num": 13, "central_lon": 75.0, "epsg": 4502},
        {"band_num": 14, "central_lon": 81.0, "epsg": 4503},
        {"band_num": 15, "central_lon": 87.0, "epsg": 4504},
        {"band_num": 16, "central_lon": 93.0, "epsg": 4505},
        {"band_num": 17, "central_lon": 99.0, "epsg": 4506},
        {"band_num": 18, "central_lon": 105.0, "epsg": 4507},
        {"band_num": 19, "central_lon": 111.0, "epsg": 4508},
        {"band_num": 20, "central_lon": 117.0, "epsg": 4509},
        {"band_num": 21, "central_lon": 123.0, "epsg": 4510},
        {"band_num": 22, "central_lon": 129.0, "epsg": 4511},
        {"band_num": 23, "central_lon": 135.0, "epsg": 4512},
    ]
}


def get_band_info(lon=None, band_type=None, with_band=None, band_num=None):
    """
    获取分带信息和EPSG编码（支持两种方式：通过经度计算 或 直接指定带号）
    """
    try:
        # 方式1：通过经度计算分带
        if lon is not None and band_type is not None and with_band is not None:
            lon = float(lon)
            if lon < 72 or lon > 135:
                return None, "经度超出范围（72.0-135.0）"

            # 确定分带号
            if band_type == "3":
                band_num_calc = int((lon + 1.5) // 3)
                band_config = CGCS2000_3DEG["with_band"] if with_band else CGCS2000_3DEG["no_band"]
            else:  # 6°分带
                band_num_calc = int(lon // 6) + 1
                band_config = CGCS2000_6DEG["with_band"] if with_band else CGCS2000_6DEG["no_band"]

            # 查找对应的EPSG
            epsg_info = next((item for item in band_config if item["band_num"] == band_num_calc), None)
            if not epsg_info:
                return None, f"未找到对应的分带信息（带号：{band_num_calc}）"

            return epsg_info, None

        # 方式2：直接指定带号查找
        elif band_num is not None and band_type is not None and with_band is not None:
            band_num = int(band_num)
            if band_type == "3":
                band_config = CGCS2000_3DEG["with_band"] if with_band else CGCS2000_3DEG["no_band"]
            else:  # 6°分带
                band_config = CGCS2000_6DEG["with_band"] if with_band else CGCS2000_6DEG["no_band"]

            epsg_info = next((item for item in band_config if item["band_num"] == band_num), None)
            if not epsg_info:
                return None, f"未找到对应的分带信息（分带类型：{band_type}°，带号：{band_num}，带号启用：{with_band}）"

            return epsg_info, None

        else:
            return None, "参数不足，无法获取分带信息"

    except Exception as e:
        return None, f"分带计算错误：{str(e)}"


def convert_coordinate(source_type, lon_x, lat_y, band_type, with_band, band_num=None, decimal_places=4):
    """
    坐标转换核心函数（支持双向转换）
    :param source_type: 源类型 - 'wgs84'（经纬度） 或 'cgcs2000'（高斯投影）
    :param lon_x: 经度（WGS84）或 X坐标（CGCS2000）
    :param lat_y: 纬度（WGS84）或 Y坐标（CGCS2000）
    :param band_type: 分带类型 - '3' 或 '6'
    :param with_band: 是否启用带号（布尔值）
    :param band_num: 带号（仅CGCS2000→WGS84时需要指定）
    :return: 转换结果或错误信息
    """
    try:
        # 类型转换和基础验证
        lon_x = float(lon_x)
        lat_y = float(lat_y)

        if source_type == 'wgs84':
            # WGS84→CGCS2000（原逻辑保持不变）
            if lat_y < 0 or lat_y > 54:
                return None, "纬度超出范围（0.0-54.0）"

            # 获取分带信息
            band_info, error = get_band_info(lon=lon_x, band_type=band_type, with_band=with_band)
            if error:
                return None, error

            # 执行转换（WGS84→CGCS2000）
            transformer = PyProjTransformer.from_crs("EPSG:4326", f"EPSG:{band_info['epsg']}")
            x, y = transformer.transform(lat_y, lon_x)

            # 格式化结果
            x = round(x, decimal_places)
            y = round(y, decimal_places)

            return {
                "type": "cgcs2000",
                "x": x,
                "y": y,
                "band_num": band_info["band_num"],
                "central_lon": band_info["central_lon"],
                "combined": f"{x:.{decimal_places}f}, {y:.{decimal_places}f}"
            }, None

        elif source_type == 'cgcs2000':
            # CGCS2000→WGS84（新增逻辑）
            if band_num is None:
                return None, "转换国家2000到经纬度时，必须指定带号"

            # 获取分带信息（通过带号查找）
            band_info, error = get_band_info(band_type=band_type, with_band=with_band, band_num=band_num)
            if error:
                return None, error

            # 执行转换（CGCS2000→WGS84）
            transformer = PyProjTransformer.from_crs(f"EPSG:{band_info['epsg']}", "EPSG:4326")
            lat, lon = transformer.transform(lon_x, lat_y)  # 注意：pyproj的transform顺序是（x, y）→（lat, lon）

            # 验证结果范围
            lon = round(lon, decimal_places)
            lat = round(lat, decimal_places)
            if lon < 72 or lon > 135:
                return None, f"转换后的经度超出合理范围（{lon}）"
            if lat < 0 or lat > 54:
                return None, f"转换后的纬度超出合理范围（{lat}）"

            return {
                "type": "wgs84",
                "longitude": lon,
                "latitude": lat,
                "band_num": band_info["band_num"],
                "central_lon": band_info["central_lon"],
                "combined": f"{lon:.{decimal_places}f}, {lat:.{decimal_places}f}"
            }, None

        else:
            return None, "不支持的源类型"

    except Exception as e:
        return None, f"转换失败：{str(e)}"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert_single', methods=['POST'])
def convert_single():
    data = request.json
    result, error = convert_coordinate(
        source_type=data['sourceType'],
        lon_x=data['lonX'],
        lat_y=data['latY'],
        band_type="3" if data['bandType'] == "3°分带" else "6",
        with_band=data['withBand'],
        band_num=data.get('bandNum'),  # 可选参数，仅CGCS2000→WGS84时需要
        decimal_places=data.get('decimalPlaces', 4)  # 新增：小数位参数，默认4位
    )

    if error:
        return jsonify({"status": "error", "message": error})
    return jsonify({"status": "success", "result": result})


@app.route('/export_template', methods=['GET'])
def export_template():
    template_type = request.args.get('type', 'xlsx')
    source_type = request.args.get('source', 'wgs84')  # 新增：模板类型（WGS84或CGCS2000）

    # 根据转换方向创建不同模板
    if source_type == 'wgs84':
        # WGS84→CGCS2000模板（原模板）
        template_data = pd.DataFrame({
            "经度": [116.397428, 121.473701, 113.264385],
            "纬度": [39.909230, 31.230416, 23.129110],
            "备注（可选）": ["北京天安门", "上海外滩", "广州塔"]
        })
        filename = 'WGS84转国家2000模板.xlsx'
    else:
        # CGCS2000→WGS84模板（新增）
        template_data = pd.DataFrame({
            "X坐标": [3990923.123, 3123041.678, 2312911.000],
            "Y坐标": [39535156.789, 38547321.987, 37532145.678],
            "带号": [39, 38, 37],
            "备注（可选）": ["北京示例点", "上海示例点", "广州示例点"]
        })
        filename = '国家2000转WGS84模板.xlsx'

    # 创建内存文件
    output = io.BytesIO()

    if template_type == 'xlsx':
        template_data.to_excel(output, index=False, engine='openpyxl')
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif template_type == 'csv':
        template_data.to_csv(output, index=False, encoding='utf-8-sig')
        mimetype = 'text/csv'
        filename = filename.replace('.xlsx', '.csv')
    else:
        template_data.to_csv(output, index=False, sep=',', encoding='utf-8-sig')
        mimetype = 'text/plain'
        filename = filename.replace('.xlsx', '.txt')

    output.seek(0)
    return send_file(
        output,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )


@app.route('/convert_batch', methods=['POST'])
def convert_batch():
    # 获取小数位参数，默认4位
    decimal_places = int(request.form.get('decimalPlaces', 4))
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "未上传文件"})

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "未选择文件"})

    # 获取请求参数
    source_type = request.form.get('sourceType')
    band_type = "3" if request.form.get('bandType') == "3°分带" else "6"
    with_band = request.form.get('withBand') == 'true'

    try:
        # 读取文件内容到BytesIO对象，解决SpooledTemporaryFile的seekable问题
        import io
        file_content = file.read()
        file_stream = io.BytesIO(file_content)
        
        if file.filename.endswith('.xlsx'):
            df = pd.read_excel(file_stream, engine='openpyxl')
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(file_stream, encoding='utf-8-sig')
        elif file.filename.endswith('.txt'):
            df = pd.read_csv(file_stream, sep=',', encoding='utf-8-sig')
        else:
            return jsonify({"status": "error", "message": "不支持的文件格式"})

        # 检查必要的列
        if source_type == 'wgs84':
            # WGS84→CGCS2000：需要经度、纬度列
            required_cols = ['经度', '纬度']
            if not all(col in df.columns for col in required_cols):
                return jsonify({"status": "error", "message": "文件必须包含'经度'和'纬度'列"})
        else:
            # CGCS2000→WGS84：需要X坐标、Y坐标、带号列
            required_cols = ['X坐标', 'Y坐标', '带号']
            if not all(col in df.columns for col in required_cols):
                return jsonify({"status": "error", "message": "文件必须包含'X坐标'、'Y坐标'和'带号'列"})

        # 执行批量转换
        results = []
        for idx, row in df.iterrows():
            try:
                if source_type == 'wgs84':
                    # WGS84→CGCS2000
                    result, error = convert_coordinate(
                        source_type='wgs84',
                        lon_x=row['经度'],
                        lat_y=row['纬度'],
                        band_type=band_type,
                        with_band=with_band,
                        decimal_places=decimal_places
                    )
                    note = row['备注（可选）'] if '备注（可选）' in df.columns else ''
                    input_info = f"{row['经度']}, {row['纬度']}"

                else:
                    # CGCS2000→WGS84
                    result, error = convert_coordinate(
                        source_type='cgcs2000',
                        lon_x=row['X坐标'],
                        lat_y=row['Y坐标'],
                        band_type=band_type,
                        with_band=with_band,
                        band_num=row['带号'],
                        decimal_places=decimal_places
                    )
                    note = row['备注（可选）'] if '备注（可选）' in df.columns else ''
                    input_info = f"{row['X坐标']}, {row['Y坐标']}（带号：{row['带号']}）"

                if error:
                    results.append({
                        "index": idx + 1,
                        "input": input_info,
                        "output": "",
                        "status": "失败",
                        "message": error,
                        "note": note
                    })
                else:
                    results.append({
                        "index": idx + 1,
                        "input": input_info,
                        "output": result['combined'],
                        "status": "成功",
                        "message": "",
                        "note": note,
                        "detail": result  # 存储详细结果供导出
                    })
            except Exception as e:
                results.append({
                    "index": idx + 1,
                    "input": input_info if 'input_info' in locals() else f"第{idx + 1}行数据",
                    "output": "",
                    "status": "失败",
                    "message": f"处理错误: {str(e)}",
                    "note": ""
                })

        # 保存结果供后续导出
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        # 构建导出用的DataFrame
        export_data = []
        for item in results:
            if source_type == 'wgs84':
                # WGS84→CGCS2000 导出格式
                export_data.append({
                    "序号": item["index"],
                    "WGS84经度": item["input"].split(',')[0].strip(),
                    "WGS84纬度": item["input"].split(',')[1].strip(),
                    "国家2000 X坐标": item["detail"]["x"] if item["status"] == "成功" else "",
                    "国家2000 Y坐标": item["detail"]["y"] if item["status"] == "成功" else "",
                    "带号": item["detail"]["band_num"] if item["status"] == "成功" else "",
                    "中央子午线": item["detail"]["central_lon"] if item["status"] == "成功" else "",
                    "转换状态": item["status"],
                    "备注": item["note"],
                    "错误信息": item["message"]
                })
            else:
                # CGCS2000→WGS84 导出格式
                export_data.append({
                    "序号": item["index"],
                    "国家2000 X坐标": item["input"].split(',')[0].strip(),
                    "国家2000 Y坐标": item["input"].split(',')[1].split('（')[0].strip(),
                    "带号": item["input"].split('：')[1].strip() if '：' in item["input"] else "",
                    "WGS84经度": item["detail"]["longitude"] if item["status"] == "成功" else "",
                    "WGS84纬度": item["detail"]["latitude"] if item["status"] == "成功" else "",
                    "中央子午线": item["detail"]["central_lon"] if item["status"] == "成功" else "",
                    "转换状态": item["status"],
                    "备注": item["note"],
                    "错误信息": item["message"]
                })

        export_df = pd.DataFrame(export_data)
        export_df.to_excel(temp_file, index=False, engine='openpyxl')
        temp_file.close()

        return jsonify({
            "status": "success",
            "results": results[:50],  # 只返回前50条预览
            "total": len(results),
            "temp_file": os.path.basename(temp_file.name),
            "source_type": source_type
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"处理文件时出错: {str(e)}"})


@app.route('/export_results/<filename>')
def export_results(filename):
    try:
        # 找到临时文件
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        if not os.path.exists(temp_path):
            return jsonify({"status": "error", "message": "文件不存在"}), 404

        # 发送文件
        return send_file(
            temp_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='坐标转换结果.xlsx'
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"导出失败: {str(e)}"})


if __name__ == '__main__':
    app.run(debug=True)