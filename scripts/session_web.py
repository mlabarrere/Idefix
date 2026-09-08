"""
Telegram session generator — browser UI, single persistent MTProto session.

Run:
    streamlit run scripts/session_web.py --server.port 8502
Then open: http://localhost:8502
"""

import asyncio
import os
import re
import threading
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Telegram Auth", page_icon="🔑", layout="centered")
st.title("🔑 Telegram — Génération de session")

ENV_PATH = Path(__file__).parent.parent / ".env"
API_ID   = int(os.environ.get("TG_API_ID", 0))
API_HASH = os.environ.get("TG_API_HASH", "")


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
    content = ENV_PATH.read_text(encoding="utf-8")
    pattern = rf"^{re.escape(key)}=.*$"
    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, f"{key}={value}", content, flags=re.MULTILINE)
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
    phone = st.text_input("Numéro Telegram", value=os.environ.get("TG_PHONE", ""),
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
                            st.info("Le code a expiré. Clique 'Renvoyer un code' pour en recevoir un nouveau.")

    with col2:
        if st.button("🔄 Renvoyer un code", use_container_width=True):
            # Disconnect existing client cleanly before retrying
            async def _disconnect():
                if rt.client:
                    try: await rt.client.disconnect()
                    except: pass
            try: rt.run(_disconnect(), timeout=5)
            except: pass
            st.session_state.step = "phone"
            st.rerun()


# ── STEP 3 : done ─────────────────────────────────────────────────────────────
elif st.session_state.step == "done":
    st.subheader("✅ Connexion réussie !")
    update_env("TG_SESSION_STRING", rt.session_string)
    update_env("TG_PHONE", rt.phone)
    st.success("**TG_SESSION_STRING** et **TG_PHONE** écrits dans `.env` automatiquement.")
    st.code(rt.session_string[:80] + "...", language=None)
    st.divider()
    st.subheader("Prochaine étape")
    st.code("python scripts/backfill.py --channel @Vbachir --limit 200", language="bash")
    if st.button("🔄 Nouvelle session"):
        for k in ["step", "auth_rt"]:
            st.session_state.pop(k, None)
        st.rerun()
