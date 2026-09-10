"""Jeana Marie's Kitchen Club - Backend API"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File, Form, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os
import io
import csv
import json
import logging
import uuid
import secrets
import string
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import stripe
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from collections import defaultdict, deque

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from storage import put_object, get_object, init_storage, APP_NAME
import email_service

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']
JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGO = "HS256"
JWT_EXP_HOURS = 24 * 30
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY') or 'sk_test_emergent'

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
_sync_client = MongoClient(MONGO_URL)
_sync_db = _sync_client[DB_NAME]

app = FastAPI(title="Jeana Marie's Kitchen Club API")
api = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)

# --- Helpers ---
def now_iso() -> str: return datetime.now(timezone.utc).isoformat()
def uid() -> str: return str(uuid.uuid4())
def hash_password(pw: str) -> str: return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
def verify_password(pw: str, hashed: str) -> bool:
    try: return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception: return False

def make_token(user_id: str, role: str, hours: int = JWT_EXP_HOURS) -> str:
    return jwt.encode({"sub": user_id, "role": role, "exp": datetime.now(timezone.utc) + timedelta(hours=hours)},
                      JWT_SECRET, algorithm=JWT_ALGO)

# --- Rate limiter (in-memory sliding window) ---
_rate_buckets: Dict[str, deque] = defaultdict(deque)

def real_ip(request: Request) -> str:
    """Get real client IP from proxy headers (Kubernetes ingress terminates the connection)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    return request.client.host if request.client else "unknown"

def rate_limit(key: str, max_hits: int, window_seconds: int):
    now = datetime.now(timezone.utc).timestamp()
    bucket = _rate_buckets[key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= max_hits:
        raise HTTPException(429, "Too many attempts. Please wait and try again.")
    bucket.append(now)

async def get_current_user(cred: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not cred: raise HTTPException(401, "Not authenticated")
    try: payload = jwt.decode(cred.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError: raise HTTPException(401, "Invalid or expired token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user: raise HTTPException(401, "User not found")
    return user

async def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin": raise HTTPException(403, "Admin only")
    return user

def has_active_membership(user: dict) -> bool:
    if user.get("role") == "admin": return True
    exp = user.get("membership_expires_at")
    if not exp: return False
    try: return datetime.fromisoformat(exp) > datetime.now(timezone.utc)
    except Exception: return False

def gen_redeem_code(prefix="JMK") -> str:
    return f"{prefix}-" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))

DURATION_DAYS = {"monthly": 30, "3month": 90, "6month": 180, "annual": 365}

# --- Feature Flags ---
DEFAULT_FLAGS = {
    # Launch-hidden features
    "kid_photo_upload": False,       # Q5: keep OFF for public launch
    "profile_pins": False,           # Sub-profile PINs
    "personalized_pdf_export": False,# Journal PDF export
    "advanced_analytics": False,     # Extra analytics dashboards
    "pwa_install": False,            # PWA prompt
    "weekly_challenges": False,      # Recipe challenges
    "adult_photo_upload": False,     # Journal photo uploads (adults)
    # Always-on for public launch
    "free_samples": True,
    "recipes_by_tier": True,
    "printables": True,
    "meal_costing": True,
    "notes_and_favorites": True,
    "admin_publishing": True,
    "stripe_checkout": True,
    "redeem_codes": True,
}

async def get_flags() -> Dict[str, bool]:
    doc = await db.settings.find_one({"key": "feature_flags"}, {"_id": 0})
    flags = dict(DEFAULT_FLAGS)
    if doc and doc.get("value"):
        flags.update(doc["value"])
    return flags

def _sync_get_flags() -> Dict[str, bool]:
    doc = _sync_db.settings.find_one({"key": "feature_flags"}, {"_id": 0})
    flags = dict(DEFAULT_FLAGS)
    if doc and doc.get("value"): flags.update(doc["value"])
    return flags

async def flag_required(name: str) -> None:
    flags = await get_flags()
    if not flags.get(name, False):
        raise HTTPException(403, f"Feature '{name}' is disabled")

# --- Models ---
class RegisterReq(BaseModel):
    email: EmailStr; password: str = Field(min_length=8); family_name: str
class LoginReq(BaseModel):
    email: EmailStr; password: str
class ForgotReq(BaseModel):
    email: EmailStr
class ResetReq(BaseModel):
    token: str; new_password: str = Field(min_length=8)
class PreferencesReq(BaseModel):
    email_optin_weekly: Optional[bool] = None
class FeaturedReq(BaseModel):
    recipe_id: Optional[str] = None
    starts_at: Optional[str] = None
    ends_at: Optional[str] = None
class ProfileCreate(BaseModel):
    name: str
    tier: Literal["little", "junior", "teen", "adult"]
    avatar_emoji: str = "🧒"
class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    tier: Optional[Literal["little", "junior", "teen", "adult"]] = None
    avatar_emoji: Optional[str] = None
    photo_opt_in: Optional[bool] = None
class RecipeBody(BaseModel):
    title: str
    tier: Literal["little", "junior", "teen", "adult"]
    description: str
    ingredients: List[str]
    steps: List[str]
    prep_time: int = 15
    cook_time: int = 15
    servings: int = 4
    photo_file_id: Optional[str] = None
    photo_url: Optional[str] = None  # legacy or external
    recipe_card_file_id: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    lesson_plan: Optional[str] = None
    homeschool_topic: Optional[str] = None
    published_at: Optional[str] = None
    is_sample: bool = False
class RecipePatch(BaseModel):
    title: Optional[str] = None; tier: Optional[str] = None; description: Optional[str] = None
    ingredients: Optional[List[str]] = None; steps: Optional[List[str]] = None
    prep_time: Optional[int] = None; cook_time: Optional[int] = None; servings: Optional[int] = None
    photo_file_id: Optional[str] = None; photo_url: Optional[str] = None
    recipe_card_file_id: Optional[str] = None
    categories: Optional[List[str]] = None
    lesson_plan: Optional[str] = None; homeschool_topic: Optional[str] = None
    published_at: Optional[str] = None; is_sample: Optional[bool] = None
class PrintableBody(BaseModel):
    title: str; tier: str; kind: str; description: str; content: str = ""
    pdf_file_id: Optional[str] = None
    thumbnail_file_id: Optional[str] = None
class PrintablePatch(BaseModel):
    title: Optional[str] = None; tier: Optional[str] = None; kind: Optional[str] = None
    description: Optional[str] = None; content: Optional[str] = None
    pdf_file_id: Optional[str] = None; thumbnail_file_id: Optional[str] = None
class JournalCreate(BaseModel):
    profile_id: str; recipe_id: Optional[str] = None; title: str; notes: str = ""
    photo_file_id: Optional[str] = None
class MealCostingCreate(BaseModel):
    profile_id: str; recipe_id: Optional[str] = None
    meal_name: str; servings: int = 4; items: List[Dict[str, Any]]
class RedeemReq(BaseModel):
    code: str
class GiftCertReq(BaseModel):
    to: str = Field(min_length=1, max_length=80)
    from_: str = Field(min_length=1, max_length=80, alias="from")
    code: str = Field(min_length=1, max_length=40)
    duration: Literal["monthly", "3month", "6month", "annual"] = "annual"
    message: Optional[str] = Field(default=None, max_length=280)
    model_config = {"populate_by_name": True}
class GenerateCodesReq(BaseModel):
    duration: Literal["monthly", "3month", "6month", "annual"]; count: int = 1; note: Optional[str] = None
class CheckoutReq(BaseModel):
    lookup_key: str; origin_url: str
class PortalReq(BaseModel):
    origin_url: str
class FavoriteReq(BaseModel):
    profile_id: str; recipe_id: str; made: bool = False
class FlagsUpdate(BaseModel):
    flags: Dict[str, bool]

# --- Startup ---
@app.on_event("startup")
async def startup():
    try:
        init_storage()
        logging.info("Object storage initialized")
    except Exception as e:
        logging.error(f"Storage init failed: {e}")

# --- Feature Flags endpoints ---
@api.get("/flags")
async def public_flags():
    """Public flag values so the frontend can gate UI."""
    return await get_flags()

@api.put("/admin/flags")
async def update_flags(body: FlagsUpdate, admin=Depends(require_admin)):
    await db.settings.update_one({"key": "feature_flags"}, {"$set": {"key": "feature_flags", "value": body.flags}}, upsert=True)
    return await get_flags()

# --- Auth ---
@api.post("/auth/register")
async def register(req: RegisterReq, request: Request):
    rate_limit(f"register:{real_ip(request)}", 10, 3600)
    if await db.users.find_one({"email": req.email.lower()}):
        raise HTTPException(400, "Email already registered")
    user = {"id": uid(), "email": req.email.lower(), "family_name": req.family_name,
            "password_hash": hash_password(req.password), "role": "family",
            "email_verified": False, "verification_token": secrets.token_urlsafe(24),
            "membership_expires_at": None, "created_at": now_iso()}
    await db.users.insert_one(user)
    return {"token": make_token(user["id"], user["role"]),
            "user": {k: v for k, v in user.items() if k not in ("password_hash", "_id", "verification_token")}}

@api.post("/auth/login")
async def login(req: LoginReq, request: Request):
    rate_limit(f"login:{real_ip(request)}:{req.email.lower()}", 5, 300)
    user = await db.users.find_one({"email": req.email.lower()}, {"_id": 0})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    user.pop("password_hash", None); user.pop("verification_token", None); user.pop("reset_token", None)
    return {"token": make_token(user["id"], user["role"]), "user": user}

@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    for k in ("password_hash", "verification_token", "reset_token", "reset_token_expires"):
        user.pop(k, None)
    user["has_active_membership"] = has_active_membership(user)
    # Surface subscription status so UI can render "Manage Membership" + "Cancels on <date>"
    user["subscription"] = {
        "has_stripe_subscription": bool(user.get("stripe_subscription_id")),
        "cancel_at_period_end": bool(user.get("subscription_cancel_at_period_end")),
        "current_period_end": user.get("subscription_current_period_end"),
        "status": user.get("subscription_status"),
    }
    return user

@api.post("/auth/forgot-password")
async def forgot(req: ForgotReq, request: Request):
    rate_limit(f"forgot:{real_ip(request)}", 5, 3600)
    user = await db.users.find_one({"email": req.email.lower()})
    if user:
        token = secrets.token_urlsafe(32)
        await db.users.update_one({"id": user["id"]}, {"$set": {
            "reset_token": token,
            "reset_token_expires": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }})
        try:
            await email_service.send_password_reset(to=user["email"], token=token)
        except Exception as e:
            logging.error(f"Password reset email failed: {e}")
    return {"ok": True}

@api.patch("/auth/preferences")
async def update_preferences(body: PreferencesReq, user=Depends(get_current_user)):
    upd = {}
    if body.email_optin_weekly is not None:
        upd["email_optin_weekly"] = bool(body.email_optin_weekly)
    if upd:
        await db.users.update_one({"id": user["id"]}, {"$set": upd})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0, "reset_token": 0})
    return u

@api.get("/unsubscribe")
async def unsubscribe(token: str):
    user = await db.users.find_one({"unsubscribe_token": token})
    if not user:
        return {"ok": False, "message": "Invalid unsubscribe link"}
    await db.users.update_one({"id": user["id"]}, {"$set": {"email_optin_weekly": False}})
    return {"ok": True, "message": "You have been unsubscribed from weekly recipe emails."}

@api.post("/admin/email/weekly-drop")
async def send_weekly_drop_broadcast(admin=Depends(require_admin)):
    doc = await db.settings.find_one({"key": "featured_recipe"}, {"_id": 0})
    rid = ((doc or {}).get("value") or {}).get("recipe_id")
    r = None
    if rid: r = await db.recipes.find_one({"id": rid}, {"_id": 0})
    if not r:
        r = await db.recipes.find_one({"is_sample": {"$ne": True}}, {"_id": 0}, sort=[("published_at", -1)])
    if not r: raise HTTPException(400, "No recipe available to announce")
    users = await db.users.find({"role": "family", "email_optin_weekly": {"$ne": False}}, {"_id": 0}).to_list(10000)
    sent, skipped, failed = 0, 0, 0
    for u in users:
        if not has_active_membership(u): skipped += 1; continue
        if not u.get("unsubscribe_token"):
            tok = secrets.token_urlsafe(24)
            await db.users.update_one({"id": u["id"]}, {"$set": {"unsubscribe_token": tok}})
            u["unsubscribe_token"] = tok
        try:
            await email_service.send_weekly_drop(
                to=u["email"], family_name=u.get("family_name", "there"),
                recipe_title=r["title"], recipe_id=r["id"],
                unsubscribe_token=u["unsubscribe_token"],
            )
            sent += 1
        except Exception as e:
            logging.error(f"Weekly drop send failed for {u.get('email')}: {e}")
            failed += 1
    return {"sent": sent, "skipped_inactive": skipped, "failed": failed, "recipe": r["title"]}  # Don't reveal existence

@api.post("/auth/reset-password")
async def reset(req: ResetReq, request: Request):
    rate_limit(f"reset:{real_ip(request)}", 10, 3600)
    user = await db.users.find_one({"reset_token": req.token})
    if not user:
        raise HTTPException(400, "Invalid or expired token")
    exp = user.get("reset_token_expires")
    if not exp or datetime.fromisoformat(exp) < datetime.now(timezone.utc):
        raise HTTPException(400, "Token expired")
    await db.users.update_one({"id": user["id"]}, {
        "$set": {"password_hash": hash_password(req.new_password)},
        "$unset": {"reset_token": "", "reset_token_expires": ""}
    })
    return {"ok": True}

# --- Files (Object Storage) ---
@api.post("/files/upload")
async def upload_file(file: UploadFile = File(...), purpose: str = Form("misc"), user=Depends(get_current_user)):
    """Upload a file to Object Storage. Returns file_id used to reference it."""
    # Kids-under-13 photo upload gate
    flags = await get_flags()
    if purpose == "child_photo" and not flags.get("kid_photo_upload"):
        raise HTTPException(403, "Child photo upload is disabled")
    if purpose == "adult_photo" and not flags.get("adult_photo_upload") and user.get("role") != "admin":
        raise HTTPException(403, "Photo upload is disabled")

    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 8MB)")

    ext = (file.filename or "bin").rsplit(".", 1)[-1].lower()[:8]
    file_id = uid()
    path = f"{APP_NAME}/{purpose}/{user['id']}/{file_id}.{ext}"
    result = put_object(path, data, file.content_type or "application/octet-stream")
    rec = {
        "id": file_id, "storage_path": result["path"], "purpose": purpose,
        "original_filename": file.filename, "content_type": file.content_type,
        "size": result.get("size", len(data)), "uploaded_by": user["id"],
        "is_deleted": False, "created_at": now_iso(),
    }
    await db.files.insert_one(rec)
    rec.pop("_id", None)
    return {"file_id": file_id, "url": f"/api/files/{file_id}"}

@api.get("/files/{file_id}")
async def download_file(file_id: str, auth: Optional[str] = Query(None), authorization: Optional[str] = Header(None)):
    """Serve stored file. Supports Bearer header or ?auth= for <img> tags."""
    rec = await db.files.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "File not found")
    # Basic auth check: must be logged in
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif auth:
        token = auth
    if not token:
        raise HTTPException(401, "Auth required")
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    try:
        data, ctype = get_object(rec["storage_path"])
    except Exception as e:
        raise HTTPException(500, f"Storage error: {e}")
    return Response(content=data, media_type=rec.get("content_type") or ctype,
                    headers={"Cache-Control": "private, max-age=3600"})

# --- Profiles ---
@api.get("/profiles")
async def list_profiles(user=Depends(get_current_user)):
    return await db.profiles.find({"user_id": user["id"]}, {"_id": 0}).to_list(20)

@api.post("/profiles")
async def create_profile(body: ProfileCreate, user=Depends(get_current_user)):
    if await db.profiles.count_documents({"user_id": user["id"]}) >= 6:
        raise HTTPException(400, "Maximum 6 profiles per family")
    p = {"id": uid(), "user_id": user["id"], "photo_opt_in": False, "pin": None,
         "created_at": now_iso(), **body.model_dump()}
    await db.profiles.insert_one(p); p.pop("_id", None); return p

@api.patch("/profiles/{pid}")
async def update_profile(pid: str, body: ProfileUpdate, user=Depends(get_current_user)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    r = await db.profiles.update_one({"id": pid, "user_id": user["id"]}, {"$set": upd})
    if r.matched_count == 0: raise HTTPException(404, "Not found")
    return await db.profiles.find_one({"id": pid}, {"_id": 0})

@api.delete("/profiles/{pid}")
async def delete_profile(pid: str, user=Depends(get_current_user)):
    await db.profiles.delete_one({"id": pid, "user_id": user["id"]}); return {"ok": True}

# --- Recipes ---
@api.get("/recipes/samples")
async def samples():
    return await db.recipes.find({"is_sample": True}, {"_id": 0}).limit(3).to_list(3)

@api.get("/recipes/featured")
async def get_featured(user=Depends(get_current_user)):
    doc = await db.settings.find_one({"key": "featured_recipe"}, {"_id": 0})
    val = (doc or {}).get("value", {}) or {}
    rid = val.get("recipe_id")
    now = datetime.now(timezone.utc)
    in_window = True
    starts, ends = val.get("starts_at"), val.get("ends_at")
    if starts:
        try:
            if datetime.fromisoformat(starts) > now: in_window = False
        except Exception: pass
    if ends:
        try:
            if datetime.fromisoformat(ends) < now: in_window = False
        except Exception: pass
    fallback_reason = None
    r = None
    if rid and in_window:
        r = await db.recipes.find_one({"id": rid}, {"_id": 0})
        if not r: fallback_reason = "featured recipe missing"
    else:
        fallback_reason = "no featured recipe scheduled" if not rid else "outside schedule window"
    if r is None:
        # Fallback to newest published non-sample recipe
        r = await db.recipes.find_one({"is_sample": {"$ne": True}}, {"_id": 0}, sort=[("published_at", -1)])
    if not r: return {"recipe": None, "fallback": bool(fallback_reason)}
    if not r.get("is_sample") and not has_active_membership(user):
        return {"recipe": None, "fallback": bool(fallback_reason)}
    return {"recipe": r, "fallback": bool(fallback_reason)}

@api.get("/recipes/this-week")
async def this_week(user=Depends(get_current_user)):
    if not has_active_membership(user): raise HTTPException(402, "Active membership required")
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    return await db.recipes.find({"published_at": {"$gte": since}}, {"_id": 0}).sort("published_at", -1).to_list(50)

@api.get("/recipes")
async def list_recipes(tier: Optional[str] = None, q: Optional[str] = None, category: Optional[str] = None, user=Depends(get_current_user)):
    if not has_active_membership(user): raise HTTPException(402, "Active membership required")
    query: Dict[str, Any] = {}
    if tier: query["tier"] = tier
    if q: query["title"] = {"$regex": q, "$options": "i"}
    if category: query["categories"] = category
    return await db.recipes.find(query, {"_id": 0}).sort("published_at", -1).to_list(500)

@api.get("/recipes/{rid}")
async def get_recipe(rid: str, user=Depends(get_current_user)):
    r = await db.recipes.find_one({"id": rid}, {"_id": 0})
    if not r: raise HTTPException(404, "Not found")
    if not r.get("is_sample") and not has_active_membership(user):
        raise HTTPException(402, "Active membership required")
    return r

@api.post("/recipes")
async def create_recipe(body: RecipeBody, admin=Depends(require_admin)):
    r = {"id": uid(), **body.model_dump(), "created_at": now_iso()}
    if not r.get("published_at"): r["published_at"] = now_iso()
    await db.recipes.insert_one(r); r.pop("_id", None); return r

@api.patch("/recipes/{rid}")
async def update_recipe(rid: str, body: RecipePatch, admin=Depends(require_admin)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    await db.recipes.update_one({"id": rid}, {"$set": upd})
    return await db.recipes.find_one({"id": rid}, {"_id": 0})

@api.delete("/recipes/{rid}")
async def delete_recipe(rid: str, admin=Depends(require_admin)):
    await db.recipes.delete_one({"id": rid}); return {"ok": True}

@api.post("/recipes/{rid}/duplicate")
async def duplicate_recipe(rid: str, admin=Depends(require_admin)):
    r = await db.recipes.find_one({"id": rid}, {"_id": 0})
    if not r: raise HTTPException(404, "Not found")
    r["id"] = uid()
    r["title"] = f"{r.get('title','')} (Copy)"
    r["is_sample"] = False
    r["published_at"] = now_iso()
    r["created_at"] = now_iso()
    await db.recipes.insert_one(r); r.pop("_id", None); return r

@api.get("/recipes/{rid}/card")
async def get_recipe_card(rid: str, user=Depends(get_current_user)):
    """Download the uploaded recipe card PDF (member-only)."""
    r = await db.recipes.find_one({"id": rid}, {"_id": 0})
    if not r: raise HTTPException(404, "Not found")
    if not r.get("is_sample") and not has_active_membership(user):
        raise HTTPException(402, "Active membership required")
    if not r.get("recipe_card_file_id"):
        raise HTTPException(404, "No recipe card attached")
    rec = await db.files.find_one({"id": r["recipe_card_file_id"], "is_deleted": False}, {"_id": 0})
    if not rec: raise HTTPException(404, "File missing")
    data, ctype = get_object(rec["storage_path"])
    return Response(content=data, media_type=rec.get("content_type") or ctype or "application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{r["title"].replace(" ","_")}_Recipe_Card.pdf"'})

# --- Favorites / Made ---
@api.get("/favorites/{pid}")
async def get_favs(pid: str, user=Depends(get_current_user)):
    return await db.favorites.find({"user_id": user["id"], "profile_id": pid}, {"_id": 0}).to_list(500)

@api.post("/favorites")
async def toggle_fav(body: FavoriteReq, user=Depends(get_current_user)):
    existing = await db.favorites.find_one({"user_id": user["id"], "profile_id": body.profile_id, "recipe_id": body.recipe_id})
    if existing:
        await db.favorites.update_one({"id": existing["id"]}, {"$set": {"made": body.made}})
        return {"ok": True, "action": "updated"}
    doc = {"id": uid(), "user_id": user["id"], "profile_id": body.profile_id,
           "recipe_id": body.recipe_id, "made": body.made, "created_at": now_iso()}
    await db.favorites.insert_one(doc); return {"ok": True, "action": "added"}

# --- Journal ---
@api.get("/journal/{pid}")
async def list_journal(pid: str, user=Depends(get_current_user)):
    return await db.journal.find({"user_id": user["id"], "profile_id": pid}, {"_id": 0}).sort("created_at", -1).to_list(500)

@api.post("/journal")
async def create_journal(body: JournalCreate, user=Depends(get_current_user)):
    if not has_active_membership(user):
        raise HTTPException(402, "Your membership has ended. Journal is read-only — reactivate to add notes.")
    flags = await get_flags()
    if body.photo_file_id and not flags.get("adult_photo_upload") and user.get("role") != "admin":
        raise HTTPException(403, "Photo attachment disabled")
    entry = {"id": uid(), "user_id": user["id"], **body.model_dump(), "created_at": now_iso()}
    await db.journal.insert_one(entry); entry.pop("_id", None); return entry

@api.delete("/journal/{eid}")
async def delete_journal(eid: str, user=Depends(get_current_user)):
    if not has_active_membership(user):
        raise HTTPException(402, "Your membership has ended. Journal is read-only.")
    await db.journal.delete_one({"id": eid, "user_id": user["id"]}); return {"ok": True}

def safe_txt(s: str) -> str:
    if not s: return ""
    return s.encode("latin-1", "replace").decode("latin-1")

def mcell(pdf: FPDF, h: float, txt: str, align: str = "L"):
    """multi_cell wrapper that resets cursor to left margin on next line - avoids fpdf2 default cursor drift."""
    pdf.multi_cell(0, h, safe_txt(txt), align=align, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

def draw_brand_header(pdf: FPDF, y: float = 10):
    """Draw the recipe book stack logo mark (mini) + brand line at top of the page."""
    x = 10
    # sage
    pdf.set_fill_color(129, 178, 154); pdf.set_draw_color(44, 30, 22); pdf.set_line_width(0.3)
    pdf.rect(x + 2, y + 12, 22, 4, style="FD")
    # honey
    pdf.set_fill_color(242, 204, 143)
    pdf.rect(x + 3.5, y + 8, 19, 4, style="FD")
    # terracotta
    pdf.set_fill_color(224, 122, 95)
    pdf.rect(x + 5, y + 4, 16, 4, style="FD")
    # chef hat (simple circle)
    pdf.set_fill_color(253, 251, 247)
    pdf.ellipse(x + 8, y - 1, 10, 6, style="FD")
    # brand text
    pdf.set_xy(x + 30, y + 3)
    pdf.set_font("Helvetica", "I", 11); pdf.set_text_color(224, 122, 95)
    pdf.cell(0, 5, safe_txt("Jeana Marie's"), ln=True)
    pdf.set_x(x + 30); pdf.set_font("Helvetica", "B", 13); pdf.set_text_color(44, 30, 22)
    pdf.cell(0, 6, safe_txt("Kitchen Club"))
    pdf.set_y(y + 22)

@api.get("/journal/{pid}/export")
async def export_journal(pid: str, user=Depends(get_current_user)):
    await flag_required("personalized_pdf_export")
    profile = await db.profiles.find_one({"id": pid, "user_id": user["id"]}, {"_id": 0})
    if not profile: raise HTTPException(404, "Profile not found")
    entries = await db.journal.find({"user_id": user["id"], "profile_id": pid}, {"_id": 0}).sort("created_at", 1).to_list(500)
    favs = await db.favorites.find({"user_id": user["id"], "profile_id": pid}, {"_id": 0}).to_list(500)
    recipes = await db.recipes.find({"id": {"$in": [f["recipe_id"] for f in favs]}}, {"_id": 0}).to_list(500) if favs else []

    pdf = FPDF(); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
    draw_brand_header(pdf)
    pdf.set_font("Helvetica", "B", 28); pdf.set_text_color(44, 30, 22); pdf.ln(20)
    pdf.multi_cell(0, 18, safe_txt(f"{user['family_name']} Family Cookbook"), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "I", 16); pdf.set_text_color(224, 122, 95)
    pdf.multi_cell(0, 12, safe_txt(f"By {profile['name']} - Jeana Marie's Kitchen Club"), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10); pdf.set_text_color(92, 74, 61); pdf.ln(10)
    pdf.cell(0, 8, safe_txt(f"Printed {datetime.now().strftime('%B %d, %Y')}"), ln=True, align="C")
    if entries:
        pdf.add_page(); pdf.set_font("Helvetica", "B", 20); pdf.set_text_color(44, 30, 22)
        pdf.cell(0, 14, "Journal", ln=True)
        for e in entries:
            pdf.set_font("Helvetica", "B", 14); pdf.set_text_color(224, 122, 95)
            pdf.cell(0, 10, safe_txt(e["title"]), ln=True)
            pdf.set_font("Helvetica", "", 11); pdf.set_text_color(44, 30, 22)
            pdf.multi_cell(0, 6, safe_txt(e.get("notes", "")), new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(4)
    for r in recipes:
        pdf.add_page(); pdf.set_font("Helvetica", "B", 18); pdf.set_text_color(44, 30, 22)
        pdf.multi_cell(0, 10, safe_txt(r["title"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "B", 12); pdf.cell(0, 8, "Ingredients", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for ing in r.get("ingredients", []): pdf.cell(0, 5, safe_txt(f"- {ing}"), ln=True)
        pdf.ln(3); pdf.set_font("Helvetica", "B", 12); pdf.cell(0, 8, "Steps", ln=True); pdf.set_font("Helvetica", "", 10)
        for i, s in enumerate(r.get("steps", []), 1): pdf.multi_cell(0, 5, safe_txt(f"{i}. {s}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    out = bytes(pdf.output(dest="S"))
    return Response(content=out, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={user['family_name'].replace(' ','_')}_Cookbook.pdf"})

# --- Meal Costing ---
@api.get("/meal-costs/{pid}")
async def list_costs(pid: str, user=Depends(get_current_user)):
    return await db.meal_costs.find({"user_id": user["id"], "profile_id": pid}, {"_id": 0}).sort("created_at", -1).to_list(500)

@api.post("/meal-costs")
async def create_cost(body: MealCostingCreate, user=Depends(get_current_user)):
    total = sum(float(i.get("qty", 1)) * float(i.get("unit_price", 0)) for i in body.items)
    per = total / max(1, body.servings)
    doc = {"id": uid(), "user_id": user["id"], **body.model_dump(),
           "total_cost": round(total, 2), "per_serving_cost": round(per, 2), "created_at": now_iso()}
    await db.meal_costs.insert_one(doc); doc.pop("_id", None); return doc

@api.delete("/meal-costs/{cid}")
async def delete_cost(cid: str, user=Depends(get_current_user)):
    await db.meal_costs.delete_one({"id": cid, "user_id": user["id"]}); return {"ok": True}

# --- Printables ---
@api.get("/printables")
async def list_printables(tier: Optional[str] = None, user=Depends(get_current_user)):
    q = {}
    if tier: q["tier"] = tier
    return await db.printables.find(q, {"_id": 0}).to_list(500)

@api.post("/printables")
async def create_printable(body: PrintableBody, admin=Depends(require_admin)):
    p = {"id": uid(), **body.model_dump(), "created_at": now_iso()}
    await db.printables.insert_one(p); p.pop("_id", None); return p

@api.patch("/printables/{pid}")
async def update_printable(pid: str, body: PrintablePatch, admin=Depends(require_admin)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    r = await db.printables.update_one({"id": pid}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(404, "Not found")
    return await db.printables.find_one({"id": pid}, {"_id": 0})

@api.delete("/printables/{pid}")
async def delete_printable(pid: str, admin=Depends(require_admin)):
    await db.printables.delete_one({"id": pid}); return {"ok": True}

@api.get("/printables/{pid}/pdf")
async def printable_pdf(pid: str, user=Depends(get_current_user)):
    p = await db.printables.find_one({"id": pid}, {"_id": 0})
    if not p: raise HTTPException(404, "Not found")

    # Track download
    await db.printables.update_one({"id": pid}, {"$inc": {"download_count": 1}})

    # Prefer uploaded PDF over generated template
    if p.get("pdf_file_id"):
        rec = await db.files.find_one({"id": p["pdf_file_id"], "is_deleted": False}, {"_id": 0})
        if rec:
            try:
                data, ctype = get_object(rec["storage_path"])
                return Response(content=data, media_type=rec.get("content_type") or ctype or "application/pdf",
                                headers={"Content-Disposition": f'attachment; filename="{p["title"].replace(" ","_")}.pdf"'})
            except Exception:
                pass  # fall through to generated

    pdf = FPDF(format="Letter"); pdf.set_auto_page_break(auto=True, margin=15); pdf.add_page()
    draw_brand_header(pdf)
    pdf.set_font("Helvetica", "B", 24); pdf.set_text_color(44, 30, 22)
    # Wrap long titles inside margins
    pdf.multi_cell(0, 12, safe_txt(p["title"]), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "I", 12); pdf.set_text_color(224, 122, 95)
    pdf.multi_cell(0, 7, safe_txt(f"Jeana Marie's Kitchen Club - {p['tier'].title()} Tier"), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(6); pdf.set_font("Helvetica", "", 12); pdf.set_text_color(44, 30, 22)
    pdf.multi_cell(0, 8, safe_txt(p.get("description", "")), new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(4)
    kind = p.get("kind")
    if kind == "shopping_list":
        pdf.set_font("Helvetica", "B", 14); pdf.cell(0, 10, "My Shopping List", ln=True); pdf.set_font("Helvetica", "", 12)
        for _ in range(20): pdf.cell(6, 10, "[ ]"); pdf.cell(0, 10, "_" * 60, ln=True)
    elif kind == "meal_costing":
        pdf.set_font("Helvetica", "B", 11)
        for h, w in [("Item", 80), ("Qty", 30), ("Unit Price", 35), ("Total", 35)]:
            pdf.cell(w, 8, h, border=1, ln=1 if h == "Total" else 0)
        pdf.set_font("Helvetica", "", 11)
        for _ in range(12):
            for w in [80, 30, 35]: pdf.cell(w, 10, "", border=1)
            pdf.cell(35, 10, "", border=1, ln=True)
    elif kind == "coloring":
        pdf.multi_cell(0, 8, safe_txt(p.get("content", "")), new_x=XPos.LMARGIN, new_y=YPos.NEXT); pdf.ln(10)
        pdf.set_draw_color(224, 122, 95); pdf.rect(30, pdf.get_y(), 150, 100)
    else:
        pdf.multi_cell(0, 8, safe_txt(p.get("content", "")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    out = bytes(pdf.output(dest="S"))
    return Response(content=out, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{p["title"].replace(" ","_")}.pdf"'})

@api.get("/printables/{pid}/thumbnail")
async def printable_thumbnail(pid: str):
    """Public thumbnail (no auth) for library thumbnails."""
    p = await db.printables.find_one({"id": pid}, {"_id": 0})
    if not p or not p.get("thumbnail_file_id"): raise HTTPException(404, "No thumbnail")
    rec = await db.files.find_one({"id": p["thumbnail_file_id"], "is_deleted": False}, {"_id": 0})
    if not rec: raise HTTPException(404, "Not found")
    data, ctype = get_object(rec["storage_path"])
    return Response(content=data, media_type=rec.get("content_type") or ctype,
                    headers={"Cache-Control": "public, max-age=3600"})

# --- Gift Certificate (public - no auth) ---
DURATION_LABEL = {"monthly": "1 Month", "3month": "3 Months", "6month": "6 Months", "annual": "1 Full Year"}

@api.post("/gift-certificate/pdf")
async def gift_certificate_pdf(body: GiftCertReq, request: Request):
    """Generate a printable gift certificate PDF. No auth: the certificate is just paper.
    We never validate the code here - it's a decorative wrapper for a code you already own."""
    rate_limit(f"giftpdf:{real_ip(request)}", 20, 3600)
    pdf = FPDF(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Warm background box
    pdf.set_fill_color(253, 251, 247)
    pdf.rect(10, 10, 195.6, 259, style="F")

    # Double border in terracotta
    pdf.set_draw_color(224, 122, 95)
    pdf.set_line_width(1.2); pdf.rect(15, 15, 185.6, 249)
    pdf.set_line_width(0.4); pdf.rect(19, 19, 177.6, 241)

    # Corner ornaments (sage)
    pdf.set_fill_color(129, 178, 154)
    for cx, cy in [(24, 24), (198, 24), (24, 258), (198, 258)]:
        pdf.ellipse(cx - 2, cy - 2, 4, 4, style="F")

    # Logo mark (mini) top-center
    center = 108
    pdf.set_fill_color(129, 178, 154); pdf.set_draw_color(44, 30, 22); pdf.set_line_width(0.3)
    pdf.rect(center - 12, 40, 24, 5, style="FD")
    pdf.set_fill_color(242, 204, 143)
    pdf.rect(center - 10, 35, 20, 5, style="FD")
    pdf.set_fill_color(224, 122, 95)
    pdf.rect(center - 8, 30, 16, 5, style="FD")
    pdf.set_fill_color(253, 251, 247)
    pdf.ellipse(center - 5, 22, 10, 6, style="FD")

    # Brand block
    pdf.set_y(55)
    pdf.set_font("Helvetica", "I", 22); pdf.set_text_color(224, 122, 95)
    pdf.cell(0, 10, safe_txt("Jeana Marie's"), ln=True, align="C")
    pdf.set_font("Helvetica", "B", 30); pdf.set_text_color(44, 30, 22)
    pdf.cell(0, 12, safe_txt("Kitchen Club"), ln=True, align="C")
    pdf.set_font("Helvetica", "", 11); pdf.set_text_color(92, 74, 61)
    pdf.cell(0, 6, safe_txt("Cooking and learning activities for homeschool families"), ln=True, align="C")

    # Certificate title
    pdf.ln(14)
    pdf.set_font("Helvetica", "B", 14); pdf.set_text_color(129, 178, 154)
    pdf.cell(0, 6, safe_txt("~ GIFT CERTIFICATE ~"), ln=True, align="C")

    # Recipient
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 11); pdf.set_text_color(92, 74, 61)
    pdf.cell(0, 5, safe_txt("This certificate is presented to"), ln=True, align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 26); pdf.set_text_color(44, 30, 22)
    pdf.cell(0, 12, safe_txt(body.to), ln=True, align="C")

    # Divider
    pdf.set_draw_color(224, 122, 95); pdf.set_line_width(0.4)
    pdf.line(80, pdf.get_y() + 4, 130, pdf.get_y() + 4)

    # Duration
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 11); pdf.set_text_color(92, 74, 61)
    pdf.cell(0, 5, safe_txt("For a family membership of"), ln=True, align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 24); pdf.set_text_color(224, 122, 95)
    pdf.cell(0, 12, safe_txt(DURATION_LABEL.get(body.duration, body.duration)), ln=True, align="C")

    # Message (optional)
    if body.message:
        pdf.ln(4)
        pdf.set_font("Helvetica", "I", 12); pdf.set_text_color(44, 30, 22)
        pdf.multi_cell(0, 6, safe_txt(f'"{body.message}"'), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Redeem code box
    pdf.ln(10)
    pdf.set_fill_color(244, 241, 234)
    pdf.rect(50, pdf.get_y(), 110, 22, style="F")
    y0 = pdf.get_y()
    pdf.set_font("Helvetica", "", 9); pdf.set_text_color(92, 74, 61)
    pdf.set_y(y0 + 3)
    pdf.cell(0, 5, safe_txt("REDEEM AT jeanamarie.club/redeem"), ln=True, align="C")
    pdf.set_font("Courier", "B", 20); pdf.set_text_color(44, 30, 22)
    pdf.cell(0, 10, safe_txt(body.code.upper()), ln=True, align="C")

    # From / signature
    pdf.ln(18)
    pdf.set_font("Helvetica", "", 11); pdf.set_text_color(92, 74, 61)
    pdf.cell(0, 5, safe_txt("With love from"), ln=True, align="C")
    pdf.set_font("Helvetica", "I", 20); pdf.set_text_color(224, 122, 95)
    pdf.cell(0, 12, safe_txt(body.from_), ln=True, align="C")

    # Footer note
    pdf.set_y(-25)
    pdf.set_font("Helvetica", "", 7); pdf.set_text_color(129, 178, 154)
    pdf.multi_cell(0, 3, safe_txt(
        "Jeana Marie's Kitchen Club provides family cooking activities and supplemental educational enrichment. "
        "It is not a school, accredited educational program or provider of academic credit."
    ), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    out = bytes(pdf.output(dest="S"))
    filename = f"KitchenClub_Gift_{body.to.replace(' ', '_')}.pdf"
    return Response(content=out, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})

# --- Redeem Codes ---
@api.post("/redeem")
async def redeem(body: RedeemReq, user=Depends(get_current_user)):
    code = await db.redeem_codes.find_one({"code": body.code.upper().strip()})
    if not code: raise HTTPException(404, "Invalid code")
    if code.get("redeemed_by"): raise HTTPException(400, "Code already redeemed")
    days = DURATION_DAYS[code["duration"]]
    cur = user.get("membership_expires_at")
    base = datetime.fromisoformat(cur) if cur and datetime.fromisoformat(cur) > datetime.now(timezone.utc) else datetime.now(timezone.utc)
    new_exp = base + timedelta(days=days)
    await db.users.update_one({"id": user["id"]}, {"$set": {"membership_expires_at": new_exp.isoformat()}})
    await db.redeem_codes.update_one({"code": code["code"]}, {"$set": {"redeemed_by": user["id"], "redeemed_at": now_iso()}})
    return {"ok": True, "duration": code["duration"], "membership_expires_at": new_exp.isoformat()}

@api.post("/admin/codes")
async def generate_codes(body: GenerateCodesReq, admin=Depends(require_admin)):
    batch_id = uid()
    codes = []
    for _ in range(body.count):
        c = {"id": uid(), "code": gen_redeem_code(), "duration": body.duration, "note": body.note,
             "batch_id": batch_id, "created_by": admin["id"],
             "redeemed_by": None, "redeemed_at": None, "created_at": now_iso()}
        await db.redeem_codes.insert_one(c); c.pop("_id", None); codes.append(c)
    return codes

@api.get("/admin/codes")
async def list_codes(admin=Depends(require_admin)):
    return await db.redeem_codes.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.get("/admin/families")
async def list_families(admin=Depends(require_admin)):
    users = await db.users.find({"role": "family"}, {"_id": 0, "password_hash": 0, "reset_token": 0, "verification_token": 0}).to_list(5000)
    for u in users:
        u["profile_count"] = await db.profiles.count_documents({"user_id": u["id"]})
        u["has_active_membership"] = has_active_membership(u)
    return users

@api.post("/admin/families/{uid_}/revoke")
async def revoke_family(uid_: str, admin=Depends(require_admin)):
    await db.users.update_one({"id": uid_}, {"$set": {"membership_expires_at": None}}); return {"ok": True}

@api.get("/admin/analytics")
async def analytics(admin=Depends(require_admin)):
    users_active = 0
    for u in await db.users.find({"role": "family"}, {"_id": 0}).to_list(10000):
        if has_active_membership(u): users_active += 1
    top = await db.favorites.aggregate([{"$group": {"_id": "$recipe_id", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": 5}]).to_list(5)
    top_recipes = []
    for t in top:
        r = await db.recipes.find_one({"id": t["_id"]}, {"_id": 0, "title": 1})
        top_recipes.append({"title": r["title"] if r else "?", "count": t["count"]})
    top_printables = []
    async for p in db.printables.find({}, {"_id": 0, "title": 1, "tier": 1, "kind": 1, "download_count": 1}).sort("download_count", -1).limit(10):
        top_printables.append({"title": p["title"], "tier": p.get("tier"), "kind": p.get("kind"),
                               "download_count": int(p.get("download_count") or 0)})
    return {
        "total_families": await db.users.count_documents({"role": "family"}),
        "active_families": users_active,
        "total_recipes": await db.recipes.count_documents({}),
        "total_printables": await db.printables.count_documents({}),
        "total_codes": await db.redeem_codes.count_documents({}),
        "codes_redeemed": await db.redeem_codes.count_documents({"redeemed_by": {"$ne": None}}),
        "top_recipes": top_recipes,
        "top_printables": top_printables,
    }

# --- Etsy Shop URL (public read, admin write) ---
class EtsyUrlReq(BaseModel):
    url: str = Field(default="", max_length=500)

@api.get("/branding/etsy-url")
async def get_etsy_url():
    doc = await db.settings.find_one({"key": "etsy_url"}, {"_id": 0})
    return {"url": (doc or {}).get("value", {}).get("url", "")}

@api.put("/admin/branding/etsy-url")
async def set_etsy_url(body: EtsyUrlReq, admin=Depends(require_admin)):
    await db.settings.update_one(
        {"key": "etsy_url"},
        {"$set": {"key": "etsy_url", "value": {"url": body.url.strip()}}},
        upsert=True,
    )
    return {"url": body.url.strip()}

# --- Recipe of the Week ---
@api.put("/admin/featured-recipe")
async def set_featured(body: FeaturedReq, admin=Depends(require_admin)):
    await db.settings.update_one(
        {"key": "featured_recipe"},
        {"$set": {"key": "featured_recipe", "value": {
            "recipe_id": body.recipe_id,
            "starts_at": body.starts_at,
            "ends_at": body.ends_at,
        }}},
        upsert=True,
    )
    return {"recipe_id": body.recipe_id, "starts_at": body.starts_at, "ends_at": body.ends_at}

@api.get("/admin/featured-recipe")
async def get_featured_admin(admin=Depends(require_admin)):
    doc = await db.settings.find_one({"key": "featured_recipe"}, {"_id": 0})
    return (doc or {}).get("value", {})

# --- Bulk print unredeemed codes ---
@api.get("/admin/codes/print-sheet.pdf")
async def codes_print_sheet(admin=Depends(require_admin)):
    codes = await db.redeem_codes.find({"redeemed_by": None}, {"_id": 0}).sort("created_at", -1).to_list(2000)
    pdf = FPDF(format="Letter"); pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page(); draw_brand_header(pdf)
    pdf.set_font("Helvetica", "B", 22); pdf.set_text_color(44, 30, 22); pdf.ln(6)
    mcell(pdf, 10, "Unredeemed Membership Codes", align="C")
    pdf.set_font("Helvetica", "I", 10); pdf.set_text_color(129, 178, 154)
    mcell(pdf, 6, f"Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')} - {len(codes)} codes total", align="C")
    pdf.ln(4)

    if not codes:
        pdf.set_font("Helvetica", "I", 11); pdf.set_text_color(129, 178, 154)
        mcell(pdf, 8, "No unredeemed codes. Generate some in the Admin > Codes tab.", align="C")
    else:
        # Group by (batch_id, duration). Legacy codes have no batch_id - group all under 'Legacy'.
        groups: Dict[Any, List[dict]] = {}
        for c in codes:
            key = (c.get("batch_id") or "legacy", c["duration"])
            groups.setdefault(key, []).append(c)
        # Sort groups: newest batch first (by first code created_at desc), duration alphabetical
        sorted_keys = sorted(groups.keys(), key=lambda k: (groups[k][0]["created_at"], k[1]), reverse=True)
        DUR = {"monthly": "Monthly", "3month": "3-Month", "6month": "6-Month", "annual": "Annual"}
        for i, key in enumerate(sorted_keys):
            batch_id, duration = key
            group_codes = groups[key]
            if i > 0: pdf.ln(4)
            when = group_codes[0]["created_at"][:10]
            pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(224, 122, 95)
            batch_label = "Legacy (pre-batch tracking)" if batch_id == "legacy" else f"Batch {batch_id[:8]}"
            mcell(pdf, 7, f"{DUR.get(duration, duration)} - {batch_label} - {when} - {len(group_codes)} code(s)")
            pdf.set_font("Helvetica", "B", 10); pdf.set_text_color(44, 30, 22)
            pdf.cell(75, 8, "Code", border=1)
            pdf.cell(30, 8, "Duration", border=1)
            pdf.cell(65, 8, "Note", border=1, ln=True)
            for c in group_codes:
                pdf.set_font("Courier", "B", 11); pdf.cell(75, 8, safe_txt(c["code"]), border=1)
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(30, 8, safe_txt(DUR.get(c["duration"], c["duration"])), border=1)
                pdf.cell(65, 8, safe_txt((c.get("note") or "")[:38]), border=1, ln=True)
    out = bytes(pdf.output(dest="S"))
    return Response(content=out, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="unredeemed_codes.pdf"'})

# --- Admin CSV/JSON export ---
@api.get("/admin/export/{entity}")
async def admin_export(entity: str, format: str = Query("csv"), admin=Depends(require_admin)):
    collections = {
        "families": ("users", {"role": "family"}, ["id", "email", "family_name", "role", "membership_expires_at", "email_verified", "created_at"]),
        "parents": ("users", {"role": "family"}, ["id", "email", "family_name", "email_verified", "created_at"]),
        "profiles": ("profiles", {}, ["id", "user_id", "name", "tier", "avatar_emoji", "photo_opt_in", "created_at"]),
        "recipes": ("recipes", {}, ["id", "title", "tier", "description", "prep_time", "cook_time", "servings", "homeschool_topic", "is_sample", "published_at", "created_at"]),
        "entitlements": ("users", {"role": "family"}, ["id", "email", "family_name", "membership_expires_at"]),
        "codes": ("redeem_codes", {}, ["id", "code", "duration", "note", "redeemed_by", "redeemed_at", "created_at"]),
        "subscriptions": ("payment_transactions", {}, ["session_id", "user_id", "lookup_key", "amount", "currency", "status", "payment_status", "stripe_subscription_id", "created_at"]),
    }
    if entity not in collections:
        raise HTTPException(400, f"Unknown entity. Valid: {list(collections)}")
    coll, filt, fields = collections[entity]
    docs = await db[coll].find(filt, {"_id": 0}).to_list(50000)
    if entity == "entitlements":
        for d in docs: d["active"] = has_active_membership(d)
        fields = fields + ["active"]
    if format == "json":
        return Response(content=json.dumps(docs, default=str, indent=2), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{entity}.json"'})
    # CSV
    buf = io.StringIO(); writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore"); writer.writeheader()
    for d in docs:
        row = {k: (str(d.get(k)) if d.get(k) is not None else "") for k in fields}
        writer.writerow(row)
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{entity}.csv"'})

# --- Logo (admin uploadable, served publicly) ---
@api.get("/branding/logo")
async def get_logo():
    doc = await db.settings.find_one({"key": "logo"}, {"_id": 0})
    if not doc:
        return {"file_id": None}
    return {"file_id": doc.get("value", {}).get("file_id")}

@api.post("/admin/branding/logo")
async def set_logo(file: UploadFile = File(...), admin=Depends(require_admin)):
    data = await file.read()
    if len(data) > 4 * 1024 * 1024:
        raise HTTPException(413, "Logo too large (max 4MB)")
    ext = (file.filename or "png").rsplit(".", 1)[-1].lower()[:8]
    fid = uid()
    path = f"{APP_NAME}/branding/logo/{fid}.{ext}"
    result = put_object(path, data, file.content_type or "image/png")
    rec = {"id": fid, "storage_path": result["path"], "purpose": "logo",
           "content_type": file.content_type, "is_deleted": False, "created_at": now_iso(),
           "uploaded_by": admin["id"], "original_filename": file.filename}
    await db.files.insert_one(rec)
    await db.settings.update_one({"key": "logo"}, {"$set": {"key": "logo", "value": {"file_id": fid, "content_type": file.content_type}}}, upsert=True)
    return {"file_id": fid}

@api.get("/branding/logo/raw")
async def get_logo_raw():
    """Public logo endpoint (no auth) - safe to embed via <img>."""
    doc = await db.settings.find_one({"key": "logo"}, {"_id": 0})
    if not doc: raise HTTPException(404, "No logo")
    fid = doc["value"]["file_id"]
    rec = await db.files.find_one({"id": fid, "is_deleted": False}, {"_id": 0})
    if not rec: raise HTTPException(404, "Not found")
    data, ctype = get_object(rec["storage_path"])
    return Response(content=data, media_type=rec.get("content_type") or ctype,
                    headers={"Cache-Control": "public, max-age=300"})

# --- Stripe Payments ---
PRICING = {
    "monthly": {"amount": 999, "interval": "month", "name": "Monthly Membership", "duration": "monthly"},
    "3month": {"amount": 2699, "interval": "month", "name": "3-Month Membership", "duration": "3month"},
    "6month": {"amount": 4999, "interval": "month", "name": "6-Month Membership", "duration": "6month"},
    "annual": {"amount": 8999, "interval": "year", "name": "Annual Membership", "duration": "annual"},
}

@api.get("/payments/pricing")
async def get_pricing():
    return [{"lookup_key": k, **v} for k, v in PRICING.items()]

@api.post("/payments/checkout")
async def checkout(body: CheckoutReq, user=Depends(get_current_user)):
    if body.lookup_key not in PRICING: raise HTTPException(400, "Invalid plan")
    prices = stripe.Price.list(lookup_keys=[body.lookup_key], active=True, limit=1).data
    if not prices: raise HTTPException(500, f"Price not configured: {body.lookup_key}")
    price = prices[0]
    kwargs = dict(
        line_items=[{"price": price.id, "quantity": 1}],
        mode="subscription" if price.recurring else "payment",
        success_url=f"{body.origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{body.origin_url}/payment/cancel",
        metadata={"user_id": user["id"], "lookup_key": body.lookup_key},
    )
    # Reuse existing Stripe customer when available so Manage Membership shows full history
    if user.get("stripe_customer_id"):
        kwargs["customer"] = user["stripe_customer_id"]
    else:
        kwargs["customer_email"] = user["email"]
    # Tag the subscription with our user_id so subscription.updated webhooks can find the user
    if price.recurring:
        kwargs["subscription_data"] = {"metadata": {"user_id": user["id"], "lookup_key": body.lookup_key}}
    try:
        session = stripe.checkout.Session.create(**kwargs, managed_payments={"enabled": True})
    except stripe.error.InvalidRequestError as e:
        msg = (e.user_message or "").lower()
        if "managed payments" in msg or "ineligible" in msg:
            session = stripe.checkout.Session.create(**kwargs, automatic_tax={"enabled": True}, billing_address_collection="required")
        else: raise
    _sync_db.payment_transactions.insert_one({
        "session_id": session.id, "user_id": user["id"], "lookup_key": body.lookup_key,
        "amount": (price.unit_amount or 0), "currency": price.currency,
        "status": "initiated", "payment_status": "pending",
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
    })
    return {"checkout_url": session.url, "session_id": session.id}

@api.post("/payments/portal")
async def customer_portal(body: PortalReq, user=Depends(get_current_user)):
    """Redirect a subscriber to Stripe's hosted Customer Portal to manage payment method,
    view invoices, or cancel future renewals (cancel_at_period_end)."""
    cust_id = user.get("stripe_customer_id")
    if not cust_id:
        raise HTTPException(400, "No Stripe customer on file. Please contact support.")
    try:
        session = stripe.billing_portal.Session.create(
            customer=cust_id,
            return_url=f"{body.origin_url}/app",
        )
    except stripe.error.InvalidRequestError as e:
        logging.error(f"Portal session creation failed for {user['email']}: {e}")
        raise HTTPException(400, "Couldn't open the billing portal. Please contact support.")
    return {"portal_url": session.url}

def _grant_membership(user_id: str, lookup_key: str):
    if lookup_key not in PRICING: return
    days = DURATION_DAYS[PRICING[lookup_key]["duration"]]
    u = _sync_db.users.find_one({"id": user_id})
    if not u: return
    cur = u.get("membership_expires_at")
    base = datetime.fromisoformat(cur) if cur and datetime.fromisoformat(cur) > datetime.now(timezone.utc) else datetime.now(timezone.utc)
    new_exp = base + timedelta(days=days)
    _sync_db.users.update_one({"id": user_id}, {"$set": {"membership_expires_at": new_exp.isoformat()}})

@api.get("/payments/status/{session_id}")
async def payment_status(session_id: str):
    rec = _sync_db.payment_transactions.find_one({"session_id": session_id})
    if not rec: raise HTTPException(404, "Not found")
    if rec.get("payment_status") != "paid":
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if s.payment_status == "paid" or s.status == "complete":
                _sync_db.payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "completed", "payment_status": "paid",
                              "stripe_subscription_id": s.subscription,
                              "updated_at": datetime.now(timezone.utc)}})
                _grant_membership(rec.get("user_id"), rec.get("lookup_key"))
                _attach_customer_and_subscription(rec.get("user_id"), s.get("customer"), s.get("subscription"))
                rec = _sync_db.payment_transactions.find_one({"session_id": session_id})
        except stripe.error.StripeError: pass
    return {"session_id": rec["session_id"], "status": rec["status"], "payment_status": rec["payment_status"]}

def _attach_customer_and_subscription(user_id: Optional[str], customer_id: Optional[str], subscription_id: Optional[str]):
    """Persist Stripe customer + subscription IDs on the user so the Customer Portal can be opened."""
    if not user_id: return
    upd = {}
    if customer_id: upd["stripe_customer_id"] = customer_id
    if subscription_id:
        upd["stripe_subscription_id"] = subscription_id
        try:
            sub = stripe.Subscription.retrieve(subscription_id)
            upd["subscription_status"] = sub.get("status")
            upd["subscription_cancel_at_period_end"] = bool(sub.get("cancel_at_period_end"))
            cpe = sub.get("current_period_end")
            if cpe: upd["subscription_current_period_end"] = datetime.fromtimestamp(cpe, tz=timezone.utc).isoformat()
        except stripe.error.StripeError: pass
    if upd:
        _sync_db.users.update_one({"id": user_id}, {"$set": upd})

def _sync_subscription_state(sub: dict):
    """Persist subscription changes (cancel_at_period_end, current_period_end, status) to the user doc.
    Also keeps membership_expires_at in sync with Stripe's current_period_end so auto-renewals extend access."""
    sub_id = sub.get("id")
    if not sub_id: return
    u = _sync_db.users.find_one({"stripe_subscription_id": sub_id}) \
        or _sync_db.users.find_one({"id": (sub.get("metadata") or {}).get("user_id")})
    if not u: return
    upd = {
        "stripe_subscription_id": sub_id,
        "stripe_customer_id": sub.get("customer") or u.get("stripe_customer_id"),
        "subscription_status": sub.get("status"),
        "subscription_cancel_at_period_end": bool(sub.get("cancel_at_period_end")),
    }
    cpe = sub.get("current_period_end")
    if cpe:
        iso = datetime.fromtimestamp(cpe, tz=timezone.utc).isoformat()
        upd["subscription_current_period_end"] = iso
        # Sync membership access to Stripe's period end (both for renewals and cancel_at_period_end)
        cur = u.get("membership_expires_at")
        try:
            cur_dt = datetime.fromisoformat(cur) if cur else None
        except Exception:
            cur_dt = None
        new_dt = datetime.fromtimestamp(cpe, tz=timezone.utc)
        if cur_dt is None or new_dt > cur_dt:
            upd["membership_expires_at"] = iso
    _sync_db.users.update_one({"id": u["id"]}, {"$set": upd})

@api.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    obj, t = event["data"]["object"], event["type"]
    if t == "checkout.session.completed":
        _sync_db.payment_transactions.update_one(
            {"session_id": obj["id"], "payment_status": {"$ne": "paid"}},
            {"$set": {"status": "completed", "payment_status": obj.get("payment_status", "paid"),
                      "stripe_subscription_id": obj.get("subscription"),
                      "updated_at": datetime.now(timezone.utc)}})
        meta = obj.get("metadata") or {}
        _grant_membership(meta.get("user_id"), meta.get("lookup_key"))
        _attach_customer_and_subscription(meta.get("user_id"), obj.get("customer"), obj.get("subscription"))
    elif t in ("customer.subscription.updated", "customer.subscription.created"):
        _sync_subscription_state(obj)
    elif t == "customer.subscription.deleted":
        # Subscription fully ended. Keep membership_expires_at as-is so access continues through paid period.
        _sync_subscription_state(obj)
        sub_id = obj.get("id")
        if sub_id:
            _sync_db.users.update_one(
                {"stripe_subscription_id": sub_id},
                {"$set": {"subscription_status": "canceled", "subscription_cancel_at_period_end": False}},
            )
    elif t == "invoice.payment_succeeded":
        # Auto-renewal invoice — refresh subscription state to extend access
        sub_id = obj.get("subscription")
        if sub_id:
            try:
                sub = stripe.Subscription.retrieve(sub_id)
                _sync_subscription_state(sub)
            except stripe.error.StripeError: pass
    elif t == "invoice.payment_failed":
        sub_id = obj.get("subscription")
        if sub_id:
            _sync_db.users.update_one(
                {"stripe_subscription_id": sub_id},
                {"$set": {"subscription_status": "past_due"}},
            )
    return {"status": "ok"}

@api.get("/")
async def root(): return {"message": "Jeana Marie's Kitchen Club API"}

app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','), allow_methods=["*"], allow_headers=["*"])

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
