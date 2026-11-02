"""JARVIS AI - FastAPI backend.

Run:  cd backend && uvicorn main:app --host 0.0.0.0 --port 8000
"""
import os
import re
import json
import sqlite3
import secrets
import subprocess
import tempfile
import zipfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

from llm import ask_llm, status as llm_status, LLMError  # noqa: E402

PROJ = ROOT / "projects"
PROJ.mkdir(exist_ok=True)

db = sqlite3.connect(ROOT / "jarvis.db", check_same_thread=False)
db.execute(
    "create table if not exists history("
    "id integer primary key, role text, content text, ts default current_timestamp)"
)

app = FastAPI(title="JARVIS AI", version="2.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

SENSITIVE = re.compile(
    r"\b(buy|pay|purchase|checkout|order|delete|remove|send|submit|confirm|transfer)\b",
    re.I,
)

_browser = None


def get_browser():
    """Playwright is optional - the API still works without it."""
    global _browser
    if _browser is None:
        from browser import Browser

        _browser = Browser()
    return _browser


def auth(x_token: str = Header(None)):
    expected = os.getenv("JARVIS_TOKEN") or ""
    if not expected:
        raise HTTPException(500, "JARVIS_TOKEN .env me set karo")
    if not secrets.compare_digest((x_token or "").encode(), expected.encode()):
        raise HTTPException(401, "Galat ya missing token")


def safe_name(n: str) -> str:
    return re.sub(r"[^\w\-]", "_", n or "")[:50] or "project"


def extract_json(raw: str):
    """Models often wrap JSON in ```json fences or add prose around it."""
    txt = raw.strip()
    txt = re.sub(r"^```(?:json)?\s*", "", txt)
    txt = re.sub(r"\s*```$", "", txt)
    try:
        return json.loads(txt)
    except Exception:
        pass
    m = re.search(r"\{.*\}", txt, re.S)
    if not m:
        raise ValueError("no JSON found")
    return json.loads(m.group())


def sandbox(lang: str, code: str) -> str:
    spec = {"python": ("py", ["python3"]), "javascript": ("js", ["node"])}
    if lang not in spec:
        return f"Unsupported language: {lang}"
    ext, cmd = spec[lang]
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / f"main.{ext}"
        f.write_text(code)
        try:
            r = subprocess.run(
                cmd + [str(f)], cwd=d, capture_output=True, text=True, timeout=10,
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": d},
            )
            return (r.stdout + r.stderr)[-4000:] or "(no output)"
        except subprocess.TimeoutExpired:
            return "Timed out (10s)"
        except FileNotFoundError as e:
            return f"Runner missing: {e}"


def make_zip(name: str, files: dict) -> str:
    name = safe_name(name)
    out = PROJ / f"{name}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path, content in files.items():
            p = Path(str(path))
            if p.is_absolute() or ".." in p.parts:
                raise HTTPException(400, f"Bad path {path}")
            z.writestr(f"{name}/{p.as_posix()}", content if isinstance(content, str) else json.dumps(content, indent=2))
    return f"/api/zip/download/{name}"


async def run_tool(tool: str, args: dict, confirmed: bool):
    needs_confirm = tool == "run_code" or (
        tool in ("click", "type") and SENSITIVE.search(json.dumps(args))
    )
    if needs_confirm and not confirmed:
        return {"confirm": True, "tool": tool, "args": args}
    if tool == "run_code":
        return {"output": sandbox(args.get("lang", "python"), args.get("code", ""))}
    if tool == "make_zip":
        return {"download": make_zip(args.get("name", "project"), args.get("files", {}))}
    try:
        return {"result": await get_browser().run(tool, args)}
    except ImportError:
        raise HTTPException(
            503,
            "Browser control is off. Server par `pip install playwright && playwright install chromium` chalao.",
        )


AGENT = """You are JARVIS, a helpful assistant fluent in Hindi, English and Hinglish.
Always reply in the user's language (Hinglish is fine).
Respond ONLY with JSON, no markdown fence:
{"say": "<short spoken reply>", "tool": null or one of
 open{url}, search{q}, new_tab{url}, switch_tab{index}, scroll{amount}, click{text},
 type{label,value}, read{}, screenshot{}, yt_search{q},
 yt{cmd: playpause|fullscreen|mute|next|volup|voldown|forward|back}, yt_channel{q},
 run_code{lang: python|javascript, code}, make_zip{name, files: {path: content}},
 "args": {...}}
Rules: at most one tool per turn. Keep "say" under 40 words. Never try to bypass CAPTCHA or logins.
If no tool is needed, set "tool" to null and just answer in "say"."""


class Chat(BaseModel):
    text: str = ""
    confirmed_action: dict | None = None


class Act(BaseModel):
    tool: str
    args: dict = {}
    confirmed: bool = False


class Zip(BaseModel):
    name: str
    files: dict[str, str]


class Gen(BaseModel):
    name: str
    prompt: str


@app.get("/api/health")
def health():
    return {"ok": True, "llm": llm_status(), "browser": _browser is not None}


@app.get("/api/status", dependencies=[Depends(auth)])
def status():
    return {"llm": llm_status(), "zips": len(list(PROJ.glob("*.zip")))}


@app.post("/api/chat", dependencies=[Depends(auth)])
async def chat(c: Chat):
    if c.confirmed_action:
        a = c.confirmed_action
        return {"say": "Ho gaya.", "data": await run_tool(a["tool"], a.get("args", {}), True)}

    text = (c.text or "").strip()
    if not text:
        raise HTTPException(400, "text khaali hai")

    db.execute("insert into history(role,content) values('user',?)", (text,))
    db.commit()
    rows = db.execute(
        "select role,content from history order by id desc limit 12"
    ).fetchall()[::-1]

    try:
        raw = await ask_llm([{"role": r, "content": t} for r, t in rows], AGENT)
    except LLMError as e:
        raise HTTPException(502, str(e))

    try:
        plan = extract_json(raw)
        if not isinstance(plan, dict):
            raise ValueError
    except Exception:
        plan = {"say": raw.strip()[:1000], "tool": None}

    data = None
    if plan.get("tool"):
        for _ in range(2):
            try:
                data = await run_tool(plan["tool"], plan.get("args") or {}, False)
                break
            except HTTPException as e:
                data = {"error": e.detail}
                break
            except Exception as e:  # browser crashes, bad selectors, etc.
                data = {"error": str(e)}
                break

    db.execute("insert into history(role,content) values('assistant',?)", (plan.get("say", ""),))
    db.commit()
    return {"say": plan.get("say", ""), "data": data}


@app.post("/api/tool", dependencies=[Depends(auth)])
async def tool(a: Act):
    return await run_tool(a.tool, a.args, a.confirmed)


@app.post("/api/zip/create", dependencies=[Depends(auth)])
def zip_create(z: Zip):
    return {"download": make_zip(z.name, z.files)}


@app.post("/api/zip/generate", dependencies=[Depends(auth)])
async def zip_generate(g: Gen):
    system = (
        'Generate a complete, working project. Respond ONLY with JSON: '
        '{"files": {"relative/path": "file content"}}. '
        "Include README.md and all config files. No markdown fences."
    )
    try:
        raw = await ask_llm([{"role": "user", "content": g.prompt}], system, max_tokens=4000)
        files = extract_json(raw)["files"]
    except LLMError as e:
        raise HTTPException(502, str(e))
    except Exception as e:
        raise HTTPException(502, f"Model ne valid files nahi diye: {e}")
    return {"download": make_zip(g.name, files), "files": list(files)}


@app.get("/api/zip/list", dependencies=[Depends(auth)])
def zip_list():
    return [p.stem for p in PROJ.glob("*.zip")]


@app.get("/api/zip/download/{name}")
def zip_dl(name: str, token: str = ""):
    expected = os.getenv("JARVIS_TOKEN") or ""
    if not secrets.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(401, "bad token")
    f = PROJ / f"{safe_name(name)}.zip"
    if not f.exists():
        raise HTTPException(404, "not found")
    return FileResponse(f, filename=f.name)


@app.get("/api/history", dependencies=[Depends(auth)])
def history():
    return db.execute("select role,content,ts from history order by id desc limit 100").fetchall()


@app.post("/api/history/clear", dependencies=[Depends(auth)])
def history_clear():
    db.execute("delete from history")
    db.commit()
    return {"ok": True}


@app.exception_handler(Exception)
async def unhandled(request, exc):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="static")
