from openai import OpenAI
from daemon import settings

_SYSTEM_TEMPLATE = (
    'You are a voice-to-text assistant. Clean up the transcript — remove filler words '
    '("um", "uh", "like", "you know"), fix grammar and punctuation, and output natural '
    "written text. Do not add content that wasn't said. Output only the cleaned text "
    "with no preamble or explanation.\n"
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
            model="gpt-4o-mini",
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
