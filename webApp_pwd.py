import streamlit as st
import streamlit.components.v1 as components
import random
import time
import re
import os
from datetime import datetime

# ===============================
# Configurazione Pagina
# ===============================
st.set_page_config(page_title="🧠 Test Scuola Specializzazione Biologia", layout="centered")

# CSS per styling avanzato
st.markdown("""
    <style>
    .stRadio > label {font-size: 18px !important; padding: 10px; border-radius: 5px; width: 100%;}
    .question-text {font-size: 22px; font-weight: bold; margin-bottom: 20px; color: #1f2937;}
    .correct-answer {color: #155724; background-color: #d4edda; border: 1px solid #c3e6cb; padding: 10px; border-radius: 5px; margin: 10px 0;}
    .wrong-answer {color: #721c24; background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 10px; border-radius: 5px; margin: 10px 0;}
    .original-id {color: #007bff; font-family: monospace; font-size: 0.9em; margin-right: 8px;}
    .stats-box {background-color: #e1f5fe; border-left: 5px solid #0288d1; padding: 10px; margin: 10px 0; border-radius: 4px;}
    .auth-container {text-align: center; margin-top: 100px; padding: 40px; border: 1px solid #ddd; border-radius: 10px; background-color: #f9f9f9;}
    </style>
""", unsafe_allow_html=True)

# ===============================
# 0. Sistema di Autenticazione
# ===============================
def check_password():
    """Restituisce True se l'utente ha inserito la password corretta del giorno."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    # Calcolo password del giorno: cuc + DD + MM
    oggi = datetime.now()
    password_corretta = f"cuc{oggi.strftime('%d%m')}"

    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    st.title("🔐 Accesso Riservato")
    st.write("Inserisci la password giornaliera per utilizzare l'applicazione.")
    
    pwd_input = st.text_input("Password", type="password", placeholder="🖕")
    
    if st.button("Sblocca Applicazione"):
        if pwd_input == password_corretta:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Password errata. Riprova.")
    
    st.markdown("</div>", unsafe_allow_html=True)
    return False

# Blocca l'esecuzione se non autenticato
if not check_password():
    st.stop()

# ===============================
# 1. Parsing Logica
# ===============================
@st.cache_data
def carica_domande(contenuto_str):
    domande = []
    lines = contenuto_str.split('\n')
    curr_domanda = None
    
    regex_domanda_start = re.compile(r'^DOMANDA:\s*(\d+)\s*[:\.-]?\s*(.*)', re.IGNORECASE)
    regex_opzione = re.compile(r'^([A-Z])\)\s*(.*)')

    for line in lines:
        line = line.strip()
        if not line: continue
            
        match_domanda = regex_domanda_start.match(line)
        if match_domanda:
            if curr_domanda and curr_domanda['opzioni'] and curr_domanda['corretta']:
                domande.append(curr_domanda)
            
            curr_domanda = {
                "id_orig": match_domanda.group(1),
                "testo": match_domanda.group(2).strip(),
                "opzioni": [],
                "corretta": None
            }
        elif curr_domanda is not None:
            match_opzione = regex_opzione.match(line)
            if match_opzione:
                lettera = match_opzione.group(1)
                testo_opzione = line
                is_correct = False
                if line.endswith("*"):
                    is_correct = True
                    testo_opzione = line[:-1].strip()
                curr_domanda["opzioni"].append(testo_opzione)
                if is_correct: curr_domanda["corretta"] = lettera
            else:
                if not curr_domanda["opzioni"]:
                    curr_domanda["testo"] += " " + line

    if curr_domanda and curr_domanda['opzioni'] and curr_domanda['corretta']:
        domande.append(curr_domanda)
    return domande

# ===============================
# 2. Gestione Stato
# ===============================
if 'stato_quiz' not in st.session_state: st.session_state.stato_quiz = 'setup'
if 'domande_selezionate' not in st.session_state: st.session_state.domande_selezionate = []
if 'indice' not in st.session_state: st.session_state.indice = 0
if 'risposte_date' not in st.session_state: st.session_state.risposte_date = {}
if 'mostra_feedback' not in st.session_state: st.session_state.mostra_feedback = False

# ===============================
# 3. Setup
# ===============================
if st.session_state.stato_quiz == 'setup':
    st.title("📂 Configurazione Quiz")
    
    opzioni_sorgente = ["DATABASE 1.txt", "DATABASE 2.txt", "Tutti i DATABASE", "Carica file .txt"]
    scelta_file = st.radio("Sorgente:", opzioni_sorgente, horizontal=True)
    
    domande_totali = []
    
    if scelta_file == "Carica file .txt":
        uploaded_file = st.file_uploader("Carica TXT", type=["txt"])
        if uploaded_file:
            testo = uploaded_file.getvalue().decode("utf-8", errors='ignore')
            domande_totali = carica_domande(testo)
    elif scelta_file == "Tutti i DATABASE":
        files = [f for f in os.listdir('.') if f.upper().startswith("DATABASE") and f.lower().endswith(".txt")]
        for f_name in sorted(files):
            try:
                with open(f_name, "r", encoding="utf-8", errors="ignore") as f:
                    domande_totali.extend(carica_domande(f.read()))
            except: pass
        if not domande_totali: st.error("Nessun file DATABASE trovato.")
    else:
        if os.path.exists(scelta_file):
            with open(scelta_file, "r", encoding="utf-8", errors="ignore") as f:
                domande_totali = carica_domande(f.read())
        else: st.error(f"File '{scelta_file}' non trovato.")

    if domande_totali:
        n_max = len(domande_totali)
        st.markdown(f"<div class='stats-box'>🔍 Analisi: <b>{n_max}</b> domande totali caricate.</div>", unsafe_allow_html=True)
        
        usa_tutti = (scelta_file == "Tutti i DATABASE")
        
        if not usa_tutti:
            st.subheader("🎯 Filtra Range")
            col_r1, col_r2 = st.columns(2)
            start_r = col_r1.number_input("Da domanda n.", 1, n_max, 1)
            end_r = col_r2.number_input("A domanda n.", 1, n_max, n_max)
        else:
            st.info("ℹ️ Modalità 'Tutti i DATABASE': intervallo manuale disattivato.")
            start_r, end_r = 1, n_max
        
        st.subheader("⚙️ Modalità e Quantità")
        c1, c2, c3 = st.columns(3)
        modalita_allenamento = c1.toggle("🏋️ Allenamento", help="Mostra subito se la risposta è corretta")
        ordine_casuale = c2.toggle("🔀 Ordine Casuale", value=True)
        minuti = c3.number_input("⏱️ Minuti", 1, 600, 60)
        
        disp = max(0, int(end_r) - int(start_r) + 1)
        num_q = st.number_input(f"❓ Quante domande estrarre? (disponibili: {disp})", 1, disp, min(80, disp))

        if st.button("🚀 INIZIA TEST", type="primary", use_container_width=True):
            fetta = domande_totali[int(start_r)-1 : int(end_r)]
            if ordine_casuale:
                st.session_state.domande_selezionate = random.sample(fetta, min(num_q, len(fetta)))
            else:
                st.session_state.domande_selezionate = fetta[:num_q]
            
            st.session_state.allenamento = modalita_allenamento
            st.session_state.durata_secondi = minuti * 60
            st.session_state.start_time = time.time()
            st.session_state.indice = 0
            st.session_state.risposte_date = {}
            st.session_state.mostra_feedback = False
            st.session_state.stato_quiz = 'in_corso'
            st.rerun()

# ===============================
# 4. Quiz in Corso
# ===============================
elif st.session_state.stato_quiz == 'in_corso':
    elapsed = time.time() - st.session_state.start_time
    rimanente = int(st.session_state.durata_secondi - elapsed)
    
    if rimanente <= 0:
        st.session_state.stato_quiz = 'fine'
        st.rerun()

    timer_color = "#ef4444" if rimanente < 300 else "#3b82f6"
    components.html(f"""
        <div style="text-align:center; background:#f0f2f6; border:2px solid {timer_color}; border-radius:10px; padding:10px; font-family:sans-serif; font-size:24px; font-weight:bold;">
            ⏳ <span id="t">--:--</span>
        </div>
        <script>
            var s = {rimanente};
            setInterval(function(){{
                var m=Math.floor(s/60), sec=s%60;
                document.getElementById("t").innerText = (m<10?"0":"")+m+":"+(sec<10?"0":"")+sec;
                if(s>0) s--;
            }},1000);
        </script>
    """, height=80)

    with st.sidebar:
        st.write(f"Domanda **{st.session_state.indice + 1}** di {len(st.session_state.domande_selezionate)}")
        st.progress((st.session_state.indice + 1) / len(st.session_state.domande_selezionate))
        if st.button("Esci e Termina"): st.session_state.stato_quiz = 'fine'; st.rerun()

    dom = st.session_state.domande_selezionate[st.session_state.indice]
    st.markdown(f"<div class='question-text'><span class='original-id'>({dom['id_orig']})</span> {dom['testo']}</div>", unsafe_allow_html=True)
    
    user_prev = st.session_state.risposte_date.get(st.session_state.indice)
    idx_sel = next((i for i, o in enumerate(dom['opzioni']) if o.startswith(user_prev)), None) if user_prev else None
    
    disabilitato = st.session_state.allenamento and st.session_state.mostra_feedback
    scelta = st.radio("Opzioni:", dom['opzioni'], index=idx_sel, key=f"q_{st.session_state.indice}", 
                      label_visibility="collapsed", disabled=disabilitato)

    if st.session_state.allenamento and st.session_state.mostra_feedback:
        is_corretta = scelta[0] == dom['corretta']
        if is_corretta:
            st.markdown(f"<div class='correct-answer'>✅ Corretto! La risposta è {dom['corretta']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='wrong-answer'>❌ Errato. La risposta corretta è {dom['corretta']}</div>", unsafe_allow_html=True)

    c_back, c_action = st.columns([1, 4])
    
    with c_back:
        if st.session_state.indice > 0 and not st.session_state.mostra_feedback:
            if st.button("⬅️"): 
                st.session_state.indice -= 1
                st.rerun()

    with c_action:
        if st.session_state.allenamento and not st.session_state.mostra_feedback:
            if st.button("Verifica Risposta", type="primary", use_container_width=True):
                if scelta:
                    st.session_state.risposte_date[st.session_state.indice] = scelta[0]
                    st.session_state.mostra_feedback = True
                    st.rerun()
                else: st.warning("Seleziona una risposta")
        else:
            txt_next = "Prossima ➡️" if st.session_state.indice < len(st.session_state.domande_selezionate)-1 else "Concludi ✅"
            if st.button(txt_next, type="primary", use_container_width=True):
                if scelta:
                    st.session_state.risposte_date[st.session_state.indice] = scelta[0]
                    if st.session_state.indice < len(st.session_state.domande_selezionate) - 1:
                        st.session_state.indice += 1
                        st.session_state.mostra_feedback = False
                        st.rerun()
                    else:
                        st.session_state.stato_quiz = 'fine'
                        st.rerun()
                else: st.warning("Seleziona una risposta")

# ===============================
# 5. Risultati
# ===============================
elif st.session_state.stato_quiz == 'fine':
    st.title("📊 Risultati Finale")
    corrette = sum(1 for i, d in enumerate(st.session_state.domande_selezionate) if st.session_state.risposte_date.get(i,"") == d['corretta'])
    totale = len(st.session_state.domande_selezionate)
    perc = (corrette/totale)*100
    
    st.markdown(f"<div style='background: {'#d4edda' if perc >= 60 else '#f8d7da'}; padding:20px; border-radius:10px; text-align:center;'><h2>{corrette}/{totale} ({perc:.1f}%)</h2></div>", unsafe_allow_html=True)
    
    for i, dom in enumerate(st.session_state.domande_selezionate):
        u = st.session_state.risposte_date.get(i, "-")
        ok = (u == dom['corretta'])
        with st.expander(f"{'✅' if ok else '❌'} Domanda {dom['id_orig']}", expanded=not ok):
            st.write(dom['testo'])
            st.markdown(f"Tua: **{u}** | Corretta: **{dom['corretta']}**")
            for o in dom['opzioni']:
                st.write(f"**{o}** 👈" if o.startswith(dom['corretta']) else o)

    if st.button("Ricomincia"):
        # Reset stato mantenendo l'autenticazione
        st.session_state.stato_quiz = 'setup'
        st.session_state.domande_selezionate = []
        st.session_state.indice = 0
        st.session_state.risposte_date = {}
        st.session_state.mostra_feedback = False

        st.rerun()



