# 🏔️ IssueSherpa

An open-weight AI guide for Hacktoberfest: find a beginner-friendly GitHub issue, then get a step-by-step plan to fix it.
Built for the MLH x DigitalOcean Hacktoberfest 2026 challenge.

## Where and how DigitalOcean is used

| Where | How |
|---|---|
| **DigitalOcean Gradient AI (Serverless Inference)** | Every AI call in `app.py` (`ask_llm()`) goes to DO's OpenAI-compatible endpoint (`https://inference.do-ai.run/v1`) running the open-weight **Llama 3.3 70B Instruct** model. It is used for (1) ranking issues by beginner-friendliness, (2) choosing which repo files to read, (3) writing the contribution plan. |
| **DigitalOcean App Platform** | The Flask app is deployed here straight from GitHub. The Gradient AI key is stored as an encrypted environment variable (`LLM_API_KEY`). |

## Files
```
app.py            Flask backend (GitHub + DigitalOcean AI calls)
index.html        Frontend (search + plan UI)
requirements.txt  Dependencies
document.md       Full project documentation
readme.md         This file
```

## Run locally
```bash
pip install -r requirements.txt
export LLM_API_KEY="your-digitalocean-model-access-key"
export GITHUB_TOKEN="optional-github-token"
python app.py          # open http://localhost:8080
```

## Environment variables
| Name | Required | Default |
|---|---|---|
| `LLM_API_KEY` | yes | DigitalOcean model access key |
| `LLM_BASE_URL` | no | `https://inference.do-ai.run/v1` |
| `LLM_MODEL` | no | `llama3.3-70b-instruct` |
| `GITHUB_TOKEN` | no | avoids GitHub rate limits |

## Deploy on DigitalOcean App Platform
1. Push these 5 files to a public GitHub repo.
2. DigitalOcean dashboard → **Create → App Platform** → pick your GitHub repo and branch.
3. It auto-detects Python. In the component settings set **Run Command** to:
   `gunicorn --bind 0.0.0.0:8080 app:app` and **HTTP Port** to `8080`.
4. Add environment variables (mark the key as *Encrypted*): `LLM_API_KEY`, optionally `GITHUB_TOKEN`.
5. Choose the Basic plan, click **Create Resource**. In a few minutes you get a live `.ondigitalocean.app` URL.

## Lic
ense
MIT
