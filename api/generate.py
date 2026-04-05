from http.server import BaseHTTPRequestHandler
import os, json, requests, hashlib

HF_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", "")
HF_URL = "https://api-inference.huggingface.co/models/facebook/musicgen-small"
_cache = {}

PROMPTS = {
    "Deep Focus": "ambient piano minimal focus concentration seamless loop",
    "Writing Flow": "gentle piano ambient flowing creative writing seamless loop",
    "Scene Mood": "cinematic atmospheric emotional strings seamless loop",
    "Emotional Access": "soft piano emotional intimate vulnerable seamless loop",
    "Late-Night": "nocturnal ambient piano dark intimate seamless loop",
    "Worldbuilding": "epic atmospheric ambient orchestral seamless loop",
    "Idea Spark": "bright uplifting piano creative energetic seamless loop",
    "Ambient Reset": "ambient drone peaceful cleansing slow seamless loop",
    "Cinematic Tension": "dark tension strings suspense cinematic seamless loop",
    "Momentum": "upbeat energetic piano forward motion seamless loop",
    "Calm & Settle": "gentle calming ambient 396hz dog anxiety seamless loop",
    "Storm Shield": "steady masking ambient 432hz calm dog seamless loop",
    "Vet Ready": "ultra calm minimal 528hz soothing seamless loop",
    "New Place": "warm welcoming ambient 639hz comfort seamless loop",
    "Senior Comfort": "slow gentle foundation 174hz comfort seamless loop",
    "Daily Calm": "balanced calm ambient 285hz daily seamless loop",
    "Purr Resonance": "deep healing 528hz feline purr resonance seamless loop",
    "Window Watch": "light alert calm 639hz observation seamless loop",
    "Settle & Sleep": "very slow sustained 432hz sleep seamless loop",
    "Vet Calm": "ultra minimal steady 396hz calm seamless loop",
    "Kitten Energy": "light gentle playful 639hz young seamless loop",
    "Senior Care": "very slow warm 174hz senior comfort seamless loop",
    "Dawn Awakening": "morning rising 285hz plant growth dawn seamless loop",
    "Growth Pulse": "steady rhythmic 200hz plant growth daily seamless loop",
    "Deep Root": "slow drone 174hz root development seamless loop",
    "Bloom Support": "bright warm 528hz flowering bloom seamless loop",
    "Seed Start": "gentle steady 396hz germination seamless loop",
    "Dusk Wind-Down": "slowing calm 432hz evening cycle seamless loop",
}

TEXTURES = {
    "Minimal Piano": "solo piano minimal sparse",
    "Warm Analog": "warm analog synthesizer gentle",
    "Ambient": "ambient drone atmospheric",
    "Dark Drone": "dark drone sustained bass",
    "Ethereal": "ethereal reverb floating",
    "Cinematic": "cinematic orchestra strings",
    "Orchestral Mist": "orchestral mist strings ambient",
    "Electronic Pulse": "electronic pulse rhythm tension",
    "Orchestral Swell": "orchestral swell strings building",
    "Sparse Strings": "sparse strings dissonant minimal",
    "Jazz Noir": "jazz noir saxophone piano",
    "Tender Theme": "tender melody emotional restraint",
}

SCENES = {
    "Chase / Action": "fast chase action propulsive",
    "Confrontation": "tense confrontation dramatic",
    "Quiet Moment": "quiet still intimate slow",
    "The Reveal": "reveal dramatic shift",
    "Romantic": "romantic slow intimate tender",
    "Dark / Tense": "dark tense dread building",
    "Comedic Beat": "comedic light timing playful",
    "Opening": "opening establishing tone",
    "Climax": "climax maximum stakes intense",
    "Aftermath": "aftermath slow quiet",
}

def make_prompt(mode, texture, genre=None, scene=None):
    base = PROMPTS.get(mode, "ambient peaceful calm music seamless loop")
    tex = TEXTURES.get(texture, "ambient gentle")
    if genre:
        g = PROMPTS.get(genre, "cinematic seamless loop")
        s = SCENES.get(scene, "cinematic")
        return f"{g} {s} {tex}"
    return f"{base} {tex}"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n))
        except Exception:
            return self._err(400, "Invalid JSON")

        mode = body.get("mode", "Deep Focus")
        texture = body.get("texture", "Minimal Piano")
        genre = body.get("genre")
        scene = body.get("scene")
        duration = min(int(body.get("duration", 30)), 60)

        key = hashlib.md5(f"{mode}:{texture}:{genre}:{scene}:{duration}".encode()).hexdigest()
        if key in _cache:
            return self._audio(_cache[key])

        if not HF_TOKEN:
            return self._err(500, "HUGGINGFACE_API_TOKEN not set")

        prompt = make_prompt(mode, texture, genre, scene)
        try:
            r = requests.post(
                HF_URL,
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json={"inputs": prompt, "parameters": {"max_new_tokens": duration * 50}},
                timeout=120,
            )
        except requests.Timeout:
            return self._err(504, "Timeout — retry in 30s")
        except Exception as e:
            return self._err(500, str(e))

        if r.status_code == 503:
            return self._err(503, "Model loading — retry in 20s")
        if r.status_code != 200:
            return self._err(r.status_code, f"HF error: {r.text[:200]}")

        _cache[key] = r.content
        self._audio(r.content)

    def _audio(self, data):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "audio/flac")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def _err(self, code, msg):
        body = json.dumps({"error": msg}).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
