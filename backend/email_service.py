"""Emergent-managed email sender for Jeana Marie's Kitchen Club.
All templates are server-side; callers pass IDs and typed args, never markup.
Follows email guardrails G1-G5."""
import os
import re
import ipaddress
import logging
import httpx
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse
from fastapi import HTTPException

logger = logging.getLogger(__name__)

EMAIL_BASE_URL = "https://integrations.emergentagent.com"

def _key() -> str: return os.environ["EMERGENT_EMAIL_KEY"]
def _from_name() -> str: return os.environ["EMAIL_FROM_NAME"]
def _reply_to() -> str: return os.environ.get("EMAIL_REPLY_TO", "")
def _app_url() -> str: return os.environ.get("APP_PUBLIC_URL", "").rstrip("/")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)

def _host_ok(host: str) -> bool:
    if not host or "xn--" in host: return False
    try: ipaddress.ip_address(host); return False
    except ValueError: pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)

def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)

class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []
    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href"); self._text = []
    def handle_data(self, data):
        if self._href is not None: self._text.append(data)
    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text))); self._href, self._text = None, []

def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan(); scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body: raise ValueError(f"Email asks for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")): continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real: continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")

async def send_email(*, to: str, subject: str, html: str) -> str | None:
    _assert_safe_email(subject, html)
    payload = {"to": [to], "subject": subject, "html": html, "from_name": _from_name()}
    rt = _reply_to()
    if rt: payload["contact_email"] = rt
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{EMAIL_BASE_URL}/api/v1/email/send",
                                     headers={"X-Email-Key": _key()}, json=payload)
        resp.raise_for_status()
        return resp.json().get("id")
    except httpx.HTTPStatusError as e:
        logger.error(f"Email send failed: {e.response.status_code} {e.response.text}")
        raise HTTPException(status_code=502, detail="Failed to send email")
    except Exception as e:
        logger.error(f"Email send error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email")

def _shell(inner: str, footer_extra: str = "") -> str:
    brand = escape(_from_name())
    return (f'<table role="presentation" width="100%" style="background:#FDFBF7;padding:24px 0;">'
            f'<tr><td align="center"><table role="presentation" width="560" style="background:#ffffff;'
            f'border-radius:16px;padding:32px;font-family:Georgia,serif;color:#2C1E16">'
            f'<tr><td style="font-family:Arial,sans-serif;font-size:12px;letter-spacing:2px;'
            f'text-transform:uppercase;color:#E07A5F;font-weight:bold">{brand}</td></tr>'
            f'<tr><td style="padding-top:14px">{inner}</td></tr>'
            f'<tr><td style="padding-top:24px;font-family:Arial,sans-serif;font-size:11px;color:#888;'
            f'border-top:1px solid #eee;padding-top:16px">'
            f'Sent by {brand}. We never ask for your password or card details by email.'
            f'{footer_extra}</td></tr></table></td></tr></table>')

async def send_password_reset(*, to: str, token: str) -> str | None:
    link = f"{_app_url()}/reset?token={escape(token)}"
    inner = (f'<h2 style="font-family:Georgia,serif;color:#2C1E16;margin:0 0 12px 0">Reset your password</h2>'
             f'<p style="font-family:Arial,sans-serif;color:#5C4A3D;line-height:1.6">Someone asked to reset '
             f'the password for your family account. If that was you, click the button below within the '
             f'next hour to choose a new one. If not, you can safely ignore this note.</p>'
             f'<p style="text-align:center;padding:20px 0"><a href="{link}" '
             f'style="background:#E07A5F;color:#ffffff;padding:14px 28px;border-radius:999px;'
             f'text-decoration:none;font-weight:bold;font-family:Arial,sans-serif">Choose a new password</a></p>'
             f'<p style="font-family:Arial,sans-serif;font-size:12px;color:#888">Link expires in 1 hour.</p>')
    return await send_email(to=to, subject="Reset your Kitchen Club password", html=_shell(inner))

async def send_receipt(*, to: str, family_name: str, plan_name: str, amount_cents: int, currency: str = "usd") -> str | None:
    inner = (f'<h2 style="font-family:Georgia,serif;color:#2C1E16;margin:0 0 12px 0">Thank you, {escape(family_name)}!</h2>'
             f'<p style="font-family:Arial,sans-serif;color:#5C4A3D;line-height:1.6">'
             f'Your Kitchen Club membership is active. Here are the details:</p>'
             f'<table style="font-family:Arial,sans-serif;font-size:14px;color:#2C1E16;margin:12px 0">'
             f'<tr><td style="padding:4px 12px 4px 0">Plan</td><td><strong>{escape(plan_name)}</strong></td></tr>'
             f'<tr><td style="padding:4px 12px 4px 0">Amount</td><td><strong>{currency.upper()} {amount_cents/100:.2f}</strong></td></tr>'
             f'</table>'
             f'<p style="text-align:center;padding:20px 0"><a href="{_app_url()}/app" '
             f'style="background:#E07A5F;color:#ffffff;padding:12px 24px;border-radius:999px;'
             f'text-decoration:none;font-weight:bold;font-family:Arial,sans-serif">Open your kitchen</a></p>')
    return await send_email(to=to, subject="Your Kitchen Club membership is active", html=_shell(inner))

async def send_weekly_drop(*, to: str, family_name: str, recipe_title: str, recipe_id: str, unsubscribe_token: str) -> str | None:
    unsub = f"{_app_url()}/unsubscribe?token={escape(unsubscribe_token)}"
    recipe_link = f"{_app_url()}/app/recipe/{escape(recipe_id)}"
    inner = (f'<h2 style="font-family:Georgia,serif;color:#2C1E16;margin:0 0 12px 0">This week in the kitchen</h2>'
             f'<p style="font-family:Arial,sans-serif;color:#5C4A3D;line-height:1.6">Hi {escape(family_name)}, '
             f'Jeana Maries new pick is ready:</p>'
             f'<p style="font-family:Georgia,serif;font-size:22px;color:#E07A5F;margin:16px 0"><strong>{escape(recipe_title)}</strong></p>'
             f'<p style="text-align:center;padding:20px 0"><a href="{recipe_link}" '
             f'style="background:#E07A5F;color:#ffffff;padding:12px 24px;border-radius:999px;'
             f'text-decoration:none;font-weight:bold;font-family:Arial,sans-serif">Open the recipe</a></p>')
    footer = f' <br><a href="{unsub}" style="color:#888">Unsubscribe from weekly recipe emails</a>.'
    return await send_email(to=to, subject=f"This week: {recipe_title}", html=_shell(inner, footer))
