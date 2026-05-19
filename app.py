"""Agenda MaLuê — ADMIN.

Versão completa pra Luene: vê valores, edita campos da equipe e salva
direto na planilha via Google Apps Script webhook.
"""
from __future__ import annotations

import io
import json
from datetime import date, datetime

DIAS_SEMANA_PT = [
    "Segunda", "Terça", "Quarta", "Quinta",
    "Sexta", "Sábado", "Domingo",
]


def dia_semana_pt(d: date) -> str:
    return DIAS_SEMANA_PT[d.weekday()]

import pandas as pd
import requests
import streamlit as st

# ============================================================
# Config
# ============================================================
SHEET_ID = "13ibY4_88N7pTK2lrLkNcudGeVyh78Kry6Y60Ijp0JD4"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
LOGO_URL = "https://raw.githubusercontent.com/malueoficial/malue-contratos/main/malue_icon.png"
ICON_URL = "https://raw.githubusercontent.com/malueoficial/malue-contratos/main/ml_agenda_icon.png"
# Materiais fixos que vão junto com todo contrato — hospedados no repo do gerador
CAMARIM_URL = "https://raw.githubusercontent.com/malueoficial/malue-contratos/main/camarim_malue_2026.pdf"
RIDER_URL = "https://raw.githubusercontent.com/malueoficial/malue-contratos/main/rider_malue_2026.pdf"
# Encurtador central — URLs curtas e rastreáveis pra mandar pra clientes via WhatsApp
MALUE_SHOWS_BASE = "https://malue-shows.streamlit.app"

WEBHOOK_URL = ""
try:
    WEBHOOK_URL = st.secrets.get("WEBHOOK_URL", "")
except Exception:
    WEBHOOK_URL = ""

st.set_page_config(
    page_title="Agenda MaLuê — Admin",
    page_icon=ICON_URL,
    layout="centered",
)

# Injeta apple-touch-icon no head do TOP document pra o iPhone usar o
# ícone certo quando adicionar à tela inicial. Streamlit roda dentro de
# iframes, então precisamos alcançar top.document (a página externa).
import streamlit.components.v1 as _components
_components.html(
    f"""
    <script>
      const ICON = '{ICON_URL}';
      function injetar() {{
        try {{
          // Alcança o topo (página fora dos iframes do Streamlit)
          const doc = (window.top && window.top.document) || document;
          // Remove os ícones padrão do Streamlit
          doc.querySelectorAll('link[rel*="apple-touch-icon"], link[rel="icon"], link[rel="shortcut icon"], link[rel="mask-icon"]').forEach(l => l.remove());
          // Adiciona o nosso em vários tamanhos
          const tamanhos = ['180x180', '152x152', '144x144', '120x120', null];
          for (const t of tamanhos) {{
            const link = doc.createElement('link');
            link.rel = 'apple-touch-icon';
            link.href = ICON;
            if (t) link.setAttribute('sizes', t);
            doc.head.appendChild(link);
          }}
          const fav = doc.createElement('link');
          fav.rel = 'icon';
          fav.href = ICON;
          doc.head.appendChild(fav);
          // Atualiza o título da página (web app)
          const title = doc.createElement('meta');
          title.setAttribute('name', 'apple-mobile-web-app-title');
          title.setAttribute('content', 'Agenda MaLuê');
          doc.head.appendChild(title);
        }} catch(e) {{ console.error('icon inject err:', e); }}
      }}
      injetar();
      // Re-inject quando Streamlit re-renderizar
      setTimeout(injetar, 500);
      setTimeout(injetar, 2000);
      setTimeout(injetar, 5000);
    </script>
    """,
    height=0,
)

# ============================================================
# Brand CSS
# ============================================================
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

      /* Filter tabs */
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

      /* Card */
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
      .show-meta-2 { color: var(--muted); font-size: 0.8rem; margin-top: 0.15rem; opacity: 0.85; }
      .show-valor {
        color: var(--lime);
        font-weight: 700;
        font-size: 0.95rem;
        margin-top: 0.3rem;
      }
      .show-time-badge {
        background: rgba(200, 240, 50, 0.18);
        color: var(--lime);
        padding: 0.2rem 0.55rem;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 800;
        margin-left: 0.4rem;
        white-space: nowrap;
      }
      .show-contrato {
        margin-top: 0.5rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
      }
      .show-contrato a {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: rgba(200, 240, 50, 0.12);
        color: var(--lime) !important;
        padding: 0.3rem 0.7rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        text-decoration: none;
        border: 1px solid rgba(200, 240, 50, 0.35);
        transition: background 0.15s;
        white-space: nowrap;
      }
      .show-contrato a:hover {
        background: rgba(200, 240, 50, 0.22);
        border-color: var(--lime);
      }

      /* Status pills */
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

      /* Form inputs no expander */
      .stTextInput input, .stSelectbox > div > div, .stTextArea textarea {
        background: #0d0d0d !important;
        color: var(--text) !important;
        border-color: #2a2a2a !important;
      }
      .stTextInput label, .stSelectbox label, .stTextArea label {
        color: var(--muted) !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 700;
      }

      /* Save button */
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

# ============================================================
# Header
# ============================================================
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
        "⚠️ Edição desabilitada — webhook não configurado. "
        "Veja INSTRUCOES_WEBHOOK.md no repo pra configurar."
    )

# ============================================================
# Load data
# ============================================================
MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


@st.cache_data(ttl=30)
def carregar_agenda() -> pd.DataFrame:
    r = requests.get(CSV_URL, timeout=10)
    r.raise_for_status()
    r.encoding = "utf-8"
    df = pd.read_csv(io.BytesIO(r.content), dtype=str, encoding="utf-8").fillna("")
    df.columns = [c.strip() for c in df.columns]
    # _sheet_row guarda a linha real na planilha (antes do sort)
    # header = linha 1, primeira linha de dados = linha 2
    df["_sheet_row"] = df.index + 2
    df["_data_dt"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
    df = df.dropna(subset=["_data_dt"])
    return df.sort_values("_data_dt").reset_index(drop=True)


try:
    df = carregar_agenda()
except Exception as e:
    st.error("Não consegui carregar a agenda.")
    st.caption(f"Detalhe técnico: {e}")
    st.stop()

# ============================================================
# Adicionar show sem contrato
# ============================================================
STATUS_OPCOES_NEW = ["Confirmado", "Contrato assinado", "Realizado", "Pago", "Cancelado", "Folga", ""]
TRAJE_OPCOES_NEW = ["", "Social", "Polo", "Casual", "Tema da festa"]
TIPO_OPCOES_NEW = ["Show", "Casamento", "Aniversário", "Corporativo", "Formatura", "Privado", "Carnaval", ""]


def adicionar_a_agenda(linha: dict) -> tuple[bool, str, int | None]:
    """POST pro webhook com action append — adiciona linha nova na agenda."""
    if not WEBHOOK_URL:
        return False, "Webhook não configurado.", None
    try:
        r = requests.post(WEBHOOK_URL, json={"append": linha}, timeout=20)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}", None
        try:
            j = r.json()
        except Exception:
            return True, "ok (sem row)", None
        if not j.get("ok"):
            return False, j.get("error", "erro desconhecido"), None
        return True, "ok", j.get("row")
    except Exception as e:
        return False, str(e), None


with st.expander("➕ Adicionar show sem contrato"):
    st.caption(
        "Use isso quando o contrato vai vir do cliente — só pra reservar a data na agenda."
    )
    with st.form("form_novo_show"):
        col_a, col_b = st.columns(2)
        with col_a:
            nova_data = st.date_input(
                "Data do show",
                value=date.today(),
                format="DD/MM/YYYY",
                key="novo_data",
            )
            novo_horario = st.text_input(
                "Horário (ex: 21h)",
                key="novo_horario",
                placeholder="21h",
            )
            novo_local = st.text_input(
                "Local",
                key="novo_local",
                placeholder="Nome do espaço / evento",
            )
            nova_cidade = st.text_input(
                "Cidade",
                key="nova_cidade",
                placeholder="Goiânia",
            )
        with col_b:
            novo_contratante = st.text_input(
                "Contratante",
                key="novo_contratante",
                placeholder="Nome de quem contratou",
            )
            novo_tipo = st.selectbox(
                "Tipo de evento",
                TIPO_OPCOES_NEW,
                key="novo_tipo",
            )
            novo_valor = st.text_input(
                "Valor (ex: R$ 15.000,00)",
                key="novo_valor",
                placeholder="R$ 0,00",
            )
            novo_status = st.selectbox(
                "Status",
                STATUS_OPCOES_NEW,
                key="novo_status",
            )
        nova_obs = st.text_area(
            "Observações",
            key="nova_obs",
            placeholder="Contrato vem do cliente, etc.",
            height=70,
        )
        submitted_novo = st.form_submit_button("Adicionar à agenda", type="primary")

        if submitted_novo:
            erros = []
            if not nova_data:
                erros.append("Informe a data.")
            if not novo_local.strip():
                erros.append("Informe o local.")
            if erros:
                for e in erros:
                    st.error(e)
            else:
                linha = {
                    "Data": nova_data.strftime("%d/%m/%Y"),
                    "Dia": dia_semana_pt(nova_data),
                    "Horário Show": novo_horario.strip(),
                    "Local": novo_local.strip(),
                    "Cidade": nova_cidade.strip(),
                    "Contratante": novo_contratante.strip(),
                    "Tipo Evento": novo_tipo,
                    "Valor": novo_valor.strip(),
                    "Status": novo_status,
                    "Observações": nova_obs.strip(),
                }
                with st.spinner("Adicionando..."):
                    ok, msg, srow = adicionar_a_agenda(linha)
                if ok:
                    st.success(f"✅ Show adicionado à agenda (linha {srow}).")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Erro: {msg}")

# ============================================================
# Filtros
# ============================================================
MESES_NOMES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

filtro = st.radio(
    "Filtro",
    ["Próximos", "Esta semana", "Este mês", "Por mês", "Todos"],
    horizontal=True,
    label_visibility="collapsed",
)

hoje = pd.Timestamp(date.today())

if filtro == "Próximos":
    df_view = df[df["_data_dt"] >= hoje]
elif filtro == "Esta semana":
    # Semana: segunda → domingo da semana corrente
    inicio_sem = hoje - pd.Timedelta(days=hoje.weekday())
    fim_sem = inicio_sem + pd.Timedelta(days=6)
    df_view = df[(df["_data_dt"] >= inicio_sem) & (df["_data_dt"] <= fim_sem)]
elif filtro == "Este mês":
    df_view = df[
        (df["_data_dt"] >= hoje)
        & (df["_data_dt"].dt.month == hoje.month)
        & (df["_data_dt"].dt.year == hoje.year)
    ]
elif filtro == "Por mês":
    # Anos disponíveis na agenda + meses
    anos_disponiveis = sorted(df["_data_dt"].dt.year.dropna().unique().astype(int).tolist())
    if not anos_disponiveis:
        anos_disponiveis = [hoje.year]
    col_m, col_a = st.columns([2, 1])
    with col_m:
        mes_escolhido = st.selectbox(
            "Mês",
            options=list(range(1, 13)),
            format_func=lambda m: MESES_NOMES[m - 1],
            index=hoje.month - 1,
            key="filtro_mes",
        )
    with col_a:
        ano_escolhido = st.selectbox(
            "Ano",
            options=anos_disponiveis,
            index=anos_disponiveis.index(hoje.year) if hoje.year in anos_disponiveis else 0,
            key="filtro_ano",
        )
    df_view = df[
        (df["_data_dt"].dt.month == mes_escolhido)
        & (df["_data_dt"].dt.year == ano_escolhido)
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


# ============================================================
# Cards com edição
# ============================================================
STATUS_OPCOES = ["", "Confirmado", "Contrato assinado", "Realizado", "Pago", "Cancelado", "Folga"]
TRAJE_OPCOES = ["", "Social", "Polo", "Casual", "Tema da festa"]
TIPO_OPCOES = ["", "Show", "Casamento", "Aniversário", "Corporativo", "Formatura", "Privado", "Carnaval"]


def salvar_no_sheet(sheet_row: int, updates: dict) -> tuple[bool, str]:
    if not WEBHOOK_URL:
        return False, "Webhook não configurado."
    try:
        payload = {"row": int(sheet_row), "updates": updates}
        r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        return True, r.text
    except Exception as e:
        return False, str(e)


def excluir_do_sheet(sheet_row: int) -> tuple[bool, str]:
    if not WEBHOOK_URL:
        return False, "Webhook não configurado."
    try:
        payload = {"delete": True, "row": int(sheet_row)}
        r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        return True, r.text
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=120)
def contar_acessos(label: str, tipo: str = "") -> dict | None:
    """Consulta o endpoint /exec?action=count do Apps Script.

    Retorna {total, encaminhado, primeiro, ultimo} ou None se falhar.
    Cacheado por 2 minutos pra não bater toda hora.
    """
    if not WEBHOOK_URL or not label:
        return None
    try:
        params = {"action": "count", "label": label}
        if tipo:
            params["type"] = tipo
        r = requests.get(WEBHOOK_URL, params=params, timeout=10)
        if r.status_code != 200:
            return None
        j = r.json()
        if not j.get("ok"):
            return None
        return j
    except Exception:
        return None


def _data_iso(data_br: str) -> str:
    """Converte DD/MM/YYYY → YYYY-MM-DD (formato usado no label do tracker)."""
    parts = (data_br or "").split("/")
    if len(parts) != 3:
        return data_br
    d, m, y = parts
    return f"{y}-{m.zfill(2)}-{d.zfill(2)}"


for idx, row in df_view.iterrows():
    d = row["_data_dt"]
    dia_num = d.day
    mes = MESES_PT[d.month - 1]
    dia_sem = row.get("Dia", "") or d.strftime("%A").capitalize()
    horario = row.get("Horário Show", "")
    local = row.get("Local", "") or "—"
    cidade = row.get("Cidade", "")
    contratante = row.get("Contratante", "")
    tipo_evento = row.get("Tipo Evento", "")
    valor = row.get("Valor", "")
    status_html = status_pill(row.get("Status", ""))

    # Defensiva forte: tira qualquer tag HTML que possa ter sido salva por engano
    # em campos que entram direto no HTML do card (Local, Cidade, Contratante, Valor).
    # Também escapa &, <, > residuais e normaliza espaços/quebras de linha.
    import re as _re
    import html as _html
    def _safe(s):
        v = str(s or "")
        # Tira tags HTML completas
        v = _re.sub(r"<[^>]*>", "", v)
        # Normaliza qualquer whitespace (inclui \n, \t) em espaço simples
        v = _re.sub(r"\s+", " ", v).strip()
        # Escapa caracteres HTML residuais (&, <, > soltos)
        v = _html.escape(v, quote=False)
        return v
    local = _safe(local) or "—"
    cidade = _safe(cidade)
    contratante = _safe(contratante)
    valor = _safe(valor)
    horario = _safe(horario)

    horario_badge = f"<span class='show-time-badge'>🕐 {horario}</span>" if horario else ""
    valor_html = f"<div class='show-valor'>💰 {valor}</div>" if valor else ""

    # Linha 1 do meta: dia da semana · tipo de show · status
    parte1 = [p for p in [dia_sem, tipo_evento] if p]
    meta1 = " · ".join(parte1)
    if status_html:
        meta1 = (meta1 + " " if meta1 else "") + status_html

    # Linha 2 do meta: contratante · cidade (se cidade ≠ local)
    cidade_show = cidade if cidade and cidade.lower() not in local.lower() else ""
    parte2 = [p for p in [contratante, cidade_show] if p]
    meta2_html = (
        f"<div class='show-meta show-meta-2'>{' · '.join(parte2)}</div>"
        if parte2 else ""
    )

    contrato_url = (row.get("Contrato URL", "") or "").strip()
    contrato_html = (
        f"<div class='show-contrato'>"
        f"<a href='{contrato_url}' target='_blank' rel='noopener'>📄 Ver contrato</a>"
        f"</div>"
        if contrato_url
        else ""
    )

    # IMPORTANTE: HTML em uma única linha pra evitar que o parser de Markdown
    # do Streamlit trate as linhas indentadas como bloco de código (4+ espaços).
    card_html = (
        f'<div class="show-card">'
        f'<div class="date-block">'
        f'<span class="date-day">{dia_num:02d}</span>'
        f'<span class="date-month">{mes}</span>'
        f'</div>'
        f'<div class="show-info">'
        f'<div class="show-title">{local}{horario_badge}</div>'
        f'<div class="show-meta">{meta1}</div>'
        f'{meta2_html}{valor_html}{contrato_html}'
        f'</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    # ============================================================
    # Links curtos pra cliente (orçamento + contrato + rider + camarim)
    # ============================================================
    slug = (row.get("Slug", "") or "").strip()
    if slug:
        with st.expander("🔗 Links curtos pra cliente"):
            st.caption(
                "Links bonitos e rastreáveis pra mandar no WhatsApp. "
                "Cada clique do cliente é registrado nos acessos."
            )
            link_orc = f"{MALUE_SHOWS_BASE}/?o={slug}"
            link_c   = f"{MALUE_SHOWS_BASE}/?c={slug}"
            link_r   = f"{MALUE_SHOWS_BASE}/?r={slug}"
            link_cam = f"{MALUE_SHOWS_BASE}/?cam={slug}"
            st.markdown("**Orçamento:**")
            st.code(link_orc, language=None)
            if contrato_url:
                st.markdown("**Contrato:**")
                st.code(link_c, language=None)
            st.markdown("**Rider técnico:**")
            st.code(link_r, language=None)
            st.markdown("**Camarim:**")
            st.code(link_cam, language=None)
    elif contrato_url:
        st.caption(
            "💡 Esse show ainda não tem slug — depois do próximo `backfillSlugs` "
            "no Apps Script os links curtos vão aparecer aqui."
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
                    "Título do show",
                    value=row.get("Local", ""),
                    key=f"l_{idx}",
                    help="É o nome que aparece em destaque no card da agenda. Pode ser nome do cliente, da casa, ou da cidade.",
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
                    "Passagem de som (hora)",
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
                # Dia da semana é sempre calculado da data
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
                ok, msg = salvar_no_sheet(row.get("_sheet_row"), updates)
                if ok:
                    st.success("✅ Salvo!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Erro ao salvar: {msg}")

        # ============================================================
        # Acessos do contrato (só se tiver Contrato URL)
        # ============================================================
        if contrato_url:
            with st.expander("📊 Acessos do contrato"):
                contratante_label = row.get("Contratante", "")
                data_iso = _data_iso(row.get("Data", ""))
                label_contrato = f"{contratante_label} | {data_iso} (contrato)"
                acessos = contar_acessos(label_contrato, tipo="contrato")
                if acessos is None:
                    st.caption("⚠️ Não consegui consultar acessos agora.")
                else:
                    total = acessos.get("total", 0)
                    encaminhado = acessos.get("encaminhado", 0)
                    primeiro = acessos.get("primeiro")
                    ultimo = acessos.get("ultimo")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Aberto", f"{total} vezes")
                    with col_b:
                        st.metric("Encaminhado (estimado)", f"~{encaminhado} vezes")
                    if primeiro:
                        st.caption(f"📥 Primeiro acesso: **{primeiro}**")
                    if ultimo:
                        st.caption(f"🕐 Último acesso: **{ultimo}**")
                    if total == 0:
                        st.info(
                            "Ainda não foi aberto pelo cliente. "
                            "(Seus cliques pelo botão 'Ver contrato' acima não contam — "
                            "essa contagem é só do link enviado pelo WhatsApp.)"
                        )
                    elif encaminhado >= 2:
                        st.warning(
                            f"⚠️ O link foi aberto {total} vezes. Pode ter sido "
                            "encaminhado pra outras pessoas."
                        )

        # ============================================================
        # Excluir (fora do form, duas etapas)
        # ============================================================
        confirm_key = f"confirm_del_{idx}"
        st.markdown("<hr style='border-color:#2a2a2a;margin:0.6rem 0;'>", unsafe_allow_html=True)
        if st.session_state.get(confirm_key):
            st.warning(
                f"⚠️ Tem certeza que quer excluir o show '{local}' "
                f"({d.strftime('%d/%m/%Y')})? Essa ação é definitiva."
            )
            col_ok, col_cancel = st.columns(2)
            with col_ok:
                if st.button("Sim, excluir", key=f"do_del_{idx}", type="primary"):
                    ok_del, msg_del = excluir_do_sheet(row.get("_sheet_row"))
                    if ok_del:
                        st.session_state[confirm_key] = False
                        st.success("✅ Show excluído da agenda.")
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
