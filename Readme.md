# WGS84-CGCS2000 坐标转换工具 🗺️

一个高效、准确的WGS84与国家2000(CGCS2000)坐标系统双向转换工具，支持单点转换和批量转换功能。

## 🎯 功能特性

- 🔄 **双向转换**：支持WGS84经纬度 ↔ CGCS2000高斯投影
- 🌐 **多种分带方式**：支持3°分带和6°分带
- 📊 **批量转换**：支持Excel/CSV/TXT文件批量导入
- 📋 **模板下载**：提供标准化转换模板
- 📥 **结果导出**：支持将转换结果导出为Excel
- 🚀 **Docker一键部署**：快速搭建生产环境

## 🚀 快速开始

### 方式一：Docker一键部署（推荐）

#### 选项1：使用官方镜像（推荐）

1. **确保已安装Docker**
   - Windows：[下载Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - Linux/macOS：使用包管理器安装

2. **运行容器**
   ```bash
   docker run -d --name wgs84-cgcs2000-converter -p 5000:5000 ghcr.io/marod1m/wgs84-cgcs2000:latest
   ```

#### 选项2：Docker Compose一键部署

1. **确保已安装Docker和Docker Compose**
   - Windows/macOS：[下载Docker Desktop](https://www.docker.com/products/docker-desktop/)（自带Docker Compose）
   - Linux：分别安装Docker和Docker Compose

2. **创建docker-compose.yml文件**
   可以直接使用项目根目录的`docker-compose.yml`文件，或者创建自定义配置：
   
   ```yaml
   version: '3.8'
   
   services:
     # 坐标转换服务
     coordinate-converter:
       image: ghcr.io/marod1m/wgs84-cgcs2000:latest
       # 容器名称（可选）
       container_name: WGS84-CGCS2000-Converter
       # 端口映射：宿主机端口:容器内端口（Flask 默认运行在 5000 端口）
       network_mode: bridge
       ports:
         - "12345:5000"
       # 环境变量配置
       environment:
         - FLASK_APP=main.py
         - FLASK_ENV=production  # 生产环境（开发时可改为 development）
         - PYTHONUNBUFFERED=1  # 确保日志实时输出
       # 重启策略：容器退出时自动重启
       restart: no
       # 工作目录（容器内的项目根目录）
       working_dir: /app
   ```
   
   > 说明：
   > - 可以根据需要修改宿主机端口（示例中使用12345，可改为任意可用端口）
   > - `FLASK_ENV`设置为`production`时性能更好，设置为`development`时支持热重载
   > - `restart: no`表示容器退出后不自动重启，可根据需求改为`always`、`on-failure`等

3. **克隆项目并启动服务**
   ```bash
   git clone https://github.com/your-repo/WGS84-CGCS2000.git
   cd WGS84-CGCS2000
   docker-compose up -d
   ```

#### 访问应用
- 如果使用官方镜像默认端口：`http://localhost:5000`
- 如果使用自定义Docker Compose配置：`http://localhost:12345`（根据您设置的宿主机端口调整）

### 方式二：本地直接运行

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **启动应用**
   ```bash
   python main.py
   ```

3. **访问应用**
   打开浏览器访问：`http://127.0.0.1:5000`

## 📖 使用指南

### 1. 单点转换

#### WGS84经纬度 → CGCS2000高斯投影

1. 在转换方向选择中点击：**WGS84经纬度 → 国家2000高斯投影**
2. 输入**经度**和**纬度**
3. 选择**分带类型**（3°分带或6°分带）
4. 选择**是否启用带号**
5. 点击**转换**按钮
6. 查看转换结果

#### CGCS2000高斯投影 → WGS84经纬度

1. 在转换方向选择中点击：**国家2000高斯投影 → WGS84经纬度**
2. 输入**X坐标**和**Y坐标**
3. 输入**带号**
4. 选择**分带类型**（3°分带或6°分带）
5. 选择**是否启用带号**
6. 点击**转换**按钮
7. 查看转换结果

### 2. 批量转换

#### WGS84经纬度 → CGCS2000高斯投影

1. **下载模板**：点击"下载WGS84转国家2000模板"
2. **填写数据**：在模板中填写经度、纬度和可选的备注
3. **上传文件**：选择填写好的文件（支持xlsx、csv、txt格式）
4. **配置参数**：选择分带类型和是否启用带号
5. **开始转换**：点击"批量转换"
6. **查看结果**：在表格中查看转换结果
7. **导出结果**：点击"导出结果"下载Excel文件

#### CGCS2000高斯投影 → WGS84经纬度

1. **下载模板**：点击"下载国家2000转WGS84模板"
2. **填写数据**：在模板中填写X坐标、Y坐标、带号和可选的备注
3. **上传文件**：选择填写好的文件（支持xlsx、csv、txt格式）
4. **配置参数**：选择分带类型和是否启用带号
5. **开始转换**：点击"批量转换"
6. **查看结果**：在表格中查看转换结果
7. **导出结果**：点击"导出结果"下载Excel文件

## 📁 项目结构

```
WGS84-CGCS2000/
├── main.py              # 主程序入口
├── templates/
│   └── index.html       # 前端界面
├── requirements.txt     # 依赖列表
├── Dockerfile           # Docker构建文件
├── docker-compose.yml   # Docker编排文件
└── README.md            # 项目说明文档
```

## 🛠️ 技术说明

### 坐标系统

- **WGS84**：全球定位系统(GPS)使用的坐标系统
- **CGCS2000**：中国国家2000大地坐标系，是我国的法定坐标系

### 分带方式

1. **3°分带**：
   - 中央经线经度：75°、78°、81°...135°
   - 带号范围：25-45
   - 适用范围：工程测量、城市测量等高精度要求

2. **6°分带**：
   - 中央经线经度：75°、81°、87°...135°
   - 带号范围：13-23
   - 适用范围：国家基本比例尺地形图等

### 带号说明

- **启用带号**：X坐标前包含带号，如38XXXXXX.YYY
- **不启用带号**：X坐标直接为投影坐标值，如XXXXXX.YYY

## 📝 数据格式要求

### WGS84→CGCS2000模板

| 经度 | 纬度 | 备注（可选） |
|------|------|-------------|
| 116.397428 | 39.909230 | 北京天安门 |
| 121.473701 | 31.230416 | 上海外滩 |

### CGCS2000→WGS84模板

| X坐标 | Y坐标 | 带号 | 备注（可选） |
|-------|-------|------|-------------|
| 39535156.789 | 3990923.123 | 39 | 北京示例点 |
| 38547321.987 | 3123041.678 | 38 | 上海示例点 |

## 🔧 常见问题

### 1. 转换结果不准确？

- 检查输入的坐标格式是否正确
- 确认选择的分带类型和带号设置是否正确
- 确保输入的经度范围在72-135°之间，纬度在0-54°之间

### 2. 批量转换失败？

- 检查文件格式是否为xlsx、csv或txt
- 确保文件包含所有必要的列（如经度、纬度或X坐标、Y坐标、带号）
- 确认列名与模板保持一致

### 3. Docker部署遇到端口冲突？

修改docker-compose.yml文件中的端口映射：

```yaml
ports:
  - "8080:5000"  # 将8080改为其他可用端口
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 联系方式

如有问题或建议，欢迎联系项目维护者。

---

**使用提示**：建议使用Docker部署方式，可获得更稳定的运行环境和更好的性能表现。