# 🌍 WGS84 / CGCS2000 坐标转换工具

> 一个开箱即用、可容器化部署、默认安全加固的坐标转换服务。  
> 支持 **WGS84 ↔ CGCS2000**、单点/批量转换、模板导出与结果下载。

## ✨ 项目亮点

- 🔄 **双向转换**：WGS84 经纬度与 CGCS2000 高斯投影互转
- 📦 **开箱即用**：`docker compose up -d` 即可启动
- 🛡️ **安全基线**：容器非 root、只读文件系统、最小化镜像上下文
- 🏷️ **规范发版**：GitHub Actions 自动生成 `vX.Y.Z` 与 `latest` 标签
- 📊 **批量处理**：支持 `xlsx/csv/txt` 导入与 Excel 导出

---

## 🧱 项目结构

```text
wgs84-cgcs2000/
├── .github/workflows/docker-image.yml  # 自动构建并推送 GHCR
├── Dockerfile                           # 生产镜像（非 root + healthcheck）
├── docker-compose.yml                   # 一键部署（默认 latest，可指定版本）
├── .dockerignore                        # 限制构建上下文，降低泄露风险
├── main.py                              # Flask 应用主程序
├── templates/index.html                 # Web 页面
├── tests/test_api_smoke.py              # 核心接口冒烟测试
└── README.md                            # 项目说明
```

---

## 🚀 快速开始（推荐 Docker）

### 1) 启动服务

```bash
docker compose up -d
```

默认访问地址：`http://localhost:5000`

### 2) 查看运行状态

```bash
docker compose ps
```

健康检查接口：`GET /healthz`

```bash
curl http://127.0.0.1:5000/healthz
```

期望返回：

```json
{"status":"ok"}
```

### 3) 停止服务

```bash
docker compose down
```

---

## 🐳 部署说明（版本号与 latest）

`docker-compose.yml` 默认拉取：

- `ghcr.io/marod1m/wgs84-cgcs2000:latest`

也支持指定版本（例如 `v1.2.0`）：

```bash
APP_VERSION=v1.2.0 docker compose up -d
```

如需修改端口（默认 5000）：

```bash
APP_PORT=8080 docker compose up -d
```

访问地址变为：`http://localhost:8080`

---

## 🔐 已实施的安全加固

### 容器层

- 使用 **非 root 用户** 运行应用（`appuser`）
- `docker-compose` 开启 **只读根文件系统**（`read_only: true`）
- 显式挂载 `tmpfs /tmp`，满足临时文件需求且减少落盘风险
- 增加 `no-new-privileges:true`，限制提权路径
- 增加应用级与容器级健康检查，便于自动恢复与观测

### 构建层

- 新增 `.dockerignore`，排除 `.git/.github/tests/.env` 等敏感或无关文件
- 仅复制运行必要文件（`main.py`、`templates`、`requirements.txt`）
- 关闭 pip 缓存与版本检查，减小镜像体积并减少噪音

### 应用层（原有 + 保持）

- 上传体积限制（10MB）
- 批量行数限制（默认 20000）
- 导出文件名/路径校验，防止路径遍历
- 参数校验（`sourceType`、`decimalPlaces` 等）

---

## ⚙️ 自动构建与发版策略

工作流文件：`.github/workflows/docker-image.yml`

### 触发规则

- `push master`：构建并推送分支标签/短 SHA 标签
- `push tag v*`：构建并推送语义化版本标签 + `latest`
- `pull_request -> master`：仅构建验证，不推送镜像

### 标签策略（单一镜像仓库，不创建多余镜像）

统一镜像名：`ghcr.io/<owner>/wgs84-cgcs2000`

- 分支构建：`master`、`sha-xxxxxxx`（便于追溯）
- 发布构建（打 tag）：
  - `v1.2.3`
  - `1.2`
  - `latest`

> 推荐发布流程：仅在确认版本可用时打 `vX.Y.Z` 标签，这样 `latest` 永远跟随正式发布。

---

## 🧪 本地验证

### 运行测试

```bash
python3 -m pytest -q tests
```

### 快速检查接口

- `GET /healthz`：服务健康
- `POST /convert_single`：单点转换
- `POST /convert_batch`：批量转换

---

## 📌 常见问题

### Q1：为什么容器设置为只读？
A：降低篡改与持久化恶意文件风险；本项目临时文件输出到 `tmpfs /tmp`，不影响功能。

### Q2：为什么 latest 只在版本 tag 时更新？
A：避免把未验证的日常提交覆盖生产默认版本，便于稳定部署与回滚。

### Q3：是否会生成多个不同镜像？
A：不会。仅维护一个仓库镜像（同名），通过不同 tag 表示版本。

---

## 🤝 贡献建议

- 提交前先跑测试：`python3 -m pytest -q tests`
- 建议 PR 描述包含：变更点、风险评估、回滚方式
- 涉及发布时请使用规范 tag：`vX.Y.Z`

