# IssueSherpa: Project Document

## Problem
First-time open-source contributors lose hours before writing any code: which issue is doable, which files matter, what should the fix look like? Many give up, and maintainers get low-quality PRs.

## Solution
IssueSherpa is a small web app that uses an **open-weight LLM (Llama 3.3)** to:
1. **Find and rank** open `good first issue` + `hacktoberfest` issues by how beginner-friendly they are.
2. **Plan a fix**: an AI agent reads the issue, picks the relevant files from the repo, reads them, and writes a step-by-step plan (summary, difficulty, files to touch, steps, tests, pitfalls).

The goal is to help beginners contribute thoughtfully, not to auto-generate PRs. The human still writes, tests and understands the code.

## How it works
```
Browser (index.html)
   │  GET /api/search?language=python
   │  POST /api/plan {url}
   ▼
Flask (app.py) ──► GitHub REST API   (issues, repo tree, file contents)
        └───────► DigitalOcean Gradient AI  (Llama 3.3, chat/completions)
```

### Agent flow for `/api/plan`
| Step | Action |
|---|---|
| 1 | Fetch issue + repo file list from GitHub |
| 2 | LLM picks up to 5 relevant files (JSON). Paths are validated against the real tree, so hallucinated files are dropped |
| 3 | App reads those files |
| 4 | LLM writes the Markdown plan using only that context |

## API
| Endpoint | Description |
|---|---|
| `GET /api/search?language=python` | Returns ranked issues `[ {title, url, repo, score, why} ]` |
| `POST /api/plan` body `{"url": "<issue url>"}` | Returns `{plan, files}` |

## Open-source / open-weight components
- Llama 3.3 70B Instruct (open-weight) served via DigitalOcean Gradient AI
- Flask, Requests, Gunicorn (open source)

## Design decisions
- **OpenAI-compatible endpoint**: swap `LLM_BASE_URL` / `LLM_MODEL` to use Ollama, vLLM, or another open model.
- **Forgiving JSON parsing**: open models sometimes add prose or code fences around JSON.
- **Graceful fallback**: if ranking fails, issues still show, just unranked.
- **No database, no login**: stateless and easy to deploy.

## Limitations
- GitHub search is rate-limited without `GITHUB_TOKEN`.
- Plans depend on at most 5 files of context; large cross-cutting issues may need more.
- The plan is guidance, not verified code. Always review and test.

## Future work
Claim-comment and PR-description drafts, a GitHub Action that comments plans on new issues
, caching.
