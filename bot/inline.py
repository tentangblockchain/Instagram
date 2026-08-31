import logging
import os
import re
import time

import yt_dlp
from telegram import InlineQueryResultArticle, InlineQueryResultVideo, InputTextMessageContent, Update
from telegram.ext import ContextTypes

from bot.constants import MESSAGES

logger = logging.getLogger(__name__)

TIKTOK_RE = re.compile(r"https?://(?:www\.)?(?:vm\.|vt\.)?tiktok\.com/\S+")
INSTAGRAM_RE = re.compile(r"https?://(?:www\.)?instagram\.com/\S+")

INLINE_VIDEO_MAX = 50 * 1024 * 1024


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query
    if not query or not query.query:
        return

    text = query.query.strip()
    user_id = query.from_user.id

    url, platform = _parse_url(text)
    if not url:
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    id="no_url",
                    title="Kirim URL Instagram / TikTok",
                    description="Contoh: @namabot instagram.com/reel/...",
                    input_message_content=InputTextMessageContent(
                        "URL tidak dikenal. Kirim link Instagram atau TikTok."
                    ),
                )
            ],
            cache_time=5,
        )
        return

    # Check membership
    channel_check = await _check_membership(update, context, user_id)
    if channel_check is not None:
        await query.answer(results=channel_check, cache_time=10)
        return

    # Check daily limit
    limit_check = await _check_daily_limit(update, context, user_id)
    if limit_check is not None:
        await query.answer(results=limit_check, cache_time=30)
        return

    # Try to get video URL
    cookies_path = context.bot_data.get("instagram_cookies", "")
    result = await _extract_video(url, platform, cookies_path)

    if result and result.get("success"):
        direct_url = result["video_url"]
        title = result.get("title", "")[:128] or f"{platform.title()} Video"
        caption = result.get("caption", "")[:1024]
        thumb = result.get("thumbnail")
        filesize = result.get("filesize", 0)
        duration = result.get("duration", 0)
        width = result.get("width", 0)
        height = result.get("height", 0)
        platform_emoji = "🎵" if platform == "tiktok" else "📱"

        results = []

        if direct_url and filesize < INLINE_VIDEO_MAX:
            results.append(
                InlineQueryResultVideo(
                    id=f"{platform}_vid_{int(time.time())}",
                    video_url=direct_url,
                    mime_type="video/mp4",
                    thumb_url=thumb or direct_url,
                    title=title,
                    caption=caption,
                    parse_mode="HTML",
                    video_width=width,
                    video_height=height,
                    video_duration=duration,
                )
            )

        fallback_url = direct_url if direct_url else url
        results.append(
            InlineQueryResultArticle(
                id=f"{platform}_txt_{int(time.time())}",
                title=f"{platform_emoji} {title}",
                description=f"Klik untuk kirim link • Kirim @namabot di DM untuk download"
                           if not direct_url
                           else f"Klik untuk kirim link ke chat",
                thumbnail_url=thumb,
                input_message_content=InputTextMessageContent(
                    f"<b>{platform_emoji} {title}</b>\n\n"
                    f"<code>{fallback_url}</code>",
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                ),
            )
        )

        await query.answer(results=results, cache_time=5)
    else:
        platform_name = "Instagram" if platform == "instagram" else "TikTok"
        await query.answer(
            results=[
                InlineQueryResultArticle(
                    id=f"{platform}_link_{int(time.time())}",
                    title=f"⬇️ Download {platform_name}",
                    description="Klik untuk kirim link, ketik /start di DM bot untuk download",
                    input_message_content=InputTextMessageContent(
                        f"<b>{platform_name}</b>\n\n<code>{url}</code>",
                        parse_mode="HTML",
                    ),
                )
            ],
            cache_time=5,
        )


async def chosen_inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user clicking inline result — auto-download to DM."""
    chosen = update.chosen_inline_result
    if not chosen:
        return

    result_id = chosen.result_id or ""
    user_id = chosen.from_user.id

    # Only process text/link results
    if "_vid_" in result_id:
        return

    url, _ = _parse_url(chosen.query)
    if not url:
        return

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=url,
        )
        logger.info(f"Inline: forwarded URL to DM of {user_id}")
    except Exception as e:
        logger.debug(f"Inline: can't DM {user_id} — {e}")


def _parse_url(text: str):
    for pattern, name in [(TIKTOK_RE, "tiktok"), (INSTAGRAM_RE, "instagram")]:
        m = pattern.search(text)
        if m:
            return m.group(0), name
    return None, None


async def _check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    channels = context.bot_data.get("required_channels", [])
    if not channels:
        return None

    bot = context.bot
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in ("member", "administrator", "creator"):
                raise ValueError("not member")
        except Exception:
            ch_list = "\n".join(f"• {c}" for c in channels)
            return [
                InlineQueryResultArticle(
                    id="not_member",
                    title="⛔ Join Channel Dulu",
                    description=f"Join {len(channels)} channel wajib",
                    input_message_content=InputTextMessageContent(
                        f"<b>Join channel berikut dulu:</b>\n{ch_list}\n\n"
                        f"Setelah join, coba inline lagi.",
                        parse_mode="HTML",
                    ),
                )
            ]
    return None


async def _check_daily_limit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    db = context.bot_data.get("db")
    if not db:
        return None
    admin_ids = context.bot_data.get("admin_ids", [])
    if user_id in admin_ids:
        return None
    is_vip = db.is_vip(user_id)
    limit = 100 if is_vip else 10
    count = db.get_daily_downloads(user_id)
    if count >= limit:
        return [
            InlineQueryResultArticle(
                id="limit",
                title="⛔ Limit Harian Habis",
                description=f"{count}/{limit} hari ini",
                input_message_content=InputTextMessageContent(
                    f"Limit download ({count}/{limit}) sudah habis. "
                    f"Ketik /start dan /menu_vip untuk upgrade."
                ),
            )
        ]
    return None


async def _extract_video(url: str, platform: str, cookies_path: str = "") -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "socket_timeout": 10,
    }
    if cookies_path and os.path.exists(cookies_path):
        opts["cookiefile"] = cookies_path
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        logger.debug(f"yt-dlp extract_info gagal untuk {platform}: {e}")
        return {"success": False}

    if not info:
        return {"success": False}

    video_url = None
    filesize = 0
    width = height = 0
    duration = info.get("duration") or 0
    title = (info.get("title") or info.get("description") or f"{platform.title()} Video")[:128]
    thumb = info.get("thumbnail") or info.get("thumbnails", [{}])[0].get("url") if info.get("thumbnails") else None
    caption = (info.get("description") or "")[:1024]

    def _try_format(fmt):
        if fmt.get("vcodec") != "none" and fmt.get("acodec") != "none":
            u = fmt.get("url") or fmt.get("manifest_url") or ""
            sz = fmt.get("filesize") or fmt.get("filesize_approx") or 0
            if u and sz > 0:
                return u, sz, fmt.get("width", 0), fmt.get("height", 0)
        elif fmt.get("vcodec") != "none" and not video_url:
            u = fmt.get("url") or fmt.get("manifest_url") or ""
            sz = fmt.get("filesize") or fmt.get("filesize_approx") or 0
            if u:
                return u, sz, fmt.get("width", 0), fmt.get("height", 0)
        return None

    req = info.get("requested_formats") or []
    if len(req) >= 2:
        video_url = req[0].get("url") or req[0].get("manifest_url") or ""
        filesize = (req[0].get("filesize") or 0) + (req[1].get("filesize") or 0)
        width = req[0].get("width") or 0
        height = req[0].get("height") or 0
    elif info.get("url"):
        video_url = info["url"]
        filesize = info.get("filesize") or info.get("filesize_approx") or 0
        width = info.get("width") or 0
        height = info.get("height") or 0
    else:
        fmts = info.get("formats") or []
        for f in fmts:
            r = _try_format(f)
            if r:
                video_url, filesize, width, height = r
                break

    if not video_url:
        return {"success": False}

    return {
        "success": True,
        "video_url": video_url,
        "title": title,
        "caption": caption,
        "thumbnail": thumb,
        "filesize": filesize,
        "duration": duration,
        "width": width,
        "height": height,
    }
