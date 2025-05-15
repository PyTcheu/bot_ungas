import streamlit as st
import base64
import hashlib
import csv
from datetime import datetime, timedelta
import os
import json

st.set_page_config(layout="wide")

from streamlit_autorefresh import st_autorefresh
from streamlit_cookies_manager import EncryptedCookieManager

cookies = EncryptedCookieManager(
    prefix="raidmanager/",
    password="algumasecretkey"
)
if not cookies.ready():
    st.stop()

# --- Configurações dos arquivos CSV ---
USERS_CSV = "users.csv"
RAIDS_CSV = "raids.csv"


# Restaurar login do cookie (apenas uma vez)
if "usuario_logado" not in st.session_state:
    usuario_cookie = cookies.get("usuario")
    if usuario_cookie:
        usuario_data = json.loads(usuario_cookie)
        usuario = usuario_data["value"]
        st.session_state.usuario_logado = usuario
    else:
        st.session_state.usuario_logado = ""

# ⛔ MOVER o st_autorefresh para depois da checagem de login
if st.session_state.usuario_logado:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=15000, limit=None, key="refresh")

def load_raids():
    raids = []
    if os.path.exists(RAIDS_CSV):
        with open(RAIDS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Converter campos que precisam
                raid = {
                    "tipo": row["tipo"],
                    "nome": row["nome"],
                    "datahora": datetime.fromisoformat(row["datahora"]),
                    "dificuldade": row["dificuldade"],
                    "desafios": row["desafios"],
                    "titulares": row["titulares"].split(";") if row["titulares"] else [],
                    "reservas": row["reservas"].split(";") if row["reservas"] else [],
                    "criador": row["criador"]
                }
                raids.append(raid)
    return raids

def load_users():
    users = {}
    if os.path.exists(USERS_CSV):
        with open(USERS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                users[row["nome"]] = row["senha"]
    return users
# --- Inicialização do estado da aplicação ---

if "users" not in st.session_state:
    st.session_state.users = load_users()

if "usuario_logado" not in st.session_state:
    user_cookie = cookies.get("usuario")
    if user_cookie:
        st.session_state.usuario_logado = user_cookie

if "mostrar_confirmacao" not in st.session_state:
    st.session_state.mostrar_confirmacao = False

if "raid_a_cancelar" not in st.session_state:
    st.session_state.raid_a_cancelar = None

# --- Cores para os cards ---
raids = load_raids()
agora = datetime.now()
ativas = []
concluidas = []
# --- Funções auxiliares ---

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def save_users(users):
    with open(USERS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["nome", "senha"])
        writer.writeheader()
        for nome, senha in users.items():
            writer.writerow({"nome": nome, "senha": senha})

def save_raids(raids):
    with open(RAIDS_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["tipo", "nome", "datahora", "dificuldade", "desafios", "titulares", "reservas", "criador"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for raid in raids:
            writer.writerow({
                "tipo": raid["tipo"],
                "nome": raid["nome"],
                "datahora": raid["datahora"].isoformat(),
                "dificuldade": raid["dificuldade"],
                "desafios": raid["desafios"],
                "titulares": ";".join(raid["titulares"]),
                "reservas": ";".join(raid["reservas"]),
                "criador": raid["criador"]
            })

def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_background_image_local(image_path):
    bin_str = get_base64_of_bin_file(image_path)
    return f"url('data:image/jpeg;base64,{bin_str}')"


# --- Login e Cadastro ---

with st.sidebar:
    st.markdown("### 👤 Login / Cadastro")
    
    if st.session_state.usuario_logado:
        st.info(f"Você está logado como: **{st.session_state.usuario_logado}**")
        if st.button("Logout"):
            st.session_state.usuario_logado = ""
            st.rerun()
    else:
        usuario = st.text_input("Usuário", value="")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            if usuario.strip() == "" or senha.strip() == "":
                st.warning("Preencha usuário e senha.")
            elif usuario not in st.session_state.users:
                st.error("Usuário não cadastrado.")
            elif st.session_state.users[usuario] != hash_password(senha):
                st.error("Senha incorreta.")
            else:
                st.session_state.usuario_logado = usuario
                cookies["usuario"] = json.dumps({
                    "value": usuario,
                    "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
                })
                st.success(f"Bem-vindo, {usuario}!")
                st.rerun()

        if st.button("Cadastrar"):
            if usuario.strip() == "" or senha.strip() == "":
                st.warning("Preencha usuário e senha para cadastro.")
            elif usuario in st.session_state.users:
                st.error("Usuário já existe.")
            else:
                st.session_state.users[usuario] = hash_password(senha)
                save_users(st.session_state.users)
                st.success("Usuário cadastrado com sucesso! Faça login.")
                st.rerun()

# --- Função para salvar e atualizar raids após qualquer modificação ---
def salvar_e_atualizar():
    save_raids(raids)

# Lista de tipos de raid disponíveis
tipos_de_raid = [
    "Limiar da Salvação",
    "Cripta da Pedra Profunda",
    "Câmara de Cristal",
    "Jardim da Salvação",
    "A Queda do Rei",
    "Raiz dos Pesadelos",
    "Voto do Discípulo",
    "O Fim de Crota",
    "Último Desejo"
]

st.title("🧭 Raid Manager - Destiny")

# --- Formulário para criar uma nova raid ---
with st.expander("➕ Criar nova Raid"):
    tipo_raid = st.selectbox("Raid", tipos_de_raid)
    nome = st.text_input("Nome da Raid")
    datahora = st.date_input("Data da Raid")
    hora = st.time_input("Hora da Raid")
    dificuldade = st.selectbox("Dificuldade", ["Normal", "Mestre"])
    desafios = st.text_area("Desafios e Triunfos (um por linha)")

    if st.button("Criar Raid"):
        if not nome.strip():
            st.warning("Informe um nome válido para a raid.")
        else:
            # Verificar se já existe raid com o mesmo nome
            nomes_existentes = [r["nome"].lower() for r in raids]
            if nome.strip().lower() in nomes_existentes:
                st.error("Já existe uma raid com esse nome. Escolha outro nome.")
            else:
                raid = {
                    "tipo": tipo_raid,
                    "nome": nome.strip(),
                    "datahora": datetime.combine(datahora, hora),
                    "dificuldade": dificuldade,
                    "desafios": desafios.strip(),
                    "titulares": [],
                    "reservas": [],
                    "criador": st.session_state.get("usuario_logado", "")
                }
                save_raids([raid])
                st.success(f"Raid '{nome}' criada com sucesso!")
                st.rerun()
                



for raid in raids:
    if raid["datahora"] + timedelta(hours=1) < agora:
        concluidas.append(raid)
    else:
        ativas.append(raid)

# Ordenar por data
ativas.sort(key=lambda r: r["datahora"])
concluidas.sort(key=lambda r: r["datahora"], reverse=True)

def exibir_raids(raids_lista):
    n_cols = 3
    for i in range(0, len(raids_lista), n_cols):
        row_raids = raids_lista[i:i + n_cols]
        cols = st.columns(n_cols)
        for idx, (raid, col) in enumerate(zip(row_raids, cols)):
            desafios_html = raid['desafios'].replace('\n', '<br>')

            bg_image_base64 = set_background_image_local("images/raid_cripta.jpg")
            with col:
                st.markdown(
                    f"""
                    <div style="position: relative; width: 100%; height: 500px; border-radius: 10px; overflow: hidden; box-shadow: 2px 2px 5px #ccc;">
                        <div style="
                            background-image: {bg_image_base64};
                            background-size: cover;
                            background-position: center;
                            filter: brightness(0.3);
                            position: absolute;
                            inset: 0;
                            z-index: 0;
                        "></div>
                        <div style="position: relative; z-index: 1; color: white; padding: 20px; height: 100%; overflow-y: auto;">
                            <h5 style="margin-bottom: 0.2rem; font-style: italic;">{raid['tipo']} - {raid['nome']}</h5>
                            <p><b>Data e Hora:</b> {raid['datahora'].strftime('%d/%m/%Y %H:%M')}</p>
                            <p><b>Dificuldade:</b> {raid['dificuldade']}</p>
                            <p><b>Desafios/Triunfos:</b><br>{desafios_html}</p>
                            <p><b>Titulares:</b></p>
                            <ul>
                                {''.join(f'<li>{nome}</li>' for nome in raid['titulares']) or '<li>Vazio</li>'}
                            </ul>
                            <p><b>Reservas:</b></p>
                            <ul>
                                {''.join(f'<li>{nome}</li>' for nome in raid['reservas']) or '<li>Vazio</li>'}
                            </ul>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if raid in ativas:
                    with st.form(f"form_{raid['nome']}"):
                        nome_participante = st.session_state.get("usuario_logado", "").strip()
                        col1, col2= st.columns([1, 1])
                    
                        with col1:
                            if nome_participante == "":
                                st.warning("Você precisa fazer login na barra lateral para participar.")
                                if nome_participante in raid["titulares"]:
                                    if st.form_submit_button("Sair como titular"):
                                        raid["titulares"].remove(nome_participante)
                                        st.success("Você saiu da raid.")
                                        st.rerun()
                                elif nome_participante in raid["reservas"]:
                                    if st.form_submit_button("Sair como reserva"):
                                        raid["reservas"].remove(nome_participante)
                                        st.success("Você saiu da raid.")
                                        st.rerun()
                            else:
                                if nome_participante in raid["titulares"] or nome_participante in raid["reservas"]:
                                    st.markdown(
                                        """
                                        <style>
                                        .inscrito-btn {
                                            background-color: #4CAF50;
                                            border: none;
                                            color: white;
                                            padding: 8px 16px;
                                            text-align: center;
                                            text-decoration: none;
                                            display: inline-block;
                                            font-size: 16px;
                                            border-radius: 5px;
                                            cursor: default;
                                            user-select: none;
                                        }
                                        </style>
                                        <button class="inscrito-btn">&#10003; Inscrito</button>
                                        """,
                                        unsafe_allow_html=True
                                    )
                                else:
                                    if st.form_submit_button("Participar"):
                                        if len(raid["titulares"]) < 6:
                                            raid["titulares"].append(nome_participante)
                                            st.success("Inscrito como titular!")
                                            save_raids([raid])
                                            st.rerun()
                                        elif len(raid["reservas"]) < 3:
                                            raid["reservas"].append(nome_participante)
                                            st.success("Inscrito como reserva!")
                                            save_raids([raid])
                                            st.rerun()
                                        else:
                                            st.error("A raid está cheia.")
                        with col2:
                            usuario = st.session_state.get("usuario_logado")
                            criador = raid.get("criador")

                            if usuario == criador:
                                # Botão cancelar raid (para o criador)
                                if st.form_submit_button("❌ Cancelar Raid", type="primary"):
                                    st.session_state.raid_a_cancelar = raid
                                    st.session_state.mostrar_confirmacao = True
                                    st.rerun()
                            else:
                                # Botão sair da raid (para participantes que não são criadores)
                                if usuario in raid["titulares"]:
                                    if st.form_submit_button("🚪 Sair como Titular", type="secondary"):
                                        raid["titulares"].remove(usuario)
                                        st.success("Você saiu como titular da raid.")
                                        save_raids(raids)
                                        st.rerun()
                                elif usuario in raid["reservas"]:
                                    if st.form_submit_button("🚪 Sair como Reserva", type="secondary"):
                                        raid["reservas"].remove(usuario)
                                        st.success("Você saiu como reserva da raid.")
                                        save_raids(raids)
                                        st.rerun()
                                        
                # Mostrar confirmação inline se essa raid é a que está para cancelar
                if st.session_state.mostrar_confirmacao and st.session_state.raid_a_cancelar == raid:
                    st.warning(f"Tem certeza que deseja cancelar a raid '{raid['nome']}'?")
                    col_confirmar, col_cancelar = st.columns(2)
                    with col_confirmar:
                        if st.button("Sim, cancelar agora"):
                            raids.remove(raid)
                            st.session_state.raid_a_cancelar = None
                            st.session_state.mostrar_confirmacao = False
                            st.success("Raid cancelada com sucesso.")
                            save_raids(raids)
                            st.rerun()
                    with col_cancelar:
                        if st.button("Não, manter raid"):
                            st.session_state.raid_a_cancelar = None
                            st.session_state.mostrar_confirmacao = False
                            st.info("Cancelamento abortado.")
                            st.rerun()

st.subheader("🟢 Raids Ativas")
if not ativas:
    st.info("Nenhuma raid ativa no momento.")
else:
    exibir_raids(ativas)

st.subheader("⚫ Raids Concluídas")
if not concluidas:
    st.info("Nenhuma raid concluída ainda.")
else:
    exibir_raids(concluidas)
