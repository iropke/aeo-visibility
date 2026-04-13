from pathlib import Path

import resend
from jinja2 import Template

from app.config import get_settings
from app.models.tables import AnalysisResult

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "email_report.html"


def _grade_color(grade: str) -> str:
    return {
        "A": "#22908b",
        "B": "#5eb6b2",
        "C": "#e6a817",
        "D": "#e67e22",
        "F": "#e74c3c",
    }.get(grade, "#5eb6b2")


async def send_report_email(analysis: AnalysisResult, email: str):
    settings = get_settings()
    if not settings.resend_api_key:
        return

    resend.api_key = settings.resend_api_key

    template_str = TEMPLATE_PATH.read_text(encoding="utf-8")
    template = Template(template_str)

    html = template.render(
        url=analysis.url,
        domain=analysis.domain,
        overall_score=analysis.overall_score,
        grade=analysis.grade,
        grade_color=_grade_color(analysis.grade or "B"),
        technical_score=analysis.technical_score or 0,
        structured_score=analysis.structured_score or 0,
        content_score=analysis.content_score or 0,
        authority_score=analysis.authority_score or 0,
        visibility_score=analysis.visibility_score or 0,
        summary=analysis.summary or "",
        recommendations=analysis.recommendations or [],
        frontend_url=settings.frontend_url,
        analysis_id=str(analysis.id),
    )

    resend.Emails.send(
        {
            "from": "AEO Visibility <noreply@aeo-visibility.vercel.app>",
            "to": [email],
            "subject": f"Your AEO Visibility Report - Score: {analysis.overall_score}/100 ({analysis.grade})",
            "html": html,
        }
    )
