import re
from datetime import datetime, timezone

from app.services.crawler import CrawlData


async def check_domain_age(domain: str) -> dict:
    try:
        import whois
        w = whois.whois(domain)
        creation_date = w.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0]
        if creation_date:
            age_days = (datetime.now(timezone.utc) - creation_date.replace(tzinfo=timezone.utc)).days
            age_years = age_days / 365.25

            if age_years >= 5:
                score = 100
            elif age_years >= 3:
                score = 80
            elif age_years >= 2:
                score = 70
            elif age_years >= 1:
                score = 50
            else:
                score = 30

            return {
                "creation_date": str(creation_date),
                "age_years": round(age_years, 1),
                "score": score,
            }
        return {"score": 40, "note": "Creation date not available in WHOIS"}
    except Exception as e:
        return {"score": 40, "note": f"WHOIS lookup failed: {str(e)[:100]}"}


def check_social_links(crawl_data: CrawlData) -> dict:
    social_patterns = {
        "twitter": r"(twitter\.com|x\.com)/",
        "facebook": r"facebook\.com/",
        "linkedin": r"linkedin\.com/",
        "instagram": r"instagram\.com/",
        "youtube": r"youtube\.com/",
    }

    found = {}
    for url, page in crawl_data.pages.items():
        for link in page.soup.find_all("a", href=True):
            href = link["href"]
            for platform, pattern in social_patterns.items():
                if platform not in found and re.search(pattern, href, re.I):
                    found[platform] = href

    score = min(len(found) * 20, 100)
    return {
        "platforms_found": list(found.keys()),
        "count": len(found),
        "score": score,
    }


def check_contact_info(crawl_data: CrawlData) -> dict:
    signals = []

    for url, page in crawl_data.pages.items():
        text = page.soup.get_text(separator=" ", strip=True).lower()

        # Check for email
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        if emails:
            signals.append("email")

        # Check for phone
        phones = re.findall(r"[\+]?[\d\-\(\)\s]{7,15}", text)
        if phones:
            signals.append("phone")

        # Check for address patterns
        if any(kw in text for kw in ["address", "location", "office"]):
            signals.append("address")

        # Check for contact page link
        for link in page.soup.find_all("a", href=True):
            if "contact" in link["href"].lower():
                signals.append("contact_page")
                break

    signals = list(set(signals))
    score = min(len(signals) * 25, 100)
    return {"signals": signals, "score": score}


def check_https_security(crawl_data: CrawlData) -> dict:
    page = crawl_data.main_page
    if not page:
        return {"score": 0}

    headers = page.headers
    security_headers = {
        "strict-transport-security": "HSTS",
        "x-content-type-options": "X-Content-Type-Options",
        "x-frame-options": "X-Frame-Options",
        "content-security-policy": "CSP",
    }

    found = []
    for header, name in security_headers.items():
        if header in headers:
            found.append(name)

    score = min(len(found) * 25, 100)
    return {"security_headers": found, "count": len(found), "score": score}


async def score(crawl_data: CrawlData) -> dict:
    domain_age = await check_domain_age(crawl_data.domain)
    social = check_social_links(crawl_data)
    contact = check_contact_info(crawl_data)
    security = check_https_security(crawl_data)

    details = {
        "domain_age": domain_age,
        "social_links": social,
        "contact_info": contact,
        "security_headers": security,
    }

    weights = {
        "domain_age": 0.3,
        "social_links": 0.25,
        "contact_info": 0.2,
        "security_headers": 0.25,
    }

    total = sum(details[k]["score"] * weights[k] for k in weights)
    return {"score": round(total), "details": details}
