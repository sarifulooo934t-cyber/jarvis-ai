# JARVIS AI 🤖

Apna personal AI assistant — **voice** (Hindi / English / Hinglish), **browser control**, **YouTube**, **code sandbox**, **AI project builder (ZIP)** aur ek **Android APK**.

Ek FastAPI backend + ek single-page web app + ek halka Android app. Koi paid service zaroori nahi — Gemini ka free API key chalta hai.

```
Phone (APK)  ──┐
Browser      ──┼──►  FastAPI server (Render / local)  ──►  AI provider (Gemini / Groq / OpenRouter / Ollama / Claude)
               │            │
               │            └──► Playwright (browser control, optional)
               └──► SQLite history + ZIP projects
```

---

## 1. Sabse pehle: free AI key lo (2 minute)

1. https://aistudio.google.com/apikey kholo → Google account se login
2. **Create API key** dabao → key copy karo (`AIza...`)
3. Bas. Free tier me roz kaafi requests mil jaati hain.

> Key **sirf server ke `.env`** me jaati hai. Phone ya browser me kabhi nahi.

Doosre options (baad me badal sakte ho):

| Provider | `.env` me | Free? | Key kahan se |
|---|---|---|---|
| **gemini** (default) | `LLM_PROVIDER=gemini` | haan | aistudio.google.com/apikey |
| groq | `LLM_PROVIDER=groq` | haan | console.groq.com/keys |
| openrouter | `LLM_PROVIDER=openrouter` | haan (free models) | openrouter.ai/keys |
| ollama | `LLM_PROVIDER=ollama` + `LLM_BASE_URL=http://localhost:11434/v1` | bilkul free, key nahi | apne PC par ollama |
| anthropic | `LLM_PROVIDER=anthropic` | nahi | console.anthropic.com |

---

## 2. Local par chalana

```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# .env kholo aur ye do line bharo:
#   JARVIS_TOKEN=<lamba random string>
#   LLM_API_KEY=<gemini key>
python -c "import secrets;print(secrets.token_urlsafe(32))"   # token banane ke liye
cd backend && uvicorn main:app --reload
```

Kholo http://localhost:8000 → **Settings** tab → `JARVIS_TOKEN` paste → Save → *Connection test*.

Browser control (Playwright) chahiye to ek baar:
```bash
playwright install chromium
```

---

## 3. Server par deploy (Render — free)

1. GitHub par ye repo push karo (already ho chuka hai).
2. https://render.com → **New +** → **Web Service** → apna repo choose karo.
3. Render `render.yaml` khud padh lega. Na padhe to manually:
   - **Runtime:** Docker
   - **Plan:** Free
   - **Health check path:** `/api/health`
4. Environment variables:
   - `JARVIS_TOKEN` → Render se **Generate** karwa lo (ya khud daalo)
   - `LLM_PROVIDER` → `gemini`
   - `LLM_MODEL` → `gemini-2.5-flash`
   - `LLM_API_KEY` → apni Gemini key
5. **Deploy** → 3-5 min → URL milega jaise `https://jarvis-ai-xxxx.onrender.com`

Notes:
- Free plan 15 min inactivity ke baad sleep karta hai; pehla request ~30s le sakta hai. Paid plan me nahi hota.
- Browser control (Playwright) chahiye to `Dockerfile` build karte waqt `--build-arg WITH_BROWSER=1` do — image bhaari ho jaati hai, free plan par tight hai. Bina browser ke baaki sab kaam karta hai.
- Railway / Koyeb / Fly.io bhi chalega — Dockerfile hi use karna hai.

---

## 4. Android app (APK)

`android/jarvis-ai.apk` — phone me copy karo, install karo (Settings me "Install unknown apps" allow karna padega).

- Pehli baar app server URL maangega → apna Render URL daalo.
- Phir app ke **Settings** tab me `JARVIS_TOKEN` daalo → Save.
- **Mic** button dabao aur bolo: *"YouTube pe Arijit Singh ke gaane chalao"*.
- Kahin bhi **long-press** → Reload / server URL badlo / data clear.

APK dobara banana ho to `android/README.md` dekho (Android Studio ya `build_apk.sh`).

---

## 5. Kya kya kar sakta hai

| Tab | Kaam |
|---|---|
| **Assistant** | Baat karo (type ya mic), jawab bol ke sunata hai, tool khud chunta hai |
| **Browser** | URL kholo, Google search, click, form fill, scroll, page padho, screenshot |
| **YouTube** | Gaana/video chalao, play-pause, next, volume, fullscreen, channel kholo |
| **Code** | Python / JavaScript chalao (10s timeout, khaali environment) |
| **Projects** | "Kya banana hai" likho → AI poori project + README bana ke ZIP de deta hai |
| **History** | Purani baatein SQLite me, clear bhi kar sakte ho |

Kuch examples:
- "Hey Jarvis, YouTube pe lofi beats chalao"
- "Google pe IRCTC ka status search karo aur padho"
- "Ek Python script likho jo folder ki files rename kare, ZIP me do"
- "2+2 ka code chala ke dikhao"

---

## 6. Structure

```
backend/
  main.py       FastAPI app, auth, chat loop, sandbox, ZIP builder
  llm.py        multi-provider AI client (gemini/groq/openrouter/openai/ollama/anthropic)
  browser.py    Playwright actions (open, click, type, yt, screenshot...)
frontend/
  index.html    poora UI (koi build step nahi, plain HTML+JS)
  manifest.webmanifest, sw.js, icons  → PWA support
android/        WebView app ka source + bana hua APK + build script
Dockerfile      server image
render.yaml     Render one-click config
```

Tool add karna ho: `backend/browser.py` me ek branch, phir `run_tool()` aur `AGENT` prompt me naam likh do.

---

## 7. Security (padh lena)

- Saare API endpoints `X-Token` maangte hain — token `.env` me, phone me sirf localStorage.
- AI keys sirf server par. Repo me kabhi commit na karo (`.gitignore` me `.env` hai).
- `run_code`, aur buy/pay/delete/send jaisa click/type — on-screen confirm ke bina nahi chalta.
- Code sandbox = subprocess + 10s timeout + khaali env. Ye **hard isolation nahi** hai — public server par ajnabi ko na do.
- CAPTCHA / login bypass kabhi nahi.
- Public URL par lagane se pehle token lamba rakho; HTTPS Render khud deta hai.

---

## 8. Problem aaye to

| Dikkat | Fix |
|---|---|
| `401 Invalid or missing token` | App ke Settings me token dobara daalo (server `.env` wala) |
| `LLM_API_KEY .env me set nahi hai` | Render → Environment me key daalo → redeploy |
| `Gemini error 400/404` | `LLM_MODEL` galat hai — `gemini-2.5-flash` rakho |
| Pehla jawab 30s le raha | Free hosting sleep me thi, normal hai |
| "Browser control is off" | server par `playwright install chromium` (ya `WITH_BROWSER=1` image) |
| Mic kaam nahi kar raha | Chrome/Edge use karo, mic permission allow karo, HTTPS zaroori hai |
| APK me blank screen | server URL galat/band hai — long-press → server URL badlo |

---

MIT license — apne use ke liye free. Enjoy 🚀
