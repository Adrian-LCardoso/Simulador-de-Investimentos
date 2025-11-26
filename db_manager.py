import streamlit as st
import hashlib
import os

# NOTA: O hash da senha deve ser feito com um algoritmo lento como bcrypt
# (mas para evitar erros de dependência, mantemos o hashlib por enquanto).

# --- FUNÇÃO DE INICIALIZAÇÃO DE ESTADO (CRÍTICA) ---
def initialize_db():
    """Garante que o banco de dados em memória seja inicializado no Session State."""
    if 'in_memory_db' not in st.session_state:
        # Apenas inicializa SE a chave ainda não existir
        st.session_state['in_memory_db'] = {
            "teste@exemplo.com": {
                "password_hash": hash_password("123456"),
                "is_premium": False,
                "simulacoes_restantes": 5
            },
            "premium@exemplo.com": {
                "password_hash": hash_password("premium123"),
                "is_premium": True,
                "simulacoes_restantes": 99999
            }
        }
    
    # Inicializa o estado de autenticação, se não existir
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'user_email' not in st.session_state:
        st.session_state['user_email'] = None
    if 'simulacoes_restantes' not in st.session_state:
        st.session_state['simulacoes_restantes'] = 0
    if 'is_premium' not in st.session_state:
        st.session_state['is_premium'] = False

# --- FUNÇÕES AUXILIARES ---

def hash_password(password):
    """Cria o hash SHA256 da senha."""
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# 1. FUNÇÕES DE AUTENTICAÇÃO (100% SIMULADAS)
# ==========================================

def login_user(email, password):
    """Tenta autenticar o usuário usando o DB em memória (Session State)."""
    # Chamamos a inicialização para ter certeza que 'in_memory_db' existe
    # Isso pode ser feito no arquivo principal (Simulador_Investimentos.py) também,
    # mas mantemos aqui para segurança.
    initialize_db()
    
    hashed_password = hash_password(password)
    # Acessa o dicionário dentro do session_state
    user_data = st.session_state['in_memory_db'].get(email) 
    
    if user_data and user_data['password_hash'] == hashed_password:
        
        # Atualiza o estado de sessão do Streamlit após o login
        st.session_state['authenticated'] = True
        st.session_state['user_email'] = email
        st.session_state['is_premium'] = user_data['is_premium']
        st.session_state['simulacoes_restantes'] = user_data['simulacoes_restantes']
        
        return True, "Login bem-sucedido (Simulado)!"
    else:
        return False, "Email ou senha incorretos."

def register_user(email, password):
    """Tenta cadastrar um novo usuário usando o DB em memória (Session State)."""
    initialize_db() # Garante o DB
    
    # Verifica se o email já existe
    if email in st.session_state['in_memory_db']: 
        return False, "Este email já está cadastrado."
        
    hashed_password = hash_password(password)
    
    # Insere o novo usuário com limite inicial de 5 simulações
    st.session_state['in_memory_db'][email] = {
        'password_hash': hashed_password, 
        'is_premium': False, 
        'simulacoes_restantes': 5
    }
    
    return True, "Cadastro realizado com sucesso (Simulado)!"

# ==========================================
# 2. FUNÇÕES DE LIMITE E PAYWALL (100% SIMULADAS)
# ==========================================

def get_simulacoes_restantes(email):
    """Retorna o número de simulações restantes e o status Premium do DB em memória."""
    initialize_db()
    user_data = st.session_state['in_memory_db'].get(email) 
    
    if user_data:
        return user_data['simulacoes_restantes'], user_data['is_premium']
    else:
        # Retorna 0 e False se o usuário não for encontrado (segurança)
        return 0, False

def decrement_simulacoes(email):
    """Decrementa o contador de simulações do usuário no DB em memória."""
    initialize_db()
    
    if email in st.session_state['in_memory_db']: 
        user_data = st.session_state['in_memory_db'][email]
        
        # Só decrementa se não for premium e se tiver simulações restantes
        if not user_data['is_premium'] and user_data['simulacoes_restantes'] > 0:
            st.session_state['in_memory_db'][email]['simulacoes_restantes'] -= 1
            # Atualiza o contador no Session State principal do Streamlit
            st.session_state['simulacoes_restantes'] = st.session_state['in_memory_db'][email]['simulacoes_restantes']
            return True
        return user_data['is_premium'] # Retorna True se for premium (não precisa decrementar)
    return False

def logout_user():
    """Faz o logout, resetando o estado de autenticação."""
    st.session_state['authenticated'] = False
    st.session_state['user_email'] = None
    st.session_state['simulacoes_restantes'] = 0
    st.session_state['is_premium'] = False
