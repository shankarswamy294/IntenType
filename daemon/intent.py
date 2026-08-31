from openai import OpenAI
from daemon import settings

# Model used for intent rewriting. Override via INTENTYPE_MODEL env var.
import os
REWRITE_MODEL = os.environ.get("INTENTYPE_MODEL", "gpt-4o-mini-2024-07-18")
# Set INTENTYPE_MODEL=gpt-5.6-luna to use GPT-5.6 Luna when available on your key.

_SYSTEM_TEMPLATE = (
    "You are a voice-to-text transcription cleaner. Your ONLY job is to clean up what "
    "the speaker said — remove filler words (\"um\", \"uh\", \"like\", \"you know\"), "
    "fix grammar and punctuation, and output the speaker's words in natural written form.\n"
    "CRITICAL RULES:\n"
    "- Preserve the speaker's exact intent, meaning, and perspective.\n"
    "- If the speaker asked a question, output a question.\n"
    "- Never generate a reply, response, or answer to what was said.\n"
    "- Never add content that wasn't spoken.\n"
    "- Output only the cleaned transcript — no preamble, no explanation.\n"
    "Tone: {tone_name}. {tone_instructions}"
)


def rewrite(raw: str, app_name: str) -> str:
    s = settings.load()
    api_key = s.get("openai_api_key", "")
    if not api_key:
        return raw

    tone_name, tone_instructions = settings.get_tone(app_name)
    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=REWRITE_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": _SYSTEM_TEMPLATE.format(
                        tone_name=tone_name,
                        tone_instructions=tone_instructions,
                    ),
                },
                {"role": "user", "content": raw},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return raw
