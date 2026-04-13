import re
from datetime import datetime, timezone

from app.services.crawler import CrawlData


def _extract_visible_text(crawl_data: CrawlData) -> str:
    page = crawl_data.main_page
    if not page:
        return ""

    soup = page.soup
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text


def check_content_length(crawl_data: CrawlData) -> dict:
    text = _extract_visible_text(crawl_data)
    word_count = len(text.split())

    if word_count >= 1500:
        score = 100
    elif word_count >= 1000:
        score = 85
    elif word_count >= 500:
        score = 70
    elif word_count >= 300:
        score = 50
    elif word_count >= 100:
        score = 30
    else:
        score = 10

    return {"word_count": word_count, "score": score}


def check_readability(crawl_data: CrawlData) -> dict:
    text = _extract_visible_text(crawl_data)
    if len(text.split()) < 30:
        return {"score": 50, "note": "Not enough text for readability analysis"}

    try:
        import textstat
        fk_grade = textstat.flesch_kincaid_grade(text)
        reading_ease = textstat.flesch_reading_ease(text)

        # Ideal: grade 8-12, reading ease 50-70
        if 6 <= fk_grade <= 12:
            score = 100
        elif fk_grade < 6:
            score = 70  # Too simple
        elif fk_grade <= 16:
            score = 60
        else:
            score = 40  # Too complex

        return {
            "flesch_kincaid_grade": round(fk_grade, 1),
            "flesch_reading_ease": round(reading_ease, 1),
            "score": score,
        }
    except Exception:
        return {"score": 50, "note": "Readability analysis unavailable"}


def check_faq_presence(crawl_data: CrawlData) -> dict:
    found_methods = []

    for url, page in crawl_data.pages.items():
        # Check for FAQ schema
        import json
        for script in page.soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict) and data.get("@type") == "FAQPage":
                    found_methods.append("faq_schema")
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "FAQPage":
                            found_methods.append("faq_schema")
            except (json.JSONDecodeError, AttributeError):
                continue

        # Check for FAQ in headings
        for heading in page.soup.find_all(["h1", "h2", "h3", "h4"]):
            text = heading.get_text(strip=True).lower()
            if any(kw in text for kw in ["faq", "frequently asked", "questions", "q&a"]):
                found_methods.append("faq_heading")
                break

        # Check for details/summary elements
        if page.soup.find("details"):
            found_methods.append("details_element")

    found_methods = list(set(found_methods))
    score = min(len(found_methods) * 50, 100) if found_methods else 0

    return {"found": bool(found_methods), "methods": found_methods, "score": score}


def check_content_freshness(crawl_data: CrawlData) -> dict:
    page = crawl_data.main_page
    if not page:
        return {"score": 50, "note": "No page data"}

    date_meta_names = [
        "article:modified_time",
        "article:published_time",
        "og:updated_time",
        "last-modified",
        "date",
        "DC.date.modified",
    ]

    for name in date_meta_names:
        meta = page.soup.find("meta", property=name) or page.soup.find("meta", attrs={"name": name})
        if meta and meta.get("content"):
            try:
                date_str = meta["content"]
                # Try parsing ISO format
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                days_ago = (datetime.now(timezone.utc) - date).days

                if days_ago <= 30:
                    score = 100
                elif days_ago <= 90:
                    score = 80
                elif days_ago <= 180:
                    score = 60
                elif days_ago <= 365:
                    score = 40
                else:
                    score = 20

                return {"last_modified": date_str, "days_ago": days_ago, "score": score}
            except (ValueError, TypeError):
                continue

    # Check Last-Modified header
    if page.headers.get("last-modified"):
        return {"last_modified": page.headers["last-modified"], "score": 60, "source": "header"}

    return {"score": 40, "note": "No modification date found"}


async def score(crawl_data: CrawlData) -> dict:
    length = check_content_length(crawl_data)
    readability = check_readability(crawl_data)
    faq = check_faq_presence(crawl_data)
    freshness = check_content_freshness(crawl_data)

    details = {
        "content_length": length,
        "readability": readability,
        "faq_presence": faq,
        "content_freshness": freshness,
    }

    weights = {
        "content_length": 0.3,
        "readability": 0.25,
        "faq_presence": 0.2,
        "content_freshness": 0.25,
    }

    total = sum(details[k]["score"] * weights[k] for k in weights)
    return {"score": round(total), "details": details}
