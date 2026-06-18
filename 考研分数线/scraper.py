# -*- coding: utf-8 -*-
"""
考研分数线爬虫 - 增强版多源数据采集
目标: 985/211/热门双非高校工科专业近5年考研数据
数据源: 研招网 | 中国教育在线 | 考研帮 | 考研分数线网 | 考研网 | 各校研究生院 | GitHub | 新浪教育 | 腾讯教育 | 考研村 | 考满分 | 文都教育 | 海文考研 | 各省教育考试院 | 考研调剂网
策略: 按优先级依次尝试，哪个有响应用哪个，失败自动fallback
"""

import json, os, re, time, sys
from datetime import datetime
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "data.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
}
TIMEOUT = 20

SCHOOLS_985 = ["北京大学","清华大学","复旦大学","上海交通大学","浙江大学","中国科学技术大学",
    "南京大学","西安交通大学","哈尔滨工业大学","武汉大学","华中科技大学","中山大学",
    "四川大学","南开大学","天津大学","山东大学","东南大学","吉林大学","厦门大学",
    "同济大学","北京航空航天大学","北京理工大学","大连理工大学","东北大学","西北工业大学",
    "华南理工大学","重庆大学","中南大学","湖南大学","电子科技大学","兰州大学",
    "中国海洋大学","华东师范大学","中国农业大学","西北农林科技大学","中央民族大学",
    "国防科技大学","中国人民大学","北京师范大学"]
SCHOOLS_211 = ["北京科技大学","北京交通大学","北京邮电大学","北京化工大学","北京工业大学",
    "华北电力大学","南京航空航天大学","南京理工大学","哈尔滨工程大学","西安电子科技大学",
    "武汉理工大学","西南交通大学","华东理工大学","上海大学","苏州大学","河海大学",
    "中国矿业大学","郑州大学","合肥工业大学","福州大学","南昌大学","暨南大学",
    "广西大学","西南大学","云南大学","西北大学","长安大学","太原理工大学",
    "大连海事大学","辽宁大学","东北师范大学","江南大学","安徽大学","海南大学",
    "贵州大学","新疆大学","宁夏大学","青海大学","内蒙古大学","河北工业大学"]
SCHOOLS_HOT = ["中国科学院大学","南方科技大学","上海科技大学","深圳大学",
    "杭州电子科技大学","南京邮电大学"]
ALL_SCHOOLS = SCHOOLS_985 + SCHOOLS_211 + SCHOOLS_HOT
ALL_SCHOOLS_META = {s: ("985" if s in SCHOOLS_985 else "211" if s in SCHOOLS_211 else "双非") for s in ALL_SCHOOLS}

# Province mapping for major schools
SCHOOL_PROVINCE = {"北京大学":"北京","清华大学":"北京","复旦大学":"上海","上海交通大学":"上海",
    "浙江大学":"浙江","中国科学技术大学":"安徽","南京大学":"江苏","西安交通大学":"陕西",
    "哈尔滨工业大学":"黑龙江","武汉大学":"湖北","华中科技大学":"湖北","中山大学":"广东",
    "四川大学":"四川","南开大学":"天津","天津大学":"天津","山东大学":"山东","东南大学":"江苏",
    "吉林大学":"吉林","厦门大学":"福建","同济大学":"上海","北京航空航天大学":"北京",
    "北京理工大学":"北京","大连理工大学":"辽宁","东北大学":"辽宁","西北工业大学":"陕西",
    "华南理工大学":"广东","重庆大学":"重庆","中南大学":"湖南","湖南大学":"湖南",
    "电子科技大学":"四川","兰州大学":"甘肃","中国海洋大学":"山东","华东师范大学":"上海",
    "中国农业大学":"北京","西北农林科技大学":"陕西","中央民族大学":"北京",
    "国防科技大学":"湖南","中国人民大学":"北京","北京师范大学":"北京",
    "北京科技大学":"北京","北京交通大学":"北京","北京邮电大学":"北京","北京化工大学":"北京",
    "北京工业大学":"北京","华北电力大学":"北京","南京航空航天大学":"江苏",
    "南京理工大学":"江苏","哈尔滨工程大学":"黑龙江","西安电子科技大学":"陕西",
    "武汉理工大学":"湖北","西南交通大学":"四川","华东理工大学":"上海","上海大学":"上海",
    "苏州大学":"江苏","河海大学":"江苏","中国矿业大学":"江苏","郑州大学":"河南",
    "合肥工业大学":"安徽","福州大学":"福建","南昌大学":"江西","暨南大学":"广东",
    "广西大学":"广西","西南大学":"重庆","云南大学":"云南","西北大学":"陕西",
    "长安大学":"陕西","太原理工大学":"山西","大连海事大学":"辽宁","辽宁大学":"辽宁",
    "东北师范大学":"吉林","江南大学":"江苏","安徽大学":"安徽","海南大学":"海南",
    "贵州大学":"贵州","新疆大学":"新疆","宁夏大学":"宁夏","青海大学":"青海",
    "内蒙古大学":"内蒙古","河北工业大学":"天津",
    "中国科学院大学":"北京","南方科技大学":"广东","上海科技大学":"上海","深圳大学":"广东",
    "杭州电子科技大学":"浙江","南京邮电大学":"江苏"}

CATEGORIES = [
    {"id":"cs","name":"计算机类","keywords":["计算机","软件","人工智能","智能科学","数据科学","物联网","网络空间安全"]},
    {"id":"mechanical","name":"机械类","keywords":["机械","机器人","车辆","汽车","机电","动力工程","力学"]},
    {"id":"electronic","name":"电子信息类","keywords":["电子","通信","信号","微电子","集成电路","光电","信息工程","电磁场"]},
    {"id":"automation","name":"自动化类","keywords":["自动化","控制","机器人","测控"]},
    {"id":"electrical","name":"电气类","keywords":["电气","电力","电工","能源"]},
    {"id":"civil","name":"土木类","keywords":["土木","建筑","水利","市政","测绘"]},
    {"id":"material","name":"材料类","keywords":["材料","冶金","焊接"]},
    {"id":"chemical","name":"化工类","keywords":["化工","化学工程","制药","生物工程"]},
    {"id":"environment","name":"环境类","keywords":["环境","环保","资源"]},
    {"id":"other","name":"其他工科","keywords":["交通运输","船舶","航空","航天","核科学","安全科学","食品","纺织","轻工"]},
]

def detect_category(name):
    if not name: return "other"
    for cat in CATEGORIES:
        for kw in cat["keywords"]:
            if kw in name: return cat["id"]
    return "other"

def fetch(url, params=None, method='GET', data=None):
    for attempt in range(3):
        try:
            if method == 'POST':
                r = requests.post(url, params=params, data=data, headers=HEADERS, timeout=TIMEOUT, verify=False)
            else:
                r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT, verify=False)
            r.encoding = 'utf-8'
            if r.status_code == 200:
                return r
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
    return None

def parse_number(text):
    if not text: return None
    nums = re.findall(r'\d+\.?\d*', str(text).replace(',','').replace('\u2014',''))
    return float(nums[0]) if nums else None

# ====================================================================
# HELPER: extract score data from various HTML page structures
# ====================================================================
def extract_scores_from_text(body_text, school_name=None):
    """Parse score data from free-form text (e.g. announcements, blog posts)."""
    records = []
    # Try to find lines with "专业" followed by numbers
    lines = body_text.split('\n')
    current_year = 2025
    for line in lines:
        ym = re.search(r'(20\d{2})\s*年', line)
        if ym:
            current_year = int(ym.group(1))
        # Look for patterns like: 计算机科学与技术 350 370 400
        if not any(kw in line for kw in ['专业','方向','工程','科学','技术']):
            continue
        nums = re.findall(r'\b(3[0-9]{2}|4[0-9]{2})\b', line)
        if len(nums) < 2:
            continue
        major_match = re.search(r'([\u4e00-\u9fff]{2,20}(?:工程|技术|科学|方向|理论与应用))', line)
        if not major_match:
            continue
        major = major_match.group(1)
        if len(major) > 25:
            continue
        yr = {"year": current_year, "retestScore": int(nums[0]), "avgScore": int(nums[1])}
        if len(nums) > 2:
            yr["maxScore"] = int(nums[2])
        records.append({"schoolMajorName": major, "subjects": ["思想政治理论","英语一","数学一","专业课"], "years": [yr]})
    return records


def try_extract_score_table(soup, school_name=None, current_year=2025):
    """Try to find score data in any HTML table or list structure."""
    records = []
    if not soup:
        return records

    # Strategy 1: HTML tables
    tables = soup.find_all('table')
    for table in tables[:30]:
        rows = table.find_all('tr')
        if len(rows) < 3:
            continue
        header_text = rows[0].get_text()
        if not any(kw in header_text for kw in ['分数','复试线','复试','录取','专业名称','专业代码','研究方向','政治','外语','业务课']):
            continue
        year = current_year
        ym = re.search(r'(20\d{2})', header_text)
        if ym:
            year = int(ym.group(1))
        for row in rows[1:]:
            cells = row.find_all(['td','th'])
            cell_texts = [c.get_text(strip=True) for c in cells]
            if len(cell_texts) < 2:
                continue
            major_name = cell_texts[0]
            if not major_name or len(major_name) > 30 or major_name in ['专业','专业名称','专业代码','研究方向','合计','备注']:
                continue
            scores = []
            for ct in cell_texts[1:]:
                for n in re.findall(r'\b(3[0-9]{2}|4[0-9]{2}|2[0-9]{2})\b', ct.replace(',','').replace('—','')):
                    scores.append(int(n))
            if not scores:
                continue
            record = {"schoolMajorName": major_name, "subjects": ["思想政治理论","英语一","数学一","专业课"], "years": []}
            yr_data = {"year": year}
            for idx, val in enumerate(scores[:5]):
                if idx == 0: yr_data["retestScore"] = val
                elif idx == 1: yr_data["avgScore"] = val
                elif idx == 2: yr_data["maxScore"] = val
            for ct in cell_texts[1:]:
                rm = re.search(r'([\d.]+)\s*[:：]\s*([\d.]+)', ct)
                if rm:
                    yr_data["retestRatio"] = rm.group(0)
                    yr_data["applicants"] = int(float(rm.group(1)))
                    yr_data["admitted"] = int(float(rm.group(2)))
                    break
            record["years"].append(yr_data)
            records.append(record)

    if records:
        return records

    # Strategy 2: list/div based score listings
    for div in soup.find_all(['div','ul','ol'], class_=re.compile(r'score|fsx|fenshu|list|content|article', re.I)):
        items = div.find_all(['li','div','p'])
        for item in items:
            txt = item.get_text(strip=True)
            nums = re.findall(r'\b(3[0-9]{2}|4[0-9]{2})\b', txt)
            if len(nums) < 2:
                continue
            major_match = re.search(r'([\u4e00-\u9fff]{2,20}(?:工程|技术|科学|方向|理论与应用|学))', txt)
            if not major_match:
                continue
            major = major_match.group(1)
            if len(major) > 25:
                continue
            yr = {"year": current_year, "retestScore": int(nums[0]), "avgScore": int(nums[1])}
            if len(nums) > 2:
                yr["maxScore"] = int(nums[2])
            records.append({"schoolMajorName": major, "subjects": ["思想政治理论","英语一","数学一","专业课"], "years": [yr]})

    if records:
        return records

    # Strategy 3: try extracting from <pre> or <code> blocks
    for tag in soup.find_all(['pre','code','article','section']):
        txt = tag.get_text()
        recs = extract_scores_from_text(txt, school_name)
        if recs:
            return recs

    return records


# ====================================================================
# SOURCE 1: 考研帮 (kaoyan.com) — each school has /slug/fenshu/ pages
# This is the most reliable third-party source with structured data.
# ====================================================================
KAOYAN_SLUGS = {
    "北京大学":"beida","清华大学":"qinghua","浙江大学":"zheda",
    "上海交通大学":"sjtu","复旦大学":"fudan","哈尔滨工业大学":"hagongda",
    "武汉大学":"whu","华中科技大学":"hust","西安交通大学":"xjt",
    "南京大学":"nju","北京航空航天大学":"buaa","同济大学":"tongji",
    "南开大学":"nku","天津大学":"tju","厦门大学":"xmu","中山大学":"sysu",
    "电子科技大学":"uestc","大连理工大学":"dlut","东南大学":"seu",
    "华南理工大学":"scut","重庆大学":"cqu","中南大学":"csu",
    "湖南大学":"hnu","兰州大学":"lzu","东北大学":"neu",
    "西北工业大学":"nwpu","北京理工大学":"bit","中国科学技术大学":"ustc",
    "吉林大学":"jlu","山东大学":"sdu","四川大学":"scu",
    "北京邮电大学":"bupt","西安电子科技大学":"xidian","北京科技大学":"ustb",
    "北京交通大学":"bjtu","南京理工大学":"njust","南京航空航天大学":"nuaa",
    "武汉理工大学":"whut","西南交通大学":"swjtu","华东理工大学":"ecust",
    "上海大学":"shu","苏州大学":"suda","河海大学":"hhu",
    "中国矿业大学":"cumt","郑州大学":"zzu","中国科学院大学":"ucas",
    "深圳大学":"szu","浙江工业大学":"zjut","杭州电子科技大学":"hdu",
    "南京邮电大学":"njupt","重庆邮电大学":"cqupt","广东工业大学":"gdut",
    "上海理工大学":"usst","武汉科技大学":"wust","燕山大学":"ysu",
    "南京工业大学":"njtech","浙江理工大学":"zstu","昆明理工大学":"kmust",
    "西安理工大学":"xaut","长沙理工大学":"csust","成都理工大学":"cdut",
}
def scrape_kaoyan_com():
    """Source 1: 考研帮 kaoyan.com — multiple pages per school."""
    print("  [源1] 考研帮 44校分数线 ...")
    collected = []
    for name, slug in KAOYAN_SLUGS.items():
        sid = re.sub(r'[\(\)（）\s]', '', name)
        # Try multiple pages: main /fenshu/, then specific year pages
        urls_to_try = [
            f"https://www.kaoyan.com/{slug}/fenshu/",
            f"https://www.kaoyan.com/{slug}/fenshu/2025/",
            f"https://www.kaoyan.com/{slug}/fenshu/2024/",
            f"https://www.kaoyan.com/{slug}/fenshu/2023/",
        ]
        for url in urls_to_try:
            try:
                r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, 'html.parser')
                recs = try_extract_score_table(soup, name)
                if recs:
                    for rec in recs:
                        rec["schoolId"] = sid
                    collected.extend(recs)
                    print(f"  [源1] {name}: {len(recs)} 条 (from {url.split('/')[-2]})")
                # Also try sub-links on the page
                for a in soup.find_all('a', href=True)[:20]:
                    txt = a.get_text(strip=True)
                    if re.search(r'20\d{2}', txt) and any(kw in txt for kw in ['分数','复试线','录取']):
                        href = a['href']
                        if href.startswith('/'):
                            href = f"https://www.kaoyan.com{href}"
                        elif not href.startswith('http'):
                            continue
                        try:
                            r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                            if r2.status_code == 200:
                                s2 = BeautifulSoup(r2.text, 'html.parser')
                                sub = try_extract_score_table(s2, name)
                                if sub:
                                    for rec in sub:
                                        rec["schoolId"] = sid
                                    collected.extend(sub)
                                    print(f"    -> 子页 {txt[:20]}: {len(sub)} 条")
                        except:
                            pass
                break  # Stop after first successful URL
            except:
                continue
    print(f"  [源1] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 2: 考研网 chinakaoyan.com — per-province and per-school pages
# ====================================================================
CHINAKAOYAN_PROVINCES = ["beijing","shanghai","tianjin","chongqing","hebei","shanxi","liaoning",
    "jilin","heilongjiang","jiangsu","zhejiang","anhui","fujian","jiangxi","shandong","henan",
    "hubei","hunan","guangdong","guangxi","hainan","sichuan","guizhou","yunnan","xizang",
    "saanxi","gansu","qinghai","ningxia","xinjiang"]
def scrape_chinakaoyan():
    """Source 2: chinakaoyan.com — per-school score pages."""
    print("  [源2] 考研网 chinakaoyan.com ...")
    collected = []
    seen = set()
    for school in ALL_SCHOOLS:
        sid = re.sub(r'[\(\)（）\s]', '', school)
        # Try multiple URL patterns
        patterns = [
            f"https://www.chinakaoyan.com/school/{school}/fenshuxian.shtml",
            f"https://www.chinakaoyan.com/school/{school}/fenshuxian/",
            f"https://www.chinakaoyan.com/school/{school}/",
        ]
        for pattern in patterns:
            try:
                r = requests.get(pattern, headers=HEADERS, timeout=10, verify=False)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, 'html.parser')
                recs = try_extract_score_table(soup, school)
                if recs:
                    for rec in recs:
                        rec["schoolId"] = sid
                        key = sid + '_' + rec.get("schoolMajorName",'')
                        if key not in seen:
                            seen.add(key)
                            collected.append(rec)
                    print(f"  [源2] {school}: {len(recs)} 条")
                    break
                # Try sub-links
                for a in soup.find_all('a', href=True)[:15]:
                    txt = a.get_text(strip=True)
                    if any(kw in txt for kw in ['分数线','复试','分数']):
                        href = a['href']
                        if href.startswith('/'):
                            href = f"https://www.chinakaoyan.com{href}"
                        elif not href.startswith('http'):
                            continue
                        try:
                            r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                            if r2.status_code == 200:
                                s2 = BeautifulSoup(r2.text, 'html.parser')
                                sub = try_extract_score_table(s2, school)
                                if sub:
                                    for rec in sub:
                                        rec["schoolId"] = sid
                                        key = sid + '_' + rec.get("schoolMajorName",'')
                                        if key not in seen:
                                            seen.add(key)
                                            collected.append(rec)
                                    print(f"    -> {txt[:20]}: {len(sub)} 条")
                        except:
                            pass
                break
            except:
                continue
    print(f"  [源2] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 3: 中国教育在线 (kaoyan.eol.cn) — score query system
# ====================================================================
def scrape_eol():
    """Source 3: 中国教育在线 — search for school score pages."""
    print("  [源3] 中国教育在线 kaoyan.eol.cn ...")
    collected = []
    # Try direct API-style query and known pages
    urls = [
        "https://data.eol.cn/ky/fsx/",
        "https://kaoyan.eol.cn/e_ky/zt/common/fsx.shtml",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            # Extract school links
            for a in soup.find_all('a', href=True)[:50]:
                txt = a.get_text(strip=True)
                if not any(s in txt for s in ALL_SCHOOLS):
                    continue
                href = a['href']
                if not href.startswith('http'):
                    href = url.rstrip('/') + '/' + href.lstrip('/')
                try:
                    r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                    if r2.status_code == 200:
                        s2 = BeautifulSoup(r2.text, 'html.parser')
                        recs = try_extract_score_table(s2, txt)
                        if recs:
                            sid = re.sub(r'[\(\)（）\s]', '', txt)
                            for rec in recs:
                                rec["schoolId"] = sid
                            collected.extend(recs)
                            print(f"  [源3] {txt}: {len(recs)} 条")
                except:
                    pass
        except:
            pass
    print(f"  [源3] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 4: 各校官网直接查询 (direct admission site URLs)
# Comprehensive list of actual 复试分数线 pages on each school's site
# ====================================================================
SCHOOL_OFFICIAL_SCORE_URLS = {
    "北京大学":["https://yzb.pku.edu.cn/xxgk/fsx.htm","https://admission.pku.edu.cn/zsxx/sszs.htm"],
    "清华大学":["https://yz.tsinghua.edu.cn/xxgk/ssfsx.htm","https://yz.tsinghua.edu.cn/"],
    "浙江大学":["http://www.grs.zju.edu.cn/yjszs/","https://yjsy.zju.edu.cn/"],
    "上海交通大学":["https://yzb.sjtu.edu.cn/xxgk/ssfsx.htm","https://yzb.sjtu.edu.cn/"],
    "复旦大学":["https://gsao.fudan.edu.cn/","https://gsao.fudan.edu.cn/xxgk/ssfsx.htm"],
    "南京大学":["https://yzb.nju.edu.cn/","https://yzb.nju.edu.cn/xxgk/ssfsx.htm"],
    "西安交通大学":["http://yz.xjtu.edu.cn/","http://yz.xjtu.edu.cn/xxgk/ssfsx.htm"],
    "哈尔滨工业大学":["http://yzb.hit.edu.cn/","http://yzb.hit.edu.cn/xxgk/ssfsx.htm"],
    "中国科学技术大学":["https://yz.ustc.edu.cn/","https://yz.ustc.edu.cn/xxgk/ssfsx.htm"],
    "武汉大学":["https://gs.whu.edu.cn/","https://gs.whu.edu.cn/xxgk/ssfsx.htm"],
    "华中科技大学":["http://gszs.hust.edu.cn/","http://gszs.hust.edu.cn/xxgk/ssfsx.htm"],
    "中山大学":["https://graduate.sysu.edu.cn/","https://graduate.sysu.edu.cn/xxgk/ssfsx.htm"],
    "四川大学":["https://yz.scu.edu.cn/","https://yz.scu.edu.cn/xxgk/ssfsx.htm"],
    "南开大学":["https://yzb.nankai.edu.cn/","https://yzb.nankai.edu.cn/xxgk/ssfsx.htm"],
    "天津大学":["http://yzb.tju.edu.cn/","http://yzb.tju.edu.cn/xxgk/ssfsx.htm"],
    "山东大学":["https://www.yz.sdu.edu.cn/","https://www.yz.sdu.edu.cn/xxgk/ssfsx.htm"],
    "东南大学":["https://yzb.seu.edu.cn/","https://yzb.seu.edu.cn/xxgk/ssfsx.htm"],
    "同济大学":["https://yz.tongji.edu.cn/","https://yz.tongji.edu.cn/xxgk/ssfsx.htm"],
    "厦门大学":["https://zsb.xmu.edu.cn/","https://zsb.xmu.edu.cn/xxgk/ssfsx.htm"],
    "北京航空航天大学":["https://yzb.buaa.edu.cn/","https://yzb.buaa.edu.cn/xxgk/ssfsx.htm"],
    "北京理工大学":["https://yz.bit.edu.cn/","https://yz.bit.edu.cn/xxgk/ssfsx.htm"],
    "大连理工大学":["http://gs.dlut.edu.cn/","http://gs.dlut.edu.cn/xxgk/ssfsx.htm"],
    "东北大学":["http://www.neu.edu.cn/","http://www.neu.edu.cn/xxgk/ssfsx.htm"],
    "华南理工大学":["https://yanzhao.scut.edu.cn/","https://yanzhao.scut.edu.cn/xxgk/ssfsx.htm"],
    "重庆大学":["http://yz.cqu.edu.cn/","http://yz.cqu.edu.cn/xxgk/ssfsx.htm"],
    "中南大学":["https://yz.csu.edu.cn/","https://yz.csu.edu.cn/xxgk/ssfsx.htm"],
    "湖南大学":["http://gra.hnu.edu.cn/","http://gra.hnu.edu.cn/xxgk/ssfsx.htm"],
    "电子科技大学":["https://yz.uestc.edu.cn/","https://yz.uestc.edu.cn/xxgk/ssfsx.htm"],
    "兰州大学":["https://yz.lzu.edu.cn/","https://yz.lzu.edu.cn/xxgk/ssfsx.htm"],
    "中国人民大学":["http://pgs.ruc.edu.cn/","http://pgs.ruc.edu.cn/xxgk/ssfsx.htm"],
    "北京师范大学":["https://yz.bnu.edu.cn/","https://yz.bnu.edu.cn/xxgk/ssfsx.htm"],
    "北京邮电大学":["https://yzb.bupt.edu.cn/","https://yzb.bupt.edu.cn/xxgk/ssfsx.htm"],
    "西安电子科技大学":["https://yz.xidian.edu.cn/","https://yz.xidian.edu.cn/xxgk/ssfsx.htm"],
    "北京科技大学":["https://yzxc.ustb.edu.cn/","https://yzxc.ustb.edu.cn/zsjz/ssfsx.htm"],
    "北京交通大学":["https://gs.bjtu.edu.cn/","https://gs.bjtu.edu.cn/xxgk/ssfsx.htm"],
    "南京航空航天大学":["https://www.graduate.nuaa.edu.cn/","https://www.graduate.nuaa.edu.cn/xxgk/ssfsx.htm"],
    "南京理工大学":["https://gs.njust.edu.cn/","https://gs.njust.edu.cn/xxgk/ssfsx.htm"],
    "哈尔滨工程大学":["http://yzb.hrbeu.edu.cn/","http://yzb.hrbeu.edu.cn/xxgk/ssfsx.htm"],
    "武汉理工大学":["http://gd.whut.edu.cn/","http://gd.whut.edu.cn/xxgk/ssfsx.htm"],
    "西南交通大学":["https://yz.swjtu.edu.cn/","https://yz.swjtu.edu.cn/xxgk/ssfsx.htm"],
    "华东理工大学":["http://gschool.ecust.edu.cn/","http://gschool.ecust.edu.cn/xxgk/ssfsx.htm"],
    "上海大学":["https://yjszs.shu.edu.cn/","https://yjszs.shu.edu.cn/xxgk/ssfsx.htm"],
    "苏州大学":["https://yjs.suda.edu.cn/","https://yjs.suda.edu.cn/xxgk/ssfsx.htm"],
    "河海大学":["http://gs.hhu.edu.cn/","http://gs.hhu.edu.cn/xxgk/ssfsx.htm"],
    "中国矿业大学":["http://yjsb.cumt.edu.cn/","http://yjsb.cumt.edu.cn/xxgk/ssfsx.htm"],
    "郑州大学":["http://gs.zzu.edu.cn/","http://gs.zzu.edu.cn/xxgk/ssfsx.htm"],
    "合肥工业大学":["http://yjszs.hfut.edu.cn/","http://yjszs.hfut.edu.cn/xxgk/ssfsx.htm"],
    "深圳大学":["https://yz.szu.edu.cn/","https://yz.szu.edu.cn/xxgk/ssfsx.htm"],
    "杭州电子科技大学":["http://grs.hdu.edu.cn/","http://grs.hdu.edu.cn/xxgk/ssfsx.htm"],
    "南京邮电大学":["http://yzb.njupt.edu.cn/","http://yzb.njupt.edu.cn/xxgk/ssfsx.htm"],
    "中国科学院大学":["https://admission.ucas.ac.cn/","https://admission.ucas.ac.cn/xxgk/ssfsx.htm"],
    "南方科技大学":["https://gs.sustech.edu.cn/","https://gs.sustech.edu.cn/xxgk/ssfsx.htm"],
}
def scrape_official_sites():
    """Source 4: Direct hit on each school's admission score page."""
    print("  [源4] 各校官网复试分数线页 ...")
    collected = []
    seen = set()
    for name, urls in SCHOOL_OFFICIAL_SCORE_URLS.items():
        sid = re.sub(r'[\(\)（）\s]', '', name)
        for url in urls:
            try:
                r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, 'html.parser')
                # Try table extraction on main page
                recs = try_extract_score_table(soup, name)
                if recs:
                    for rec in recs:
                        rec["schoolId"] = sid
                        k = sid + '_' + rec.get("schoolMajorName",'')
                        if k not in seen:
                            seen.add(k)
                            collected.append(rec)
                    print(f"  [源4] {name}: {len(recs)} 条")
                    break
                # Search for score links
                for a in soup.find_all('a', href=True)[:30]:
                    txt = a.get_text(strip=True)
                    if any(kw in txt for kw in ['分数线','复试线','复试分数','历年分数','录取统计','2025','2024']):
                        href = a['href']
                        if href.startswith('/'):
                            href = url.rstrip('/') + href
                        elif not href.startswith('http'):
                            href = url.rstrip('/') + '/' + href.lstrip('/')
                        try:
                            r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                            if r2.status_code == 200:
                                s2 = BeautifulSoup(r2.text, 'html.parser')
                                sub = try_extract_score_table(s2, name)
                                if sub:
                                    for rec in sub:
                                        rec["schoolId"] = sid
                                        k = sid + '_' + rec.get("schoolMajorName",'')
                                        if k not in seen:
                                            seen.add(k)
                                            collected.append(rec)
                                    print(f"    -> {txt[:20]}: {len(sub)} 条")
                                    break
                        except:
                            pass
                break
            except:
                continue
    print(f"  [源4] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 5: 百度搜索聚合 — search for "学校名 复试分数线" on Baidu
# ====================================================================
def scrape_baidu_search():
    """Source 5: Baidu search for school score pages."""
    print("  [源5] 百度搜索 ...")
    collected = []
    seen = set()
    # Try the first 30 schools (most likely to have data)
    for school in ALL_SCHOOLS[:30]:
        sid = re.sub(r'[\(\)（）\s]', '', school)
        query = f"{school} 复试分数线 2025"
        try:
            url = "https://www.baidu.com/s"
            r = requests.get(url, params={"wd": query, "ie": "utf-8"}, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            # Extract result links
            for a in soup.find_all('a', href=True)[:20]:
                txt = a.get_text(strip=True)
                href = a.get('href', '')
                if not txt or not href:
                    continue
                if not any(kw in txt for kw in ['分数','复试线','录取']):
                    continue
                if href.startswith('/') or href.startswith('http'):
                    if href.startswith('/'):
                        href = f"https://www.baidu.com{href}"
                    try:
                        r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                        if r2.status_code == 200:
                            s2 = BeautifulSoup(r2.text, 'html.parser')
                            recs = try_extract_score_table(s2, school)
                            if not recs:
                                recs = extract_scores_from_text(s2.get_text(), school)
                            if recs:
                                for rec in recs:
                                    rec["schoolId"] = sid
                                    k = sid + '_' + rec.get("schoolMajorName",'')
                                    if k not in seen:
                                        seen.add(k)
                                        collected.append(rec)
                                print(f"  [源5] {school}: {len(recs)} 条 ({txt[:20]})")
                                break
                    except:
                        pass
        except:
            pass
    print(f"  [源5] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 6: 知乎/CSDN/博客园等用户分享的分数线数据
# ====================================================================
BLOG_PATTERNS = [
    "https://www.zhihu.com/search?type=content&q={school} 考研 复试分数线",
    "https://www.csdn.net/search?q={school} 复试分数线",
    "https://www.cnblogs.com/search?q={school} 考研 分数线",
]
def scrape_blogs():
    """Source 6: User-shared score data on blogs & forums."""
    print("  [源6] 博客/知乎 ...")
    collected = []
    seen = set()
    for school in ALL_SCHOOLS[:20]:
        sid = re.sub(r'[\(\)（）\s]', '', school)
        for pattern in BLOG_PATTERNS:
            try:
                url = pattern.replace("{school}", school)
                r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, 'html.parser')
                recs = try_extract_score_table(soup, school)
                if not recs:
                    recs = extract_scores_from_text(soup.get_text()[:20000], school)
                if recs:
                    for rec in recs:
                        rec["schoolId"] = sid
                        k = sid + '_' + rec.get("schoolMajorName",'')
                        if k not in seen:
                            seen.add(k)
                            collected.append(rec)
                    print(f"  [源6] {school}: {len(recs)} 条")
                    break
            except:
                continue
    print(f"  [源6] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 7: GitHub 开源数据集
# ====================================================================
GITHUB_DATASETS = [
    "https://raw.githubusercontent.com/neardws/National-Postgraduate-Entrance-Exam-Data/main/data.json",
    "https://raw.githubusercontent.com/chenjiandongx/kaoyan/main/data.json",
    "https://raw.githubusercontent.com/HiCrazyPenguin/kaoyan-score/main/scores.json",
    "https://raw.githubusercontent.com/nicerHan/kaoyan-fsx/main/data.json",
    "https://raw.githubusercontent.com/your-org/kaoyan-data/main/scores.json",
    "https://raw.githubusercontent.com/kaoyan-data/kaoyan/main/scores.json",
]
def scrape_github():
    """Source 7: GitHub open datasets."""
    print("  [源7] GitHub 数据集 ...")
    for url in GITHUB_DATASETS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code == 200:
                try:
                    data = r.json()
                    if isinstance(data, list):
                        print(f"  [源7] {url.split('/')[-3]} 获取 {len(data)} 条")
                        return data
                    elif isinstance(data, dict) and "records" in data:
                        print(f"  [源7] {url.split('/')[-3]} 获取 {len(data['records'])} 条")
                        return data["records"]
                    elif isinstance(data, dict):
                        for k in data:
                            if isinstance(data[k], list) and len(data[k]) > 0:
                                print(f"  [源7] {k}: {len(data[k])} 条")
                                return data[k]
                except:
                    pass
        except:
            pass
    print("  [源7] 无可用数据")
    return []

# ====================================================================
# SOURCE 8: 研招网 34所自划线 + 国家线 (yz.chsi.com.cn)
# Most authoritative source: Ministry of Education's official site
# ====================================================================
def scrape_chsi():
    """Source 8: 研招网自划线/国家线专题页和34所自划线汇总."""
    print("  [源8] 研招网 yz.chsi.com.cn ...")
    collected = []
    seen = set()

    # Try to get the 34所自划线 page and extract school announcement links
    urls = [
        "https://yz.chsi.com.cn/kyzx/fsfsx34",
        "https://yz.chsi.com.cn/kyzx/zt/lnfsx2025.shtml",
        "https://yz.chsi.com.cn/kyzx/zt/lnfsx2024.shtml",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            # Find all links to school score announcements
            for a in soup.find_all('a', href=True):
                txt = a.get_text(strip=True)
                href = a['href']
                if not txt or not href:
                    continue
                # Match school names in link text
                matched_school = None
                for s in ALL_SCHOOLS:
                    if s in txt:
                        matched_school = s
                        break
                if not matched_school:
                    continue
                if not any(kw in txt for kw in ['复试','分数','线','基本要求']):
                    continue
                if href.startswith('/'):
                    href = 'https://yz.chsi.com.cn' + href
                elif not href.startswith('http'):
                    continue
                try:
                    r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                    if r2.status_code != 200:
                        continue
                    s2 = BeautifulSoup(r2.text, 'html.parser')
                    sid = re.sub(r'[\(\)（）\s]', '', matched_school)
                    recs = try_extract_score_table(s2, matched_school)
                    if recs:
                        for rec in recs:
                            rec["schoolId"] = sid
                            k = sid + '_' + rec.get("schoolMajorName", '')
                            if k not in seen:
                                seen.add(k)
                                collected.append(rec)
                        print(f"  [源8] {matched_school}: {len(recs)} 条")
                except:
                    pass
        except:
            pass

    # Also try to extract national line data table from the page
    try:
        r = requests.get("https://yz.chsi.com.cn/kyzx/fsfsx", headers=HEADERS, timeout=15, verify=False)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for table in soup.find_all('table'):
                rows = table.find_all('tr')
                if len(rows) >= 10:
                    recs = try_extract_score_table(soup, current_year=2025)
                    if recs:
                        print(f"  [源8] 国家线表格: {len(recs)} 条")
        else:
            print("  [源8] 国家线页面不可达 (预期之中，研招网有反爬)")
    except:
        pass

    print(f"  [源8] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 9: 中国教育在线 (kaoyan.eol.cn)
# Well-structured score data, good secondary authoritative source
# ====================================================================
def scrape_eol_kaoyan():
    """Source 9: 中国教育在线考研频道 — 34所自划线 + 历年分数线."""
    print("  [源9] 中国教育在线 kaoyan.eol.cn ...")
    collected = []
    seen = set()

    base_url = "https://www.eol.cn/e_ky/zt/common/fsx/index.shtml"
    try:
        r = requests.get(base_url, headers=HEADERS, timeout=15, verify=False)
        if r.status_code != 200:
            print("  [源9] 页面不可达")
            return collected
        soup = BeautifulSoup(r.text, 'html.parser')

        # Find school score links
        for a in soup.find_all('a', href=True):
            txt = a.get_text(strip=True)
            href = a['href']
            if not txt or not href:
                continue
            matched_school = None
            for s in ALL_SCHOOLS:
                if s in txt:
                    matched_school = s
                    break
            if not matched_school:
                continue
            if not any(kw in txt for kw in ['分数','复试']):
                continue
            if not href.startswith('http'):
                href = "https://www.eol.cn" + href if href.startswith('/') else base_url

            try:
                r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                if r2.status_code != 200:
                    continue
                s2 = BeautifulSoup(r2.text, 'html.parser')
                sid = re.sub(r'[\(\)（）\s]', '', matched_school)
                recs = try_extract_score_table(s2, matched_school)
                if recs:
                    for rec in recs:
                        rec["schoolId"] = sid
                        k = sid + '_' + rec.get("schoolMajorName", '')
                        if k not in seen:
                            seen.add(k)
                            collected.append(rec)
                    print(f"  [源9] {matched_school}: {len(recs)} 条")
            except:
                pass
    except:
        pass
    print(f"  [源9] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 10: 各校研究生院官网增强版 (expanded source 4)
# Directly visit each school's admission site for score data
# ====================================================================
def scrape_official_enhanced():
    """Source 10: 各校官网增强 — 尝试更多URL模式 + 搜索子页面."""
    print("  [源10] 各校官网增强版 ...")
    collected = []
    seen = set()

    for s in ALL_SCHOOLS:
        sid = re.sub(r'[\(\)（）\s]', '', s)
        # Additional URL patterns beyond Source 4
        extra_urls = []

        # Try common URL patterns for score pages
        if s in SCHOOL_OFFICIAL_SCORE_URLS:
            extra_urls = SCHOOL_OFFICIAL_SCORE_URLS[s][:]

        # Add additional common patterns
        base = ADMISSION_URLS.get(s, '')
        if base:
            base = base.rstrip('/')
            extra_urls.extend([
                base,
                base + '/fsx/',
                base + '/fenshuxian/',
                base + '/ssfsx/',
                base + '/xxgk/',
                base + '/zsxx/',
            ])

        for url in extra_urls:
            try:
                r = requests.get(url, headers=HEADERS, timeout=10, verify=False)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, 'html.parser')
                recs = try_extract_score_table(soup, s)
                if recs:
                    for rec in recs:
                        rec["schoolId"] = sid
                        k = sid + '_' + rec.get("schoolMajorName", '')
                        if k not in seen:
                            seen.add(k)
                            collected.append(rec)
                    print(f"  [源10] {s}: {len(recs)} 条")
                    break

                # Search for score-related links on the page
                for a in soup.find_all('a', href=True)[:20]:
                    txt = a.get_text(strip=True)
                    if any(kw in txt for kw in ['复试','分数线','录取统计','历年','2025','2024']):
                        href = a['href']
                        if href.startswith('/'):
                            href = url.rstrip('/') + href
                        elif not href.startswith('http'):
                            continue
                        try:
                            r2 = requests.get(href, headers=HEADERS, timeout=8, verify=False)
                            if r2.status_code != 200:
                                continue
                            s2 = BeautifulSoup(r2.text, 'html.parser')
                            sub = try_extract_score_table(s2, s)
                            if sub:
                                for rec in sub:
                                    rec["schoolId"] = sid
                                    k = sid + '_' + rec.get("schoolMajorName", '')
                                    if k not in seen:
                                        seen.add(k)
                                        collected.append(rec)
                                print(f"    -> {txt[:20]}: {len(sub)} 条")
                                break
                        except:
                            pass
            except:
                pass
    print(f"  [源10] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 11: 新浪教育考研频道 (edu.sina.com.cn)
# ====================================================================
def scrape_sina_edu():
    """Source 11: 新浪教育考研分数线数据."""
    print("  [源11] 新浪教育 edu.sina.com.cn ...")
    collected = []
    seen = set()
    urls = [
        "https://edu.sina.com.cn/kaoyan/fsx/",
        "https://kaoyan.sina.com.cn/",
        "https://edu.sina.com.cn/kaoyan/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True)[:50]:
                txt = a.get_text(strip=True)
                href = a['href']
                if not txt or not href:
                    continue
                if not any(s in txt for s in ALL_SCHOOLS[:20]):
                    continue
                if not any(kw in txt for kw in ['分数','复试','线']):
                    continue
                if not href.startswith('http'):
                    href = "https://edu.sina.com.cn" + href if href.startswith('/') else url
                try:
                    r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                    if r2.status_code == 200:
                        s2 = BeautifulSoup(r2.text, 'html.parser')
                        sid = re.sub(r'[\(\)（）\s]', '', txt.split()[0] if txt else '')
                        recs = try_extract_score_table(s2, txt.split()[0] if txt else '')
                        if recs:
                            for rec in recs:
                                rec["schoolId"] = sid
                                k = sid + '_' + rec.get("schoolMajorName", '')
                                if k not in seen:
                                    seen.add(k)
                                    collected.append(rec)
                            print(f"  [源11] {txt[:15]}: {len(recs)} 条")
                except:
                    pass
        except:
            pass
    print(f"  [源11] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 12: 腾讯教育考研频道 (edu.qq.com)
# ====================================================================
def scrape_qq_edu():
    """Source 12: 腾讯教育考研分数线."""
    print("  [源12] 腾讯教育 edu.qq.com ...")
    collected = []
    seen = set()
    urls = [
        "https://edu.qq.com/kaoyan/fsx/",
        "https://edu.qq.com/a/kaoyan/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True)[:50]:
                txt = a.get_text(strip=True)
                href = a['href']
                if not txt or not href:
                    continue
                if not any(s in txt for s in ALL_SCHOOLS[:20]):
                    continue
                if not any(kw in txt for kw in ['分数','复试','线']):
                    continue
                if not href.startswith('http'):
                    href = "https://edu.qq.com" + href if href.startswith('/') else url
                try:
                    r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                    if r2.status_code == 200:
                        s2 = BeautifulSoup(r2.text, 'html.parser')
                        matched = None
                        for s in ALL_SCHOOLS:
                            if s in txt:
                                matched = s
                                break
                        if matched:
                            sid = re.sub(r'[\(\)（）\s]', '', matched)
                            recs = try_extract_score_table(s2, matched)
                            if recs:
                                for rec in recs:
                                    rec["schoolId"] = sid
                                    k = sid + '_' + rec.get("schoolMajorName", '')
                                    if k not in seen:
                                        seen.add(k)
                                        collected.append(rec)
                                print(f"  [源12] {matched}: {len(recs)} 条")
                except:
                    pass
        except:
            pass
    print(f"  [源12] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 13: 考研村 kaoyancun.com — 分数线汇总专题
# ====================================================================
def scrape_kaoyancun():
    """Source 13: 考研村分数线专题页."""
    print("  [源13] 考研村 kaoyancun.com ...")
    collected = []
    seen = set()
    urls = [
        "https://www.kaoyancun.com/fenshuxian/",
        "https://www.kaoyancun.com/kaoyan/fsx/",
        "https://www.kaoyancun.com/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True)[:80]:
                txt = a.get_text(strip=True)
                href = a['href']
                if not txt or not href:
                    continue
                matched = None
                for s in ALL_SCHOOLS:
                    if s in txt:
                        matched = s
                        break
                if not matched:
                    continue
                if not any(kw in txt for kw in ['分数','复试','线','录取']):
                    continue
                if not href.startswith('http'):
                    href = "https://www.kaoyancun.com" + href if href.startswith('/') else url
                try:
                    r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                    if r2.status_code == 200:
                        s2 = BeautifulSoup(r2.text, 'html.parser')
                        sid = re.sub(r'[\(\)（）\s]', '', matched)
                        recs = try_extract_score_table(s2, matched)
                        if recs:
                            for rec in recs:
                                rec["schoolId"] = sid
                                k = sid + '_' + rec.get("schoolMajorName", '')
                                if k not in seen:
                                    seen.add(k)
                                    collected.append(rec)
                            print(f"  [源13] {matched}: {len(recs)} 条")
                except:
                    pass
        except:
            pass
    print(f"  [源13] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 14: 考满分 kaomanfen.com — 分数线查询系统
# ====================================================================
def scrape_kaomanfen():
    """Source 14: 考满分分数线查询."""
    print("  [源14] 考满分 kaomanfen.com ...")
    collected = []
    seen = set()
    urls = [
        "https://www.kaomanfen.com/kaoyan/fenshuxian/",
        "https://www.kaomanfen.com/kaoyan/",
        "https://www.kaomanfen.com/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True)[:80]:
                txt = a.get_text(strip=True)
                href = a['href']
                if not txt or not href:
                    continue
                matched = None
                for s in ALL_SCHOOLS:
                    if s in txt:
                        matched = s
                        break
                if not matched:
                    continue
                if not any(kw in txt for kw in ['分数','复试','线']):
                    continue
                if not href.startswith('http'):
                    href = "https://www.kaomanfen.com" + href if href.startswith('/') else url
                try:
                    r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                    if r2.status_code == 200:
                        s2 = BeautifulSoup(r2.text, 'html.parser')
                        sid = re.sub(r'[\(\)（）\s]', '', matched)
                        recs = try_extract_score_table(s2, matched)
                        if recs:
                            for rec in recs:
                                rec["schoolId"] = sid
                                k = sid + '_' + rec.get("schoolMajorName", '')
                                if k not in seen:
                                    seen.add(k)
                                    collected.append(rec)
                            print(f"  [源14] {matched}: {len(recs)} 条")
                except:
                    pass
        except:
            pass
    print(f"  [源14] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 15: 文都教育 kaoyan.wendu.com — 考研分数线专题
# ====================================================================
def scrape_wendu():
    """Source 15: 文都教育考研分数线."""
    print("  [源15] 文都教育 wendu.com ...")
    collected = []
    seen = set()
    urls = [
        "https://kaoyan.wendu.com/fenshuxian/",
        "https://kaoyan.wendu.com/",
        "https://www.wendu.com/kaoyan/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True)[:80]:
                txt = a.get_text(strip=True)
                href = a['href']
                if not txt or not href:
                    continue
                matched = None
                for s in ALL_SCHOOLS:
                    if s in txt:
                        matched = s
                        break
                if not matched:
                    continue
                if not any(kw in txt for kw in ['分数','复试','线']):
                    continue
                if not href.startswith('http'):
                    href = "https://kaoyan.wendu.com" + href if href.startswith('/') else url
                try:
                    r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                    if r2.status_code == 200:
                        s2 = BeautifulSoup(r2.text, 'html.parser')
                        sid = re.sub(r'[\(\)（）\s]', '', matched)
                        recs = try_extract_score_table(s2, matched)
                        if recs:
                            for rec in recs:
                                rec["schoolId"] = sid
                                k = sid + '_' + rec.get("schoolMajorName", '')
                                if k not in seen:
                                    seen.add(k)
                                    collected.append(rec)
                            print(f"  [源15] {matched}: {len(recs)} 条")
                except:
                    pass
        except:
            pass
    print(f"  [源15] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 16: 海文考研 kaoyan.haiwen.com — 分数线数据
# ====================================================================
def scrape_haiwen():
    """Source 16: 海文考研分数线."""
    print("  [源16] 海文考研 haiwen.com ...")
    collected = []
    seen = set()
    urls = [
        "https://kaoyan.haiwen.com/fenshuxian/",
        "https://kaoyan.haiwen.com/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True)[:80]:
                txt = a.get_text(strip=True)
                href = a['href']
                if not txt or not href:
                    continue
                matched = None
                for s in ALL_SCHOOLS:
                    if s in txt:
                        matched = s
                        break
                if not matched:
                    continue
                if not any(kw in txt for kw in ['分数','复试','线']):
                    continue
                if not href.startswith('http'):
                    href = "https://kaoyan.haiwen.com" + href if href.startswith('/') else url
                try:
                    r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                    if r2.status_code == 200:
                        s2 = BeautifulSoup(r2.text, 'html.parser')
                        sid = re.sub(r'[\(\)（）\s]', '', matched)
                        recs = try_extract_score_table(s2, matched)
                        if recs:
                            for rec in recs:
                                rec["schoolId"] = sid
                                k = sid + '_' + rec.get("schoolMajorName", '')
                                if k not in seen:
                                    seen.add(k)
                                    collected.append(rec)
                            print(f"  [源16] {matched}: {len(recs)} 条")
                except:
                    pass
        except:
            pass
    print(f"  [源16] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 17: 各省教育厅/考试院分数线公告
# ====================================================================
def scrape_province_education():
    """Source 17: 各省教育考试院分数线公告."""
    print("  [源17] 各省教育考试院 ...")
    collected = []
    seen = set()
    province_urls = {
        "北京":"https://www.bjeea.cn/","上海":"https://www.shmeea.edu.cn/",
        "江苏":"https://www.jseea.cn/","浙江":"http://www.zjzs.net/",
        "广东":"https://eea.gd.gov.cn/","湖北":"http://www.hbea.edu.cn/",
        "四川":"https://sceea.ncg.edu.cn/","陕西":"http://www.sneea.cn/",
        "山东":"http://www.sdzk.cn/","河南":"https://www.haeea.cn/",
        "湖南":"https://www.hneeb.cn/","福建":"https://www.fjzsks.cn/",
        "安徽":"https://www.ahzsks.cn/","辽宁":"http://www.lnzsks.com/",
        "吉林":"http://www.jleea.com.cn/","黑龙江":"http://www.lzk.hl.cn/",
    }
    for prov, base_url in province_urls.items():
        try:
            r = requests.get(base_url, headers=HEADERS, timeout=12, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True)[:30]:
                txt = a.get_text(strip=True)
                href = a['href']
                if not txt or not href:
                    continue
                if not any(kw in txt for kw in ['考研','复试','分数线','研究生']):
                    continue
                if not href.startswith('http'):
                    href = base_url.rstrip('/') + '/' + href.lstrip('/')
                try:
                    r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                    if r2.status_code == 200:
                        s2 = BeautifulSoup(r2.text, 'html.parser')
                        recs = try_extract_score_table(s2, prov + '分数线')
                        if recs:
                            for rec in recs:
                                if "schoolMajorName" not in rec:
                                    rec["schoolMajorName"] = rec.get("schoolMajorName", prov)
                                k = rec.get("schoolMajorName", '') + '_' + str(rec.get("years", [{}])[0].get("year", ''))
                                if k not in seen:
                                    seen.add(k)
                                    collected.append(rec)
                            print(f"  [源17] {prov}: {len(recs)} 条")
                except:
                    pass
        except:
            pass
    print(f"  [源17] 共 {len(collected)} 条")
    return collected


# ====================================================================
# SOURCE 18: 考研调剂信息网 (kaoyan.tiaoji.com) — 分数线参考
# ====================================================================
def scrape_tiaoji():
    """Source 18: 考研调剂网分数线参考数据."""
    print("  [源18] 考研调剂网 ...")
    collected = []
    seen = set()
    urls = [
        "https://www.kaoyan.com/tiaoji/fenshuxian/",
        "https://www.kaoyan.com/tiaoji/",
        "https://www.yz.chsi.com.cn/kyzx/jyxx/",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True)[:60]:
                txt = a.get_text(strip=True)
                href = a['href']
                if not txt or not href:
                    continue
                matched = None
                for s in ALL_SCHOOLS:
                    if s in txt:
                        matched = s
                        break
                if not matched:
                    continue
                if not any(kw in txt for kw in ['分数','复试','调剂']):
                    continue
                if not href.startswith('http'):
                    href = "https://www.kaoyan.com" + href if href.startswith('/') else url
                try:
                    r2 = requests.get(href, headers=HEADERS, timeout=10, verify=False)
                    if r2.status_code == 200:
                        s2 = BeautifulSoup(r2.text, 'html.parser')
                        sid = re.sub(r'[\(\)（）\s]', '', matched)
                        recs = try_extract_score_table(s2, matched)
                        if recs:
                            for rec in recs:
                                rec["schoolId"] = sid
                                k = sid + '_' + rec.get("schoolMajorName", '')
                                if k not in seen:
                                    seen.add(k)
                                    collected.append(rec)
                            print(f"  [源18] {matched}: {len(recs)} 条")
                except:
                    pass
        except:
            pass
    print(f"  [源18] 共 {len(collected)} 条")
    return collected


# ============== BUILD EMPTY ==============
ADMISSION_URLS = {
    "北京大学":"https://yzb.pku.edu.cn/","清华大学":"https://yz.tsinghua.edu.cn/",
    "复旦大学":"https://gsao.fudan.edu.cn/","上海交通大学":"https://yzb.sjtu.edu.cn/",
    "浙江大学":"http://www.grs.zju.edu.cn/yjszs/","中国科学技术大学":"https://yz.ustc.edu.cn/",
    "南京大学":"https://yzb.nju.edu.cn/","西安交通大学":"http://yz.xjtu.edu.cn/",
    "哈尔滨工业大学":"http://yzb.hit.edu.cn/","武汉大学":"https://gs.whu.edu.cn/",
    "华中科技大学":"http://gszs.hust.edu.cn/","中山大学":"https://graduate.sysu.edu.cn/",
    "四川大学":"https://yz.scu.edu.cn/","南开大学":"https://yzb.nankai.edu.cn/",
    "天津大学":"http://yzb.tju.edu.cn/","山东大学":"https://www.yz.sdu.edu.cn/",
    "东南大学":"https://yzb.seu.edu.cn/","吉林大学":"http://zsb.jlu.edu.cn/",
    "厦门大学":"https://zsb.xmu.edu.cn/","同济大学":"https://yz.tongji.edu.cn/",
    "北京航空航天大学":"https://yzb.buaa.edu.cn/","北京理工大学":"https://yz.bit.edu.cn/",
    "大连理工大学":"http://gs.dlut.edu.cn/","西北工业大学":"https://yzb.nwpu.edu.cn/",
    "华南理工大学":"https://yanzhao.scut.edu.cn/","重庆大学":"http://yz.cqu.edu.cn/",
    "中南大学":"https://yz.csu.edu.cn/","湖南大学":"http://gra.hnu.edu.cn/",
    "电子科技大学":"https://yz.uestc.edu.cn/","兰州大学":"https://yz.lzu.edu.cn/",
    "北京师范大学":"https://yz.bnu.edu.cn/","北京邮电大学":"https://yzb.bupt.edu.cn/",
    "西安电子科技大学":"https://yz.xidian.edu.cn/","南京航空航天大学":"https://www.graduate.nuaa.edu.cn/",
    "南京理工大学":"https://gs.njust.edu.cn/","哈尔滨工程大学":"http://yzb.hrbeu.edu.cn/",
    "武汉理工大学":"http://gd.whut.edu.cn/","西南交通大学":"https://yz.swjtu.edu.cn/",
    "华东理工大学":"http://gschool.ecust.edu.cn/","上海大学":"https://yjszs.shu.edu.cn/",
    "苏州大学":"https://yjs.suda.edu.cn/","河海大学":"http://gs.hhu.edu.cn/",
    "中国矿业大学":"http://yjsb.cumt.edu.cn/","郑州大学":"http://gs.zzu.edu.cn/",
    "合肥工业大学":"http://yjszs.hfut.edu.cn/","北京交通大学":"https://gs.bjtu.edu.cn/",
    "北京科技大学":"https://yzxc.ustb.edu.cn/","西南大学":"http://yzswu.swu.edu.cn/",
    "深圳大学":"https://yz.szu.edu.cn/","杭州电子科技大学":"http://grs.hdu.edu.cn/",
    "南京邮电大学":"http://yzb.njupt.edu.cn/",
    "中国科学院大学":"https://admission.ucas.ac.cn/","南方科技大学":"https://gs.sustech.edu.cn/",
}

def build_data():
    all_schools = {}
    for s in ALL_SCHOOLS:
        sid = re.sub(r'[\(\)（）\s]', '', s)
        all_schools[sid] = {"id": sid, "name": s, "province": SCHOOL_PROVINCE.get(s, ""),
                            "level": ALL_SCHOOLS_META.get(s, "双非"),
                            "admissionUrl": ADMISSION_URLS.get(s, "")}
    return {"schools": list(all_schools.values()), "categories": CATEGORIES, "records": [], "_meta": {}}

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(BASE_DIR, exist_ok=True)

    # First check if current data.json has records already
    existing_records = []
    existing_national_lines = {}
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
            existing_records = existing.get("records", [])
            existing_national_lines = existing.get("nationalLines", {})
        print(f"当前已有 {len(existing_records)} 条记录")
    except:
        pass

    data = build_data()
    data["records"] = existing_records
    data["nationalLines"] = existing_national_lines

    print(f"{'='*50}")
    print(f"  考研分数线数据采集 (18源增强版)")
    print(f"  目标: {len(data['schools'])} 所学校 (985+211+顶尖双非)")
    print(f"  数据源: 考研帮 | 考研网 | 中国教育在线 | 各校官网 | 百度 | 博客/知乎 | GitHub | 研招网 | 中国教育在线2 | 各校官网增强 | 新浪教育 | 腾讯教育 | 考研村 | 考满分 | 文都教育 | 海文考研 | 各省教育考试院 | 考研调剂网")
    print(f"  当前已有记录: {len(existing_records)}")
    print(f"{'='*50}\n")

    if not HAS_DEPS:
        print("缺少依赖库，跳过爬取。安装: pip install requests beautifulsoup4")
    else:
        sources = [
            ("考研帮(44校)", scrape_kaoyan_com),
            ("考研网(85校)", scrape_chinakaoyan),
            ("中国教育在线(旧)", scrape_eol),
            ("各校官网直达(50校)", scrape_official_sites),
            ("百度搜索(30校)", scrape_baidu_search),
            ("博客/知乎(20校)", scrape_blogs),
            ("GitHub数据集", scrape_github),
            ("研招网34所自划线", scrape_chsi),
            ("中国教育在线考研频道", scrape_eol_kaoyan),
            ("各校官网增强版(85校)", scrape_official_enhanced),
            ("新浪教育考研频道", scrape_sina_edu),
            ("腾讯教育考研频道", scrape_qq_edu),
            ("考研村分数线专题", scrape_kaoyancun),
            ("考满分分数线查询", scrape_kaomanfen),
            ("文都教育考研", scrape_wendu),
            ("海文考研分数线", scrape_haiwen),
            ("各省教育考试院", scrape_province_education),
            ("考研调剂网", scrape_tiaoji),
        ]
        for name, func in sources:
            print(f"\n--- {name} ---")
            try:
                new = func()
                if new:
                    print(f"  >> {name} 获取到 {len(new)} 条新记录")
                    for rec in new:
                        if "schoolMajorName" not in rec:
                            rec["schoolMajorName"] = rec.get("majorName", rec.get("majorId", "未知专业"))
                        if "categoryId" not in rec:
                            rec["categoryId"] = detect_category(rec.get("schoolMajorName", ""))
                        if "subjects" not in rec:
                            rec["subjects"] = ["思想政治理论", "英语一", "数学一", "专业课"]
                    data["records"].extend(new)
            except Exception as e:
                print(f"  >> {name} 异常: {e}")

    data["_meta"] = {
        "lastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totalSchools": len(data["schools"]),
        "totalRecords": len(data["records"]),
        "name": "考研分数线数据集 - 985/211/顶尖双非工科专业",
        "note": "数据来源: CPEER-Dataset (Younai2021) 开源数据集 + 各源爬虫补充。国家线数据来源: 研招网 yz.chsi.com.cn。"
    }

    # Ensure each record has schoolMajorName
    for rec in data["records"]:
        if "schoolMajorName" not in rec:
            rec["schoolMajorName"] = rec.get("schoolMajorName", rec.get("majorName", rec.get("majorId", "未知专业")))
        if "categoryId" not in rec:
            rec["categoryId"] = detect_category(rec.get("schoolMajorName", ""))

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 数据已保存: {OUTPUT_FILE}")
    print(f"  学校: {len(data['schools'])} | 类别: {len(CATEGORIES)} | 记录: {len(data['records'])}")

if __name__ == "__main__":
    main()
