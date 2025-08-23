import requests

class Client:
    def __init__(self, base: str, user_name: str = "sayang", custom_prompt: str = "", ai_name: str = "Changli", model: str = "gemma3:4b"):
        self.base = base.rstrip("/")
        self.sess = requests.Session()
        self.chat_id = None
        self.user_name = user_name
        self.custom_prompt = custom_prompt
        self.ai_name = ai_name
        self.model = model

    def set_identity(self, user_name: str, custom_prompt: str, ai_name: str = None, model: str = None):
        self.user_name = user_name
        self.custom_prompt = custom_prompt
        if ai_name is not None:
            self.ai_name = ai_name
        if model is not None:
            self.model = model

    def healthy(self, timeout=0.8) -> bool:
        try:
            r = self.sess.get(self.base + "/config", timeout=timeout)
            return r.ok
        except Exception:
            return False

    def get_config(self, timeout=5):
        r = self.sess.get(self.base + "/config", timeout=timeout)
        r.raise_for_status()
        return r.json()
    
    def get_models(self, timeout=8):
        r = self.sess.get(self.base + "/models", timeout=timeout)
        r.raise_for_status()
        return r.json()

    def send(self, text: str, timeout=320) -> str:
        payload = {
            "message": text,
            "user_name": self.user_name,
            "custom_prompt": self.custom_prompt,
            "ai_name": self.ai_name,
            "model" : self.model,
        }
        if not self.chat_id:
            r = self.sess.post(self.base + "/chat", json=payload, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            self.chat_id = data.get("chat_id")
            self.model = data.get("model", self.model)
            return data.get("response", "")
        else:
            r = self.sess.post(self.base + f"/chat/{self.chat_id}", json=payload, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            self.model = data.get("model", self.model)
            return data.get("response", "")

    def get_history(self, chat_id: str, timeout=15):
        r = self.sess.get(self.base + f"/chat/{chat_id}", timeout=timeout)
        r.raise_for_status()
        return r.json() 
    
    def get_profile(self, timeout=8):
        r = self.sess.get(self.base + "/profile", timeout=timeout)
        r.raise_for_status()
        return r.json()

    def save_profile(self, about: str, job: str, facts: list[str] | None = None, timeout=10):
        payload = {"about": about, "job": job}
        if facts is not None: payload["facts"] = facts
        r = self.sess.post(self.base + "/profile", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()

    def clear_memory(self, chat_id: str, timeout=8):
        r = self.sess.post(self.base + f"/chat/{chat_id}/memory/clear", timeout=timeout)
        r.raise_for_status()
        return r.json()

    def get_i18n(self, lang: str, timeout=5):
        r = self.sess.get(self.base + f"/i18n/{(lang or 'en_us').lower()}", timeout=timeout)
        r.raise_for_status()
        return r.json()

    def set_settings(self, patch: dict, timeout=5):
        r = self.sess.post(self.base + "/settings", json=(patch or {}), timeout=timeout)
        r.raise_for_status()
        return r.json()
