"""Personal keys: from the environment, else from .env in the working copy (git-ignored).

Only the names in FROM_ENV_FILE are read from .env. The environment wins when both are set. A key is returned to the
caller that makes the request, and never printed, logged or written anywhere by these scripts.

    DBT_API_KEY=...          the Digital Bible Platform (scripts/fetch_edition.py)
    DBT_API_BASE_URL=...     its address, if not https://4.dbt.io/api (not a secret; read the same way)
    ANTHROPIC_API_KEY=...    the model through the API (scripts/probe_language.py, priors.py, onboard.py)
    NLLB_HOST=user@host      a GPU machine for the second-draft model, and NLLB_DIR, NLLB_PYTHON there
                             (scripts/nllb/remote.py; not secrets, but private: they stay out of the repo)
    NETLIFY_AUTH_TOKEN=...   a Netlify personal access token, and NETLIFY_SITE_ID=... the site's id, for
                             scripts/deploy_site.py --netlify (docs/website.md)
"""
import os, re

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.environ.get("MAKE_TANAKH_ROOT") or CODE)   # the data root (books.py)
ENV_FILE = os.path.join(ROOT, ".env")
FROM_ENV_FILE = ("DBT_API_KEY", "DBT_API_BASE_URL", "ANTHROPIC_API_KEY", "NLLB_HOST", "NLLB_DIR", "NLLB_PYTHON",
                 "NETLIFY_AUTH_TOKEN", "NETLIFY_SITE_ID")


def key(name):
    """The value of `name`: the environment, else its line in .env (for the names in FROM_ENV_FILE). None if unset."""
    v = os.environ.get(name)
    if not v and name in FROM_ENV_FILE and os.path.exists(ENV_FILE):
        for line in open(ENV_FILE, encoding="utf-8"):
            m = re.match(rf"\s*(?:export\s+)?{re.escape(name)}\s*=\s*(.*?)\s*$", line)
            if m:
                v = m[1].strip("'\"")
    return v or None
