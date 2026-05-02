import re

import anthropic

from app.config import get_settings
from app.services.crawler import CrawlData


def _extract_site_topic(crawl_data: CrawlData) -> str:
    page = crawl_data.main_page
    if not page:
        return crawl_data.domain

    parts = []

    # Title
    title = page.soup.find("title")
    if title:
        parts.append(title.get_text(strip=True))

    # Meta description
    meta = page.soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        parts.append(meta["content"])

    # H1
    h1 = page.soup.find("h1")
    if h1:
        parts.append(h1.get_text(strip=True))

    return " | ".join(parts) if parts else crawl_data.domain


async def _generate_queries(site_topic: str, domain: str) -> list[str]:
    settings = get_settings()
    client = anthropic.AsyncAnthropic(api_key=settings.claude_api_key)

    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Given this website topic/description: '{site_topic}' "
                        f"(domain: {domain}), generate exactly 5 search queries that "
                        f"a user might ask an AI assistant that could lead to this website "
                        f"being mentioned. Return only the queries, one per line, no numbering."
                    ),
                }
            ],
        )
        lines = [
            line.strip()
            for line in message.content[0].text.strip().split("\n")
            if line.strip()
        ]
        return lines[:5]
    except Exception:
        # Fallback queries
        return [
            f"What is {domain}?",
            f"Best services by {domain}",
            f"Tell me about {domain} company",
        ]


async def _check_claude_visibility(query: str, domain: str) -> dict:
    settings = get_settings()
    client = anthropic.AsyncAnthropic(api_key=settings.claude_api_key)

    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role": "user", "content": query}],
        )
        response_text = message.content[0].text.lower()
        domain_clean = domain.lower().replace("www.", "")

        mentioned = domain_clean in response_text
        # Also check brand name (domain without TLD)
        brand = domain_clean.split(".")[0]
        brand_mentioned = brand in response_text if len(brand) > 3 else False

        return {
            "query": query,
            "mentioned": mentioned or brand_mentioned,
            "domain_match": mentioned,
            "brand_match": brand_mentioned,
        }
    except Exception as e:
        return {"query": query, "mentioned": False, "error": str(e)[:100]}


async def score(crawl_data: CrawlData) -> dict:
    site_topic = _extract_site_topic(crawl_data)
    domain = crawl_data.domain

    queries = await _generate_queries(site_topic, domain)

    results = []
    for query in queries:
        result = await _check_claude_visibility(query, domain)
        results.append(result)

    mentions = sum(1 for r in results if r.get("mentioned"))
    total_queries = len(results)

    if total_queries == 0:
        visibility_score = 0
    else:
        visibility_score = round(mentions / total_queries * 100)

    details = {
        "queries_tested": total_queries,
        "mentions_found": mentions,
        "query_results": results,
        "site_topic": site_topic[:200],
    }

    return {"score": visibility_score, "details": details}
