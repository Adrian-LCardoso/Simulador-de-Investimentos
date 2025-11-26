# db_manager.py
import streamlit as st
import psycopg2
from bcrypt import hashpw, checkpw, gensalt 
from datetime import datetime

# --- 1. Conexão Segura ---

def get_db_connection():
    """Conecta ao PostgreSQL usando credenciais SEGURAS do Streamlit Secrets."""
    # st.secrets['postgres'] carrega o bloco INI que você configurou
    DB_SECRETS = st.secrets['postgres'] 
    
    try:
        conn = psycopg2.connect(
            host=DB_SECRETS['host'],
            database=DB_SECRETS['database'],
            user=DB_SECRETS['user'],
            password=DB_SECRETS['password'],
            port=DB_SECRETS['port']
        )
        return conn
    except Exception as e:
        # st.error(f"Erro ao conectar com o Banco de Dados.") 
        return None

# --- 2. Funções de Autenticação ---

def register_user(email, password):
    """Insere um novo usuário na tabela 'users' com senha criptografada."""
    conn = get_db_connection()
    if not conn: return False, "Erro de conexão com o DB."
    
    # 1. Criptografar a Senha (Obrigatório para segurança!)
    hashed_password = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')
    
    try:
        with conn.cursor() as cur:
            # Insere com 5 simulações e status não-premium por padrão
            cur.execute("""
                INSERT INTO users (email, password_hash)
                VALUES (%s, %s);
            """, (email, hashed_password))
        
        conn.commit()
        return True, "Cadastro realizado com sucesso! 🎉"
        
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False, "O e-mail já está cadastrado."
    except Exception as e:
        conn.rollback()
        return False, f"Erro inesperado no cadastro."
    finally:
        conn.close()

def login_user(email, password):
    """Verifica as credenciais do usuário."""
    conn = get_db_connection()
    if not conn: return False, "Erro de conexão com o DB."

    try:
        with conn.cursor() as cur:
            # 1. Busca a senha criptografada
            cur.execute("SELECT password_hash FROM users WHERE email = %s", (email,))
            result = cur.fetchone()

            if result:
                stored_hash = result[0].encode('utf-8')
                # 2. Compara a senha (Segurança!)
                if checkpw(password.encode('utf-8'), stored_hash):
                    return True, "Login bem-sucedido!"
                
            return False, "Credenciais inválidas."
                
    except Exception as e:
        return False, f"Erro no login."
    finally:
        conn.close()

# --- 3. Funções de Monetização (Paywall) ---

def get_simulacoes_restantes(email):
    """Busca o limite de uso e o status premium do usuário."""
    conn = get_db_connection()
    if not conn: return 0, False # Default para erro
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT simulacoes_restantes, is_premium FROM users WHERE email = %s", (email,))
            result = cur.fetchone()
            if result:
                return result[0], result[1] # Retorna (limite, is_premium)
            return 0, False
    except Exception as e:
        return 0, False
    finally:
        conn.close()

def decrement_simulacoes(email):
    """Diminui o contador de simulações restantes em 1."""
    conn = get_db_connection()
    if not conn: return False
    
    try:
        with conn.cursor() as cur:
            # Diminui o contador, garantindo que não fique negativo
            cur.execute("""
                UPDATE users
                SET simulacoes_restantes = GREATEST(simulacoes_restantes - 1, 0)
                WHERE email = %s AND is_premium = FALSE;
            """, (email,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()
