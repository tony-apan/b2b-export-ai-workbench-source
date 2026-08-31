#!/usr/bin/env python3
"""AllinCMS 单页模块构建器（Blocks Library）—— 纯 JSON 构造，跨平台零依赖。
每个函数返回 document.elements 的单条记录 {type,props,children:[],anchorId}，
也可用作 build_page_document 的组装单元。配合 interface-kit/allincms_api.py 的 save_home 提交。"""
import json

def media(name, url, alt=None):
    v={"name":name,"type":"image","source":"url","url":url}
    if alt: v["alt"]=alt
    return {"type":"image","value":v}

def target_custom(href): return {"type":"custom","href":href}
def target_anchor(anchor_id): return {"type":"action","anchorId":anchor_id}

def el(block_type, props):
    return {"type":block_type,"props":props,"children":[],"anchorId":None}

# ---------- 页面区块 ----------
def hero(eyebrow,title,description,img_name,img_url,secondary_note="",media_caption="",kicker="",meta="",product_name="",product_desc="",price="",actions=None,service_items=None,campaign_pills=None):
    """actions/service_items/campaign_pills 建议显式传（不传服务端回填模板默认内容！）。
    actions=[(label, href, variant)]；service_items=[(label, value)]；campaign_pills=[(label, value)]"""
    act=[{"label":l,"target":target_custom(h),"variant":v} for (l,h,v) in (actions or [])]
    svc=[{"label":l,"value":v} for (l,v) in (service_items or [])]
    pills=[{"label":l,"value":v} for (l,v) in (campaign_pills or [])]
    return el("hero-commerce",{
        "eyebrow":eyebrow,"title":title,"description":description,"secondaryNote":secondary_note,
        "media":media(img_name,img_url),"fit":"cover","mediaCaption":media_caption,
        "mediaKicker":kicker,"mediaMeta":meta,"productName":product_name,
        "productDescription":product_desc,"productPriceLabel":price,
        "actions":act,"serviceItems":svc,"campaignPills":pills})

def carousel(slides, service_items=None):
    return el("carousel-campaign",{"slides":slides,"serviceItems":service_items or []})

def slide(eyebrow,title,description,img_name,img_url,price,product,primary_label,primary_href,secondary_label,secondary_href,show_mask=True):
    return {"eyebrow":eyebrow,"title":title,"description":description,
            "media":media(img_name,img_url),"fit":"cover","showMask":show_mask,
            "price":price,"product":product,
            "primaryLabel":primary_label,"primaryTarget":target_custom(primary_href),
            "secondaryLabel":secondary_label,"secondaryTarget":target_custom(secondary_href)}

def service_item(icon,title,description): return {"icon":icon,"title":title,"description":description}

def category_grid(section_label,headline,supporting,items,columns=3):
    return el("category-showcase-grid",{"sectionLabel":section_label,"headline":headline,
        "supportingCopy":supporting,"items":items,"columnCount":columns})

def category_item(name,description,img_name,img_url,href):
    return {"name":name,"description":description,"media":media(img_name,img_url),"fit":"cover","target":target_custom(href)}

def feature_grid(eyebrow,heading,description,rows,columns=3):
    return el("feature-grid-proof",{"eyebrow":eyebrow,"heading":heading,"description":description,
        "proofRows":rows,"columnCount":columns})

def feature_row(label,title,description,meta,action_label,href):
    return {"label":label,"title":title,"description":description,"meta":meta,
            "actionLabel":action_label,"target":target_custom(href)}

def product_showcase(label,headline,supporting,merch_note,cta_label,cta_href,list_path="/products",detail_path="/products/{product}",category_slug=""):
    return el("featured-product-list-showcase",{
        "sectionLabel":label,"headline":headline,"supportingCopy":supporting,
        "merchandisingNote":merch_note,"ctaLabel":cta_label,"ctaTarget":target_custom(cta_href),
        "productActionLabel":"View product","featuredProductActionLabel":"View featured product","fit":"cover",
        "associatedListPage":{"path":list_path,"href":list_path},
        "associatedDetailPage":{"path":detail_path,"href":detail_path},"categorySlug":category_slug})

def product_list(detail_path="/products/{product}",page_size=12,toolbar=True,sort="newest",columns=3):
    return el("full-product-list-filtered",{"associatedDetailPage":{"path":detail_path,"href":detail_path},
        "pageSize":page_size,"showToolbar":toolbar,"sortOrder":sort,"columnCount":columns,
        "productActionLabel":"View product","fit":"cover"})

def material_split(label,headline,supporting,img_name,img_url,notes,action_label,href):
    return el("material-story-split",{"sectionLabel":label,"headline":headline,"supportingCopy":supporting,
        "media":media(img_name,img_url),"fit":"cover","notes":notes,
        "actionLabel":action_label,"actionTarget":target_custom(href)})

def material_note(title,description): return {"title":title,"description":description}

def proof_quotes(label,headline,rating,reviews,columns=3):
    return el("social-proof-quotes",{"sectionLabel":label,"headline":headline,"ratingLabel":rating,
        "reviews":reviews,"columnCount":columns})

def review(quote,name,detail): return {"quote":quote,"name":name,"detail":detail}

def news_list(label,headline,supporting,cta_label,cta_href,list_path="/posts",detail_path="/posts/{post}",category_slug=""):
    return el("featured-news-list-editorial",{"sectionLabel":label,"headline":headline,"supportingCopy":supporting,
        "digestLabel":"Latest stories","featureLabel":"Featured story","ctaLabel":cta_label,"ctaTarget":target_custom(cta_href),
        "associatedListPage":{"path":list_path,"href":list_path},
        "associatedDetailPage":{"path":detail_path,"href":detail_path},
        "categorySlug":category_slug,"sortOrder":"newest","fit":"cover",
        "postActionLabel":"Read","featureActionLabel":"Read story"})

def faq(label,headline,supporting,support_note,items):
    return el("faq-accordion",{"sectionLabel":label,"headline":headline,"supportingCopy":supporting,
        "supportNote":support_note,"items":items})

def faq_item(question,answer): return {"question":question,"answer":answer}

def newsletter(label,headline,supporting,email_ph="Email address",submit="Subscribe",fine="Product news only. Unsubscribe anytime."):
    return el("newsletter-inline",{"sectionLabel":label,"headline":headline,"supportingCopy":supporting,
        "emailPlaceholder":email_ph,"submitLabel":submit,"finePrint":fine})

def contact_split(eyebrow,title,description,resp_title,resp_desc,email,phone,address,hours,form_card_eyebrow="Inquiry intake",form_card_title="Send the details",form_card_desc="Share a few details about your request so we can send a useful reply."):
    return el("contact-form-split",{"eyebrow":eyebrow,"title":title,"description":description,
        "responseTitle":resp_title,"responseDescription":resp_desc,
        "emailLabel":"Email","emailValue":email,"phoneLabel":"Phone","phoneValue":phone,
        "addressLabel":"Office","addressValue":address,"hoursLabel":"Hours","hoursValue":hours,
        "formCardEyebrow":form_card_eyebrow,"formCardTitle":form_card_title,"formCardDescription":form_card_desc})

# ---------- 公司页 / 联系页区块（模板标准组件，字段严格对齐模板页 schema）
# 注意：未提供的展示字段会被服务端用模块默认值回填（含模板文案！），显式传空/自定义以覆盖 ----------
def breadcrumb():
    return el("breadcrumb-inline", {})

def about_intro(eyebrow,title,description,body,img_name,img_url,fit="cover",caption=""):
    return el("about-intro-media",{"eyebrow":eyebrow,"title":title,"description":description,
        "body":body,"media":media(img_name,img_url),"fit":fit,"caption":caption})

def company_story(section_label,headline,lead,body,img_name,img_url,fit="cover",note="",note_label=""):
    return el("company-story-media",{"sectionLabel":section_label,"headline":headline,
        "lead":lead,"body":body,"media":media(img_name,img_url),"fit":fit,
        "note":note,"noteLabel":note_label})

def company_stats(section_label,headline,description,stats,column_count=None):
    p={"sectionLabel":section_label,"headline":headline,"description":description,"stats":stats}
    if column_count: p["columnCount"]=column_count
    return el("company-stats-grid",p)

def stat(value,label,description): return {"value":value,"label":label,"description":description}

def company_values(section_label,headline,description,values,column_count=None):
    p={"sectionLabel":section_label,"headline":headline,"description":description,"values":values}
    if column_count: p["columnCount"]=column_count
    return el("company-values-grid",p)

def value_item(title,description): return {"title":title,"description":description}

def company_team(section_label,headline,description,members,column_count=None,photo_fit="cover"):
    p={"sectionLabel":section_label,"headline":headline,"description":description,
       "members":members,"photoFit":photo_fit}
    if column_count: p["columnCount"]=column_count
    return el("company-team-grid",p)

def team_member(name,role,bio,photo=None): return {"name":name,"role":role,"bio":bio,"photo":photo}

def contact_header(eyebrow,title,description,items):
    return el("contact-header-summary",{"eyebrow":eyebrow,"title":title,
        "description":description,"items":items})

def info_item(label,value): return {"label":label,"value":value}

def contact_info(section_label,headline,description,items,column_count=None,social_links=None):
    """social_links 必须显式传（默认 []）：不传则服务端回填模板默认链接 Instagram/LinkedIn 裸域名假链接！"""
    p={"sectionLabel":section_label,"headline":headline,"description":description,
       "items":items,"socialLinks":[{"label":l,"href":u} for (l,u) in (social_links or [])]}
    if column_count: p["columnCount"]=column_count
    return el("contact-info-grid",p)

def contact_info_item(type_,label,value,detail): return {"type":type_,"label":label,"value":value,"detail":detail}

def location_map(section_label,headline,address,description,lat,lng,zoom=14,map_mode="m",url="",details=None):
    return el("location-map-interactive",{"sectionLabel":section_label,"headline":headline,
        "address":address,"description":description,"latitude":lat,"longitude":lng,
        "zoom":zoom,"mapMode":map_mode,"url":url,"details":details or []})

def map_detail(label,value): return {"label":label,"value":value}

# ---------- 全局区块（globals.elements） ----------
def _nav_entry(label, href, children):
    return {"label": label, "target": target_custom(href),
            "children": [_nav_entry(l, h, c) for (l, h, c) in children]}

def header(site_title,tagline,navigation,cta_label="Get a Quote",cta_anchor="contact-form-dialog",logo=None):
    """navigation: [(label, href, [(child_label, child_href, [])...])...]。
    children 必须递归转 dict，否则服务端丢弃并回填模板默认（如 "Bags"）。"""
    nav=[_nav_entry(l,h,c) for (l,h,c) in navigation]
    return el("header-dropdown",{"siteTitle":site_title,"tagline":tagline,"logoMedia":logo,"logoFit":"cover",
        "logoTarget":target_custom("/"),"navigation":nav,
        "ctaLabel":cta_label,"ctaTarget":target_anchor(cta_anchor)})

def footer(brand,kicker,description,columns,social_links=None,copyright="",system_note=""):
    cols=[{"title":t,"links":[{"label":l,"target":target_custom(h)} for (l,h) in links]} for (t,links) in columns]
    return el("footer-columns",{"brand":brand,"kicker":kicker,"description":description,"columns":cols,
        "socialLinks":[{"label":l,"target":target_custom(u)} for (l,u) in (social_links or [])],
        "copyright":copyright,"systemNote":system_note})

def contact_dialog(title,description,eyebrow="Product support",form_slug="contact-inquiry",close_label="Close contact dialog",anchor_id="contact-form-dialog"):
    """anchor_id 必须与 header() 的 cta_anchor 一致：anchorId 为 null 时公开站渲染器
    静默丢弃整个弹窗元素（CTA 点击只改 URL hash，零报错）——ISS-094 实证 2026-09-01。"""
    e = el("contact-dialog-form-modal",{"title":title,"description":description,"eyebrow":eyebrow,
        "closeLabel":close_label,"formSlug":form_slug})
    e["anchorId"] = anchor_id
    return e

def social_float(url,label="WhatsApp",brand="whatsapp"):
    return el("social-floating-button",{"brand":brand,"url":url,"label":label,"showLabel":False,"position":"bottom-right"})

# ---------- 页面组装 ----------
def page_document(elements_list, globals_extra=None):
    """elements_list: [(key, element), ...]；自动加 page-root 并保留顺序。"""
    els={}
    order=[]
    for k,e in elements_list:
        els[k]=e; order.append(k)
    els["page-root"]={"type":"page-root","props":{"className":None},"children":order,"anchorId":None}
    return {"root":"page-root","elements":els}

if __name__=="__main__":
    # 自检：构建一个标准 Home，输出 JSON 供提交
    doc=page_document([
        ("carousel-campaign-1",carousel([slide("12h hot 24h cold","Keep it hot.","desc","img1","http://x/a.jpg","From $29","Product","Shop","/products","Guide","/posts")], [service_item("truck","Ship","Fast")])),
        ("hero-commerce-1",hero("New","Title","Desc","img1","http://x/a.jpg")),
        ("faq-accordion-1",faq("Questions","FAQ","sub","note",[faq_item("Q1","A1")])),
        ("contact-form-split-1",contact_split("Contact","Tell us","desc","after","reply","e@x.com","+1","Addr","9-5")),
    ])
    print("build ok, elements:",list(doc["elements"].keys()))
