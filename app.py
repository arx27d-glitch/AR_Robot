import logging
import re
import os
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
import asyncio
import config
import aiohttp
import traceback
import math
import mimetypes
import secrets

from config import multi_clients, work_loads
from AloneX.helpers import pyro_utils
from AloneX.helpers.render_template import render_page

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()


# Landing page. Plain HTML/CSS/JS (no build step, no CDN): the "glow card grid" effect is a port of the
# React/Tailwind GlowCardGrid component. Every card has a blurred copy of its icon that follows the pointer
# and shows through a backdrop-filtered border ring, so the borders glow towards the cursor.
LANDING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#0a0e1a">
    <meta name="description" content="AR Assistant Bot: AI tools, movies and anime, a smart chatbot, fonts, calculator and group management on Telegram.">
    <title>AR X Bot</title>
    <style>
        :root {
            color-scheme: dark;
            --bg: #0a0e1a;
            --fg: #f4f6fb;
            --muted: rgba(244, 246, 251, 0.55);
            --ring: rgba(255, 255, 255, 0.12);
            --accent: #4CAF50;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html {
            -webkit-text-size-adjust: 100%;
        }

        body {
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
            color: var(--fg);
            line-height: 1.6;
            min-height: 100vh;
            background:
                radial-gradient(1100px 560px at 15% -10%, rgba(41, 76, 160, 0.55) 0%, transparent 62%),
                radial-gradient(900px 520px at 100% 0%, rgba(22, 120, 70, 0.40) 0%, transparent 58%),
                var(--bg);
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 32px 20px 24px;
        }

        /* ---------- hero ---------- */
        .hero {
            text-align: center;
            padding: 56px 20px 44px;
        }

        .hero img {
            width: 132px;
            height: 132px;
            object-fit: cover;
            border-radius: 50%;
            border: 3px solid var(--accent);
            box-shadow: 0 0 44px rgba(76, 175, 80, 0.35);
        }

        .hero h1 {
            margin-top: 22px;
            font-size: clamp(2rem, 5.2vw, 3rem);
            letter-spacing: -0.02em;
            line-height: 1.15;
            background: linear-gradient(90deg, #8BC34A, #4CAF50 45%, #38bdf8);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        .hero p {
            margin-top: 10px;
            color: var(--muted);
            font-size: 1.05rem;
        }

        .cta-button {
            display: inline-block;
            margin-top: 26px;
            padding: 14px 34px;
            color: #fff;
            text-decoration: none;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            border-radius: 30px;
            background: linear-gradient(45deg, #4CAF50, #8BC34A);
            box-shadow: 0 4px 18px rgba(76, 175, 80, 0.32);
            transition: transform 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
        }

        .cta-button:hover {
            background: linear-gradient(45deg, #45a049, #7CB342);
            transform: translateY(-2px);
            box-shadow: 0 6px 22px rgba(76, 175, 80, 0.45);
        }

        .section-title {
            margin: 6px 0 22px;
            text-align: center;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: var(--muted);
        }

        /* ---------- glow card grid (port of GlowCardGrid / GlowCard) ---------- */
        .glow-grid {
            --card-radius: 16px;

            --card-icon-blur: 25px;
            --card-icon-saturate: 5;
            --card-icon-brightness: 1.3;
            --card-icon-scale: 4;
            --card-icon-opacity: 0.3;

            --card-border-width: 3px;
            --card-border-blur: 10px;
            --card-border-saturate: 4.2;
            --card-border-brightness: 2.5;
            --card-border-contrast: 2.5;

            display: grid;
            gap: 16px;
            width: 100%;
            grid-template-columns: 1fr;
        }

        @media (min-width: 640px) {
            .glow-grid { grid-template-columns: repeat(2, 1fr); }
        }

        @media (min-width: 900px) {
            .glow-grid { grid-template-columns: repeat(3, 1fr); }
        }

        .glow-card {
            position: relative;
            width: 100%;
            height: 13rem;
            overflow: hidden;
            border-radius: var(--card-radius);
            background: rgba(255, 255, 255, 0.03);
            box-shadow: 0 0 0 1px var(--ring);
            container-type: size;
            -webkit-user-select: none;
            user-select: none;
            transition: transform 0.2s ease;
        }

        .glow-card:active {
            transform: scale(0.98);
        }

        .glow-card__inner {
            position: absolute;
            inset: 0;
            display: flex;
            overflow: hidden;
            border-radius: var(--card-radius);
            clip-path: inset(0 round var(--card-radius));
        }

        /* blurred, enlarged copy of the icon that follows the pointer */
        .glow-card__bg {
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            pointer-events: none;
            transform: translate3d(calc(var(--pointer-x, -10) * 50cqi), calc(var(--pointer-y, -10) * 50cqh), 0)
                       scale(var(--card-icon-scale));
            filter: blur(var(--card-icon-blur)) brightness(var(--card-icon-brightness)) saturate(var(--card-icon-saturate));
            opacity: var(--card-icon-opacity);
            will-change: transform, filter;
        }

        .glow-card__bg svg {
            width: 5rem;
            height: 5rem;
        }

        .glow-card__content {
            position: relative;
            z-index: 1;
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 14px;
            padding: 0 18px;
            text-align: center;
        }

        .glow-card__icon {
            display: grid;
            place-items: center;
            width: 64px;
            height: 64px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.06);
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
        }

        .glow-card__icon svg {
            width: 30px;
            height: 30px;
        }

        .glow-card__title {
            font-size: 1rem;
            font-weight: 600;
            line-height: 1.1;
            color: var(--fg);
        }

        .glow-card__text {
            margin-top: 6px;
            font-size: 0.85rem;
            line-height: 1.35;
            color: rgba(244, 246, 251, 0.5);
        }

        /* the glowing ring: only the border area of this layer is visible (mask), and it boosts what is behind it */
        .glow-card__border {
            position: absolute;
            inset: 0;
            pointer-events: none;
            border-radius: var(--card-radius);
            border: var(--card-border-width) solid transparent;
            -webkit-backdrop-filter: blur(var(--card-border-blur)) brightness(var(--card-border-brightness))
                                     contrast(var(--card-border-contrast)) saturate(var(--card-border-saturate));
            backdrop-filter: blur(var(--card-border-blur)) brightness(var(--card-border-brightness))
                             contrast(var(--card-border-contrast)) saturate(var(--card-border-saturate));
            clip-path: inset(0 round var(--card-radius));
            -webkit-mask-image: linear-gradient(#fff 0 100%), linear-gradient(#fff 0 100%);
            mask-image: linear-gradient(#fff 0 100%), linear-gradient(#fff 0 100%);
            -webkit-mask-origin: border-box, padding-box;
            mask-origin: border-box, padding-box;
            -webkit-mask-clip: border-box, padding-box;
            mask-clip: border-box, padding-box;
            -webkit-mask-composite: xor;
            mask-composite: exclude;
        }

        footer {
            margin-top: 56px;
            padding: 22px 20px;
            text-align: center;
            color: var(--muted);
            border-top: 1px solid rgba(255, 255, 255, 0.07);
        }

        footer a {
            color: var(--accent);
            text-decoration: none;
        }

        footer a:hover {
            text-decoration: underline;
        }

        @media (max-width: 640px) {
            .hero { padding: 36px 12px 32px; }
            .hero img { width: 110px; height: 110px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <section class="hero">
            <img src="https://i.ibb.co/PZmh6bkf/file-337.jpg" alt="TOJI">
            <h1>AR Assistant Bot</h1>
            <p>Your all-in-one Telegram assistant powered by AI</p>
            <a href="https://t.me/arProGuardBot?start=help" class="cta-button">Start Using Bot</a>
        </section>

        <h2 class="section-title">What it can do</h2>

        <div class="glow-grid" id="glow-grid">
            <div class="glow-card" data-slot="glow-card" style="color: hsl(150 85% 62%)">
                <div class="glow-card__inner">
                    <div class="glow-card__bg" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
                    </div>
                    <div class="glow-card__content">
                        <div class="glow-card__icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
                        </div>
                        <div>
                            <h3 class="glow-card__title">AI Tools</h3>
                            <p class="glow-card__text">Advanced AI-powered features for chat, image generation, and more</p>
                        </div>
                    </div>
                </div>
                <div class="glow-card__border"></div>
            </div>

            <div class="glow-card" data-slot="glow-card" style="color: hsl(330 90% 68%)">
                <div class="glow-card__inner">
                    <div class="glow-card__bg" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3Z"/><path d="m6.2 5.3 3.1 3.9"/><path d="m12.4 3.4 3.1 4"/><path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/></svg>
                    </div>
                    <div class="glow-card__content">
                        <div class="glow-card__icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3Z"/><path d="m6.2 5.3 3.1 3.9"/><path d="m12.4 3.4 3.1 4"/><path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/></svg>
                        </div>
                        <div>
                            <h3 class="glow-card__title">Movies &amp; Anime</h3>
                            <p class="glow-card__text">Access to a vast collection of movies and anime content</p>
                        </div>
                    </div>
                </div>
                <div class="glow-card__border"></div>
            </div>

            <div class="glow-card" data-slot="glow-card" style="color: hsl(200 95% 62%)">
                <div class="glow-card__inner">
                    <div class="glow-card__bg" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>
                    </div>
                    <div class="glow-card__content">
                        <div class="glow-card__icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>
                        </div>
                        <div>
                            <h3 class="glow-card__title">Smart Chatbot</h3>
                            <p class="glow-card__text">Toji remembers you and chats like a friend, in your own language</p>
                        </div>
                    </div>
                </div>
                <div class="glow-card__border"></div>
            </div>

            <div class="glow-card" data-slot="glow-card" style="color: hsl(45 95% 62%)">
                <div class="glow-card__inner">
                    <div class="glow-card__bg" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 7 4 4 20 4 20 7"/><line x1="9" x2="15" y1="20" y2="20"/><line x1="12" x2="12" y1="4" y2="20"/></svg>
                    </div>
                    <div class="glow-card__content">
                        <div class="glow-card__icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 7 4 4 20 4 20 7"/><line x1="9" x2="15" y1="20" y2="20"/><line x1="12" x2="12" y1="4" y2="20"/></svg>
                        </div>
                        <div>
                            <h3 class="glow-card__title">Font Styling</h3>
                            <p class="glow-card__text">Creative text formatting and stylish font options</p>
                        </div>
                    </div>
                </div>
                <div class="glow-card__border"></div>
            </div>

            <div class="glow-card" data-slot="glow-card" style="color: hsl(270 90% 72%)">
                <div class="glow-card__inner">
                    <div class="glow-card__bg" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="20" x="4" y="2" rx="2"/><line x1="8" x2="16" y1="6" y2="6"/><line x1="16" x2="16" y1="14" y2="18"/><path d="M16 10h.01"/><path d="M12 10h.01"/><path d="M8 10h.01"/><path d="M12 14h.01"/><path d="M8 14h.01"/><path d="M12 18h.01"/><path d="M8 18h.01"/></svg>
                    </div>
                    <div class="glow-card__content">
                        <div class="glow-card__icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="20" x="4" y="2" rx="2"/><line x1="8" x2="16" y1="6" y2="6"/><line x1="16" x2="16" y1="14" y2="18"/><path d="M16 10h.01"/><path d="M12 10h.01"/><path d="M8 10h.01"/><path d="M12 14h.01"/><path d="M8 14h.01"/><path d="M12 18h.01"/><path d="M8 18h.01"/></svg>
                        </div>
                        <div>
                            <h3 class="glow-card__title">Calculator</h3>
                            <p class="glow-card__text">Quick and easy calculations right in your chat</p>
                        </div>
                    </div>
                </div>
                <div class="glow-card__border"></div>
            </div>

            <div class="glow-card" data-slot="glow-card" style="color: hsl(15 95% 66%)">
                <div class="glow-card__inner">
                    <div class="glow-card__bg" aria-hidden="true">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                    </div>
                    <div class="glow-card__content">
                        <div class="glow-card__icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                        </div>
                        <div>
                            <h3 class="glow-card__title">Group Management</h3>
                            <p class="glow-card__text">Comprehensive tools for managing Telegram groups</p>
                        </div>
                    </div>
                </div>
                <div class="glow-card__border"></div>
            </div>
        </div>

        <footer>
            <p>Made with ❤️ by <a href="https://t.me/LustyAntidote" target="_blank" rel="noopener">@AR</a></p>
        </footer>
    </div>

    <script>
        (function () {
            var grid = document.getElementById("glow-grid");
            if (!grid) return;
            var cards = Array.prototype.slice.call(grid.querySelectorAll("[data-slot='glow-card']"));
            var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
            var touchOnly = window.matchMedia && window.matchMedia("(hover: none)").matches;

            function setPointer(card, x, y) {
                card.style.setProperty("--pointer-x", x.toFixed(3));
                card.style.setProperty("--pointer-y", y.toFixed(3));
            }

            if (reduceMotion) {
                // no movement: a fixed, gentle glow
                cards.forEach(function (card) { setPointer(card, 0.35, -0.3); });
                return;
            }

            // mouse / pen / touch drag: the glow follows the pointer (like the React component)
            var lastEvent = null, ticking = false;
            function update() {
                ticking = false;
                if (!lastEvent) return;
                cards.forEach(function (card) {
                    var r = card.getBoundingClientRect();
                    var x = (lastEvent.clientX - (r.left + r.width / 2)) / (r.width / 2);
                    var y = (lastEvent.clientY - (r.top + r.height / 2)) / (r.height / 2);
                    setPointer(card, x, y);
                });
            }
            document.addEventListener("pointermove", function (e) {
                lastEvent = e;
                if (!ticking) { ticking = true; requestAnimationFrame(update); }
            }, { passive: true });

            // phones have no hovering pointer, so the glow drifts slowly on its own until the first touch
            if (touchOnly) {
                var start = performance.now();
                (function orbit(now) {
                    if (lastEvent) return;
                    var t = (now - start) / 1000;
                    cards.forEach(function (card, i) {
                        setPointer(card, 0.8 * Math.sin(t * 0.7 + i), 0.8 * Math.cos(t * 0.55 + i * 1.3));
                    });
                    requestAnimationFrame(orbit);
                })(start);
            }
        })();
    </script>
</body>
</html>
"""


@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.Response(text=LANDING_HTML, content_type="text/html")


@routes.get("/favicon.ico", allow_head=True)
async def favicon_handler(request):
    # browsers ask for this on every visit; without it the catch-all media route below logs an error
    return web.Response(status=204)




####################################################################################################





class InvalidHash(Exception):
    message = "Invalid hash"

class FIleNotFound(Exception):
    message = "File not found"


@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)


        if match:
            secure_hash = match.group(1)
            message_id = int(match.group(2))
        else:
            message_id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")


        return web.Response(text=await render_page(message_id, secure_hash), content_type='text/html')
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logger.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

@routes.get(r"/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)


        if match:
            secure_hash = match.group(1)
            message_id = int(match.group(2))
        else:
            message_id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")


        return await media_streamer(request, message_id, secure_hash)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logger.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))



class_cache = {}

async def media_streamer(request: web.Request, message_id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)

    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]

    if config.MULTI_CLIENT:
        logger.debug(f"Client {index} is now serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logger.debug(f"Using cached ByteStreamer object for client {index}")
      
    else:
        logger.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = pyro_utils.ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
 
    logger.debug("before calling get_file_properties")
    file_id = await tg_connect.get_file_properties(message_id)
    logger.debug("after calling get_file_properties")

    if file_id.unique_id[:6] != secure_hash:
        logger.debug(f"Invalid hash for message with ID {message_id}")
        raise InvalidHash

    file_size = file_id.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = request.http_range.stop or file_size - 1

    req_length = until_bytes - from_bytes
    new_chunk_size = await pyro_utils.chunk_size(req_length)
    offset = await pyro_utils.offset_fix(from_bytes, new_chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = (until_bytes % new_chunk_size) + 1
    part_count = math.ceil(req_length / new_chunk_size)
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, new_chunk_size
    )

    mime_type = file_id.mime_type
    file_name = file_id.file_name
    disposition = "attachment"
    if mime_type:
        if not file_name:
            try:
                file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
            except (IndexError, AttributeError):
                file_name = f"{secrets.token_hex(2)}.bin"
    else:
        if file_name:
            mime_type = mimetypes.guess_type(file_id.file_name)
        else:
            mime_type = "application/octet-stream"
            file_name = f"{secrets.token_hex(2)}.bin"
    if "video/" in mime_type or "audio/" in mime_type:
        disposition = "inline"
    return_resp = web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Range": f"bytes={from_bytes}-{until_bytes}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )

    if return_resp.status == 200:
        return_resp.headers.add("Content-Length", str(file_size))

    return return_resp
####################################################################################################
def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

async def keep_alive():
    """
    Pings config.WEB_URL every config.WEB_SLEEP seconds.
    Handles cancellation gracefully so shutdown won't leave a pending task.
    """
    if not config.WEB_URL:
        return

    try:
        while True:
            await asyncio.sleep(config.WEB_SLEEP)
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(config.WEB_URL) as resp:
                        logger.info("Pinged %s with response: %s", config.WEB_URL, resp.status)
            except asyncio.TimeoutError:
                logger.warning("Couldn't connect to the site URL (timeout).")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Error while pinging keep-alive URL")
    except asyncio.CancelledError:
        logger.info("keep_alive task cancelled, exiting cleanly.")
        raise
async def _on_startup(app: web.Application):
    """Start background keep_alive task (if configured) and save it on app"""
    if config.WEB_URL:
        logger.debug("Starting keep_alive background task")
        task = asyncio.create_task(keep_alive(), name="keep_alive_task")
        app["keep_alive_task"] = task
async def _on_cleanup(app: web.Application):
    """Cancel background task and await it so it doesn't remain pending"""
    task = app.get("keep_alive_task")
    if not task:
        return
    logger.debug("Cancelling keep_alive background task")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.debug("keep_alive task cancelled successfully during cleanup")
    except Exception:
        logger.exception("Error while waiting for keep_alive task during cleanup")
def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    web_app.on_startup.append(_on_startup)
    web_app.on_cleanup.append(_on_cleanup)

    return web_app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    try:
        web.run_app(web_server(), host="0.0.0.0", port=port)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down web app")
