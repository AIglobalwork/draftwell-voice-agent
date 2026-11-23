"""Manual check, not part of the tests or CI: can GOOGLE_VOICE_API_KEY open a Gemini Live session?
Lists the live models and tries a connection on each API version. Prints statuses only, never the key.
Run from agent/: uv run scripts/check_gemini_live.py"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
KEY = os.environ.get("GOOGLE_VOICE_API_KEY", "")
MODELS = ["gemini-3.8-live", "gemini-3.1-flash-live-preview"]


def clean(text: str) -> str:
    """Error text without the key or any URL (a URL can carry the key)."""
    text = text.replace(KEY, "***") if KEY else text
    return " ".join(w for w in text.split() if "://" not in w and "key=" not in w)[:160]


def client(api_version: str | None) -> genai.Client:
    # Same as the LiveKit plugin: only a timeout, and api_version only when it is set.
    options = types.HttpOptions(timeout=10_000)
    if api_version:
        options.api_version = api_version
    return genai.Client(api_key=KEY, http_options=options)


async def try_connect(model: str, api_version: str | None) -> str:
    try:
        c = client(api_version)  # keep a reference: a closed client cannot connect
        async with asyncio.timeout(20):
            async with c.aio.live.connect(model=model, config={"response_modalities": ["AUDIO"]}):
                return "CONNECTED"
    except Exception as e:
        return f"FAILED: {type(e).__name__}: {clean(str(e))}"


async def main() -> None:
    if not KEY:
        raise SystemExit("GOOGLE_VOICE_API_KEY is not set")
    plugin_version = client(None)._api_client._http_options.api_version
    print(f"api_version the plugin ends up with (none passed): {plugin_version}")

    print("\na) live models in models.list() (v1beta):")
    listed = set()
    lister = client("v1beta")
    for m in lister.models.list():
        if "live" in m.name:
            listed.add(m.name.removeprefix("models/"))
            print(f"   {m.name}: bidiGenerateContent={'bidiGenerateContent' in (m.supported_actions or [])}")

    print("\nb, c) live.connect:")
    for model in MODELS:
        if model not in listed:
            print(f"   {model}: not in the list, skipped")
            continue
        for version in dict.fromkeys([plugin_version, "v1beta", "v1alpha"]):
            print(f"   {model} on {version}: {await try_connect(model, version)}")


asyncio.run(main())
