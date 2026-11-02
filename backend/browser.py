"""Playwright browser control. Optional - import errors are handled by main.py.

On a server (Docker / Render) run headless:  BROWSER_HEADLESS=1
On your own laptop you can watch it work:    BROWSER_HEADLESS=0
"""
import base64
import os
import urllib.parse

from playwright.async_api import async_playwright

HEADLESS = os.getenv("BROWSER_HEADLESS", "1") not in ("0", "false", "False")
TIMEOUT = int(os.getenv("BROWSER_TIMEOUT_MS", "20000"))


class Browser:
    def __init__(self):
        self.pw = self.br = self.ctx = self.page = None

    async def _ensure(self):
        if self.page and not self.page.is_closed():
            return
        if not self.pw:
            self.pw = await async_playwright().start()
        if not self.br:
            launch = {"headless": HEADLESS}
            args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
            try:
                self.br = await self.pw.chromium.launch(channel="chrome", args=args, **launch)
            except Exception:
                self.br = await self.pw.chromium.launch(args=args, **launch)
            self.ctx = await self.br.new_context(
                accept_downloads=True,
                viewport={"width": 1280, "height": 800},
                locale="en-IN",
            )
        self.page = self.ctx.pages[-1] if self.ctx.pages else await self.ctx.new_page()

    async def run(self, action, a):
        await self._ensure()
        p = self.page
        if action == "open":
            url = a["url"]
            if not url.startswith("http"):
                url = "https://" + url
            await p.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT)
            return f"Opened {p.url}"
        if action == "search":
            q = urllib.parse.quote(a["q"])
            await p.goto(f"https://www.google.com/search?q={q}", wait_until="domcontentloaded", timeout=TIMEOUT)
            return "Searched Google"
        if action == "new_tab":
            self.page = await self.ctx.new_page()
            if a.get("url"):
                await self.page.goto(a["url"], wait_until="domcontentloaded", timeout=TIMEOUT)
            return f"Tab {len(self.ctx.pages)} opened"
        if action == "switch_tab":
            self.page = self.ctx.pages[int(a["index"])]
            await self.page.bring_to_front()
            return "Switched tab"
        if action == "scroll":
            await p.mouse.wheel(0, int(a.get("amount", 600)))
            return "Scrolled"
        if action == "click":
            await p.get_by_text(a["text"]).first.click(timeout=8000)
            return f"Clicked '{a['text']}'"
        if action == "type":
            await p.get_by_label(a["label"]).first.fill(a["value"], timeout=8000)
            return f"Filled '{a['label']}'"
        if action == "read":
            return (await p.inner_text("body"))[:4000]
        if action == "screenshot":
            png = await p.screenshot(full_page=False)
            return {"image": base64.b64encode(png).decode()}
        if action == "yt_search":
            q = urllib.parse.quote(a["q"])
            await p.goto(f"https://www.youtube.com/results?search_query={q}",
                         wait_until="domcontentloaded", timeout=TIMEOUT)
            await p.wait_for_selector("ytd-video-renderer a#video-title", timeout=TIMEOUT)
            await p.click("ytd-video-renderer a#video-title")
            return "Playing top result"
        if action == "yt":
            keys = {"playpause": "k", "fullscreen": "f", "mute": "m", "next": "Shift+N",
                    "volup": "ArrowUp", "voldown": "ArrowDown", "forward": "l", "back": "j"}
            if a.get("cmd") not in keys:
                raise ValueError(f"unknown yt cmd {a.get('cmd')}")
            await p.focus("#movie_player")
            await p.keyboard.press(keys[a["cmd"]])
            return a["cmd"]
        if action == "yt_channel":
            q = urllib.parse.quote(a["q"])
            await p.goto(f"https://www.youtube.com/results?search_query={q}&sp=EgIQAg%253D%253D",
                         wait_until="domcontentloaded", timeout=TIMEOUT)
            await p.click("ytd-channel-renderer a")
            return "Opened channel"
        raise ValueError(f"unknown action {action}")
