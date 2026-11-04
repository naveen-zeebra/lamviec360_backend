# ─────────────────────────────────────────────────────────────────────────────
# File    : shared/notifications/renderer.py
# Purpose : Token substitution & HTML/Plain-text email renderer
# ─────────────────────────────────────────────────────────────────────────────

import os
import re
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

from shared.notifications.templates.catalog import NOTIFICATION_CATALOG
from shared.environment import env

_LAYOUT_PATH = os.path.join(os.path.dirname(__file__), "templates", "master_layout.html")
_MASTER_LAYOUT_CACHE: Optional[str] = None


def get_master_layout() -> str:
    global _MASTER_LAYOUT_CACHE
    if _MASTER_LAYOUT_CACHE is None:
        if os.path.exists(_LAYOUT_PATH):
            with open(_LAYOUT_PATH, "r", encoding="utf-8") as f:
                _MASTER_LAYOUT_CACHE = f.read()
        else:
            _MASTER_LAYOUT_CACHE = "<html><body>{{body_content_html}}</body></html>"
    return _MASTER_LAYOUT_CACHE


def replace_tokens(text: str, context: Dict[str, Any]) -> str:
    """Replaces {{key}} in text with corresponding context value."""
    if not text:
        return ""
    result = text
    for key, val in context.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, str(val) if val is not None else "")
    return result


def strip_html_tags(html: str) -> str:
    """Helper to convert HTML to clean readable plain text."""
    clean = re.sub(r"<style[\s\S]*?>[\s\S]*?</style>", "", html, flags=re.IGNORECASE)
    clean = re.sub(r"<br\s*/?>", "\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"</p>", "\n\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"</div>", "\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<li[^>]*>", " • ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"[ \t]+", " ", clean)
    clean = re.sub(r"\n\s*\n", "\n\n", clean)
    return clean.strip()


def render_notification(
    event: str,
    language: str = "vi",
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, str]:
    """
    Renders subject, html_content, and text_content for a given scenario.
    Returns: (subject, html_content, text_content)
    """
    ctx = context.copy() if context else {}

    # Standard default system tokens
    ctx.setdefault("current_year", datetime.utcnow().year)
    ctx.setdefault("portal_url", env.JOBSEEKER_WEB_URL)
    ctx.setdefault("employer_dashboard_url", f"{env.COMPANY_WEB_URL}/company/overview")
    ctx.setdefault("employer_pipeline_url", f"{env.COMPANY_WEB_URL}/company/candidates")
    ctx.setdefault("tracker_url", f"{env.JOBSEEKER_WEB_URL}/applications")
    ctx.setdefault("unsubscribe_url", f"{env.JOBSEEKER_WEB_URL}/settings?tab=notifications")
    ctx.setdefault("privacy_url", f"{env.JOBSEEKER_WEB_URL}/privacy")
    ctx.setdefault("support_url", f"{env.JOBSEEKER_WEB_URL}/support")

    # Fetch scenario from catalog (default fallback: SCN-APP-01)
    scenario = NOTIFICATION_CATALOG.get(event)
    if not scenario:
        raise ValueError(f"Unknown notification event scenario: {event}")

    # Fallback to 'vi' if language is not supported in the scenario
    lang = language.lower() if language and language.lower() in ("vi", "en") else "vi"
    content_pack = scenario.get(lang) or scenario.get("vi")

    # Localized category badge
    badge_label = scenario.get(f"badge_{lang}") or scenario.get("badge_vi", "")
    badge_html = f'<div class="badge-status">{badge_label}</div>' if badge_label else ""

    # Subject & Headline
    raw_subject = content_pack.get("subject", "")
    subject = replace_tokens(raw_subject, ctx)

    raw_headline = content_pack.get("headline", "")
    headline = replace_tokens(raw_headline, ctx)

    # Body
    raw_body = content_pack.get("body", "")
    body_content = replace_tokens(raw_body, ctx)

    # Action Button
    cta_text = content_pack.get("cta_text", "")
    cta_url = replace_tokens(content_pack.get("cta_url", ""), ctx)
    action_button_html = ""
    if cta_text and cta_url:
        action_button_html = f'<div style="text-align: center; margin-top: 24px;"><a href="{cta_url}" class="btn-primary" target="_blank">{cta_text} &rarr;</a></div>'

    # Master Layout injection
    master_layout = get_master_layout()
    layout_context = {
        **ctx,
        "subject": subject,
        "headline": headline,
        "category_badge_html": badge_html,
        "body_content_html": body_content,
        "action_button_html": action_button_html,
    }
    html_output = replace_tokens(master_layout, layout_context)
    text_output = strip_html_tags(f"{headline}\n\n{body_content}\n\n{cta_text}: {cta_url}" if cta_url else f"{headline}\n\n{body_content}")

    return subject, html_output, text_output

