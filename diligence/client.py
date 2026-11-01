"""Meta Model API client (OpenAI SDK, hackathon endpoint).

The submitted app calls this at runtime. Model: muse-spark-1.3.
Configure via environment:
    META_MODEL_API_BASE / OPENAI_BASE_URL  (hackathon endpoint)
    META_MODEL_API_KEY  / OPENAI_API_KEY   (key)
"""
import os

MODEL = "muse-spark-1.3"


def build_client():
    base_url = os.getenv("META_MODEL_API_BASE") or os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("META_MODEL_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not base_url:
        raise RuntimeError(
            "Missing Meta Model endpoint: set META_MODEL_API_BASE "
            "(or OPENAI_BASE_URL)."
        )
    if not api_key:
        raise RuntimeError(
            "Missing Meta Model key: set META_MODEL_API_KEY (or OPENAI_API_KEY)."
        )
    from openai import OpenAI  # lazy: tests and tools run without it

    return OpenAI(base_url=base_url, api_key=api_key)


def complete_memo(client, system_prompt, payload):
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=1200,
    )
    return resp.choices[0].message.content
