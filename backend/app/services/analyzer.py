from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import AnalysisResult
from app.scoring import technical, structured, content, authority, visibility
from app.services.cache import set_cached_result
from app.services.crawler import crawl_site


def compute_grade(score: int) -> str:
    if score >= 85:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 30:
        return "D"
    return "F"


def generate_recommendations(categories: dict, language: str = "en") -> list[dict]:
    recs = []
    priority_map = {(0, 30): "high", (30, 60): "medium", (60, 100): "low"}

    def get_priority(score: int) -> str:
        for (lo, hi), p in priority_map.items():
            if lo <= score < hi:
                return p
        return "low"

    tips = {
        "technical": {
            "robots_txt": {
                "en": ("Add robots.txt", "Create a robots.txt file that allows AI crawlers to index your site."),
                "ko": ("robots.txt 추가", "AI 크롤러가 사이트를 인덱싱할 수 있도록 robots.txt 파일을 생성하세요."),
            },
            "sitemap_xml": {
                "en": ("Add XML Sitemap", "Create and submit an XML sitemap to help AI systems discover your pages."),
                "ko": ("XML 사이트맵 추가", "AI 시스템이 페이지를 발견할 수 있도록 XML 사이트맵을 생성하고 제출하세요."),
            },
            "ssl": {
                "en": ("Enable HTTPS", "Secure your site with SSL/TLS to build trust with AI systems."),
                "ko": ("HTTPS 활성화", "AI 시스템과의 신뢰를 구축하기 위해 SSL/TLS로 사이트를 보호하세요."),
            },
            "page_speed": {
                "en": ("Improve Page Speed", "Optimize loading performance. Faster sites are preferred by AI crawlers."),
                "ko": ("페이지 속도 개선", "로딩 성능을 최적화하세요. 빠른 사이트가 AI 크롤러에게 선호됩니다."),
            },
        },
        "structured": {
            "json_ld": {
                "en": ("Add Schema.org Markup", "Implement JSON-LD structured data so AI can understand your content."),
                "ko": ("Schema.org 마크업 추가", "AI가 콘텐츠를 이해할 수 있도록 JSON-LD 구조화 데이터를 구현하세요."),
            },
            "open_graph": {
                "en": ("Add Open Graph Tags", "Include og:title, og:description, og:image for better AI previews."),
                "ko": ("오픈 그래프 태그 추가", "더 나은 AI 미리보기를 위해 og:title, og:description, og:image를 포함하세요."),
            },
            "meta_description": {
                "en": ("Optimize Meta Description", "Write a clear, 120-160 character meta description for AI summaries."),
                "ko": ("메타 설명 최적화", "AI 요약을 위해 명확한 120-160자 메타 설명을 작성하세요."),
            },
            "heading_hierarchy": {
                "en": ("Fix Heading Structure", "Use a single H1 and logical H2-H6 hierarchy for AI readability."),
                "ko": ("헤딩 구조 수정", "AI 가독성을 위해 단일 H1과 논리적인 H2-H6 계층을 사용하세요."),
            },
        },
        "content": {
            "content_length": {
                "en": ("Add More Content", "Aim for 1000+ words of substantive content for better AI comprehension."),
                "ko": ("콘텐츠 추가", "더 나은 AI 이해를 위해 1000자 이상의 실질적인 콘텐츠를 목표로 하세요."),
            },
            "faq_presence": {
                "en": ("Add FAQ Section", "Include an FAQ section with schema markup for direct AI answers."),
                "ko": ("FAQ 섹션 추가", "직접적인 AI 답변을 위해 스키마 마크업이 포함된 FAQ 섹션을 추가하세요."),
            },
        },
        "authority": {
            "social_links": {
                "en": ("Add Social Media Links", "Link to your social profiles to establish brand authority."),
                "ko": ("소셜 미디어 링크 추가", "브랜드 권위를 확립하기 위해 소셜 프로필에 링크하세요."),
            },
        },
        "visibility": {
            "query_results": {
                "en": ("Improve AI Visibility", "Create content that directly answers common industry questions."),
                "ko": ("AI 가시성 개선", "일반적인 업계 질문에 직접 답변하는 콘텐츠를 만드세요."),
            },
        },
    }

    for cat_name, cat_data in categories.items():
        if cat_data["score"] >= 80:
            continue
        details = cat_data.get("details", {})
        cat_tips = tips.get(cat_name, {})
        for check_name, check_data in details.items():
            if isinstance(check_data, dict) and check_data.get("score", 100) < 70:
                tip = cat_tips.get(check_name, {}).get(language)
                if tip:
                    recs.append({
                        "category": cat_name,
                        "priority": get_priority(check_data["score"]),
                        "title": tip[0],
                        "description": tip[1],
                    })

    # Sort by priority
    order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: order.get(r["priority"], 3))
    return recs[:10]


async def run_full_analysis(analysis_id: str, db: AsyncSession):
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise ValueError(f"Analysis {analysis_id} not found")

    analysis.status = "processing"
    await db.commit()

    try:
        # Step 1: Crawl
        crawl_data = await crawl_site(analysis.url, analysis.domain)

        if not crawl_data.pages:
            raise ValueError(f"Could not fetch any pages for {analysis.domain}")

        # Step 2: Score each category
        tech_result = await technical.score(crawl_data)
        analysis.technical_score = tech_result["score"]
        analysis.technical_details = tech_result["details"]
        await db.commit()

        struct_result = await structured.score(crawl_data)
        analysis.structured_score = struct_result["score"]
        analysis.structured_details = struct_result["details"]
        await db.commit()

        cont_result = await content.score(crawl_data)
        analysis.content_score = cont_result["score"]
        analysis.content_details = cont_result["details"]
        await db.commit()

        auth_result = await authority.score(crawl_data)
        analysis.authority_score = auth_result["score"]
        analysis.authority_details = auth_result["details"]
        await db.commit()

        vis_result = await visibility.score(crawl_data)
        analysis.visibility_score = vis_result["score"]
        analysis.visibility_details = vis_result["details"]
        await db.commit()

        # Step 3: Compute overall
        overall = round(
            analysis.technical_score * 0.2
            + analysis.structured_score * 0.2
            + analysis.content_score * 0.2
            + analysis.authority_score * 0.2
            + analysis.visibility_score * 0.2
        )
        analysis.overall_score = overall
        analysis.grade = compute_grade(overall)

        # Step 4: Generate recommendations
        categories = {
            "technical": tech_result,
            "structured": struct_result,
            "content": cont_result,
            "authority": auth_result,
            "visibility": vis_result,
        }
        analysis.recommendations = generate_recommendations(categories, analysis.language)

        # Step 5: Generate summary
        analysis.summary = _generate_summary(analysis, analysis.language)

        analysis.status = "completed"
        analysis.completed_at = datetime.now(timezone.utc)
        await db.commit()

        # Cache result
        await set_cached_result(analysis.domain, str(analysis.id))

    except Exception as e:
        analysis.status = "failed"
        analysis.error_message = str(e)[:500]
        await db.commit()
        raise


def _generate_summary(analysis: AnalysisResult, language: str = "en") -> str:
    grade = analysis.grade
    score = analysis.overall_score

    if language == "ko":
        summaries = {
            "A": f"귀하의 사이트는 AI 검색 환경에 매우 잘 최적화되어 있습니다 (점수: {score}/100). 대부분의 AEO 기준을 충족하고 있으며, 작은 개선만으로 최고 수준을 유지할 수 있습니다.",
            "B": f"귀하의 사이트는 AI 검색에서 양호한 가시성을 보이고 있습니다 (점수: {score}/100). 몇 가지 핵심 영역을 개선하면 AI 답변 엔진에서 더 자주 인용될 수 있습니다.",
            "C": f"귀하의 사이트는 AI 가시성에서 개선의 여지가 있습니다 (점수: {score}/100). 구조화된 데이터와 콘텐츠 최적화에 집중하면 의미 있는 향상이 가능합니다.",
            "D": f"귀하의 사이트는 AI 검색 환경에서 낮은 노출을 보이고 있습니다 (점수: {score}/100). 기본적인 기술 설정과 콘텐츠 구조부터 개선이 필요합니다.",
            "F": f"귀하의 사이트는 AI 검색에서 거의 노출되지 않고 있습니다 (점수: {score}/100). 전반적인 AEO 전략 수립이 시급합니다.",
        }
    else:
        summaries = {
            "A": f"Your site is exceptionally well-optimized for AI search environments (Score: {score}/100). It meets most AEO criteria and only needs minor refinements to maintain top-tier visibility.",
            "B": f"Your site shows good visibility in AI search (Score: {score}/100). Improving a few key areas can help your site get cited more often by AI answer engines.",
            "C": f"Your site has room for improvement in AI visibility (Score: {score}/100). Focus on structured data and content optimization for meaningful gains.",
            "D": f"Your site has low exposure in AI search environments (Score: {score}/100). Start by improving basic technical setup and content structure.",
            "F": f"Your site has minimal visibility in AI search (Score: {score}/100). A comprehensive AEO strategy is urgently needed.",
        }

    return summaries.get(grade, summaries["C"])
