---
title: "运行时文件夹结构 v2（四层物理分离）"
description: "母库知识/工具代码/客户私有数据/会话 scratch 四层物理分离的结构约定；解决'每次清理'残留问题。"
type: "meta"
status: "Adopted（迁移已执行 2026-08-30；绑定任务卡 id-0073 已立项）"
owner: "AI"
created: "2026-08-30"
last_updated: "2026-08-30"
doc_id: "id-0072"
sources: ["用户结构诉求 2026-08-30", "残留实测（217 /tmp 文件 + 64 tracked 修改 + skill 仓 dirty）"]
related: ["AGENTS.md", "in-repository-agency-runtime-model.md"]
visibility: "public"
redaction_status: "safe-to-publish"
redaction_note: "仅结构规则与统计数，无凭据/客户数据；fluxpedal 为 allowlist synthetic 示例品牌"
---
# 运行时文件夹结构 v2

## 问题（实测）
1. 母库根混四类物：tracked 知识 + customer-runtime/ + tmp/fluxpedal-site（未 ignore 未 tracked 的静态站产物）+ dist/（已 ignore）。注：REVIEW-RECORDS 实为 tracked 治理记录（7 文件），不是运行残留——不迁。
2. 客户实战改脏母库：64 个 tracked 修改（41 工具 + 23 wiki/docs），每次发布前人工分拣。
3. /tmp 成黑洞：217 个跨会话散落文件（chunk/HTML/探测脚本），无分区无 TTL，"每次清理"真凶。
4. 工具 CWD 残留：contact-scan/audit-html 写相对路径（已修：SCRATCH_DIR，site_pipeline.py）。

## 目标结构（四层物理分离）
```
~/Work/01_Data/
├── 701_kecheng/            # 母库=纯可发布知识+工具（git；保持干净）
├── 701_runtime/            # 客户运行区（独立物理根；本地私有；不进公开仓）
│   ├── 00_shared/interface-kit/   # 工具包**当前权威副本就在 runtime**（母库 tracked 无 interface-kit、dist/ 无同步源——"母库 dist 同步"是待建管线，见待办①）
│   ├── 10_clients/<client>/       # 每客户私有（TASK/HANDOFF/70_evidence）
│   ├── 20_scratch/<YYYY-MM-DD>/   # 结构化 scratch（chunk/HTML/flight/探测脚本；>7 天整目录删）
│   │                                 #   ⚠️ TTL 豁免闸门：凡被 TASK/HANDOFF/issues 引用的 scratch（如 8/12 artifacts 基线、chunk action id 证据）必须先 promote 进任务 70_evidence 再清——promote-to-70_evidence 闸门，引用检查先行（flash 实锤：5 个客户状态文件引 chunk、/tmp 路径）
│   └── 99_tmp/                    # 纯临时（随时清空）
```

## 规则
0. **adapter 脏源承认（根因未隔离）**：sub-libraries/ADAPTERS 是 tracked 且客户实战必改（fluxpedal 当天刚需改适配器即证）——mv customer-runtime 不解决"母库被改脏"复发；工具改动必须走当日 release 快速通道或 runtime-override，不靠清理。
1. 母库只读不改；改知识走 release 流程，不混客户活。
2. 客户数据全落 runtime/10_clients；TASK.json/HANDOFF/70_evidence 是唯一状态真源。
3. 会话垃圾全落 runtime/20_scratch/<日期> 或 SCRATCH_DIR；按目录删，不按文件清。
4. /tmp 只留 token 与真临时文件。
5. 工具产物必须走 SCRATCH_DIR（环境变量），禁止 CWD 依赖写入。
6. 迁移方式（已授权并于 2026-08-30 执行；TERRA 六条件已核备）：
   ① 先修 .gitignore：加无斜杠行 `/customer-runtime`（实证：尾斜杠模式不匹配软链，软链会被 git add -A 误提交为 symlink blob）——**已修 2026-08-30**。
   ② 整目录**相对**软链（标记为 legacy shim 过渡层）：`ln -s ../701_runtime <母库根>/customer-runtime`（相对链以链接所在目录为锚，整树搬迁仍有效；**禁用 00_shared 变体**——运行区内部绝对引用指向 10_clients，只链 00_shared 会全断）。同时 `mv tmp/fluxpedal-site ../701_runtime/10_clients/fluxpedal-site/`（静态站产物归客户区）。
   ③ **顺序敏感（先 mv 后 mkdir）**：`ls ../701_runtime` 必须不存在 → **先** `mv customer-runtime ../701_runtime/`（整目录改名，此时 10_clients/00_shared 已就位）→ **再** `mkdir -p ../701_runtime/20_scratch ../701_runtime/99_tmp` → 再 `mv tmp/fluxpedal-site ../701_runtime/10_clients/fluxpedal-site/`（此时目标父目录已存在）。**若先 mkdir ../701_runtime 再 mv，customer-runtime 会被套成 701_runtime/customer-runtime/ 子目录**。同卷 rename 原子，无需备份副本。
   ④ 迁后验证（**绝对路径**，避免 cwd 依赖）：`python3 -c "import os;print(os.path.realpath('/Users/tony/Work/01_Data/701_kecheng/customer-runtime'))"` 必须输出 `/Users/tony/Work/01_Data/701_runtime`；`ls /Users/tony/Work/01_Data/701_kecheng/customer-runtime/00_shared/interface-kit/site_pipeline.py` 经软链可达；`git -C /Users/tony/Work/01_Data/701_kecheng status --short | grep customer-runtime` 必须为空。
   ⑤ 64 tracked 修改全为知识升级（TERRA 8 文件抽查 0 客户残留）→ 走 release 分拣（需用户授权，不裸 push）；untracked 剔除 `.tmp-dbg.mjs`/`tmp/`/`.DS_Store`。
   ⑥ skill 仓 3 文件 commit；本文档入库。（后续 2026-08-30：skill 仓整体封存，安装壳合并进母库 SKILL-INSTALL/，见当日日志与母库 CHANGELOG。）
   **执行序（显式，一次复制可跑；在母库根执行）**：
   ```bash
   cd /Users/tony/Work/01_Data/701_kecheng
   ls ../701_runtime 2>/dev/null && { echo "目标已存在，中止"; exit 1; }   # 前置闸门 A1
   [ "$(df /Users/tony/Work/01_Data/701_kecheng | tail -1 | awk '{print $1}')" = "$(df /Users/tony/Work/01_Data | tail -1 | awk '{print $1}')" ] || { echo "跨设备，mv 非原子，中止"; exit 1; }  # 闸门 A2 同卷断言
   mv customer-runtime ../701_runtime                                        # ① 整目录改名（原子）
   mkdir -p ../701_runtime/20_scratch ../701_runtime/99_tmp                  # ② 再建 scratch（顺序！）
   mv tmp/fluxpedal-site ../701_runtime/10_clients/fluxpedal-site            # ③ 静态站归客户区
   [ ! -e customer-runtime ] && ln -s ../701_runtime customer-runtime        # ④ 前置闸门 B：原目录必须已不存在
   python3 -c "import os;print(os.path.realpath('/Users/tony/Work/01_Data/701_kecheng/customer-runtime'))"  # ⑤ = /Users/tony/Work/01_Data/701_runtime
   ls customer-runtime/00_shared/interface-kit/site_pipeline.py              # ⑥ 经软链可达
   git status --short | grep customer-runtime || echo "OK: git 无条目"       # ⑦ 无输出=通过
   ```
   **回滚一句话**：`rm customer-runtime && mv ../701_runtime customer-runtime`（软链未建则直接反向 mv）。
   **警告 1（删链）**：迁后软链是运行必需品——运行区内部绝对引用（TASK.json/media-manifest 等）全部经旧路径解析，**删链=运行区全断**。
   **警告 2（整树搬迁）**：运行区 11 个文件含 `701_kecheng/customer-runtime` **绝对路径**引用（<client-task>-fast-run TASK.json/image-index/media-manifest、<client-task> HANDOFF、internal-allincms-test 系列）——相对软链随母库整树走不断，但这 11 处绝对引用**在整树改名/搬迁后全断**；迁后应统一改 $RUNTIME_ROOT 或相对锚（与待办 RUNBOOK 路径约定同批）。

## 待办
- [x] **① interface-kit 真源已立项**（绑定条款履行）：任务卡 id-0073（DoD/步骤/期限 2026-09-06）
- [x] **迁移已执行**（2026-08-30 17:14）：7/7 步通过（闸门 A1/A2/B + realpath 断言 + 软链可达 + git 无条目）；功能级验证通过（registry VERIFY PASS / 工具语法 OK / dry-run 连 API 成功 / 站点 200）；母库根已纯净（tmp/ 已清，pdfs 归 runtime/90_archive）
- [x] 用户授权迁移 + 软链（2026-08-30 已履行；六条件核备：①gitignore ②相对链 ③701_runtime 先验 ④realpath ⑤64 分拣 ⑥skill commit）。绑定条款（TERRA X3）与待办①同日履行
- [ ] 母库 64 个 tracked 修改按 release 流程分拣（TERRA 8 文件抽查全=知识升级；不裸 push，需用户授权）；untracked 剔除 .tmp-dbg.mjs/tmp//.DS_Store
- [ ] ~/.agents/skills 仓 3 个脏文件 commit（TERRA 判合规；.git 目录实证存在——flash-1 误报"无 git 仓"已核销）
- [x] .DS_Store 加 .gitignore（已忽略）；RUNBOOK 路径约定已改 $RUNTIME_ROOT（2026-08-30）
