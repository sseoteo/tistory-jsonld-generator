#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
범용 티스토리 JSON-LD 자동 생성기
------------------------------------
어떤 티스토리 블로그 포스팅 URL이든
JSON-LD 스키마 코드를 자동으로 생성해줍니다.

사용법:
  python tistory_jsonld.py
  또는 URL 직접 인수로 전달:
  python tistory_jsonld.py https://example.tistory.com/123
"""

import json
import re
import sys
from datetime import datetime
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("\n[오류] 필요한 패키지가 없습니다.")
    print("아래 명령어로 설치 후 다시 실행하세요.\n")
    print("  pip install requests beautifulsoup4\n")
    sys.exit(1)


# ──────────────────────────────────────────────
# 페이지 로딩
# ──────────────────────────────────────────────
def fetch_page(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "html.parser")
    except requests.exceptions.ConnectionError:
        print(f"\n  [오류] 페이지에 접근할 수 없습니다: {url}")
    except requests.exceptions.Timeout:
        print("\n  [오류] 페이지 로딩 시간이 초과됐습니다. 다시 시도해주세요.")
    except requests.exceptions.HTTPError as e:
        print(f"\n  [오류] HTTP 오류: {e}")
    except Exception as e:
        print(f"\n  [오류] 예상치 못한 오류: {e}")
    return None


# ──────────────────────────────────────────────
# 블로그 기본 정보 추출 (범용)
# ──────────────────────────────────────────────
def extract_blog_info(soup, url):
    parsed = urlparse(url)
    blog_url = f"{parsed.scheme}://{parsed.netloc}"
    blog_domain = parsed.netloc  # e.g. example.tistory.com

    # 블로그 이름: og:site_name 또는 title 앞부분
    blog_name = ""
    site_name_tag = soup.find("meta", property="og:site_name")
    if site_name_tag:
        blog_name = site_name_tag.get("content", "").strip()

    if not blog_name:
        title_tag = soup.find("title")
        if title_tag:
            # "포스팅 제목 :: 블로그이름" 패턴에서 블로그 이름 추출
            parts = title_tag.text.split("::")
            if len(parts) >= 2:
                blog_name = parts[-1].strip()
            else:
                blog_name = title_tag.text.strip()

    # 블로그 설명
    blog_desc = ""
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag:
        blog_desc = desc_tag.get("content", "").strip()

    # 블로그 로고/파비콘
    blog_logo = ""
    logo_candidates = [
        soup.find("link", rel="apple-touch-icon"),
        soup.find("link", rel=lambda r: r and "icon" in r),
    ]
    for candidate in logo_candidates:
        if candidate and candidate.get("href"):
            href = candidate["href"]
            blog_logo = href if href.startswith("http") else urljoin(blog_url, href)
            break

    # 저자 이름 (티스토리 공통 패턴)
    author = ""
    author_candidates = [
        soup.find("meta", attrs={"name": "author"}),
        soup.find("meta", property="article:author"),
        soup.find("meta", attrs={"name": "twitter:creator"}),
    ]
    for candidate in author_candidates:
        if candidate and candidate.get("content"):
            author = candidate["content"].strip()
            break

    # 저자명이 없으면 블로그명을 저자로 사용
    if not author:
        author = blog_name

    return {
        "blog_url": blog_url,
        "blog_domain": blog_domain,
        "blog_name": blog_name,
        "blog_desc": blog_desc,
        "blog_logo": blog_logo,
        "author": author,
    }


# ──────────────────────────────────────────────
# 포스팅 정보 추출
# ──────────────────────────────────────────────
def extract_post_info(soup, url):
    # 제목
    title = ""
    for sel in [
        soup.find("meta", property="og:title"),
        soup.find("meta", attrs={"name": "twitter:title"}),
        soup.find("h1"),
        soup.find("h2"),
    ]:
        if sel:
            val = sel.get("content") or sel.get_text()
            if val and val.strip():
                title = val.strip()
                # "제목 :: 블로그명" 패턴이면 제목만 추출
                if "::" in title:
                    title = title.split("::")[0].strip()
                break

    # 설명
    description = ""
    for sel in [
        soup.find("meta", property="og:description"),
        soup.find("meta", attrs={"name": "description"}),
        soup.find("meta", attrs={"name": "twitter:description"}),
    ]:
        if sel and sel.get("content"):
            description = sel["content"].strip()
            break

    # 설명이 없으면 본문 첫 문단 추출
    if not description:
        body_candidates = soup.select(
            "div.article-view, div#content, div.tt_article_useless_p_margin, "
            "div[id*='article'], div[class*='article'], div[class*='content']"
        )
        for body in body_candidates:
            paras = body.find_all("p")
            for p in paras:
                text = p.get_text(strip=True)
                if len(text) > 30:
                    description = text[:200]
                    break
            if description:
                break

    # 대표 이미지
    image = ""
    for sel in [
        soup.find("meta", property="og:image"),
        soup.find("meta", attrs={"name": "twitter:image"}),
    ]:
        if sel and sel.get("content"):
            image = sel["content"].strip()
            break

    # 발행일
    date_published = ""
    date_modified = ""
    date_candidates = [
        soup.find("meta", property="article:published_time"),
        soup.find("meta", attrs={"name": "article:published_time"}),
        soup.find("time"),
    ]
    for sel in date_candidates:
        if sel:
            val = sel.get("content") or sel.get("datetime") or sel.get_text()
            if val and val.strip():
                date_published = val.strip()
                break

    modified_tag = soup.find("meta", property="article:modified_time")
    if modified_tag:
        date_modified = modified_tag.get("content", "").strip()

    # 날짜 파싱 실패 시 오늘 날짜
    if not date_published:
        date_published = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00")

    if not date_modified:
        date_modified = date_published

    # 카테고리
    category = ""
    cat_candidates = [
        soup.find("meta", property="article:section"),
        soup.find("meta", attrs={"name": "article:section"}),
        soup.select_one("a[href*='category']"),
        soup.select_one(".category, #category, [class*='category']"),
    ]
    for sel in cat_candidates:
        if sel:
            val = sel.get("content") or sel.get_text()
            if val and val.strip():
                category = val.strip()
                break

    # 태그/키워드
    tags = []
    keywords_tag = soup.find("meta", attrs={"name": "keywords"})
    if keywords_tag and keywords_tag.get("content"):
        tags = [t.strip() for t in keywords_tag["content"].split(",") if t.strip()]

    if not tags:
        article_tags = soup.find_all("meta", property="article:tag")
        tags = [t.get("content", "").strip() for t in article_tags if t.get("content")]

    if not tags:
        tag_links = soup.select("a[href*='tag'], .tag, [class*='tag-link']")
        for t in tag_links[:10]:
            txt = t.get_text(strip=True)
            if txt and len(txt) < 30:
                tags.append(txt)

    return {
        "url": url,
        "title": title,
        "description": description,
        "image": image,
        "date_published": date_published,
        "date_modified": date_modified,
        "category": category,
        "tags": list(dict.fromkeys(tags)),  # 중복 제거
    }


# ──────────────────────────────────────────────
# 스키마 타입 판별
# ──────────────────────────────────────────────
def guess_schema_type(post_info):
    title = post_info["title"].lower()
    category = post_info["category"].lower()
    combined = title + " " + category

    if any(k in combined for k in ["리뷰", "후기", "사용기", "review"]):
        return "Review"
    if any(k in combined for k in ["레시피", "recipe", "요리", "만들기"]):
        return "Recipe"
    if any(k in combined for k in ["뉴스", "공지", "안내", "보도"]):
        return "NewsArticle"
    return "BlogPosting"


# ──────────────────────────────────────────────
# JSON-LD 생성
# ──────────────────────────────────────────────
def build_schema(post_info, blog_info, schema_type):
    schemas = []

    # 1. 메인 포스팅 스키마
    article = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": post_info["url"]
        },
        "headline": post_info["title"],
        "url": post_info["url"],
        "datePublished": post_info["date_published"],
        "dateModified": post_info["date_modified"],
        "author": {
            "@type": "Person",
            "name": blog_info["author"]
        },
        "publisher": {
            "@type": "Organization",
            "name": blog_info["blog_name"],
            "url": blog_info["blog_url"],
        },
        "inLanguage": "ko-KR",
    }

    if blog_info.get("blog_logo"):
        article["publisher"]["logo"] = {
            "@type": "ImageObject",
            "url": blog_info["blog_logo"]
        }

    if post_info["description"]:
        article["description"] = post_info["description"]

    if post_info["image"]:
        article["image"] = {
            "@type": "ImageObject",
            "url": post_info["image"]
        }

    if post_info["category"]:
        article["articleSection"] = post_info["category"]

    if post_info["tags"]:
        article["keywords"] = ", ".join(post_info["tags"])

    schemas.append(article)

    # 2. BreadcrumbList
    breadcrumb_items = [
        {
            "@type": "ListItem",
            "position": 1,
            "name": blog_info["blog_name"],
            "item": blog_info["blog_url"]
        }
    ]
    if post_info["category"]:
        breadcrumb_items.append({
            "@type": "ListItem",
            "position": 2,
            "name": post_info["category"],
            "item": blog_info["blog_url"]
        })
    breadcrumb_items.append({
        "@type": "ListItem",
        "position": len(breadcrumb_items) + 1,
        "name": post_info["title"],
        "item": post_info["url"]
    })

    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": breadcrumb_items
    }
    schemas.append(breadcrumb)

    return schemas


def format_output(schemas):
    result = []
    for schema in schemas:
        json_str = json.dumps(schema, ensure_ascii=False, indent=2)
        result.append(f'<script type="application/ld+json">\n{json_str}\n</script>')
    return "\n\n".join(result)


# ──────────────────────────────────────────────
# 미리보기 출력
# ──────────────────────────────────────────────
def print_preview(post_info, blog_info, schema_type):
    desc_preview = post_info["description"]
    if len(desc_preview) > 60:
        desc_preview = desc_preview[:60] + "..."

    print("\n" + "─" * 56)
    print("  추출된 정보 미리보기")
    print("─" * 56)
    print(f"  블로그명   : {blog_info['blog_name'] or '(찾지 못함)'}")
    print(f"  저자       : {blog_info['author'] or '(찾지 못함)'}")
    print(f"  제목       : {post_info['title'] or '(찾지 못함)'}")
    print(f"  발행일     : {post_info['date_published']}")
    print(f"  카테고리   : {post_info['category'] or '(찾지 못함)'}")
    print(f"  설명       : {desc_preview or '(찾지 못함)'}")
    print(f"  이미지     : {'있음' if post_info['image'] else '(찾지 못함)'}")
    print(f"  태그       : {', '.join(post_info['tags'][:5]) if post_info['tags'] else '(없음)'}")
    print(f"  스키마타입 : {schema_type}")
    print("─" * 56)


# ──────────────────────────────────────────────
# 결과 저장
# ──────────────────────────────────────────────
def save_result(output, url):
    slug = re.sub(r"[^\w]", "_", url.split("//")[-1])[:50]
    filename = f"jsonld_{slug}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(output)
    return filename


# ──────────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────────
def main():
    print("\n" + "=" * 56)
    print("   범용 티스토리 JSON-LD 자동 생성기")
    print("=" * 56)
    print("  어떤 티스토리 블로그 URL이든 붙여넣으면")
    print("  JSON-LD 스키마 코드를 자동으로 만들어줍니다.")
    print("  종료하려면 'q' 입력\n")

    # 인수로 URL이 직접 전달된 경우
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
        for url in urls:
            process_url(url)
        return

    while True:
        url = input("  URL 입력 > ").strip()

        if url.lower() == "q":
            print("\n  종료합니다.\n")
            break

        if not url.startswith("http"):
            print("  [!] http 또는 https로 시작하는 URL을 입력해주세요.\n")
            continue

        process_url(url)


def process_url(url):
    print("\n  페이지 읽는 중...")
    soup = fetch_page(url)
    if not soup:
        return

    print("  정보 추출 중...")
    blog_info = extract_blog_info(soup, url)
    post_info = extract_post_info(soup, url)
    schema_type = guess_schema_type(post_info)

    print_preview(post_info, blog_info, schema_type)

    fix = input("\n  그대로 생성할까요? (Enter=예 / n=직접 수정) > ").strip().lower()

    if fix == "n":
        print("\n  수정할 항목을 입력하세요. (변경 없으면 Enter)\n")

        new_title = input(f"  제목 [{post_info['title']}] > ").strip()
        if new_title:
            post_info["title"] = new_title

        new_author = input(f"  저자명 [{blog_info['author']}] > ").strip()
        if new_author:
            blog_info["author"] = new_author

        new_blog = input(f"  블로그명 [{blog_info['blog_name']}] > ").strip()
        if new_blog:
            blog_info["blog_name"] = new_blog

        new_desc = input(f"  설명 (Enter=유지) > ").strip()
        if new_desc:
            post_info["description"] = new_desc

        new_category = input(f"  카테고리 [{post_info['category']}] > ").strip()
        if new_category:
            post_info["category"] = new_category

        new_tags = input("  태그 (쉼표로 구분, Enter=유지) > ").strip()
        if new_tags:
            post_info["tags"] = [t.strip() for t in new_tags.split(",") if t.strip()]

        type_options = {"1": "BlogPosting", "2": "NewsArticle", "3": "Article", "4": "Review"}
        print(f"\n  스키마 타입: 1=BlogPosting  2=NewsArticle  3=Article  4=Review")
        new_type = input(f"  현재: {schema_type} (Enter=유지) > ").strip()
        if new_type in type_options:
            schema_type = type_options[new_type]

    schemas = build_schema(post_info, blog_info, schema_type)
    output = format_output(schemas)

    print("\n" + "─" * 56)
    print("  생성된 JSON-LD 코드")
    print("─" * 56)
    print(output)
    print("─" * 56)

    save_choice = input("\n  파일로 저장할까요? (Enter=예 / n=건너뜀) > ").strip().lower()
    if save_choice != "n":
        filename = save_result(output, url)
        print(f"\n  저장 완료: {filename}")
        print("  티스토리 HTML 편집 모드 맨 아래에 붙여넣으면 적용됩니다.\n")
    else:
        print("\n  위 코드를 복사해서 사용하세요.\n")


if __name__ == "__main__":
    main()
