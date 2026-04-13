from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


@dataclass
class PageData:
    url: str
    status_code: int
    html: str
    soup: BeautifulSoup
    headers: dict


@dataclass
class CrawlData:
    domain: str
    input_url: str
    pages: dict[str, PageData] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def main_page(self) -> Optional[PageData]:
        return self.pages.get(self.input_url) or next(iter(self.pages.values()), None)


PATHS_TO_CHECK = ["/", "/about", "/contact", "/blog"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AEOVisibilityBot/1.0; "
        "+https://aeo-visibility.vercel.app)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


async def crawl_site(url: str, domain: str) -> CrawlData:
    data = CrawlData(domain=domain, input_url=url)
    base = f"https://{domain}"

    urls_to_fetch = [url]
    for path in PATHS_TO_CHECK:
        full = urljoin(base, path)
        if full != url:
            urls_to_fetch.append(full)

    async with httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=True,
        timeout=httpx.Timeout(10.0),
        verify=True,
    ) as client:
        for fetch_url in urls_to_fetch:
            try:
                resp = await client.get(fetch_url)
                if resp.status_code < 400:
                    soup = BeautifulSoup(resp.text, "lxml")
                    data.pages[fetch_url] = PageData(
                        url=fetch_url,
                        status_code=resp.status_code,
                        html=resp.text,
                        soup=soup,
                        headers=dict(resp.headers),
                    )
            except Exception as e:
                data.errors.append(f"{fetch_url}: {str(e)}")

    return data
