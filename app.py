"""IssueSherpa - open-weight AI guide for Hacktoberfest contributions.
LLM calls go to DigitalOcean Gradient AI (Llama 3.3, OpenAI-compatible API)."""
import base64
import json
import os
import re

import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)

# ---- DigitalOcean Gradient AI settings (set these as env vars in DO App Platform) ----
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://inference.do-ai.run/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.3-70b-instruct")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # optional, avoids rate limits


# ------------------------------ LLM (DigitalOcean) ------------------------------
def ask_llm(system, user, temperature=0.3, max_tokens=1500):
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not set")
    r = requests.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={
            "model": LLM_MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=90,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def parse_json(text):
    """Open models sometimes add prose/```fences``` around JSON; be forgiving."""
    text = re.sub(r"```(?:json)?", "", text)
    pairs = sorted([("{", "}"), ("[", "]")], key=lambda p: text.find(p[0]) % (len(text) + 1))
    for o, c in pairs:
        s, e = text.find(o), text.rfind(c)
        if s != -1 and e > s:
            try:
                return json.loads(text[s : e + 1])
            except json.JSONDecodeError:
                pass
    raise ValueError("no JSON in model output")


# ------------------------------ GitHub helpers ------------------------------
def gh(path, **params):
    h = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    r = requests.get(f"https://api.github.com{path}", headers=h, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def parse_issue_url(url):
    m = re.search(r"github\.com/([^/\s]+)/([^/\s]+)/issues/(\d+)", url or "")
    if not m:
        raise ValueError("Not a valid GitHub issue URL")
    return m.group(1), m.group(2), int(m.group(3))


def read_file(owner, repo, path):
    try:
        d = gh(f"/repos/{owner}/{repo}/contents/{path}")
        return base64.b64decode(d["content"]).decode("utf-8", errors="replace")
    except Exception:
        return ""


# ------------------------------ Routes ------------------------------
@app.get("/")
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")


@app.get("/api/search")
def search():
    lang = request.args.get("language", "python")
    q = f'is:issue is:open label:"good first issue" label:hacktoberfest no:assignee language:{lang}'
    try:
        items = gh("/search/issues", q=q, sort="updated", order="desc", per_page=8)["items"]
    except Exception as e:
        return jsonify(error=f"GitHub error: {e}"), 502
    issues = [
        {
            "title": i["title"],
            "url": i["html_url"],
            "repo": i["repository_url"].split("/repos/")[-1],
            "body": (i.get("body") or "")[:400],
            "score": 0,
            "why": "",
        }
        for i in items
    ]
    if issues:  # rank with the open-weight model; fall back to unranked if it fails
        try:
            listing = "\n\n".join(f"[{n}] {x['repo']}: {x['title']}\n{x['body']}" for n, x in enumerate(issues))
            scores = parse_json(ask_llm(
                'Score each GitHub issue 1-10 for beginner-friendliness (clear, small scope). '
                'Reply ONLY with JSON: [{"index":0,"score":7,"why":"short reason"}]',
                listing, temperature=0.1))
            for s in scores:
                if 0 <= s.get("index", -1) < len(issues):
                    issues[s["index"]].update(score=s.get("score", 0), why=s.get("why", ""))
            issues.sort(key=lambda x: x["score"], reverse=True)
        except Exception:
            pass
    for x in issues:
        x.pop("body")
    return jsonify(issues=issues)


@app.post("/api/plan")
def plan():
    try:
        owner, repo, num = parse_issue_url((request.get_json(silent=True) or {}).get("url"))
        issue = gh(f"/repos/{owner}/{repo}/issues/{num}")
        branch = gh(f"/repos/{owner}/{repo}")["default_branch"]
        tree = [t["path"] for t in gh(f"/repos/{owner}/{repo}/git/trees/{branch}", recursive=1)["tree"]
                if t["type"] == "blob"][:400]
        issue_text = f"Title: {issue['title']}\n\n{(issue.get('body') or '')[:3000]}"

        # Agent step 1: let the model choose which files matter
        files = []
        try:
            pick = parse_json(ask_llm(
                'Pick up to 5 files from the list most relevant to fixing this issue. '
                'Reply ONLY with JSON: {"files": ["path"]}',
                f"{issue_text}\n\nFILES:\n" + "\n".join(tree), temperature=0.1))
            files = [f for f in pick.get("files", []) if f in tree][:5]  # block hallucinated paths
        except Exception:
            pass

        # Agent step 2: read them
        code = "\n\n".join(f"### {f}\n{read_file(owner, repo, f)[:3000]}" for f in files)

        # Agent step 3: write the plan
        result = ask_llm(
            "You are a friendly mentor for first-time open-source contributors. Write a Markdown plan with "
            "sections: Summary, Difficulty, Files to touch, Step-by-step plan, How to test, Pitfalls. "
            "Do not invent files not present in the context.",
            f"{issue_text}\n\nFILE EXCERPTS:\n{code or 'none'}", max_tokens=1800)
        return jsonify(plan=result, files=files)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        return jsonify(error=f"Failed: {e}"), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
      
