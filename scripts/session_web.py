"""
Telegram session generator — browser UI, single persistent MTProto session.

Run:
    make session
    # equivalent:
    uv run --extra session --extra collect \
        streamlit run scripts/session_web.py --server.port 8502
Then open: http://localhost:8502

Reads TELEGRAM_API_ID / TELEGRAM_API_HASH (legacy aliases TG_API_ID / TG_API_HASH)
and writes TELEGRAM_SESSION_STRING / TELEGRAM_PHONE_NUMBER into .env.
"""

import asyncio
import importlib.util
import re
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from src.ingestor.session import resolve_session_env  # noqa: E402

load_dotenv()

st.set_page_config(page_title="Telegram Auth", page_icon="🔑", layout="centered")
st.title("🔑 Telegram — Génération de session")

ENV_PATH = ROOT / ".env"
_ENV = resolve_session_env()  # TELEGRAM_* first, then the legacy TG_* aliases
API_ID   = int(_ENV["api_id"] or 0)
API_HASH = _ENV["api_hash"] or ""

if importlib.util.find_spec("hydrogram") is None:
    st.error(
        "Hydrogram n'est pas installé (extra `collect`). Lancer : `make session`, ou "
        "`uv run --extra session --extra collect streamlit run scripts/session_web.py "
        "--server.port 8502`."
    )
    st.stop()
if not API_ID or not API_HASH:
    st.error(
        "TELEGRAM_API_ID et TELEGRAM_API_HASH (alias TG_API_ID / TG_API_HASH) doivent "
        "être définis, par exemple dans `.env` — à obtenir sur https://my.telegram.org, "
        "puis relancer."
    )
    st.stop()


# ── Persistent async runtime ─────────────────────────────────────────────────
# One event loop in a daemon thread so the Hydrogram client stays connected
# between the "send code" and "sign in" steps. asyncio.run() kills connections
# on exit — this avoids that.

class _AsyncRuntime:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self._thread.start()
        self.client = None
        self.phone_code_hash: str | None = None
        self.session_string: str | None = None
        self.error: str | None = None

    def run(self, coro, timeout: int = 30):
        """Run a coroutine in the persistent loop and block until done."""
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return fut.result(timeout=timeout)


def _get_runtime() -> _AsyncRuntime:
    if "auth_rt" not in st.session_state:
        st.session_state.auth_rt = _AsyncRuntime()
    return st.session_state.auth_rt


def update_env(key: str, value: str) -> None:
    # A fresh clone may have no .env yet (the API id/hash can come from the shell).
    content = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.is_file() else ""
    pattern = rf"^{re.escape(key)}=.*$"
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, lambda _: f"{key}={value}", content, flags=re.MULTILINE)
    else:
        content += f"\n{key}={value}\n"
    ENV_PATH.write_text(content, encoding="utf-8")


# ── Step machine ──────────────────────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = "phone"

rt = _get_runtime()


# ── STEP 1 : phone ────────────────────────────────────────────────────────────
if st.session_state.step == "phone":
    st.subheader("Étape 1 / 2 — Numéro de téléphone")
    phone = st.text_input("Numéro Telegram", value=_ENV["phone"] or "",
                          placeholder="+33612345678")

    if st.button("📨 Envoyer le code", type="primary", use_container_width=True):
        if not phone.strip().startswith("+"):
            st.error("Commence par + (ex: +33612345678)")
        else:
            with st.spinner("Connexion à Telegram..."):
                async def _send():
                    from hydrogram import Client
                    rt.client = Client(
                        "disinfo_auth",
                        api_id=API_ID,
                        api_hash=API_HASH,
                        in_memory=True,
                    )
                    await rt.client.connect()
                    sent = await rt.client.send_code(phone.strip())
                    rt.phone_code_hash = sent.phone_code_hash
                    rt.phone = phone.strip()

                try:
                    rt.run(_send(), timeout=20)
                    st.session_state.step = "code"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")


# ── STEP 2 : code ─────────────────────────────────────────────────────────────
elif st.session_state.step == "code":
    st.subheader("Étape 2 / 2 — Code de vérification")
    st.success(f"✅ Code envoyé sur **{rt.phone}** — valable ~5 minutes")
    st.warning("⚡ Entre le code **immédiatement** avant qu'il n'expire !")

    code = st.text_input("Code reçu par SMS / Telegram", placeholder="12345",
                         max_chars=6, key="code_input")
    password = st.text_input("Mot de passe 2FA (laisser vide si pas activé)",
                             type="password", key="pw_input")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Se connecter", type="primary", use_container_width=True):
            if not code.strip():
                st.error("Entre le code.")
            else:
                with st.spinner("Authentification..."):
                    async def _signin():
                        from hydrogram.errors import SessionPasswordNeeded
                        try:
                            await rt.client.sign_in(
                                rt.phone, rt.phone_code_hash, code.strip()
                            )
                        except SessionPasswordNeeded:
                            if not password:
                                raise ValueError("2FA activée — entre ton mot de passe")
                            await rt.client.check_password(password)
                        rt.session_string = await rt.client.export_session_string()
                        await rt.client.disconnect()

                    try:
                        rt.run(_signin(), timeout=20)
                        st.session_state.step = "done"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
                        if "PHONE_CODE_EXPIRED" in str(e):
                            st.info("Le code a expiré. Clique 'Renvoyer un code' pour en "
                                    "recevoir un nouveau.")

    with col2:
        if st.button("🔄 Renvoyer un code", use_container_width=True):
            # Disconnect existing client cleanly before retrying
            async def _disconnect():
                if rt.client:
                    try:
                        await rt.client.disconnect()
                    except Exception:
                        pass
            try:
                rt.run(_disconnect(), timeout=5)
            except Exception:
                pass
            st.session_state.step = "phone"
            st.rerun()


# ── STEP 3 : done ─────────────────────────────────────────────────────────────
elif st.session_state.step == "done":
    st.subheader("✅ Connexion réussie !")
    update_env("TELEGRAM_SESSION_STRING", rt.session_string)
    update_env("TELEGRAM_PHONE_NUMBER", rt.phone)
    st.success(
        "**TELEGRAM_SESSION_STRING** et **TELEGRAM_PHONE_NUMBER** écrits dans `.env` "
        "automatiquement."
    )
    st.warning("La chaîne de session est un secret (accès en lecture au compte) : "
               "ne jamais la committer ni la partager.")
    # The FULL string (copy button), so it can also be pasted into another .env.
    st.code(rt.session_string, language=None, wrap_lines=True)
    st.divider()
    st.subheader("Prochaine étape")
    st.code("uv run --extra collect python scripts/backfill.py --channel @Vbachir --limit 200",
            language="bash")
    if st.button("🔄 Nouvelle session"):
        for k in ["step", "auth_rt"]:
            st.session_state.pop(k, None)
        st.rerun()
