# 多客户 / 多站工作区约定

把「用户发资料 → 提炼成 Karpathy 知识库 → 建多个站」这件事,组织成一个**私有工作区**。
一个客户一文件夹,客户下每个网站各自独立子文件夹。用 `scripts/init_workspace.py` 搭骨架。

## 为什么工作区必须和 skill 分开(安全红线)

skill 包(本仓库)是**公开**的、只读的、软链挂各 AI loader;工作区放客户原始资料、真实
联系方式、真实站点 key,是**私有 PII**。**两者绝不能混**:

- ✅ 工作区放在 skill 包外(默认约定 `~/allincms-workspace`,或用户任选一个私有文件夹);
- ✅ 工作区放进**独立私有仓**或 `.gitignore`,绝不 commit 进公开的 skill 仓;
- ❌ 把资料丢进 skill 文件夹再 `git push` = 客户 PII 泄漏到公网、不可逆。

`init_workspace.py` 会拒绝把工作区建在 skill 包内,工作区 README 顶部也有醒目警告。

## 目录结构

```
<workspace>/                             # 私有,skill 包外
  README.md                              # 索引:客户 / 网站 / 线上 siteKey / URL / 状态
  clients/
    <client-slug>/                       # 一客户一文件夹
      brief.md                           # 客户总览
      raw/                               # Karpathy raw:原始资料,只增不改
      wiki/                              # Karpathy wiki:提炼的【客户级】知识(跨该客户所有站复用)
        company.md  brand.md  contact.md  products/
      sites/
        <site-slug>/                     # 每个网站一个独立子文件夹
          brief.md                       # 本站定位
          source-wiki/                   # 本站 source wiki(客户 wiki 子集 + 站定制)
          package/                       # 确认的内容包
          run/                           # build 续跑态(本站的持久 run folder)
          residue-blacklist.json         # 本站残留黑名单(改造模式用)
          live.md                        # 上线记录:siteKey / URL / 日期 / 验收
```

## 客户级共享 vs 站级独立(一客户多站的核心)

| 放**客户级**(共享,改一次全站用) | 放**站级**(独立,站间隔离) |
|---|---|
| 公司介绍、品牌调性、真实联系方式 | 本站选哪些产品、写什么文案 |
| 原始资料存档(raw)、可跨站复用的产品知识 | 目标 URL / SEO / source-wiki / 内容包 / build 状态 / 残留黑名单 / 上线记录 |

一个客户开多个站,通常是按**产品线 / 市场 / 语言 / 渠道**分站:公司与联系方式一套(录一次),
产品组合与文案各自(站间隔离)。客户级共享消灭重复录入,站级独立保证站间不串味。

## Karpathy 分层怎么落

- **raw 只增不改**:发来的资料原样存档;要纠错就新增更正件,不改原件——保证每条知识可回溯到来源。
- **wiki 演化**:AI 把 raw 提炼成结构化 markdown;每条知识标 `sourceRef`(来自哪份 raw),缺口标 gap,绝不编造。
- 这条链的下游正好接 `check_content_quality.py`(发布前查"每字段可追溯、不占位、不幻觉")。

## 和 run folder / run-mode / 质量闸的关系

- **本站 run folder** = `sites/<site>/run/`。把它作为 `--output-dir` 传给各 helper,或把
  `ALLINCMS_RUN_HOME` 指向它,build 产物就落在这个站内、跨会话可续跑。多站各跑各的、互不干扰。
- **run-mode**:每站独立。新建站 `from_scratch`(残留闸自动 ON);改造已有模板站
  `template_conversion`;日常更新自有干净站 `incremental_update`。用 `resolve_run_mode.py` 定,
  已有站要问用户(见其 confirmationPrompt)。
- **残留黑名单**:改造某站前,把那个站的旧内容指纹填进 `sites/<site>/residue-blacklist.json`,
  发布后喂给 `check_template_residue.py` 全站扫。

## init 脚本用法

```bash
# 1) 建工作区(一次)
python3 skills/allincms-bulk-content-upload/scripts/init_workspace.py --action init-workspace --root ~/allincms-workspace
# 2) 新客户
python3 .../init_workspace.py --action new-client --root ~/allincms-workspace --client acme-rf
# 3) 客户下每个网站
python3 .../init_workspace.py --action new-site --root ~/allincms-workspace --client acme-rf --site eu-store
```

脚本**绝不覆盖**已存在的 client/site 目录(保护你已放进去的资料),slug 强制 kebab-case,新建站前要求客户已存在,并把每个站登记进 README 索引。

## 安全红线(重申)

- 工作区私有,绝不进公开 skill 仓;真实联系方式只放客户 `wiki/contact.md` 一处,产品/文章引用它,不各处重录。
- 本地文件夹名(slug)≠ 线上 siteKey;两者映射记在 README 索引里。
- skill 若要把某客户经验沉淀成**全局可复用知识**,必须脱敏后才回流,绝不把客户 PII / 真实 siteKey 带进公开 skill。
