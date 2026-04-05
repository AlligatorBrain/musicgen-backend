import os
import json
import requests
import hashlib
from http.server import BaseHTTPRequestHandler

HF_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", "")
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/musicgen-small"

_cache = {}

def build_prompt(mode, texture, genre=None, scene=None):
    base_prompts = {
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
        "Research Mode": "calm neutral ambient background focus",
        "Revision": "gentle thoughtful piano calm reflective",
        "Calm & Settle": "gentle calming ambient 396hz dog anxiety relief",
        "Storm Shield": "steady masking ambient 432hz calm dog",
        "Vet Ready": "ultra calm minimal 528hz soothing dog",
        "New Place": "warm welcoming ambient 639hz dog comfort",
        "Senior Comfort": "slow gentle foundation 174hz aging dog comfort",
        "Daily Calm": "balanced calm ambient 285hz dog daily",
        "Purr Resonance": "deep healing 528hz feline purr resonance calm",
        "Window Watch": "light alert calm 639hz cat observation",
        "Settle & Sleep": "very slow sustained 432hz cat sleep",
        "Vet Calm": "ultra minimal steady 396hz cat stress",
        "Kitten Energy": "light gentle playful 639hz young cat",
        "Senior Care": "very slow warm 174hz senior cat comfort",
        "Dawn Awakening": "morning rising 285hz plant growth dawn",
        "Growth Pulse": "steady rhythmic 200hz plant growth daily",
        "Deep Root": "slow drone 174hz root development soil",
        "Bloom Support": "bright warm 528hz flowering bloom",
        "Seed Start": "gentle steady 396hz germination seedling",
        "Dusk Wind-Down": "slowing calm 432hz plant evening cycle",
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
        "Blank Verse": "minimal piano sparse poetic silence",
        "Lyric Flow": "melodic piano lyrical flowing song",
        "Dark Sonnet": "dark minor piano formal tension",
        "Love Poem": "tender intimate piano vulnerable",
        "Spoken Word": "rhythmic percussion forward spoken word",
        "Memory Poem": "hazy ambient memory nostalgic piano",
        "Nature Verse": "nature ambient organic birds gentle",
        "Haiku Space": "extreme sparse silence minimal haiku",
        "Elegy": "slow grief piano strings elegy loss",
        "Celebration": "bright joyful piano uplifting celebration",
        "Script Read": "neutral cinematic piano reading focus",
        "Budget Build": "steady mathematical neutral ambient",
        "Composition Flow": "harmonic open spacious piano composing",
        "Scoring Session": "cinematic tension dark scoring film",
        "Post Pipeline": "ambient neutral editorial background",
        "Late-Night Edit": "nocturnal dark sustained edit focus",
        "Creative Reset": "ambient cleansing slow peaceful reset",
        "Review Mode": "neutral calm analytical piano review",
    }
    texture_prompts = {
        "Minimal Piano": "solo piano minimal sparse",
        "Warm Analog": "warm analog synthesizer gentle",
        "Ambient": "ambient drone atmospheric",
        "Dark Drone": "dark drone sustained bass",
        "Ethereal": "ethereal reverb floating",
        "Cinematic": "cinematic orchestra strings",
        "Orchestral Mist": "orchestral mist strings ambient",
        "Textural Guitar": "guitar textural ambient",
        "Vocal Haze": "vocal haze ethereal choir",
        "Electronic Drift": "electronic drift synthesizer",
        "Organic Pulse": "organic pulse rhythm gentle",
        "Percussive Motion": "percussion rhythm motion",
        "Electronic Pulse": "electronic pulse rhythm tension",
        "Orchestral Swell": "orchestral swell strings building",
        "Sparse Strings": "sparse strings dissonant minimal",
        "Jazz Noir": "jazz noir saxophone piano",
        "Ambient Score": "ambient score sparse silence",
        "Propulsive Rhythm": "propulsive rhythm driving forward",
        "Elfman Quirk": "quirky playful whimsical orchestra",
        "Action Brass": "action brass bold driving",
        "Tender Theme": "tender melody emotional restraint",
        "Documentary Real": "neutral ambient grounded",
    }
    scene_map = {
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
    mode_prompt = base_prompts.get(mode, "ambient peaceful calm music")
    texture_prompt = texture_prompts.get(texture, "ambient gentle")
    if genre:
        genre_prompt = base_prompts.get(genre, "cinematic")
        scene_prompt = scene_map.get(scene, "cinematic")
        return f"{genre_prompt} {scene_prompt} {texture_prompt} seamless loop"
    return f"{mode_prompt} {texture_prompt} seamless loop"


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception:
            return self._error(400, "Invalid JSON")

        mode = body.get("mode", "Deep Focus")
        texture = body.get("texture", "Minimal Piano")
        genre = body.get("genre")
        scene = body.get("scene")
        duration = min(int(body.get("duration", 30)), 60)

        key = hashlib.md5(f"{mode}:{texture}:{genre}:{scene}:{duration}".encode()).hexdigest()
        if key in _cache:
            return self._send_audio(_cache[key])

        if not HF_TOKEN:
            return self._error(500, "HUGGINGFACE_API_TOKEN not set")

        prompt = build_prompt(mode, texture, genre, scene)
        try:
            resp = requests.post(
                HF_API_URL,
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json={"inputs": prompt, "parameters": {"max_new_tokens": duration * 50}},
                timeout=120,
            )
        except requests.Timeout:
            return self._error(504, "MusicGen timed out — retry")
        except Exception as e:
            return self._error(500, str(e))

        if resp.status_code == 503:
            return self._error(503, "Model loading — retry in 20s")
        if resp.status_code != 200:
            return self._error(resp.status_code, f"HF error: {resp.text[:200]}")

        _cache[key] = resp.content
        self._send_audio(resp.content)

    def _send_audio(self, data):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "audio/flac")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def _error(self, code, msg):
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg}).encode())

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
