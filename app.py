# -*- coding: utf-8 -*-
"""Leilao 05 Seja Digital - versao ONLINE (Streamlit Cloud).
O diretor aperta INICIAR LEILAO e todas as telas abertas passam a mostrar LEILAO INICIADO.
Estado compartilhado: arquivo JSON pequeno no Dropbox (secrets [dropbox]). Sem secrets (uso local): arquivo local.
Acesso: o app deve ser PRIVADO no Streamlit Cloud (Share > so os e-mails liberados).
Opcional (deixar VAZIO no app publico): [acesso] diretores = ["email1", "email2"] nos secrets -> so eles veem o botao INICIAR/Reiniciar;
os demais so acompanham. Lista vazia/ausente = quem entrou pode clicar."""
import base64
import datetime as dt
import io
import json
import math
import struct
import threading
import wave
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

AQUI = Path(__file__).parent
ESTADO_LOCAL = AQUI / "leilao_estado.json"
LOGO = AQUI / "logo_seja_digital.png"
TITULO = "Leilão 05 de Atendimento a Localidades com SMP"
LINK = "https://sejadigital.com.br/leilao05/"
DATA_LEILAO = "08/12/2026"
TZ = ZoneInfo("America/Sao_Paulo")

# cores da marca (do site/logo): azul, laranja do ":" e branco
AZUL, LARANJA = "#2B3990", "#FF5010"

st.set_page_config(page_title="Leilão 05 - Seja Digital", page_icon="🔨", layout="centered")


# ---------------------------------------------------------------- estado compartilhado
def _dbx_cfg():
    try:
        c = st.secrets["dropbox"]
        return c if "estado_path" in c else None
    except Exception:
        return None


def _dbx():
    import dropbox
    c = _dbx_cfg()
    d = dropbox.Dropbox(oauth2_refresh_token=c["refresh_token"], app_key=c["app_key"],
                        app_secret=c["app_secret"], timeout=15)
    if c.get("root_namespace_id"):
        d = d.with_path_root(dropbox.common.PathRoot.root(c["root_namespace_id"]))
    return d


@st.cache_resource
def _mem():
    return {"est": None, "t": 0.0, "lock": threading.Lock()}


def ler_estado():
    """Dict do estado ({} = nao iniciado) ou None se nao deu para ler e nao ha nada conhecido."""
    m = _mem()
    agora = time.time()
    if m["est"] is not None and agora - m["t"] < 1.5:
        return m["est"]
    with m["lock"]:
        try:
            if _dbx_cfg():
                import dropbox
                try:
                    _, r = _dbx().files_download(_dbx_cfg()["estado_path"])
                    est = json.loads(r.content.decode("utf-8") or "{}")
                except dropbox.exceptions.ApiError as e:
                    if "not_found" in str(e):
                        est = {}
                    else:
                        raise
            else:
                est = json.loads(ESTADO_LOCAL.read_text(encoding="utf-8")) if ESTADO_LOCAL.exists() else {}
            m["est"], m["t"] = est, agora
        except Exception:
            pass  # mantem o ultimo estado conhecido; se nao houver, devolve None (tela "Conectando")
        return m["est"]


def gravar_estado(d):
    m = _mem()
    with m["lock"]:
        if _dbx_cfg():
            import dropbox
            _dbx().files_upload(json.dumps(d).encode("utf-8"), _dbx_cfg()["estado_path"],
                                mode=dropbox.files.WriteMode.overwrite)
        else:
            ESTADO_LOCAL.write_text(json.dumps(d), encoding="utf-8")
        m["est"], m["t"] = d, time.time()


# ---------------------------------------------------------------- quem pode clicar
def _email_viewer():
    for nome in ("user", "experimental_user"):
        try:
            e = str(getattr(st, nome).get("email") or "").strip().lower()
            if e:
                return e
        except Exception:
            pass
    try:
        raw = str(st.context.headers.get("X-Streamlit-User") or "")
        if raw:
            raw += "=" * (-len(raw) % 4)
            return str(json.loads(base64.b64decode(raw)).get("email") or "").strip().lower()
    except Exception:
        pass
    return ""


def pode_clicar():
    try:
        lista = {str(x).strip().lower() for x in st.secrets.get("acesso", {}).get("diretores", [])}
    except Exception:
        lista = set()
    return (not lista) or (_email_viewer() in lista)


# ---------------------------------------------------------------- som de campainha (sintetizado, sem arquivo)
@st.cache_resource
def campainha_wav():
    """'Ding' unico e alto de campainha de balcao de hotel, gerado em Python (WAV 16 bits)."""
    sr = 22050
    dur = 2.4
    n = int(sr * dur)
    # parciais de sino (razoes inarmonicas) com decaimento exponencial
    parciais = [(1.0, 1.0, 3.0), (2.76, 0.55, 4.5), (5.40, 0.30, 6.5), (8.93, 0.12, 9.0)]
    f0 = 1568.0  # sol 6
    quadros = bytearray()
    for i in range(n):
        t = i / sr
        v = 0.0
        for inicio in (0.0,):  # um toque so
            if t >= inicio:
                tt = t - inicio
                for r, amp, dec in parciais:
                    v += amp * math.exp(-dec * tt) * math.sin(2 * math.pi * f0 * r * tt)
        v = max(-1.0, min(1.0, v * 0.95))
        quadros += struct.pack("<h", int(v * 32767))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(quadros))
    return buf.getvalue()


def tocar_campainha():
    st.audio(campainha_wav(), format="audio/wav", autoplay=True)


# ---------------------------------------------------------------- visual
def logo_html():
    if LOGO.exists():
        b64 = base64.b64encode(LOGO.read_bytes()).decode()
        return f'<img src="data:image/png;base64,{b64}" class="logo-img">'
    return ('<div class="wordmark">Seja<span class="dp">:</span>Digital</div>'
            '<div class="slogan">tudo está conectado</div>')


def _logo_inst(nome, arquivo):
    p = AQUI / arquivo
    if p.exists():
        b64 = base64.b64encode(p.read_bytes()).decode()
        return f'<div class="caixa-inst"><img src="data:image/png;base64,{b64}" alt="{nome}"></div>'
    return f'<div class="caixa-inst"><span class="txt-inst">{nome}</span></div>'


def rodape_html():
    """Faixa branca: MCom | Anatel, na mesma caixa (mesmo tamanho); GIRED logo abaixo."""
    return (
        '<div class="inst">'
        + _logo_inst("Ministério das Comunicações", "logo_mcom.png")
        + _logo_inst("Anatel", "logo_anatel.png")
        + "</div>"
        + ('<div class="gired-leg"><b>GIRED</b> · Grupo de Implantação do Processo de Redistribuição e '
           'Digitalização de Canais de TV e RTV</div>')
    )


GAVEL = (
    '<svg class="gavel" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="4" '
    'stroke-linecap="round" stroke-linejoin="round"><rect x="24" y="4" width="30" height="18" rx="4" '
    'transform="rotate(40 39 13)"/><path d="M33 32 10 54"/><path d="M6 59h28"/></svg>'
)

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&display=swap');
#MainMenu, header, footer {{visibility:hidden;}}
.stApp {{background:{AZUL}; font-family:'Montserrat','Gotham',sans-serif;}}
.bloco {{text-align:center; padding-top:7vh; color:#fff; font-family:'Montserrat','Gotham',sans-serif;}}
.wordmark {{font-size:3.6rem; font-weight:800; letter-spacing:-2px; color:#fff; line-height:1;}}
.wordmark .dp {{color:{LARANJA}; margin:0 2px;}}
.slogan {{font-size:.8rem; letter-spacing:1px; margin-top:4px; opacity:.9;}}
.logo-img {{max-height:100px;}}
.filete {{width:90px; height:4px; background:{LARANJA}; margin:34px auto 30px; border-radius:2px;}}
.edicao {{font-size:1.7rem; font-weight:600; line-height:1.3; margin:0 0 8px;}}
.sub {{opacity:.85; font-size:1rem; font-weight:400;}}
.gavel {{width:56px; height:56px; color:#fff; opacity:.9; margin:34px 0 8px;}}
.iniciado {{font-size:3.6rem; font-weight:800; letter-spacing:3px; color:#fff; margin:26px 0 0;
  animation: surge 1.2s ease-out both;}}
.filete.cresce {{animation: cresce 1.2s ease-out .3s both;}}
@keyframes surge {{from{{opacity:0; transform:translateY(14px);}} to{{opacity:1; transform:none;}}}}
@keyframes cresce {{from{{width:0;}} to{{width:160px;}}}}
.aovivo {{display:inline-flex; align-items:center; gap:10px; font-size:.95rem; letter-spacing:3px;
  font-weight:600; margin-top:6px;}}
.ponto {{width:11px; height:11px; border-radius:50%; background:{LARANJA}; animation: pisca 1.8s ease-in-out infinite;}}
@keyframes pisca {{0%,100%{{opacity:1;}} 50%{{opacity:.25;}}}}
.hora {{font-size:1.1rem; margin-top:26px; opacity:.9;}}
div[data-testid="stVerticalBlock"] {{align-items:center;}}
div[data-testid="stElementContainer"]:has(.bloco) {{width:100%;}}
div.stButton > button {{
  display:block; margin:0 auto; padding:20px 54px; font-size:1.3rem; font-weight:800; letter-spacing:2px;
  border-radius:6px; border:2px solid {LARANJA}; color:#fff; background:{LARANJA};
  font-family:'Montserrat','Gotham',sans-serif;
}}
div.stButton > button:hover {{background:#fff; color:{AZUL}; border-color:#fff;}}
a.lk {{color:#fff; opacity:.8; font-size:.95rem;}}
.inst {{display:inline-flex; align-items:center; justify-content:center; gap:34px; flex-wrap:wrap;
  background:#fff; border-radius:10px; padding:14px 30px; margin-top:38px;}}
.caixa-inst {{width:190px; height:56px; display:flex; align-items:center; justify-content:center;}}
.caixa-inst img {{max-width:100%; max-height:100%; object-fit:contain;}}
.txt-inst {{color:{AZUL}; font-weight:800; font-size:.95rem; text-align:center;}}
.seja-azul {{color:{AZUL}; font-weight:800; font-size:1.9rem; letter-spacing:-1px; line-height:1;}}
.seja-azul .dp {{color:{LARANJA};}}
.gired-leg {{margin:12px auto 0; max-width:760px; font-size:.72rem; line-height:1.45; opacity:.85; letter-spacing:.2px;}}
.gired-leg b {{letter-spacing:2px; font-size:.8rem;}}
div[data-testid="stAudio"], div[data-testid="stElementContainer"]:has(audio), audio {{
  position:absolute !important; width:1px !important; height:1px !important; opacity:0 !important;
  overflow:hidden !important; margin:0 !important; padding:0 !important; pointer-events:none !important;}}
.st-key-reset button, .st-key-recarregar button {{
  background:transparent !important; border:none !important; color:#fff !important; opacity:.28;
  font-size:1.5rem; font-weight:400; padding:2px 14px; letter-spacing:0; margin-top:28px;
}}
.st-key-reset button:hover, .st-key-recarregar button:hover {{opacity:.9; background:transparent !important; color:#fff !important;}}
.st-key-reset_sim button, .st-key-reset_nao button {{
  background:transparent; border:1px solid rgba(255,255,255,.6); color:#fff; padding:10px 22px; font-size:.95rem; letter-spacing:0;
}}
</style>
""",
    unsafe_allow_html=True,
)


@st.fragment(run_every=2)
def tela():
    """Relê o estado a cada 2 s: quem apertar o botão em qualquer computador faz TODAS as telas abertas mudarem."""
    estado = ler_estado()
    clicar = pode_clicar()

    if estado is None:
        st.markdown(
            f"""<div class="bloco">{logo_html()}<div class="filete"></div>
            <div class="sub">Conectando…</div></div>""",
            unsafe_allow_html=True,
        )
        if st.button("↻", key="recarregar", help="Tentar de novo"):
            _mem()["est"] = None
            st.rerun()
    elif not estado.get("iniciado"):
        st.markdown(
            f"""<div class="bloco">{logo_html()}
            <div class="filete"></div>
            <div class="edicao">{TITULO}</div>
            <div class="sub">{DATA_LEILAO} · aguardando o início</div>
            {GAVEL}</div>""",
            unsafe_allow_html=True,
        )
        st.session_state["_vi_aguardando"] = True
        if clicar and st.button("INICIAR LEILÃO", key="btn_iniciar"):
            gravar_estado({"iniciado": True, "quando": dt.datetime.now(TZ).isoformat()})
            st.rerun()
        st.markdown(f'<div class="bloco" style="padding-top:0">{rodape_html()}</div>', unsafe_allow_html=True)
    else:
        quando = dt.datetime.fromisoformat(estado["quando"]).strftime("%d/%m/%Y às %H:%M:%S")
        st.markdown(
            f"""<div class="bloco">{logo_html()}
            <div class="iniciado">LEILÃO INICIADO</div>
            <div class="filete cresce"></div>
            <div class="edicao">{TITULO}</div>
            <div class="aovivo"><span class="ponto"></span>EM ANDAMENTO</div>
            <div class="hora">Início: {quando} (horário de Brasília)</div>
            <div class="sub" style="margin-top:30px">
              <a class="lk" href="{LINK}" target="_blank">sejadigital.com.br/leilao05</a></div>
            {rodape_html()}</div>""",
            unsafe_allow_html=True,
        )
        if st.session_state.get("_vi_aguardando"):  # so toca quando ESTA tela viu a virada (nao ao recarregar)
            st.session_state["_vi_aguardando"] = False
            st.session_state["_sino_ate"] = time.time() + 5
        if time.time() < st.session_state.get("_sino_ate", 0):  # mantem o <audio> na tela ate o som acabar
            tocar_campainha()
        if clicar:
            if st.session_state.get("_conf_reset"):
                st.markdown('<div class="sub" style="margin-top:24px;text-align:center">Voltar para antes do leilão?</div>',
                            unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("Sim, recomeçar", key="reset_sim"):
                    gravar_estado({})
                    st.session_state["_conf_reset"] = False
                    st.rerun()
                if c2.button("Cancelar", key="reset_nao"):
                    st.session_state["_conf_reset"] = False
                    st.rerun()
            elif st.button("↺", key="reset", help="Recomeçar"):
                st.session_state["_conf_reset"] = True
                st.rerun()


tela()
