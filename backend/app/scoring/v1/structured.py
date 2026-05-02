import json
import re

from app.services.crawler import CrawlData


def check_jsonld(crawl_data: CrawlData) -> dict:
    page = crawl_data.main_page
    if not page:
        return {"found": False, "types": [], "score": 0}

    scripts = page.soup.find_all("script", type="application/ld+json")
    types = []
    for script in scripts:
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict):
                t = data.get("@type", "")
                if t:
                    types.append(t)
            elif isinstance(data, list):
                for item in data:
                    t = item.get("@type", "") if isinstance(item, dict) else ""
                    if t:
                        types.append(t)
        except (json.JSONDecodeError, AttributeError):
            continue

    if not types:
        return {"found": False, "types": [], "score": 0}

    # More schema types = better AI readability
    score = min(len(types) * 25, 100)
    return {"found": True, "types": types, "count": len(types), "score": score}


def check_og_tags(crawl_data: CrawlData) -> dict:
    page = crawl_data.main_page
    if not page:
        return {"found": {}, "score": 0}

    required = ["og:title", "og:description", "og:image", "og:url"]
    found = {}
    for tag in required:
        meta = page.soup.find("meta", property=tag)
        if meta and meta.get("content"):
            found[tag] = meta["content"]

    score = round(len(found) / len(required) * 100)
    return {"found": found, "missing": [t for t in required if t not in found], "score": score}


def check_meta_description(crawl_data: CrawlData) -> dict:
    page = crawl_data.main_page
    if not page:
        return {"found": False, "score": 0}

    meta = page.soup.find("meta", attrs={"name": "description"})
    if not meta or not meta.get("content"):
        return {"found": False, "score": 0}

    desc = meta["content"].strip()
    length = len(desc)

    if 120 <= length <= 160:
        score = 100
    elif 80 <= length < 120:
        score = 75
    elif 160 < length <= 200:
        score = 70
    elif 50 <= length < 80:
        score = 50
    else:
        score = 25

    return {"found": True, "length": length, "content": desc[:200], "score": score}


def check_heading_hierarchy(crawl_data: CrawlData) -> dict:
    page = crawl_data.main_page
    if not page:
        return {"score": 0}

    headings = {}
    for level in range(1, 7):
        tag = f"h{level}"
        found = page.soup.find_all(tag)
        if found:
            headings[tag] = len(found)

    if not headings:
        return {"headings": {}, "score": 0, "issues": ["No headings found"]}

    issues = []
    score = 100

    # Check H1
    h1_count = headings.get("h1", 0)
    if h1_count == 0:
        issues.append("Missing H1 tag")
        score -= 40
    elif h1_count > 1:
        issues.append(f"Multiple H1 tags ({h1_count})")
        score -= 20

    # Check logical hierarchy (H2 should exist if H3 does, etc.)
    for level in range(3, 7):
        tag = f"h{level}"
        parent = f"h{level - 1}"
        if tag in headings and parent not in headings:
            issues.append(f"{tag.upper()} found without {parent.upper()}")
            score -= 10

    # Bonus for depth
    if len(headings) >= 3:
        score = min(score + 10, 100)

    return {"headings": headings, "issues": issues, "score": max(score, 0)}


def check_twitter_cards(crawl_data: CrawlData) -> dict:
    page = crawl_data.main_page
    if not page:
        return {"found": False, "score": 0}

    card = page.soup.find("meta", attrs={"name": "twitter:card"})
    title = page.soup.find("meta", attrs={"name": "twitter:title"})

    found = bool(card and card.get("content"))
    return {"found": found, "score": 100 if found else 0}


async def score(crawl_data: CrawlData) -> dict:
    jsonld = check_jsonld(crawl_data)
    og = check_og_tags(crawl_data)
    meta_desc = check_meta_description(crawl_data)
    headings = check_heading_hierarchy(crawl_data)
    twitter = check_twitter_cards(crawl_data)

    details = {
        "json_ld": jsonld,
        "open_graph": og,
        "meta_description": meta_desc,
        "heading_hierarchy": headings,
        "twitter_cards": twitter,
    }

    weights = {
        "json_ld": 0.3,
        "open_graph": 0.2,
        "meta_description": 0.2,
        "heading_hierarchy": 0.2,
        "twitter_cards": 0.1,
    }

    total = sum(details[k]["score"] * weights[k] for k in weights)
    return {"score": round(total), "details": details}
