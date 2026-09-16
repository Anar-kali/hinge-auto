"""Custom mode — the user's opener voice and stated rubric.

MESSAGE_VOICE points at voice/custom.py, written from the user's own
reply style guide.

PREFERENCES below encodes what the user actually stated: intelligence
is the real type, and strong physical attractiveness is an independent
second route to a like — either one alone is enough; brown skin tone is
explicitly not a negative; obesity is the one hard exclusion.

Note on height: Hinge stores height as a profile field and exposes a
Height filter in-app. That is exact. Judging height from photos is
mostly guesswork, so the rubric below deliberately does NOT gate on it —
set the in-app Height filter instead (see filters.py).
"""

NAME = "custom"
DESCRIPTION = "Intelligence or strong attractiveness — either passes."

# Not stated by the user. Set these, or use Hinge's in-app age filter.
AGE_MIN = None
AGE_MAX = None

MESSAGE_VOICE = "custom"

MAX_LIKES_PER_SESSION = None
MAX_PROFILES_PER_SESSION = None

# Empty on purpose. Premades are sent VERBATIM, bypassing the voice
# rules — the opposite of what the user's guide asks for (every line
# anchored to something specific in her profile). A premade is by
# definition copy-pasteable to anyone.
PREMADES = []

PREFERENCES = """
Default decision: considered judgment. Lean LIKE when EITHER the profile
shows genuine intelligence OR she is clearly, strongly physically
attractive. These are two independent routes — either one alone is
enough. Skip only when neither is present, or a hard exclusion applies.

## Primary criterion: intelligence

This is the actual type. Weight it above everything else. Judge it from
what she has written, not from credentials alone.

Strong signals:
- Prompt answers with a real idea, a specific opinion, or wit that
  required thought to construct.
- Writing that is precise, or funny in a way that depends on word
  choice.
- Curiosity: things she is into, described with specificity rather than
  as a list of generic interests.
- Evidence of a demanding field, craft, or discipline — but only as
  supporting evidence, never as the whole case.

Weak or absent signals:
- Every prompt left at the default, one-word, or filled with cliches
  ("fluent in sarcasm", "ask me anything").
- Nothing written anywhere that reveals how she thinks.

If a profile shows no evidence of how she thinks, that is a SKIP with
skip_reason="preferences" — UNLESS she clears the attractiveness bar in
the next section, which passes her on its own.

## Physical attractiveness: an independent route to a LIKE

The user leans toward tall, fit, fair women. This works two ways:

1. As a weighting. It breaks ties between otherwise comparable
   profiles and raises enthusiasm on one that already passes on
   intelligence. It is never on its own a reason to SKIP an
   intelligent profile.

2. As a standalone pass. If she is clearly and strongly physically
   attractive, that alone is sufficient — LIKE her even when the
   profile reveals nothing about how she thinks. Thin, cliche,
   one-word, or default prompts do NOT disqualify an attractive
   profile. Do not skip for "generic prompts", "no intellectual
   signal", or "no insight into how she thinks" when the photos
   clearly carry the profile on their own.

   Hold a HIGH bar here. This route is for profiles where
   attractiveness is striking and obvious across several photos --
   roughly the strongest quarter of what comes through the queue, not
   simply "she looks good". Attractive-but-not-striking does NOT
   qualify. If she is short of that band AND the writing shows
   nothing, that is a SKIP, and the correct one.

   Calibration check: if you find yourself passing nearly every
   profile on this route, the bar has slipped. Raise it. A run where
   this route passes everything carries no information.

Explicitly:
- Curly hair is a mild positive. Nudge enthusiasm up a little where it
  is clearly present. Keep this SMALL -- it breaks ties, it never
  carries a profile on its own, and its absence is never a mark
  against anyone.
- The user is less drawn to the darkest end of the skin-tone range.
  Treat this as a mild reduction in enthusiasm only, applied at the
  margin on an already-borderline profile. It is NOT a gate and never
  a skip_reason on its own.
- Brown and medium skin tones remain explicitly NOT a negative. The
  user stated this directly and it still stands. Do not down-weight them,
  and never let tone hold back a profile that otherwise clears a route.
- Never mention skin tone in the `reasoning` field, and never in a
  message. Weigh it silently; do not narrate it.
- Do not skip for being short, or for not matching the "fair" lean.
  These reduce enthusiasm; they do not disqualify.
- Height is usually not determinable from photos. Do not guess at it.
  If Hinge shows a height field, you may use it; otherwise ignore
  height entirely.

## Hard exclusion

Skip if she is visibly overweight or heavier — this covers clearly
obese AND clearly chubby/heavyset, not obesity alone. Use
skip_reason="preferences".

This is the one physical criterion that is a gate rather than a lean.
Apply it carefully:
- Only when body type is CLEARLY determinable across the photos.
- Not from a single unflattering angle, a loose outfit, a group shot
  where you cannot tell who she is, or face-only crops.
- If body type is not clearly determinable, do NOT skip on that basis.
  Fall through to the rest of the rubric and judge on intelligence.
  A wrong skip here is worse than a wrong like — it costs a profile
  that may well have matched.
- Being fit or average build is not this gate. It only fires once body
  type reads as visibly heavier than average across multiple photos.

## Also skip

- Fake / bot / spam profiles: a single AI-generated or stock photo; a
  bio that is only an off-platform handle ("snap me at X"); photos and
  stated info that obviously contradict each other. Use
  skip_reason="preferences" unless it is plainly low-effort, in which
  case use skip_reason="low_effort".
- Genuinely empty profiles — no readable prompts, no bio, no photo with
  a person visible. Use skip_reason="low_effort".

## When you like but have no hook

If she passes the rubric but offers no specific detail worth writing
about, still LIKE, with message="" and message_archetype="empty". Per
the voice rules, an empty opener beats a generic one.

## Reasoning field

Reference concrete details ("the prompt about X", "photo 3 shows...").
State which route drove the decision — intelligence, attractiveness, or
both — and for a SKIP, say why neither applied. Stay factual and
non-judgmental in how you describe people.
"""
