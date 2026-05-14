"""Agenda MaLuê — ADMIN.

Versão completa pra Luene: vê valores, edita campos da equipe e salva
direto na planilha via Google Apps Script webhook.
"""
from __future__ import annotations

import io
import json
from datetime import date, datetime

import pandas as pd
import requests
import streamlit as st

DIAS_SEMANA_PT = [
    "Segunda", "Terça", "Quarta", "Quinta",
    "Sexta", "Sábado", "Domingo",
]


def dia_semana_pt(d: date) -> str:
    return DIAS_SEMANA_PT[d.weekday()]


# ============================================================
# Config
# ============================================================
SHEET_ID = "13ibY4_88N7pTK2lrLkNcudGeVyh78Kry6Y60Ijp0JD4"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
LOGO_URL = "https://raw.githubusercontent.com/malueoficial/malue-contratos/main/malue_icon.png"

WEBHOOK_URL = ""
try:
    WEBHOOK_URL = st.secrets.get("WEBHOOK_URL", "")
except Exception:
    WEBHOOK_URL = ""

st.set_page_config(
    page_title="Agenda MaLuê — Admin",
    page_icon=LOGO_URL,
    layout="centered",
)

st.markdown(
    """
    <style>
      :root {
        --bg: #0a0a0a;
        --card: #161616;
        --card-hover: #1f1f1f;
        --lime: #c8f032;
        --text: #f5f5f5;
        --muted: #8a8a8a;
      }
      .stApp { background: var(--bg) !important; }
      html, body, [class*="css"] {
        color: var(--text);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      }
      .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 4rem !important;
        max-width: 720px !important;
      }
      h1, h2, h3, h4 { color: var(--text); font-weight: 800; letter-spacing: -0.5px; }
      .stMarkdown p { color: var(--text); }

      .header-wrap { text-align: center; margin-bottom: 1.4rem; }
      .header-logo {
        width: 110px;
        height: 110px;
        border-radius: 20px;
        margin: 0 auto 0.6rem;
        display: block;
      }
      .header-title {
        font-size: 2.2rem;
        font-weight: 900;
        color: var(--text);
        line-height: 1;
        margin: 0.3rem 0 0.2rem 0;
      }
      .header-sub {
        color: var(--lime);
        font-weight: 700;
        font-size: 0.9rem;
        letter-spacing: 1.2px;
        text-transform: uppercase;
      }
      .admin-badge {
        display: inline-block;
        background: rgba(200,240,50,0.18);
        color: var(--lime);
        padding: 0.15rem 0.5rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-left: 0.4rem;
      }

      .stRadio > div { flex-direction: row !important; justify-content: center; gap: 0.3rem; }
      .stRadio label {
        background: var(--card);
        border: 1px solid #2a2a2a;
        padding: 0.4rem 1rem !important;
        border-radius: 999px !important;
        cursor: pointer;
        color: var(--text) !important;
      }
      .stRadio label:hover { border-color: var(--lime); }

      .show-card {
        background: var(--card);
        border: 1px solid #222;
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
        margin-bottom: 0.5rem;
        display: flex;
        gap: 1rem;
        align-items: center;
      }
      .show-card:hover { background: var(--card-hover); border-color: var(--lime); }
      .date-block {
        background: var(--lime);
        color: #0a0a0a;
        border-radius: 12px;
        padding: 0.6rem 0.4rem;
        min-width: 64px;
        text-align: center;
        font-weight: 900;
      }
      .date-day { font-size: 1.6rem; line-height: 1; display: block; }
      .date-month {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        display: block;
        margin-top: 0.15rem;
      }
      .show-info { flex: 1; min-width: 0; }
      .show-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--text);
        margin: 0;
        word-break: break-word;
      }
      .show-meta { color: var(--muted); font-size: 0.85rem; margin-top: 0.2rem; }
      .show-valor {
        color: var(--lime);
        font-weight: 700;
        font-size: 0.95rem;
        margin-top: 0.3rem;
      }

      .status-pill {
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .status-confirmado { background: rgba(200,240,50,0.18); color: var(--lime); }
      .status-realizado { background: #2a2a2a; color: #888; }
      .status-pago { background: rgba(100,200,100,0.18); color: #6fc66f; }
      .status-contrato { background: rgba(100,160,255,0.18); color: #7eb6ff; }
      .status-cancelado { background: rgba(255,100,100,0.18); color: #ff7a7a; }
      .status-folga { background: rgba(255,180,80,0.15); color: #ffb04a; }

      [data-testid="stExpander"] {
        background: var(--card) !important;
        border: 1px solid #222 !important;
        border-radius: 12px !important;
        margin-top: -0.1rem;
        margin-bottom: 0.8rem;
      }
      [data-testid="stExpander"] summary {
        color: var(--lime) !important;
        font-weight: 700;
        font-size: 0.85rem;
        padding: 0.6rem 1rem !important;
      }
      [data-testid="stExpander"] > div > div {
        padding: 0.6rem 1rem !important;
      }

      .stTextInput input, .stSelectbox > div > div, .stTextArea textarea {
        background: #0d0d0d !important;
        color: var(--text) !important;
        border-color: #2a2a2a !important;
      }
      .stTextInput label, .stSelectbox label, .stTextArea label, .stDateInput label {
        color: var(--muted) !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 700;
      }

      div[data-testid="stForm"] button[type="submit"] {
        background: var(--lime) !important;
        color: #0a0a0a !important;
        font-weight: 800 !important;
        border-radius: 10px !important;
        padding: 0.5rem 1.5rem !important;
        border: none !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="header-wrap">
      <img class="header-logo" src="{LOGO_URL}" alt="MaLuê">
      <div class="header-title">AGENDA <span class="admin-badge">ADMIN</span></div>
      <div class="header-sub">Música com energia · 2026</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not WEBHOOK_URL:
    st.warning(
        "⚠️ Edição desabilitada — webhook não configurado."
    )

MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


@st.cache_data(ttl=30)
def carregar_agenda() -> pd.DataFrame:
    r = requests.get(CSV_URL, timeout=10)
    r.raise_for_status()
    r.encoding = "utf-8"
    df = pd.read_csv(io.BytesIO(r.content), dtype=str, encoding="utf-8").fillna("")
    df.columns = [c.strip() for c in df.columns]
    df["_data_dt"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    df = df.dropna(subset=["_data_dt"])
    return df.sort_values("_data_dt").reset_index(drop=True)


try:
    df = carregar_agenda()
except Exception as e:
    st.error("Não consegui carregar a agenda.")
    st.caption(f"Detalhe técnico: {e}")
    st.stop()

filtro = st.radio(
    "Filtro",
    ["Próximos", "Este mês", "Todos"],
    horizontal=True,
    label_visibility="collapsed",
)

hoje = pd.Timestamp(date.today())
if filtro == "Próximos":
    df_view = df[df["_data_dt"] >= hoje]
elif filtro == "Este mês":
    df_view = df[
        (df["_data_dt"] >= hoje)
        & (df["_data_dt"].dt.month == hoje.month)
        & (df["_data_dt"].dt.year == hoje.year)
    ]
else:
    df_view = df

if df_view.empty:
    st.markdown(
        "<div style='text-align:center;color:#666;padding:2rem;'>"
        "Nenhum show.</div>",
        unsafe_allow_html=True,
    )
    st.stop()


def status_pill(status: str) -> str:
    if not status:
        return ""
    s = status.lower()
    classe = "status-confirmado"
    if "realizado" in s: classe = "status-realizado"
    elif "pago" in s: classe = "status-pago"
    elif "contrato" in s: classe = "status-contrato"
    elif "cancela" in s: classe = "status-cancelado"
    elif "folga" in s: classe = "status-folga"
    return f"<span class='status-pill {classe}'>{status}</span>"


STATUS_OPCOES = ["", "Confirmado", "Contrato assinado", "Realizado", "Pago", "Cancelado", "Folga"]
TRAJE_OPCOES = ["", "Social", "Polo", "Casual", "Tema da festa"]
TIPO_OPCOES = ["", "Show", "Casamento", "Aniversário", "Corporativo", "Formatura", "Privado", "Carnaval"]


def salvar_no_sheet(row_index: int, updates: dict) -> tuple[bool, str]:
    if not WEBHOOK_URL:
        return False, "Webhook não configurado."
    try:
        payload = {"row": row_index + 2, "updates": updates}
        r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        return True, r.text
    except Exception as e:
        return False, str(e)


def excluir_do_sheet(row_index: int) -> tuple[bool, str]:
    if not WEBHOOK_URL:
        return False, "Webhook não configurado."
    try:
        payload = {"delete": True, "row": row_index + 2}
        r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        return True, r.text
    except Exception as e:
        return False, str(e)


for idx, row in df_view.iterrows():
    d = row["_data_dt"]
    dia_num = d.day
    mes = MESES_PT[d.month - 1]
    dia_sem = row.get("Dia", "") or d.strftime("%A").capitalize()
    horario = row.get("Horário Show", "")
    local = row.get("Local", "") or "—"
    cidade = row.get("Cidade", "")
    valor = row.get("Valor", "")
    status_html = status_pill(row.get("Status", ""))

    cidade_str = f" · {cidade}" if cidade and cidade.lower() not in local.lower() else ""
    horario_str = f" · {horario}" if horario else ""
    valor_html = f"<div class='show-valor'>💰 {valor}</div>" if valor else ""

    st.markdown(
        f"""
        <div class="show-card">
          <div class="date-block">
            <span class="date-day">{dia_num:02d}</span>
            <span class="date-month">{mes}</span>
          </div>
          <div class="show-info">
            <div class="show-title">{local}</div>
            <div class="show-meta">{dia_sem}{cidade_str}{horario_str} {status_html}</div>
            {valor_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("✏️ Editar este show"):
        with st.form(f"form_{idx}"):
            col1, col2 = st.columns(2)
            with col1:
                data_in = st.date_input(
                    "Data do evento",
                    value=d.date(),
                    format="DD/MM/YYYY",
                    key=f"d_{idx}",
                )
                horario_in = st.text_input(
                    "Horário do show", value=row.get("Horário Show", ""), key=f"h_{idx}"
                )
                local_in = st.text_input(
                    "Local", value=row.get("Local", ""), key=f"l_{idx}"
                )
                cidade_in = st.text_input(
                    "Cidade", value=row.get("Cidade", ""), key=f"c_{idx}"
                )
                contratante_in = st.text_input(
                    "Contratante", value=row.get("Contratante", ""), key=f"co_{idx}"
                )
                valor_in = st.text_input(
                    "Valor (R$)", value=row.get("Valor", ""), key=f"v_{idx}"
                )
            with col2:
                passagem_in = st.text_input(
                    "Passagem de som",
                    value=row.get("Passagem de Som", ""),
                    key=f"p_{idx}",
                    placeholder="ex.: 18h",
                )
                traje_atual = row.get("Traje", "")
                traje_in = st.selectbox(
                    "Traje",
                    options=TRAJE_OPCOES,
                    index=TRAJE_OPCOES.index(traje_atual) if traje_atual in TRAJE_OPCOES else 0,
                    key=f"t_{idx}",
                )
                empresa_in = st.text_input(
                    "Empresa de som",
                    value=row.get("Empresa de Som", ""),
                    key=f"e_{idx}",
                )
                tipo_atual = row.get("Tipo Evento", "")
                tipo_in = st.selectbox(
                    "Tipo de evento",
                    options=TIPO_OPCOES,
                    index=TIPO_OPCOES.index(tipo_atual) if tipo_atual in TIPO_OPCOES else 0,
                    key=f"ti_{idx}",
                )
                status_atual = row.get("Status", "")
                status_in = st.selectbox(
                    "Status",
                    options=STATUS_OPCOES,
                    index=STATUS_OPCOES.index(status_atual) if status_atual in STATUS_OPCOES else 0,
                    key=f"s_{idx}",
                )

            obs_in = st.text_area(
                "Observações",
                value=row.get("Observações", ""),
                key=f"o_{idx}",
                height=70,
            )

            submitted = st.form_submit_button("💾 Salvar alterações")
            if submitted:
                dia_calculado = dia_semana_pt(data_in)
                updates = {
                    "Data": data_in.strftime("%d/%m/%Y"),
                    "Dia": dia_calculado,
                    "Horário Show": horario_in,
                    "Passagem de Som": passagem_in,
                    "Local": local_in,
                    "Cidade": cidade_in,
                    "Contratante": contratante_in,
                    "Tipo Evento": tipo_in,
                    "Traje": traje_in,
                    "Empresa de Som": empresa_in,
                    "Valor": valor_in,
                    "Status": status_in,
                    "Observações": obs_in,
                }
                ok, msg = salvar_no_sheet(idx, updates)
                if ok:
                    st.success("✅ Salvo!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar: {msg}")

        # Excluir (fora do form, duas etapas)
        confirm_key = f"confirm_del_{idx}"
        st.markdown("<hr style='border-color:#2a2a2a;margin:0.6rem 0;'>", unsafe_allow_html=True)
        if st.session_state.get(confirm_key):
            st.warning(
                f"⚠️ Tem certeza que quer excluir '{local}' "
                f"({d.strftime('%d/%m/%Y')})? Essa ação é definitiva."
            )
            col_ok, col_cancel = st.columns(2)
            with col_ok:
                if st.button("Sim, excluir", key=f"do_del_{idx}", type="primary"):
                    ok_del, msg_del = excluir_do_sheet(idx)
                    if ok_del:
                        st.session_state[confirm_key] = False
                        st.success("✅ Show excluído.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Erro ao excluir: {msg_del}")
            with col_cancel:
                if st.button("Cancelar", key=f"cancel_del_{idx}"):
                    st.session_state[confirm_key] = False
                    st.rerun()
        else:
            if st.button("🗑️ Excluir este show", key=f"trigger_del_{idx}"):
                st.session_state[confirm_key] = True
                st.rerun()
