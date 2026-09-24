"""Deterministic branded recipe-card PDF generator (US Letter). Renders stored recipe data verbatim."""
import io
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

import requests
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image

logger = logging.getLogger(__name__)

FONT_DIR = "/usr/share/fonts/truetype/liberation"
VENDOR_FONT_DIR = str(Path(__file__).resolve().parent / "fonts")
ESPRESSO, MUTED, TERRACOTTA, HONEY, SAGE, CREAM = (44, 30, 22), (92, 74, 61), (224, 122, 95), (242, 204, 143), (129, 178, 154), (253, 251, 247)
TIER_LABEL = {"little": "Little Chefs (ages 3-5)", "junior": "Junior Cooks (ages 6-9)", "young": "Young Chefs (ages 10-12)",
              "teen": "Teen Kitchen (ages 13-15+)", "family": "Family Kitchen", "adult": "Family Kitchen"}
PAGE_W, MARGIN = 215.9, 16
CONTENT_W = PAGE_W - 2 * MARGIN
IMG_W, IMG_H = 70, 52  # mm, fixed frame; image is center-cropped to this ratio


class RecipeCardPDF(FPDF):
    def __init__(self, title: str):
        super().__init__(format="Letter", unit="mm")
        self.recipe_title = title
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=22)
        for style, f in (("", "Regular"), ("B", "Bold"), ("I", "Italic"), ("BI", "BoldItalic")):
            self.add_font("Sans", style, f"{FONT_DIR}/LiberationSans-{f}.ttf")
            self.add_font("Serif", style, f"{FONT_DIR}/LiberationSerif-{f}.ttf")
        # Glyph fallback (fractions like ⅓, check marks, etc.) — vendored, license-free DejaVu
        self.add_font("DejaVu", "", f"{VENDOR_FONT_DIR}/DejaVuSans.ttf")
        self.add_font("DejaVu", "B", f"{VENDOR_FONT_DIR}/DejaVuSans-Bold.ttf")
        self.add_font("DejaVu", "I", f"{VENDOR_FONT_DIR}/DejaVuSans.ttf")
        self.add_font("DejaVu", "BI", f"{VENDOR_FONT_DIR}/DejaVuSans-Bold.ttf")
        self.set_fallback_fonts(["DejaVu"])

    def header(self):
        y = 10; x = MARGIN
        self.set_draw_color(*ESPRESSO); self.set_line_width(0.3)
        self.set_fill_color(*SAGE); self.rect(x + 1, y + 9, 16, 3, style="FD")
        self.set_fill_color(*HONEY); self.rect(x + 2, y + 6, 14, 3, style="FD")
        self.set_fill_color(*TERRACOTTA); self.rect(x + 3, y + 3, 12, 3, style="FD")
        self.set_fill_color(*CREAM); self.ellipse(x + 5.5, y - 0.5, 7, 4, style="FD")
        self.set_xy(x + 22, y); self.set_font("Serif", "I", 10); self.set_text_color(*TERRACOTTA)
        self.cell(0, 4.5, "Jeana Marie's", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(x + 22); self.set_font("Sans", "B", 11); self.set_text_color(*ESPRESSO)
        self.cell(0, 5, "Kitchen Club", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if self.page_no() > 1:
            self.set_xy(x, y + 2); self.set_font("Sans", "I", 9); self.set_text_color(*MUTED)
            self.cell(0, 5, self.recipe_title, align="R")
        self.set_draw_color(*HONEY); self.set_line_width(0.6); self.line(MARGIN, y + 16, PAGE_W - MARGIN, y + 16)
        self.set_y(y + 21)

    def footer(self):
        self.set_y(-16)
        self.set_draw_color(*HONEY); self.set_line_width(0.4); self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.set_y(-13); self.set_font("Sans", "", 8); self.set_text_color(*MUTED)
        self.cell(CONTENT_W / 2, 5, "Jeana Marie's Kitchen Club  |  Supplemental family enrichment, not an accredited school")
        self.cell(CONTENT_W / 2, 5, f"Page {self.page_no()} of {{nb}}", align="R")

    # ---- building blocks ----
    def section(self, label: str):
        if self.get_y() > self.h - 45: self.add_page()
        self.ln(3)
        self.set_fill_color(*TERRACOTTA); self.rect(MARGIN, self.get_y() + 1, 2.2, 6, style="F")
        self.set_x(MARGIN + 5); self.set_font("Sans", "B", 12.5); self.set_text_color(*ESPRESSO)
        self.cell(0, 8, label.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def body(self, txt: str, size: float = 10.5, style: str = "", color=ESPRESSO, w: float = 0):
        self.set_font("Sans", style, size); self.set_text_color(*color)
        self.multi_cell(w or 0, 5.6, txt, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def _needed_height(self, txt: str, w: float, size: float = 10.5) -> float:
        self.set_font("Sans", "", size)
        lines = self.multi_cell(w, 5.6, txt, dry_run=True, output="LINES")
        return 5.6 * max(1, len(lines))

    def _ensure_space(self, h: float):
        if self.get_y() + h > self.h - self.b_margin: self.add_page()

    def bullet(self, txt: str):
        self._ensure_space(min(self._needed_height(txt, CONTENT_W - 6), 40))
        y0 = self.get_y()
        self.set_fill_color(*SAGE); self.ellipse(MARGIN + 1.5, y0 + 2.1, 1.8, 1.8, style="F")
        self.set_x(MARGIN + 6); self.body(txt, w=CONTENT_W - 6)

    def numbered(self, n: int, txt: str):
        self._ensure_space(min(self._needed_height(txt, CONTENT_W - 10), 40))
        y0 = self.get_y()
        self.set_fill_color(*TERRACOTTA); self.ellipse(MARGIN, y0 + 0.6, 6.5, 6.5, style="F")
        self.set_xy(MARGIN, y0 + 0.6); self.set_font("Sans", "B", 9.5); self.set_text_color(255, 255, 255)
        self.cell(6.5, 6.5, str(n), align="C")
        self.set_xy(MARGIN + 10, y0); self.body(txt, w=CONTENT_W - 10); self.ln(1.2)


def _fetch_image(recipe: dict, get_object) -> Optional[bytes]:
    try:
        if recipe.get("photo_file_id") and get_object is not None:
            data, _ = get_object(recipe["photo_file_id"]); return data
        url = (recipe.get("photo_url") or "").strip()
        if url.startswith("https://"):
            r = requests.get(url, timeout=8, headers={"User-Agent": "KitchenClub-RecipeCard/1.0"})
            if r.ok and r.headers.get("Content-Type", "").startswith("image/") and len(r.content) > 0: return r.content
    except Exception as e:
        logger.warning(f"Recipe card image unavailable ({type(e).__name__})")
    return None


def _prepare_image(raw: bytes) -> Optional[io.BytesIO]:
    """Center-crop to the IMG_W:IMG_H frame (no distortion), flatten to RGB JPEG."""
    try:
        im = Image.open(io.BytesIO(raw)); im.load()
        im = im.convert("RGB")
        target = IMG_W / IMG_H; w, h = im.size
        if w / h > target:
            nw = int(h * target); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = int(w / target); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
        im.thumbnail((1200, 1200))
        out = io.BytesIO(); im.save(out, "JPEG", quality=85, optimize=True); out.seek(0); return out
    except Exception as e:
        logger.warning(f"Recipe card image rejected ({type(e).__name__})"); return None


def build_recipe_card(recipe: dict, *, get_object=None, include_image: bool = True) -> Tuple[bytes, dict]:
    """Returns (pdf_bytes, meta). Text is rendered exactly as stored; sections appear only when data exists."""
    title = (recipe.get("title") or "Untitled recipe").strip()
    pdf = RecipeCardPDF(title)
    pdf.set_title(f"{title} - Recipe Card"); pdf.set_author("Jeana Marie's Kitchen Club")
    pdf.set_subject("Kitchen Club recipe card"); pdf.set_creator("Jeana Marie's Kitchen Club"); pdf.set_lang("en-US")
    try: pdf.set_creation_date(datetime.fromisoformat(recipe["published_at"]))
    except Exception: pdf.set_creation_date(datetime(2026, 1, 1, tzinfo=timezone.utc))
    pdf.alias_nb_pages()
    pdf.add_page()

    img = _prepare_image(_fetch_image(recipe, get_object)) if include_image and (recipe.get("photo_url") or recipe.get("photo_file_id")) else None
    top = pdf.get_y()
    text_w = CONTENT_W - (IMG_W + 6 if img else 0)

    # Title block
    tier = TIER_LABEL.get(recipe.get("tier") or "", recipe.get("tier") or "")
    if recipe.get("homeschool_topic") or tier:
        pdf.set_font("Sans", "B", 8.5); pdf.set_text_color(*SAGE)
        pdf.multi_cell(text_w, 4.5, "  |  ".join(x for x in (tier, recipe.get("homeschool_topic") or "") if x).upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Serif", "B", 24); pdf.set_text_color(*ESPRESSO)
    pdf.multi_cell(text_w, 10, title, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if recipe.get("description"):
        pdf.ln(1); pdf.set_font("Sans", "I", 10.5); pdf.set_text_color(*MUTED)
        pdf.multi_cell(text_w, 5.6, recipe["description"], align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Details chips
    details = []
    if recipe.get("prep_time") is not None: details.append(("Prep", f"{recipe['prep_time']} min"))
    if recipe.get("cook_time") is not None: details.append(("Cook", f"{recipe['cook_time']} min"))
    if recipe.get("prep_time") is not None and recipe.get("cook_time") is not None: details.append(("Total", f"{recipe['prep_time'] + recipe['cook_time']} min"))
    if recipe.get("yield_text"): details.append(("Makes", str(recipe["yield_text"])))
    elif recipe.get("servings") is not None: details.append(("Serves", str(recipe["servings"])))
    if recipe.get("time_text"):
        pdf.ln(1); pdf.set_font("Sans", "", 9); pdf.set_text_color(*MUTED)
        pdf.multi_cell(text_w, 5, str(recipe["time_text"]), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if details:
        pdf.ln(3); y = pdf.get_y(); x = MARGIN; chip_w = min(34, text_w / len(details) - 2)
        for label, val in details:
            pdf.set_fill_color(*CREAM); pdf.set_draw_color(*HONEY); pdf.set_line_width(0.4)
            pdf.rect(x, y, chip_w, 13, style="FD")
            pdf.set_xy(x, y + 1.2); pdf.set_font("Sans", "", 7.5); pdf.set_text_color(*MUTED); pdf.cell(chip_w, 4, label.upper(), align="C")
            pdf.set_xy(x, y + 5.6); pdf.set_font("Sans", "B", 11); pdf.set_text_color(*ESPRESSO); pdf.cell(chip_w, 6, val, align="C")
            x += chip_w + 2
        pdf.set_y(y + 15)

    if img:
        pdf.image(img, x=PAGE_W - MARGIN - IMG_W, y=top, w=IMG_W, h=IMG_H)
        pdf.set_draw_color(*HONEY); pdf.set_line_width(0.6); pdf.rect(PAGE_W - MARGIN - IMG_W, top, IMG_W, IMG_H)
        pdf.set_y(max(pdf.get_y(), top + IMG_H + 2))

    # Ingredients
    ingredients = [i for i in (recipe.get("ingredients") or []) if str(i).strip()]
    if ingredients:
        pdf.section("Ingredients")
        for i in ingredients: pdf.bullet(str(i))

    # Steps
    steps = [s for s in (recipe.get("steps") or []) if str(s).strip()]
    if steps:
        pdf.section("Instructions")
        for n, s in enumerate(steps, 1): pdf.numbered(n, str(s))

    # Optional stored sections (only rendered when present in the record)
    for key, label in (("safety_notes", "Safety & Adult Help"), ("tips", "Tips")):
        val = recipe.get(key)
        if val:
            pdf.section(label)
            if isinstance(val, list):
                for v in val: pdf.bullet(str(v))
            else: pdf.body(str(val))
    activities = recipe.get("activities") or recipe.get("lesson_plan")
    if activities or recipe.get("homeschool_topic"):
        pdf.section("Learning Activity")
        if recipe.get("homeschool_topic"): pdf.body(f"Topic: {recipe['homeschool_topic']}", style="B", color=SAGE)
        if isinstance(activities, list):
            for a in activities: pdf.bullet(str(a))
        elif activities: pdf.body(str(activities))

    data = bytes(pdf.output())
    return data, {"pages": pdf.pages_count, "size": len(data), "image_included": bool(img)}
