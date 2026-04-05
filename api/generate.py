import os
import json
import requests
import hashlib

_cache = {}

HF_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", "")
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/musicgen-small"

def build_prompt(mode, texture, genre=None, scene=None):
    base = {
        "Deep Focus": "ambient piano minimal focus concentration",
        "Writing Flow": "gentle piano ambient flowing creative writing",
        "Scene Mood": "cinematic atmospheric emotional strings",
        "Emotional Access": "soft piano emotional intimate vulnerable",
        "Late-Night": "nocturnal ambient piano dark intimate",
        "Worldbuilding": "epic atmospheric ambient orchestral",
        "Idea Spark": "bright uplifting piano creative energetic",
        "Ambient Reset": "ambient drone peaceful cleansing slow",
        "Cinematic Tension": "dark tension strings suspense cinematic",
        "Momentum": "upbeat energetic piano forward motion",
        "Calm & Settle": "gentle calming ambient 396hz dog anxiety relief",
        "Storm Shield": "steady masking ambient 432hz calm dog storms",
        "Vet Ready": "ultra calm minimal 528hz soothing dog vet",
        "New Place": "warm welcoming ambient 639hz dog comfort",
        "Senior Comfort": "slow gentle foundation 174hz aging dog",
        "Daily Calm": "balanced calm ambient 285hz dog daily",
        "Purr Resonance": "deep healing 528hz feline purr resonance",
        "Window Watch": "light alert calm 639hz cat observation",
        "Settle & Sleep": "very slow sustained 432hz cat sleep",
        "Vet Calm": "ultra minimal steady 396hz cat stress",
        "Kitten Energy": "light gentle playful 639hz young cat",
        "Senior Care": "very slow warm 174hz senior cat comfort",
        "Dawn Awakening": "morning rising 285hz plant growth dawn",
        "Growth Pulse": "steady rhythmic 200hz plant growth daily",
        "Deep Root": "slow drone 174hz root development soil",
        "Bloom Support": "bright warm 528hz flowering bloom plants",
        "Seed Start": "gentle steady 396hz germination seedling",
        "Dusk Wind-Down": "slowing calm 432hz plant evening cycle",
        "Blank Verse": "minimal piano sparse poetic silence",
        "Lyric Flow": "melodic piano lyrical flowing song",
        "Dark Sonnet": "dark minor piano formal tension poem",
        "Love Poem": "tender intimate piano vulnerable love",
        "Spoken Word": "rhythmic percussion forward spoken word",
        "Memory Poem": "hazy ambient memory nostalgic piano",
        "Haiku Space": "extreme sparse silence minimal haiku zen",
        "Elegy": "slow grief piano strings elegy loss",
        "Celebration": "bright joyful piano uplifting celebration",
        "Script Read": "neutral cinematic piano reading focus",
        "Budget Build": "steady mathematical neutral ambient",
        "Composition Flow": "harmonic open spacious piano composing",
        "Scoring Session": "cinematic tension dark scoring film",
        "Post Pipeline": "ambient neutral editorial background",
        "Action / Thriller": "action thriller tension fast cinematic",
        "Drama": "dramatic emotional cinematic strings piano",
        "Horror": "dark horror dissonant strings dread tension",
        "Romantic Comedy": "light romantic playful piano charming",
        "Sci-Fi / Fantasy": "sci-fi atmospheric electronic epic ambient",
        "Crime / Noir": "jazz noir dark saxophone moody",
        "Prestige Drama": "slow burn dramatic piano strings",
        "Western": "western acoustic guitar sparse ambient",
        "Animation": "whimsical playful bright orchestral",
        "True Crime": "procedural tension dark ambient",
        "Comedy": "light comedic playful bright piano",
        "Limited Series": "tension drama suspense cinematic",
    }
    textures = {
        "Minimal Piano": "solo piano minimal sparse",
        "Warm Analog": "warm analog synthesizer gentle",
        "Ambient": "ambient drone atmospheric",
        "Dark Drone": "dark drone sustained bass",
        "Ethereal": "ethereal reverb floating",
        "Cinematic": "cinematic orchestra strings",
        "Orchestral Mist": "orchestral mist strings ambient",
        "Textural Guitar": "guitar textural ambient",
        "Electronic Pulse": "electronic pulse rhythm tension",
        "Orchestral Swell": "orchestral swell strings building",
        "Sparse Strings": "sparse strings dissonant minimal",
        "Jazz Noir": "jazz noir saxophone piano",
        "Ambient Score": "ambient score sparse silence",
        "Propulsive Rhythm": "propulsive rhythm driving forward",
        "Tender Theme": "tender melody emotional restraint",
    }
    scenes = {
        "Chase / Action": "fast chase action propulsive",
        "Confrontation": "tense confrontation dramatic",
        "Quiet Moment": "quiet still intimate slow",
        "The Reveal": "reveal dramatic shift",
        "Romantic": "romantic slow intimate tender",
        "Dark / Tense": "dark tense dread building",
        "Comedic Beat": "comedic light timing playful",
        "Montage": "montage forward motion",
        "Opening": "opening establishing tone",
        "Climax": "climax maximum stakes intense",
        "Aftermath": "aftermath slow quiet",
        "Exposition": "neutral informational background",
    }
    mode_p = base.get(mode, "ambient peaceful calm music")
    texture_p = textures.get(texture, "ambient gentle")
    if genre:
        genre_p = base.get(genre, "cinematic")
        scene_p = scenes.get(scene, "cinematic")
        return f"{genre_p} {scene_p} {texture_p} seamless loop"
    return f"{mode_p} {texture_p} seamless loop"


def handler(request):
    if request.method == "OPTIONS":
        return Response("", status=200, headers=cors_headers())

    try:
        body = request.json()
    except Exception:
        return Response(json.dumps({"error": "Invalid JSON"}), status=400,
                       content_type="application/json", headers=cors_headers())

    mode = body.get("mode", "Deep Focus")
    texture = body.get("texture", "Minimal Piano")
    genre = body.get("genre")
    scene = body.get("scene")
    duration = min(int(body.get("duration", 30)), 60)

    key = hashlib.md5(f"{mode}:{texture}:{genre}:{scene}:{duration}".encode()).hexdigest()
    if key in _cache:
        return Response(_cache[key], status=200, content_type="audio/flac",
                       headers={**cors_headers(), "Cache-Control": "public, max-age=3600"})

    if not HF_TOKEN:
        return Response(json.dumps({"error": "HUGGINGFACE_API_TOKEN not configured"}),
                       status=500, content_type="application/json", headers=cors_headers())

    prompt = build_prompt(mode, texture, genre, scene)
    try:
        resp = requests.post(
            HF_API_URL,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": duration * 50}},
            timeout=120,
        )
    except requests.Timeout:
        return Response(json.dumps({"error": "MusicGen timed out — retry in 30s"}),
                       status=504, content_type="application/json", headers=cors_headers())
    except Exception as e:
        return Response(json.dumps({"error": str(e)}),
                       status=500, content_type="application/json", headers=cors_headers())

    if resp.status_code == 503:
        return Response(json.dumps({"error": "Model loading — retry in 20s"}),
                       status=503, content_type="application/json", headers=cors_headers())
    if resp.status_code != 200:
        return Response(json.dumps({"error": f"HF error {resp.status_code}"}),
                       status=resp.status_code, content_type="application/json", headers=cors_headers())

    _cache[key] = resp.content
    return Response(resp.content, status=200, content_type="audio/flac",
                   headers={**cors_headers(), "Cache-Control": "public, max-age=3600"})


def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


class Response:
    def __init__(self, body, status=200, content_type="text/plain", headers=None):
        self.body = body
        self.status_code = status
        self.content_type = content_type
        self.headers = headers or {}
