# 技术文档与交接说明

> 项目：`wgs84-cgcs2000`
> 当前基线：`v2.0.3`
> 更新日期：2026-11-02
> 适用读者：后续开发、测试、运维、项目负责人

## 0. 阅读建议

- 先读第 1、2、3 节，建立项目全貌。
- 开发前重点读第 4、7 节。
- 部署和排障重点读第 8、9 节。
- 做版本规划重点读第 5、6 节。

---

## 1. 项目定位

### 1.1 项目是什么

一个面向内网、小团队和单机部署的 Web 坐标转换工具，支持：

- WGS84
- CGCS2000 高斯-克吕格投影（3° / 6° 分带）
- GCJ02（火星坐标）
- BD09（百度坐标）

提供单点转换、批量文件转换、模板下载、结果导出、经纬度格式互转和可选在线地图校验。

### 1.2 项目不是什么

明确边界可以避免后续过度设计：

- 不是正式测绘成果生产系统，不能替代官方测绘软件、控制点成果和审批流程。
- 不包含 GCJ02 / BD09 官方保密参数，只使用公开近似算法。
- 不是多租户 SaaS，当前没有账号、权限、计费和租户隔离。
- 不是高并发任务平台，当前没有消息队列、任务重试和对象存储。
- 不是 GIS 数据管理平台，不处理 Shapefile、GeoJSON、栅格、拓扑和空间数据库。

### 1.3 典型使用场景

- 将 GPS 采集的 WGS84 坐标转换为 CGCS2000 工程坐标。
- 将 CGCS2000 成果反算为 WGS84 / GCJ02 / BD09 用于地图展示。
- 对 Excel / CSV 批量数据做统一坐标转换并保留原始附加列。
- 在地图上快速检查源坐标和目标坐标是否落在合理位置。
- 在浏览器内完成十进制与度分秒格式互转。

### 1.4 技术栈

| 层级 | 技术 | 说明 |
| --- | --- | --- |
| Web 框架 | Flask 3.1 | 单页渲染、JSON API、文件上传 |
| 数据处理 | pandas / NumPy | CSV / Excel 读取、批量处理、导出 |
| 投影转换 | pyproj / PROJ | WGS84 与 CGCS2000 EPSG 转换 |
| Excel | openpyxl | 模板生成、批量结果导出 |
| 生产服务 | Gunicorn | 多 worker + gthread |
| 前端 | Bootstrap 5 + 原生 JS | 本地化资源，无 CDN |
| 地图 | Leaflet 1.9 | 天地图 WMTS（唯一在线底图） |
| 测试 | pytest | API 与核心转换测试 |
| 构建发布 | Docker / GitHub Actions | amd64 + arm64 多架构镜像 |

---

## 2. 项目完整规划

### 2.1 目标架构

```text
浏览器
  |
  |  HTML / JSON / multipart
  v
Flask (main.py)
  |-- 参数校验与坐标系别名归一化
  |-- 单点转换 convert_single
  |-- 批量转换 convert_batch
  |-- 模板导出 export_template
  |-- 结果下载 export_results
  |-- 地图公开配置 + CSP
  |
  +--> 转换核心 convert_coordinate
  |      |-- WGS84 <-> CGCS2000：pyproj / EPSG
  |      |-- WGS84 <-> GCJ02 / BD09：geo_conversion.py
  |
  +--> 文件层 pandas / openpyxl
  |      |-- CSV / TXT 多编码读取
  |      |-- XLSX 读取与导出
  |      |-- 额外列保留与公式注入防护
  |
  +--> 临时文件 /tmp/coord_cvt_*.xlsx
         |-- 1 小时后由下次批量请求触发清理

浏览器地图
  |-- Leaflet 本地资源
  |-- 天地图 WMTS（vec_w + cva_w）
  |-- 浏览器端 Key，可通过环境变量或页面设置提供
```

### 2.2 模块边界

| 模块 | 文件 | 职责 | 不应承担 |
| --- | --- | --- | --- |
| Web 入口 | `main.py` | 路由、校验、编排、文件处理、地图配置 | 复杂前端逻辑、持久化业务数据 |
| 转换算法 | `geo_conversion.py` | GCJ02 / BD09 偏移与反算 | 投影分带、文件读写 |
| 页面 | `templates/index.html` | 表单、结果、地图、DMS、日志 | 可信服务端校验 |
| 静态资源 | `static/vendor/`、`static/css`、`static/js` | Bootstrap / Leaflet 本地依赖、移动端增强层 | 业务代码 |
| 测试 | `tests/test_api_smoke.py`、`tests/test_mobile_ui_contract.py` | API、核心行为、移动端资产与契约回归 | 浏览器 E2E |
| 部署 | `Dockerfile`、`docker-compose*.yml` | 单机容器部署 | 集群编排 |
| CI | `.github/workflows/docker-image.yml` | 测试、多架构构建、GHCR 发布 | 生产运行 |
| 文档 | `README.md`、`docs/TECHNICAL.md` | 使用说明与交接 | 运行时依赖 |

### 2.3 分阶段规划

| 阶段 | 目标 | 状态 |
| --- | --- | --- |
| 阶段 1：基础转换 | WGS84 / CGCS2000、单点、批量、模板、导出 | 已完成 |
| 阶段 2：多坐标系 | GCJ02 / BD09、任意组合、地图校验、移动端 | 已完成 |
| 阶段 3：工程质量 | 参数校验、安全头、测试、CI、多架构镜像 | 基本完成 |
| 阶段 4：平台化 | 认证、任务队列、审计、对象存储、可观测性 | 未开始 |
| 阶段 5：专业 GIS | 自定义投影、高程基准、GeoJSON/Shapefile、离线瓦片 | 未开始 |

### 2.4 非功能目标

| 维度 | 当前目标 | 现状 |
| --- | --- | --- |
| 单次上传大小 | 10 MB | Flask `MAX_CONTENT_LENGTH` |
| 单次批量行数 | 20,000 行 | `MAX_BATCH_ROWS` |
| 批量预览 | 前 50 条 | `MAX_PREVIEW_ROWS` |
| 地图点数 | 前 50 条 | 仅前 50 条计算地图坐标 |
| 临时文件保留 | 约 1 小时 | 下次批量请求触发清理 |
| 浏览器兼容 | 现代 Chrome / Edge / Firefox / Safari | 使用 WebP、Clipboard 回退 |
| 部署架构 | 单机 Docker / 群晖 | 无外部数据库 |
| 可用性 | 单实例尽力可用 | 无高可用和自动扩缩容 |

### 2.5 核心设计决策

1. **统一 WGS84 作为中间坐标系**
   所有源坐标先转为 WGS84，再转为目标坐标。这样 4 种坐标系只需要维护 4 组“到/从 WGS84”的逻辑，避免 16 条两两转换分支。

2. **CGCS2000 使用 EPSG 权威参数**
   3° / 6° 分带分别使用 EPSG 4513–4554、4491–4512 等编码，不手写投影公式。带号、中央子午线、含带号 Y 前缀都在 `main.py` 中校验。

3. **GCJ02 / BD09 使用公开近似算法**
   仅适用于中国范围，结果可能与官方接口存在米级差异。算法放在独立的 `geo_conversion.py`，便于替换或增加测试。

4. **批量处理不引入数据库**
   当前使用 `/tmp/coord_cvt_*.xlsx` 保存导出结果，按时间清理。优点是部署简单；缺点是重启、清理、多实例共享和审计能力有限。

5. **地图默认关闭，用户勾选后才请求第三方瓦片**
   页面不主动泄露坐标。地图服务固定为天地图，CSP 只在启用时放行 `https://*.tianditu.gov.cn`。

6. **保持旧接口兼容**
   `/convert_single` 不传 `targetType` 时保持旧行为：`wgs84 → cgcs2000`，`cgcs2000 / gcj02 / bd09 → wgs84`。这样旧前端或脚本不会因升级立即失效。

7. **前端依赖本地化**
   Bootstrap、Leaflet 和移动端增强样式/脚本均放在 `static/`，不依赖 CDN，适合内网和离线环境。

### 2.6 坐标约定与分带规则

- 经纬度字段统一为 `lonX`（经度）、`latY`（纬度）。
- CGCS2000 输入/输出中：
  - `X` = 北方向 Northing
  - `Y` = 东方向 Easting
- 3° 分带：带号 25–45，经度有效范围约 73.5°–136.5°。
- 6° 分带：带号 13–23，经度有效范围约 72°–138°。
- 含带号时，Y 的前两位必须等于带号。
- 不含带号时，Y 应在 0–1,000,000 米范围内。
- 目标带号可留空自动选带，也可固定带号；固定带号会校验目标经度与中央子午线是否匹配。

---

## 3. 已完成内容

### 3.1 后端与转换能力

- 4 种坐标系任意组合转换。
- WGS84 ↔ CGCS2000 使用 pyproj / EPSG。
- GCJ02 / BD09 正反算，WGS84 反解使用迭代法。
- CGCS2000 3° / 6° 分带、含带号/不含带号、目标固定带号。
- 带号前缀、Y 范围、反算经度偏离中央子午线等异常校验。
- 旧接口默认目标兼容。
- 单点 JSON 接口和批量 multipart 接口。
- 模板下载：xlsx / csv / txt。
- 批量导出：xlsx，保留额外列。
- 公式注入防护：`= + - @` 等危险前缀处理。
- 路径遍历防护：结果下载只允许临时目录内的合法文件名。
- 413 / 500 统一 JSON 错误响应。
- 临时文件按 1 小时清理。

### 3.2 前端能力

- 单点 / 批量 / 经纬度格式转换三个标签页。
- 源/目标坐标系动态表单。
- CGCS2000 分带设置按需显示。
- 单点交换、填入示例、清空、Enter 触发转换。
- 批量交换、清空、文件选择、模板下载、结果导出。
- DMS 三种模式：十进制 → 度分秒、度分秒 → 十进制、度分秒 → 压矿格式。
- DMS 单点和批量转换、CSV 导出。
- 复制按钮支持安全上下文 Clipboard API 和 HTTP 兼容回退。
- 复制成功/失败按钮反馈，无结果时禁用。
- 日志区记录关键操作。
- 移动端顶部 sticky 三段式标签，避免标签换行。
- 移动端源/目标坐标系全宽选择、独立交换按钮和安全区分 padding。
- 移动端输入控件统一 16px 字号和至少 44px 触控高度，避免 iOS 聚焦缩放。
- 批量与 DMS 结果在移动端显示为卡片列表，桌面端继续使用原表格。
- 移动端单点结果紧凑排版、转换后自动滚动，地图开启后自动定位。
- 移动端日志默认折叠，发生错误自动展开；地图控件和横竖屏尺寸自适应。
- 桌面端 ≥768px 保持原布局，移动端样式全部位于独立媒体查询。

### 3.3 地图能力

- 单点地图预览：源坐标、目标坐标、原始数值落图。
- 批量地图预览：前 50 条成功结果。
- 底图固定为天地图 WMTS，坐标系为 WGS84。
- 地图默认关闭，勾选后才加载。
- 天地图 Key 优先级：浏览器 localStorage > 服务端 `TIANDITU_KEY`。
- 无 Key 时地图勾选禁用，并提供“地图设置”入口。
- 瓦片加载连续失败时显示错误提示和重试入口。
- CSP 只放行 `https://*.tianditu.gov.cn`。
- v2.0.0 起移除 OpenStreetMap 和自定义 XYZ 瓦片。

### 3.4 安全与工程化

- CSP、`X-Content-Type-Options`、`X-Frame-Options`、`Referrer-Policy`、`Permissions-Policy`。
- 上传大小限制、扩展名白名单、行数上限。
- 前端输出使用 `textContent` / `escapeHtml`，地图弹窗使用 DOM 节点而非 HTML 字符串。
- GitHub Actions：先跑 pytest，再构建 amd64 + arm64 镜像。
- GHCR 镜像标签：当前版本 `2.0.3`、`2.0`、`latest`；历史损坏版本 `2.0.0`、`2.0.1`、`2.0.2` 已清理。
- README 包含部署、接口、地图配置、参考项目和界面预览。
- 当前自动化测试 29 个。

### 3.5 性能基线

| 场景 | 环境 | 观察结果 |
| --- | --- | --- |
| 20,000 行批量转换 | 开发容器，本地文件 | 单次冒烟约 3.5 秒；未做正式压测 |
| 地图预览 | 批量前 50 条 | 仅前 50 条生成地图坐标，避免无谓反算 |
| 上传限制 | 10 MB | 超过后由 Flask 返回 413 |
| 批量上限 | 20,000 行 | 超过后返回 400 |

> 上述数据是开发期冒烟值，不是 SLA。正式扩容前应使用真实文件和目标服务器做基准测试。

### 3.6 已验证的功能矩阵

| 功能 | 验证方式 | 结果 |
| --- | --- | --- |
| 单点 4×4 坐标系组合 | Playwright 浏览器回归 | 16/16 通过 |
| 批量 4×4 坐标系组合 | Playwright 浏览器回归 | 16/16 通过 |
| 3° / 6° 分带 | 浏览器 + pytest | 通过 |
| 含带号 / 不含带号 | 浏览器 + pytest | 通过 |
| 目标固定带号 | 浏览器 + pytest | 通过 |
| DMS 三种模式 | 浏览器回归 | 通过 |
| 模板下载 | Playwright 下载事件 | 通过 |
| 批量结果导出 | Playwright 下载事件 | 通过 |
| DMS CSV 导出 | Playwright 下载事件 | 通过 |
| 天地图瓦片与标记 | Playwright（模拟瓦片） | 通过 |
| HTTP 非安全上下文复制回退 | Playwright | 通过 |
| 移动端 320–430px 与横屏布局 | Playwright 触摸模拟 | 无横向溢出，标签不换行，卡片表格通过 |
| 移动端地图与日志 | Playwright 触摸模拟 | 天地图 300px / 横屏 220px，日志折叠与错误展开通过 |
| 桌面端像素回归 | 768 / 1280 / 1440 截图对比 | 与改造前一致 |
| 移动端资产契约 | pytest | 通过 |
| API 回归 | pytest | 29 passed |

> 浏览器回归脚本目前是开发期临时脚本，尚未纳入仓库 CI；这是后续需要补的工程项。

---

## 4. 代码结构与关键流程

### 4.1 目录结构

```text
.
├── main.py                       Flask 入口、API、转换编排、文件处理、地图配置
├── geo_conversion.py             GCJ02 / BD09 公开近似算法
├── templates/
│   └── index.html                单页前端（HTML + CSS + JS）
├── static/
│   ├── css/
│   │   └── mobile.css            移动端专属样式（≤767.98px）
│   ├── js/
│   │   └── mobile.js             移动端滚动、日志折叠、地图尺寸增强
│   ├── favicon.ico
│   └── vendor/
│       ├── bootstrap/            Bootstrap 5 本地资源与许可证
│       └── leaflet/              Leaflet 1.9 本地资源与许可证
├── tests/
│   ├── test_api_smoke.py         API 与核心转换测试
│   └── test_mobile_ui_contract.py 移动端资产、标记与作用域契约测试
├── docs/
│   ├── TECHNICAL.md              本文档
│   └── images/                   README 预览图（WebP）
├── .github/workflows/
│   └── docker-image.yml          pytest + 多架构镜像发布
├── Dockerfile
├── docker-compose.yml            群晖/单机简化版
├── docker-compose.full.yml       进阶安全版
├── .env.example
├── .dockerignore
├── .gitignore
├── requirements.txt
└── README.md
```

### 4.2 单点转换流程

1. 前端收集 `sourceType`、`targetType`、坐标、分带、小数位数。
2. `POST /convert_single`。
3. `_normalize_crs` / `_resolve_target_type` 归一化坐标系。
4. `_to_wgs84` 把源坐标转为 WGS84：
   - WGS84：范围校验。
   - CGCS2000：分带校验 → pyproj 反算 → 合理性校验。
   - GCJ02 / BD09：中国范围校验 → 迭代/偏移反算。
5. `_from_wgs84` 把 WGS84 转为目标坐标：
   - CGCS2000：自动选带或固定带号 → pyproj 正算。
   - GCJ02 / BD09：偏移正算。
6. `convert_coordinate` 组装结果、兼容旧字段、按需生成地图坐标。
7. 返回 JSON；前端渲染结果，可选加载地图。

### 4.3 批量转换流程

1. 前端上传文件并提交表单字段。
2. `convert_batch` 校验参数、文件大小、扩展名、行数。
3. `_read_dataframe` 读取 CSV / TXT / XLSX。
4. 列名标准化，拒绝重复列，检查必要列。
5. 识别备注列和额外列。
6. 使用 `itertuples` 遍历，逐行调用 `convert_coordinate`。
7. 前 50 行生成地图坐标，其余跳过地图反算以提升性能。
8. `_build_export_rows` 生成导出表：
   - 系统列固定；
   - 额外列冲突时自动改名为 `附加_原列名`；
   - 备注/额外列做公式注入防护。
9. 写入 `/tmp/coord_cvt_*.xlsx`。
10. 返回前 50 条预览、统计信息和临时文件名。
11. 前端展示表格和地图；用户点击导出下载完整 Excel。

### 4.4 地图与 CSP 流程

1. `_get_map_config` 读取 `MAP_PROVIDER` 和 `TIANDITU_KEY`。
2. `MAP_PROVIDER` 只接受 `tianditu` / `none`；旧值回退为 `tianditu`。
3. `_inject_app_context` 把公开地图配置和应用版本注入模板。
4. `_map_origins` 仅在天地图启用时加入 `https://*.tianditu.gov.cn`。
5. `_add_security_headers` 写入 CSP。
6. 前端 `getTiandituKey` 优先读取 localStorage，其次使用 `MAP_CFG.tianditu_key`。
7. `tileLayers` 创建天地图矢量底图和注记图层。
8. 用户填写 Key 并勾选地图后才加载瓦片。

### 4.5 前端关键状态

| 变量 | 用途 |
| --- | --- |
| `g_lastSingle` | 最近一次单点成功结果，供复制和地图使用 |
| `g_batchFile` | 最近一次批量导出的临时文件名 |
| `g_lastBatchResults` | 批量预览结果（最多 50 条） |
| `g_dmsMode` | 当前 DMS 模式 |
| `g_dmsResults` | DMS 批量结果 |
| `g_singleMap` / `g_batchMap` | Leaflet 地图实例 |
| `g_singleLayer` / `g_batchLayer` | 地图标记图层 |
| `g_tileErrors` | 天地图瓦片连续失败计数 |
| `TIANDITU_KEY_STORAGE` | 浏览器 localStorage 中的天地图 Key 键名 |

### 4.6 移动端增强层

移动端优化不修改转换逻辑；除新增地图设置入口外，桌面端原有布局保持不变。由两个独立文件实现：

- `static/css/mobile.css`：移动端规则位于 `max-width: 767.98px` 或触屏横屏媒体查询内；桌面端只增加隐藏的短标签、结果说明字号和地图设置面板样式。
- `static/js/mobile.js`：通过 `matchMedia` 判断移动端；桌面端不执行滚动、折叠和地图尺寸刷新。
- `templates/index.html`：增加移动端 class、短标签、`data-label`、ARIA、地图设置面板和少量行为挂载点；桌面端除地图设置入口外保持原布局。

移动端行为：

1. 单点转换成功后滚动到结果区。
2. 批量转换成功后滚动到统计区。
3. 开启地图后滚动到地图容器。
4. 日志默认折叠，错误日志触发自动展开。
5. 横竖屏切换和窗口变化后刷新 Leaflet 尺寸。

### 4.7 关键函数索引

| 函数 | 位置 | 作用 |
| --- | --- | --- |
| `_get_transformer` | `main.py` | 缓存 pyproj Transformer |
| `get_band_info` | `main.py` | 按经度或带号查询 EPSG 分带 |
| `_to_wgs84` | `main.py` | 源坐标 → WGS84 |
| `_from_wgs84` | `main.py` | WGS84 → 目标坐标 |
| `convert_coordinate` | `main.py` | 单点转换核心编排 |
| `_get_map_config` | `main.py` | 地图公开配置 |
| `_sample_rows` | `main.py` | 模板示例行 |
| `_read_dataframe` | `main.py` | CSV/TXT/XLSX 读取 |
| `_build_export_rows` | `main.py` | 批量导出表构造 |
| `_extra_column_names` | `main.py` | 额外列冲突改名 |
| `convert_batch` | `main.py` | 批量转换路由 |
| `copyTextToClipboard` | `templates/index.html` | 复制兼容封装 |
| `doSingleConvert` | `templates/index.html` | 单点请求与渲染 |
| `doBatchConvert` | `templates/index.html` | 批量请求与渲染 |
| `refreshSingleMap` | `templates/index.html` | 单点地图刷新 |
| `refreshBatchMap` | `templates/index.html` | 批量地图刷新 |
| `setDmsMode` | `templates/index.html` | DMS 模式切换与清理 |
| `invalidateAppMaps` | `templates/index.html` | 刷新单点/批量地图尺寸 |
| `MobileEnhance` | `static/js/mobile.js` | 移动端判定、结果滚动和批量滚动 |

### 4.8 数据格式约定

单点请求：

```json
{
  "sourceType": "wgs84",
  "targetType": "gcj02",
  "lonX": 116.397428,
  "latY": 39.90923,
  "bandType": "3°分带",
  "sourceWithBand": true,
  "targetWithBand": true,
  "targetBandNum": null,
  "decimalPlaces": 6
}
```

批量模板列：

- 经纬度源：`经度`、`纬度`
- CGCS2000 源：`X坐标`、`Y坐标`、`带号`
- 可选备注：`备注（可选）` 或 `备注`
- 其他列保留到导出结果；与系统列重名时导出为 `附加_原列名`

---

## 5. 未完成方案与技术债

### 5.1 高优先级

| 事项 | 现状 | 风险 | 建议 |
| --- | --- | --- | --- |
| 访问控制 | 无登录、无鉴权 | 暴露公网时任何人可上传/下载 | 反向代理 Basic Auth / OIDC，或增加应用内账号 |
| 限流与配额 | 无 | 大文件/高频请求可拖垮单实例 | Nginx `limit_req`、Flask-Limiter、按 IP/用户配额 |
| 依赖安全 | Werkzeug 已升级到 3.1.9，修复 GHSA-g6x2-hccm-hh4m；复核后 7 个锁定版本 OSV 均无告警 | 旧版 pandas / NumPy 仍需长期跟踪 | 每季度执行 OSV / pip-audit；升级 Python 3.12 + pandas 2.x 需单独立项验证 |
| 浏览器 E2E 入 CI | 仅开发期脚本 | 前端回归靠人工 | 增加 Playwright 测试目录与 CI job |
| 临时文件治理 | /tmp + 1 小时清理 | 重启丢失、无审计、多实例不共享 | 对象存储/S3 或数据库记录 + 定期任务 |
| 日志与监控 | 主要靠 Gunicorn 日志 | 故障定位慢 | 结构化日志、请求 ID、Prometheus 指标、健康检查告警 |

### 5.2 中优先级

| 事项 | 现状 | 风险/影响 | 建议 |
| --- | --- | --- | --- |
| 异步任务 | 同步请求内完成批量转换 | 大文件请求占用 worker | 任务队列（RQ/Celery）+ 状态轮询 |
| 流式处理 | 文件整体读入内存 | 20k 行以内可接受，更大文件受限 | 分块读取、流式导出、提高上限前先压测 |
| API 文档 | README 手写 | 字段变更易不同步 | OpenAPI/Swagger，自动生成示例 |
| API 版本化 | 无 `/v1` | 未来破坏性变更困难 | 新增 `/api/v1`，旧接口保留 |
| 前端拆分 | 核心仍为单文件 HTML，移动端样式/行为已拆到 `static/css` 与 `static/js` | 维护和复用成本仍偏高 | 继续拆分核心 CSS/JS 模块，或迁移轻量框架 |
| CSP 强化 | `script-src 'unsafe-inline'` | XSS 防线较弱 | 改用 nonce/hash，移除 inline script |
| 坐标精度验证 | 已知点 + 公开算法 | 缺少权威控制点回归 | 建立控制点基准集，定期比对官方 SDK |
| 自定义投影 | 仅内置 CGCS2000 分带 | 不能处理地方坐标系 | 支持 EPSG/Proj4 参数输入与白名单 |

### 5.3 低优先级/长期

| 事项 | 说明 |
| --- | --- |
| 高程/大地水准面 | 当前只有平面坐标，无高程基准转换 |
| GeoJSON / Shapefile | 当前只支持表格文件 |
| 离线地图 | 当前依赖在线瓦片，内网离线需自建瓦片服务 |
| 国际化 | 当前中文界面，无 i18n |
| 多租户 | 当前单实例单团队使用 |
| 审计与留存 | 当前无操作审计、无历史任务列表 |
| 集群部署 | 当前临时文件与内存状态不适合多副本 |
| 许可证 | 仓库尚未声明开源许可证，接手前需确认发布范围 |

### 5.4 不建议现在做的事

- 不要为了“看起来先进”引入微服务、Kubernetes、消息队列。当前用户量和数据量下，单 Flask + 单机 Docker 更易维护。
- 不要在未建立控制点回归前，把 GCJ02/BD09 宣称为“官方精确坐标”。
- 不要在没有鉴权和限流前直接把服务暴露到公网。
- 不要盲目升级所有依赖；先建立 Python 3.10/3.12 双版本测试，再升级基础镜像。

---

## 6. 未来路线图

### P0：1–2 周内建议完成

1. 在 GitHub Security 页面确认 moderate 告警，升级受影响依赖。
2. 增加 Playwright E2E 到 CI，覆盖单点、批量、DMS、复制、下载、地图。
3. 增加反向代理鉴权和限流示例（Nginx / Caddy）。
4. 增加请求 ID、结构化日志和基础 Prometheus 指标。
5. 明确临时文件生命周期和多实例限制，写入部署文档。

### P1：1–2 个月

1. 批量任务异步化：任务表 + 队列 + 状态查询 + 结果过期。
2. OpenAPI 文档与 `/api/v1` 版本化。
3. 前端拆分为独立 CSS/JS 模块，补充前端单元测试。
4. 增加控制点基准测试，记录与官方 SDK 的偏差。
5. 支持可配置的上传大小、行数、预览条数。

### P2：3–6 个月

1. 对象存储或数据库持久化导出结果。
2. 自定义 EPSG / Proj4 投影参数。
3. GeoJSON / Shapefile 输入输出。
4. 离线瓦片/内网地图方案。
5. 多租户、审计、配额、国际化（按实际需求决定是否做）。

### 关键决策点

| 决策 | 选项 A | 选项 B | 建议 |
| --- | --- | --- | --- |
| 部署形态 | 单机 Docker | Kubernetes | 先用单机，出现多副本需求再上 K8s |
| 批量执行 | 同步 | 队列异步 | 20k 行以内同步；更大或需要重试时上队列 |
| 结果存储 | /tmp | 对象存储/数据库 | 单机短期用 /tmp；需要审计/多实例时迁移 |
| 认证 | 反向代理 | 应用内账号 | 小团队优先反向代理，减少代码复杂度 |
| 前端 | 原生 JS 单页 | Vue/React | 当前规模原生足够；模块化优先于换框架 |

---

## 7. 开发指南

### 7.1 本地运行

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q tests
MAP_PROVIDER=tianditu .venv/bin/python main.py
```

访问 `http://127.0.0.1:5000/`。

### 7.2 测试

```bash
.venv/bin/python -m pytest -q tests
```

当前测试重点：

- 单点 WGS84 / GCJ02 / BD09 已知值与往返。
- CGCS2000 带号前缀、缺带号、分带边界。
- 批量 GCJ02 → WGS84。
- 模板示例值。
- 地图配置与本地静态资源。
- 批量前 50 条地图数据。
- 天地图 Key 优先级、无 Key 状态和设置面板契约。
- 地图默认 provider 为天地图。
- 额外列与系统列冲突改名。

### 7.3 新增坐标系

1. 在 `CRS_LABELS`、`CRS_ALIASES`、`DEFAULT_TARGET` 增加条目。
2. 在 `_to_wgs84` / `_from_wgs84` 增加转换分支。
3. 在 `convert_coordinate` 的结果组装中处理目标字段。
4. 更新前端 `CRS`、`SAMPLES`、表单联动和地图原始点逻辑。
5. 增加已知值、边界、往返测试。
6. 更新 README 和技术文档。

### 7.4 修改地图配置

1. 在 `_get_map_config` 调整天地图开关和 Key 读取。
2. 在 `_map_origins` 维护 CSP 域名。
3. 在前端 `tileLayers` 调整天地图 WMTS 图层。
4. 更新 `.env.example`、compose、README。
5. 测试 Key 优先级、CSP、无 Key 状态和瓦片加载。

### 7.5 新增导出列

1. 在 `_build_export_rows` 的 `reserved` 集合中登记新列名。
2. 确保额外列冲突时仍使用 `附加_` 前缀。
3. 对用户可控字符串调用 `_safe_excel_value`。
4. 增加导出测试。

### 7.6 发布流程

```bash
# 1. 修改版本示例（README / .env.example / compose 注释）
# 2. 运行测试
.venv/bin/python -m pytest -q tests

# 3. 提交并打标签
git add ...
git commit -m "feat: ..."
git tag -a vX.Y.Z -m "vX.Y.Z: ..."
git push origin master
git push origin vX.Y.Z
```

GitHub Actions 会：

1. 在 `master`、PR 和标签推送时运行 pytest。
2. `master` / PR 只跑测试，不构建或推送镜像。
3. `v*` 标签推送时构建 `linux/amd64` + `linux/arm64` 镜像。
4. 使用 Docker manifest list 输出，关闭 provenance / SBOM，兼容旧版 Docker。
5. 推送 `X.Y.Z`、`X.Y`、`latest` 到 GHCR。
6. 发布后校验 manifest 类型、无 `unknown/unknown`，并运行镜像核对 `APP_VERSION`。
7. 发布后只清理指定的历史错误版本；禁止按“无标签”删除 GHCR 版本，避免误删多架构子 manifest。

### 7.7 代码风格与注释

- Python 使用 4 空格缩进，函数保持单一职责。
- 关键算法、兼容逻辑、安全校验必须有 docstring 或行内注释。
- 前端用户数据进入 DOM 前必须转义；地图弹窗使用 `textContent`。
- 不引入未使用依赖；新增依赖需更新 `requirements.txt` 和 Docker 构建验证。

---

## 8. 运维说明

### 8.1 环境变量

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `MAP_PROVIDER` | `tianditu` | `tianditu` / `none` |
| `TIANDITU_KEY` | 空 | 天地图浏览器端 Key，可由页面设置覆盖 |
| `APP_PORT` | `5000` | compose 宿主机端口 |
| `APP_VERSION` | `latest` | compose 镜像标签；发布构建时也写入镜像运行版本 |

### 8.2 部署方式

- `docker-compose.yml`：群晖/单机简化版，默认天地图，适合快速试用。
- `docker-compose.full.yml`：带容器名、健康检查、安全选项，适合长期运行。
- 直接运行：`MAP_PROVIDER=tianditu python main.py`，仅建议开发使用。

### 8.3 健康检查与日志

- 健康检查：`GET /healthz` 返回 `{"status":"ok","version":"2.0.3"}`；`v2.0.1` 之前的镜像只有 `status`。
- Gunicorn 日志输出到容器标准输出。
- 批量临时文件：`/tmp/coord_cvt_*.xlsx`，默认保留约 1 小时。

### 8.4 常见问题

| 现象 | 可能原因 | 处理 |
| --- | --- | --- |
| 地图不显示 | 未配置天地图 Key | 打开页面“地图设置”填写 Key，或配置 `TIANDITU_KEY` |
| 地图瓦片被 CSP 拦截 | CSP 未包含天地图域名 | 检查 `MAP_PROVIDER` 和 `_map_origins`，重启服务 |
| 天地图提示 Key 无效 | Key 错误或域名未加入白名单 | 检查天地图控制台 Key、域名/IP 白名单和 HTTPS |
| 群晖拉取 manifest unknown | 标签不存在，或索引引用的子 manifest 被误删 | 使用 `2.0.3`；检查 `docker version` / `docker manifest inspect`；必要时重建 Container Manager 项目，或临时指定 `platform: linux/amd64` |
| 复制按钮失败 | 非 HTTPS 且浏览器不支持回退 | 已在代码中回退；仍失败时检查浏览器权限 |
| 批量导出 404 | 临时文件过期或服务重启 | 重新执行批量转换 |
| 上传 413 | 超过 10MB | 拆分文件或调整 `MAX_CONTENT_LENGTH` |
| 批量报列名错误 | 模板列名不匹配 | 下载对应源坐标系模板 |
| 带号不匹配 | Y 前缀与带号参数不一致 | 检查“Y 含带号”开关和数据 |
| 目标带号报错 | 固定带号与经度不匹配 | 留空自动选带，或改用正确带号 |

---

## 9. 安全、合规与隐私

### 9.1 数据流与隐私

- 坐标数据只在用户主动勾选地图时发送到第三方瓦片服务。
- 地图默认关闭；服务端不会主动把坐标写入日志。
- 批量文件在服务端临时保存为 Excel，默认 1 小时后清理。
- 如需处理敏感坐标，建议内网部署、关闭地图或使用自建瓦片。

### 9.2 已知安全措施

- 上传大小、扩展名、行数限制。
- 文件名路径遍历防护。
- Excel 公式注入防护。
- 前端输出转义。
- CSP 与安全响应头。
- 地图 Key 仅使用浏览器端公开 Key。

### 9.3 仍需注意

- 当前无登录鉴权，公网部署前必须加反向代理认证。
- 当前无 CSRF Token；因为接口不使用 Cookie 会话，风险较低，但加认证后需重新评估。
- CSP 仍允许 `unsafe-inline`，未来应改为 nonce/hash。
- 临时文件下载没有用户归属校验，依赖随机文件名和短保留期。
- GCJ02 / BD09 为公开近似算法，不能用于需要官方保密参数的场景。

---

## 10. 已知限制

- 批量上限 20,000 行、上传上限 10 MB。
- 地图预览只展示前 50 条。
- 临时文件不跨实例共享，服务重启后旧下载链接失效。
- 无高程/大地水准面转换。
- 无 Shapefile / GeoJSON / 空间数据库支持。
- 无任务历史、审计日志、用户配额。
- 前端为单文件，长期维护成本会上升。
- 依赖版本偏旧，升级需要单独验证。

---



## 11. v2.0.3 复核与发布记录

### 11.1 复核范围

本次复核覆盖：

- 当前完整代码、配置、部署文件和文档。
- WGS84 / CGCS2000 / GCJ02 / BD09 单点与批量转换路径。
- 模板下载、批量导出、DMS 导出、天地图预览、复制按钮。
- 参数校验、异常处理、文件安全、CSP、依赖和敏感信息。
- 桌面端、移动端和天地图设置面板。

### 11.2 代码与配置复核结论

| 检查项 | 结果 |
| --- | --- |
| CGCS2000 EPSG 配置 | 3° / 6° 分带与中央子午线常量一致；重点抽查带号 20、39 |
| 源到 WGS84 转换 | WGS84、CGCS2000、GCJ02、BD09 分支均有边界校验 |
| WGS84 到目标转换 | 目标自动选带、固定带号、含/不含带号均有校验 |
| 单点接口 | JSON 校验、参数归一化、错误码和旧接口兼容均正常 |
| 批量接口 | 扩展名、大小、行数、列名、空值、重复列均有防护 |
| 额外列 | 与系统列冲突时自动改名为 `附加_原列名`，不再覆盖统计列 |
| 导出安全 | 公式注入、路径遍历、临时文件命名均有防护 |
| 地图配置 | 仅保留天地图；无 Key 时禁用地图并引导设置；CSP 仅放行天地图域名 |
| 前端复制 | Clipboard API + HTTP 兼容回退；无结果时按钮禁用 |
| DMS | 三种模式、批量、导出、模式切换清理均正常 |
| 文档 | README、技术文档、预览图链接均存在 |

复核中未发现新的高危代码执行路径或可直接利用的文件读写漏洞。项目当前没有登录和限流，不能直接暴露到公网。

### 11.3 近期修复

v2.0.3：

- 修复 GHCR 清理逻辑按“无标签”删除版本、误删多架构子 manifest 的问题；镜像索引不再悬空，`manifest unknown` 已解决。
- 移除自动删除无标签版本的步骤，改为只清理指定的历史错误版本。
- 重新发布 `2.0.3`、`2.0`、`latest`，清理已损坏的 `2.0.0`、`2.0.1`、`2.0.2`。

v2.0.2：

- 镜像构建改为 Docker manifest list，关闭 provenance / SBOM attestation，修复旧版 Docker / 群晖 Container Manager 对 OCI index 兼容不足导致的 `manifest unknown`。
- CI 增加 manifest 类型、`unknown/unknown` 和运行版本校验。
- `master` / PR 不再构建镜像，只有标签发布镜像，减少无效构建产物。
- README 增加群晖 Docker 版本排查和项目缓存处理说明。

v2.0.1：

- GHCR 清理策略改为只删除无正式版本标签的构建镜像，保留所有 `X.Y.Z` 正式版本。
- `/healthz` 增加 `version` 字段；镜像构建通过 `APP_VERSION` 参数写入运行版本。
- 地图设置面板显示当前应用版本。
- 新增 `CHANGELOG.md`。

### 11.4 v2.0.0 地图迁移

- 移除 OpenStreetMap、`OSM_TILE_URL`、OSM 外部反代方案。
- 移除自定义 XYZ 瓦片、`MAP_TILE_URL`、`MAP_TILE_ATTRIBUTION`、`MAP_TILE_CRS`。
- `MAP_PROVIDER` 只接受 `tianditu` / `none`；旧值自动回退为 `tianditu`。
- 天地图 Key 支持服务端 `TIANDITU_KEY` 和浏览器 localStorage 覆盖。
- 未配置 Key 时地图勾选禁用，页面提供“地图设置”入口。
- 天地图瓦片连续失败时显示 Key、白名单和网络排查提示。

### 11.5 测试与验证记录

| 检查 | 命令/方式 | 结果 |
| --- | --- | --- |
| Python 单元/API 测试（含移动端契约） | `pytest -q tests` | 29 passed |
| Python 语法 | `py_compile` / `compileall` | 通过 |
| 静态检查 | `ruff check --select E9,F,I` | 通过 |
| 前端 JS 语法 | 渲染模板后 `node --check` | 通过 |
| YAML 语法 | PyYAML 解析 compose / workflow | 通过 |
| HTML 结构 | HTMLParser 栈检查 | 无未闭合标签 |
| DOM 一致性 | 重复 ID、缺失 `getElementById`、缺失 label | 均为 0 |
| 单点浏览器回归 | 4×4 坐标系组合 | 通过 |
| 批量浏览器回归 | 4×4 坐标系组合 | 通过 |
| DMS | 三种模式 + 批量 + 导出 | 通过 |
| 复制 | HTTPS/安全上下文 + HTTP 回退 | 通过 |
| 地图 | 天地图模拟瓦片、无 Key 状态、设置面板 | 通过 |
| 下载 | 模板、批量结果、DMS CSV | 通过 |
| 移动端布局 | 320 / 360 / 390 / 430px + 844×390 横屏 | 无横向溢出，标签不换行，输入 16px，触控 ≥44px |
| 移动端表格 | 批量 / DMS 卡片列表 | 表头隐藏、字段标签完整、无横向滚动 |
| 移动端地图 | 天地图 + 触摸模拟 | 单点/批量标记、42px 控件、竖屏 300px / 横屏 220px |
| 镜像兼容性 | CI manifest 校验 + 容器运行 | Docker manifest list、APP_VERSION 一致 |
| 桌面端回归 | 768 / 1280 / 1440 截图对比 | 除新增地图设置入口外布局稳定 |
| 文档链接 | README 图片与技术文档 | 均存在 |

### 11.6 本次复核后的残余风险

1. 无登录、无权限、无限流；公网部署前必须加反向代理认证和限流。
2. 临时导出文件保存在 `/tmp`，没有用户归属校验；依赖随机文件名和 1 小时清理。
3. CSP 仍使用 `'unsafe-inline'`，因为前端脚本内联在模板中；后续应改用 nonce/hash。
4. pandas / NumPy 版本较旧，长期需要升级评估。
5. 浏览器 E2E 尚未纳入 CI，当前仍是开发期脚本。
6. 没有权威控制点基准，GCJ02/BD09 精度只能作为近似参考。
7. 单实例架构不适合多副本共享临时文件；扩容前需要任务队列和对象存储。
8. 天地图 Key 为浏览器端 Key，必须依赖域名白名单和 HTTPS 降低滥用风险。

### 11.7 发布后验证

- 推送标签后确认 GitHub Actions 的 test 与 docker job 成功。
- 确认 GHCR 仅保留 `2.0.3` 及其子 manifest，`latest` 指向 `2.0.3`；`2.0.0`、`2.0.1`、`2.0.2` 已删除。
- 确认 `2.0.3` manifest 类型为 `application/vnd.docker.distribution.manifest.list.v2+json`，无 `unknown/unknown`。
- 通过 `/healthz` 核对运行版本，确认不是 `dev` 或旧版本。
- 确认远端只有预期的 tag / release，无历史构建镜像残留。
- 发现未同步文档时，直接更新 README、CHANGELOG 或本文档，不积压到下次发布。

---

## 12. 参考资料

项目依赖、算法来源和地图服务参考见 README 的「参考项目与资料」章节，主要包括：

- PROJ / pyproj / EPSG.io
- coordTransform_py / eviltransform
- Flask / pandas / NumPy / openpyxl / Gunicorn
- Bootstrap / Leaflet / 天地图

README 入口：[`README.md`](../README.md)

更新记录：[`CHANGELOG.md`](../CHANGELOG.md)
