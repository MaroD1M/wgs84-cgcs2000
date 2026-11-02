# 更新记录

## v2.0.2 - 2026-11-01

- 发布镜像改为 Docker manifest list，关闭 provenance/SBOM attestation，修复部分群晖 Container Manager / 旧版 Docker 拉取时报 `manifest unknown` 的兼容性问题。
- CI 增加发布后校验：确认 manifest 类型、无 `unknown/unknown` 条目，并运行镜像核对 `APP_VERSION`。
- master/PR 只跑测试，只有标签构建镜像，减少无效构建产物。
- README 增加群晖 Docker 版本排查和“SSH 可拉取但项目失败”的处理方式。
- 保留 `2.0.0`、`2.0.1` 正式镜像。

## v2.0.1 - 2026-11-01

- 修复 GHCR 清理策略：保留所有正式 `X.Y.Z` 版本，只删除无正式版本标签的构建镜像，避免固定版本用户因新版本发布而无法拉取。
- `/healthz` 增加运行版本字段，地图设置面板显示应用版本，便于排查镜像标签与运行实例不一致。
- README 增加 Git 标签与镜像标签对照，以及 `manifest unknown` 拉取失败排查。
- 更新技术文档、Compose 注释和预览图。

## v2.0.0 - 2026-11-01

- 在线地图改为仅支持天地图，移除 OpenStreetMap 和自定义 XYZ 瓦片。
- 新增地图设置面板：浏览器端天地图 Key 保存到 localStorage，服务端 `TIANDITU_KEY` 作为默认值。
- 无 Key、Key 无效、域名白名单错误和瓦片加载失败时提供明确提示。
- 保留并完善移动端响应式布局、卡片式结果表格和触控优化。
- 历史提交、标签、Release 和旧 GHCR 镜像完成清理。
