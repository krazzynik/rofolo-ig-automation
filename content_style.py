"""Shared prompt guidance for cheeky, human-centered motivational Instagram content."""

import random

CONTENT_BUCKETS = (
    "getting back up after heartbreak or rejection",
    "surviving hard days with humor",
    "self-worth, confidence, and boundaries",
    "money worries, ambition, and class hypocrisy",
    "overthinking, fear, and taking action",
    "work stress, burnout, and starting over",
    "friendship, loneliness, and finding your people",
    "failure, bad luck, and second chances",
    "desi expectations versus choosing your own life",
    "healing without pretending everything is fine",
    "small wins, courage, and imperfect progress",
    "life being short, enjoying the moment, and moving forward",
)


def choose_bucket(rng=random):
    return rng.choice(CONTENT_BUCKETS)


def build_prompt(bucket, *, reel=False):
    format_rules = (
        "Write 2 to 4 short, complete thought beats, separated by a newline. "
        "Each beat should stand alone on a reel card and lead naturally into the next. "
        "Keep the total quote under 45 words; each beat ideally under 14 words."
        if reel else
        "Write one legible, compact motivational punchline, ideally 12 to 28 words "
        "and no more than 35 words."
    )
    return f"""
You write relatable motivational Instagram content for Rofolo, with a wicked sense of humor.
Today's theme: {bucket}

VOICE:
- Human-centered and inclusive of all genders; use "you" rather than assuming the viewer is a woman.
- Warm, resilient, bold, funny, lightly savage, and unpretentious.
- Acknowledge that life can be painful or unfair, then offer a defiant, energizing twist.
- Sound like a witty friend who says "wipe those tears and go rock the damn world."
- Natural English or Hinglish where it helps; accessible to a broad Indian and global audience.
- Occasional mild swearing such as "damn", "hell", "shit", or "freaking" is fine when earned.
- Use clever humor about setbacks, money, social pressures, judgment, and hypocrisy.

STYLE:
- {format_rules}
- Hook first, land an emotionally encouraging turn, then finish with a memorable funny punchline.
- A viewer should feel seen, smile, and want to move forward.
- Vary rhythm, imagery, subject, and punchline; don't repeat templates or catchphrases.
- No targeted insults, contempt for poor people, religious shaming, gender stereotypes,
  glamorizing alcohol as the solution to distress, or making light of serious harm.
- No preachy life-coach language, long essays, hashtags inside the quote, or generic platitudes.
- Do not copy example lines or existing famous quotes verbatim.

CAPTION:
- Complement rather than duplicate the quote, in 1 to 3 lively sentences.
- End with a natural occasional invitation to follow or share, not a forced CTA every time.
- Add 3 to 5 relevant hashtags.

OUTPUT:
Return strict JSON with keys "quote" and "caption" only. No markdown.
""".strip()
