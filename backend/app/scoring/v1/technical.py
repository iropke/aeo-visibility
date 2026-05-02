import httpx

from app.services.crawler import CrawlData


async def check_robots_txt(domain: str) -> dict:
    url = f"https://{domain}/robots.txt"
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url)
            found = resp.status_code == 200 and len(resp.text.strip()) > 0
            has_sitemap_ref = "sitemap:" in resp.text.lower() if found else False
            disallow_all = "disallow: /" in resp.text.lower() and "allow:" not in resp.text.lower() if found else False
            score = 0
            if found:
                score = 100
                if disallow_all:
                    score = 30  # Blocks crawlers
                if has_sitemap_ref:
                    score = min(score + 10, 100)
            return {"found": found, "has_sitemap_ref": has_sitemap_ref, "disallow_all": disallow_all, "score": score}
    except Exception:
        return {"found": False, "score": 0, "error": "Could not fetch robots.txt"}


async def check_sitemap(domain: str) -> dict:
    urls = [f"https://{domain}/sitemap.xml", f"https://{domain}/sitemap_index.xml"]
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for url in urls:
                resp = await client.get(url)
                if resp.status_code == 200 and ("<?xml" in resp.text[:100] or "<urlset" in resp.text[:500]):
                    return {"found": True, "url": url, "score": 100}
        return {"found": False, "score": 0}
    except Exception:
        return {"found": False, "score": 0, "error": "Could not check sitemap"}


async def check_ssl(url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False, verify=True) as client:
            resp = await client.get(url)
            is_https = str(resp.url).startswith("https://")
            return {"valid": is_https, "score": 100 if is_https else 0}
    except httpx.ConnectError:
        return {"valid": False, "score": 0, "error": "Connection failed"}
    except Exception:
        return {"valid": False, "score": 50, "note": "SSL check inconclusive"}


def check_canonical(crawl_data: CrawlData) -> dict:
    page = crawl_data.main_page
    if not page:
        return {"found": False, "score": 0}
    link = page.soup.find("link", rel="canonical")
    if link and link.get("href"):
        return {"found": True, "href": link["href"], "score": 100}
    return {"found": False, "score": 0}


def check_meta_viewport(crawl_data: CrawlData) -> dict:
    page = crawl_data.main_page
    if not page:
        return {"found": False, "score": 0}
    meta = page.soup.find("meta", attrs={"name": "viewport"})
    if meta and meta.get("content"):
        content = meta["content"]
        has_width = "width=" in content
        return {"found": True, "content": content, "score": 100 if has_width else 60}
    return {"found": False, "score": 0}


async def check_page_speed(url: str) -> dict:
    """Lightweight page speed check using response time heuristics."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url)
            elapsed_ms = resp.elapsed.total_seconds() * 1000
            content_length = len(resp.content)

            # Score based on response time
            if elapsed_ms < 500:
                speed_score = 100
            elif elapsed_ms < 1000:
                speed_score = 85
            elif elapsed_ms < 2000:
                speed_score = 70
            elif elapsed_ms < 3000:
                speed_score = 50
            else:
                speed_score = 30

            return {
                "response_time_ms": round(elapsed_ms),
                "content_size_kb": round(content_length / 1024, 1),
                "score": speed_score,
            }
    except Exception:
        return {"score": 0, "error": "Could not measure page speed"}


async def score(crawl_data: CrawlData) -> dict:
    domain = crawl_data.domain
    url = crawl_data.input_url

    robots = await check_robots_txt(domain)
    sitemap = await check_sitemap(domain)
    ssl = await check_ssl(url)
    canonical = check_canonical(crawl_data)
    viewport = check_meta_viewport(crawl_data)
    speed = await check_page_speed(url)

    details = {
        "robots_txt": robots,
        "sitemap_xml": sitemap,
        "ssl": ssl,
        "canonical": canonical,
        "mobile_viewport": viewport,
        "page_speed": speed,
    }

    weights = {
        "robots_txt": 0.15,
        "sitemap_xml": 0.15,
        "ssl": 0.2,
        "canonical": 0.1,
        "mobile_viewport": 0.15,
        "page_speed": 0.25,
    }

    total = sum(details[k]["score"] * weights[k] for k in weights)
    return {"score": round(total), "details": details}
