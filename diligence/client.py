"""Meta Model API client (OpenAI SDK, hackathon endpoint).

The submitted app calls this at runtime. Model: muse-spark-1.3.
Endpoint defaults to the Meta Model API; override only if the organizers
designate another base URL:
    META_MODEL_API_BASE / OPENAI_BASE_URL  (default https://api.meta.ai/v1)
    META_MODEL_API_KEY  / OPENAI_API_KEY   (required; create at dev.meta.ai)
"""
import os

MODEL = "muse-spark-1.3"
DEFAULT_BASE_URL = "https://api.meta.ai/v1"


def resolve_base_url():
    return (
        os.getenv("META_MODEL_API_BASE")
        or os.getenv("OPENAI_BASE_URL")
        or DEFAULT_BASE_URL
    )


def build_client():
    api_key = os.getenv("META_MODEL_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing Meta Model key: set META_MODEL_API_KEY (create one at "
            "dev.meta.ai). $150 of hackathon credits apply to the 10-day "
            "development window."
        )
    try:
        from openai import OpenAI  # lazy: tests and tools run without it
    except ImportError:
        raise RuntimeError(
            "The openai package is required for Meta Model API calls: "
            "pip install -r requirements.txt."
        )

    return OpenAI(base_url=resolve_base_url(), api_key=api_key)


def complete_json(client, system_prompt, payload, max_tokens=1200):
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


def complete_memo(client, system_prompt, payload):
    return complete_json(client, system_prompt, payload)
