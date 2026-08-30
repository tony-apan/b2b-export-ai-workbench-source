# 建站必备内容清单（AI 提前梳理，逐项映射真实内容）

> 用途：建站前对照本清单规划内容；每项标注来源（客户资料/CC 素材/demo 占位）。全站内容 = 下列模块字段全填。
> 工具：brief.json（templates/brief-schema.json）→ site_pipeline.py validate；页面组装见 MODULES.md。

## A. 品牌层（导航/首页/全站）
| 项 | 字段 | 说明/示例 |
|---|---|---|
| 品牌名 | header.siteTitle / footer.brand | 显示名（如 Demo） |
| 品牌标语 | header.tagline / footer.kicker | 一句话（如 "Touring kayaks"） |
| 站名（SEO title 前缀） | site.name | 如 "Demo Site" |
| 主 CTA 文案 | header.ctaLabel | "Get a Quote"（弹窗表单） |
| 社媒账号 | footer.socialLinks | 无则显式 []（防模板假链接） |
| 版权/细则 | footer.copyright / systemNote | 含 demo 标注则列入替换清单 |

## B. 分类体系
| 项 | 说明 |
|---|---|
| 产品分类 1-2 个 | contentType:'products'，slug 建议 product- 前缀，挂接产品 |
| 文章分类 1-2 个 | contentType:'posts'（模板已有 Buying Guides 等可复用）；slug 勿与模板重复（先读 categoryOptions） |
| 标签 3 个左右 | contentType:'posts'，slug 同上注意模板已有项 |

## C. 产品（每个产品一张卡：字段全填）
| 项 | 字段 | 说明 |
|---|---|---|
| 名称 | name | 型号+品类（"Demo Product Two-Seat Touring Kayak"） |
| slug | slug | 小写横线；**create 后 draft slug 会变时间戳，publish 时 payload 必须带正确 slug** |
| 描述 | description | 1-2 句卖点 + 素材来源声明（demo 标注） |
| 规格 5-8 项 | specifications[{key,value}] | 尺寸/容量/材质/重量/结构/认证等（采购决策字段） |
| 价格标签 | productPriceLabel | "From $1,499"（无价格可不填） |
| 主图 | media（**扁平格式** {name,alt,type,source,url}） | 必需；上传后资产 URL 带扩展名 |
| 多图 | mediaList | 可空 |
| 分类 | categories:[产品分类id] | **不可用文章分类** |
| 正文 | content（Slate） | 可空；**有正文才显示正文区**（空则无正文区/不显示空态） |

## D. 文章（每篇：buying guide / material care / how-to 类）
| 项 | 字段 | 说明 |
|---|---|---|
| 标题 | title | 有 buyer intent（"How to Choose..."） |
| slug | slug | 同上注意 publish 纠正 |
| 摘要 | excerpt | 列表页卡片显示 |
| 封面图 | coverImage | 扁平格式 |
| 正文 3 段起 | content: Slate [{type:heading/paragraph, children:[{text}]}] | **只使用验证过的块**（heading/paragraph；link/图片/列表块未实测勿用） |
| 分类/标签 | categories / tags | id 数组 |

## E. 公司页（About：6 模块字段）
| 模块 | 字段 |
|---|---|
| about-intro | eyebrow/title/description/body + media + fit + caption（caption 显式传防回填） |
| company-story | sectionLabel/headline/lead/body + media + note/noteLabel（显式） |
| company-stats | stats ×3-4 {value,label,description} |
| company-values | values ×2-3 {title,description} |
| company-team | members ×2-3 {name,role,bio}（name 用客户授权实名或角色化"Customer Care"档） |

## F. 联系页（Contact：5 模块字段）
| 模块 | 字段 |
|---|---|
| contact-header | eyebrow/title/description + items[{label,value}]（响应时间/适用场景） |
| contact-info | items[{type:email/phone/address,label,value,detail}] + **socialLinks 显式 []** |
| location-map | address + lat/lng + zoom + details[{label,value}] |
| contact-form | 与 info 同值（邮箱/电话/地址/营业时间）；表单表单库联系 initialForms.contact-inquiry |

## G. 首页 11 模块（可选裁剪）
carousel(2 slides) / category-grid(3 卡：分类/指南/批发) / hero(全字段+actions+serviceItems+campaignPills 显式) /
features(3) / products showcase / materials / proof(3 评价) / news / faq(3) / newsletter / contact-split

## H. 素材
| 项 | 说明 |
|---|---|
| 产品图每产品 1-2 张 | 客户自有最优；CC 素材记录 author+license（manifest） |
| 公司页图 1-2 张 | 同上 |
| 图片要求 | URL 带扩展名；alt 必填；避免同页重复用同一张图（分类卡/hero 错开） |

## I. 上线前替换清单（demo 值 → 真实值）
1. 邮箱（**影响表单提交链路**）2. 电话 3. 地址 4. WhatsApp/社媒 URL 5. footer demo 标注 6. 产品/文章正文 synthetic 声明 7. 地图坐标

## J. 勿漏检项（对抗经验）
- 空态扫描：`No content is available yet|No items yet|No results|coming soon`（多为 related 推荐区无数据或正文区空——**目录单品时删详情页 related 模块**）
- 首页 H1 结构、导航下拉指向真实分类、分类卡勿重复同图
- readback diff 仅无害回填；globals 变更 7 页重交；产品=产品分类 文章=文章分类
