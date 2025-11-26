import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import db_manager 

# Iniciando o Banco de Dados
db_manager.initialize_db()

# Configuração da Página
st.set_page_config(
    page_title="Simulador de Investimentos",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 1. AUTENTICAÇÃO E LÓGICA DO PAYWALL
# ==========================================

def handle_login(email, password):
    """Lida com a tentativa de Login."""
    success, message = db_manager.login_user(email, password)
    if success:
        # A função login_user já atualiza st.session_state['logged_in'] etc.
        st.success(message)
        st.rerun() 
    else:
        st.error(message)

def handle_register(email, password):
    """Lida com a tentativa de Cadastro."""
    if not email or not password:
        st.error("Email e senha não podem ser vazios.")
        return

    success, message = db_manager.register_user(email, password)
    if success:
        st.success(message + " Fazendo login...")
        handle_login(email, password)
    else:
        st.error(message)

def render_login_page():
    """Renderiza a tela de Login e Cadastro."""
    
    # Sua introdução aqui, adaptada à sua experiência (Contabilidade/Ciência de Dados)
    st.title("Acesso ao Simulador de Investimentos 📊")
    st.subheader(f"Analise o valor líquido de seus investimentos com a precisão de um analista de FP&A.")
    st.markdown(
        "Cadastre-se para ter acesso a 5 simulações gratuitas por dia. Assine o plano Premium para acesso ilimitado. "
    )

    login_tab, register_tab = st.tabs(["🔒 Fazer Login", "✏️ Criar Conta"])

    with login_tab:
        with st.form("login_form"):
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Senha", type="password", key="login_password")
            submitted = st.form_submit_button("Entrar")
            if submitted:
                handle_login(login_email, login_password)

    with register_tab:
        with st.form("register_form"):
            reg_email = st.text_input("Email para Cadastro", key="reg_email")
            reg_password = st.text_input("Criar Senha", type="password", key="reg_password")
            confirm_password = st.text_input("Confirme a Senha", type="password", key="confirm_password")
            
            submitted = st.form_submit_button("Cadastrar")
            if submitted:
                if reg_password and reg_password == confirm_password:
                    handle_register(reg_email, reg_password)
                elif not reg_password:
                    st.error("A senha não pode ser vazia.")
                else:
                    st.error("As senhas não coincidem.")


# ==========================================
# 2. FUNÇÕES AUXILIARES E CÁLCULOS
# ==========================================

def parse_br_currency(text_input):
    """Converte string BR (ex: 1.000,00) para float."""
    try:
        cleaned_text = text_input.replace(".", "").replace(",", ".")
        return float(cleaned_text)
    except:
        return 0.0

def format_br(value):
    """Formata float para R$"""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calcular_poupanca(valor_inicial, dias):
    # Taxa da Poupança (TR + 0.5% a.a. ou 70% da Selic)
    # Aqui, usamos uma simplificação de 0.5% ao mês + TR ~ 6.17% a.a. para benchmark.
    taxa_anual = 0.0617
    fator_diario = (1 + taxa_anual)**(1 / 365.0)
    data = []
    montante = valor_inicial
    for d in range(0, dias + 1):
        if d > 0: montante *= fator_diario
        rendimento = montante - valor_inicial
        data.append((d, montante, rendimento))
    df_poupanca = pd.DataFrame(data, columns=["Dia", "Montante Líquido", "Rendimento Líquido"])
    montante_final = df_poupanca["Montante Líquido"].iloc[-1]
    rendimento_final = montante_final - valor_inicial
    return {
        "df": df_poupanca.rename(columns={"Montante Líquido": "Montante Líquido"}),
        "montante_liquido": montante_final,
        "rendimento_liquido": rendimento_final,
        "rendimento_bruto": rendimento_final,
        "ir_devido": 0.0,
        "aliquota": 0.0,
        "taxa_nominal_aa": 6.17
    }

def calcular_ativo_geral(valor_inicial, dias, tipo_rentabilidade, params, is_isento):
    """Calcula a rentabilidade bruta, IR e resultado líquido para diferentes tipos de ativos."""
    taxa_anual_nominal = 0.0
    
    if tipo_rentabilidade == "PRÉ":
        taxa_anual_nominal = params['taxa_fixa'] / 100.0
    elif tipo_rentabilidade == "PÓS":
        taxa_referencia = params['taxa_ref'] / 100.0
        percentual = params['percentual'] / 100.0
        taxa_anual_nominal = taxa_referencia * percentual
    elif tipo_rentabilidade == "IPCA":
        ipca = params['ipca_proj'] / 100.0
        juro_real = params['taxa_fixa'] / 100.0
        # Fórmula de Fisher para rentabilidade nominal (aproximada)
        taxa_anual_nominal = ((1 + ipca) * (1 + juro_real)) - 1
        
    fator_diario = (1 + taxa_anual_nominal)**(1 / 365.0)
    data = []
    montante = valor_inicial
    aliquota_ir_fixa = 0.0
    
    # Tabela Regressiva de IR (Válida para Renda Fixa Não Isenta)
    if not is_isento:
        if dias <= 180: aliquota_ir_fixa = 22.5
        elif dias <= 360: aliquota_ir_fixa = 20.0
        elif dias <= 720: aliquota_ir_fixa = 17.5
        else: aliquota_ir_fixa = 15.0

    for d in range(0, dias + 1):
        if d > 0: montante *= fator_diario
        rendimento_total = montante - valor_inicial
        
        # Simula o montante líquido apenas para exibição no gráfico de linha
        montante_liquido_simples = montante
        if not is_isento:
             # O cálculo líquido final é feito no final, mas aqui simulamos uma progressão
             ir_parcial = rendimento_total * (aliquota_ir_fixa/100.0)
             montante_liquido_simples = valor_inicial + (rendimento_total - ir_parcial)
        
        data.append((d, montante, rendimento_total, montante_liquido_simples))
        
    df = pd.DataFrame(data, columns=["Dia", "Montante Bruto", "Rendimento Bruto", "Montante Líquido"])
    
    # Cálculo Final do Resultado Líquido (Baseado no Montante Bruto Final)
    bruto_final = df["Montante Bruto"].iloc[-1]
    rendimento_bruto_final = bruto_final - valor_inicial
    aliquota_ir = aliquota_ir_fixa
    ir_devido = 0.0
    
    if not is_isento:
        ir_devido = rendimento_bruto_final * (aliquota_ir / 100.0)
        
    rendimento_liquido = rendimento_bruto_final - ir_devido
    
    return {
        "df": df,
        "montante_liquido": valor_inicial + rendimento_liquido,
        "rendimento_liquido": rendimento_liquido,
        "rendimento_bruto": rendimento_bruto_final,
        "ir_devido": ir_devido,
        "aliquota": aliquota_ir,
        "taxa_nominal_aa": taxa_anual_nominal * 100
    }

# ==========================================
# 3. LÓGICA PRINCIPAL (ROTEAMENTO)
# ==========================================

# ROTEADOR: Se logado, roda o simulador. Se não, roda a página de login.
if st.session_state['authenticated']: # Usa 'authenticated' que foi inicializado no db_manager
    
    # 1. Recuperar Limite e Status Premium
    # Estes dados já estão em st.session_state, atualizados pelo login_user
    sim_restantes = st.session_state['simulacoes_restantes']
    is_premium = st.session_state['is_premium']
    
    # 2. Lógica do Paywall Freemium (Verifica se o usuário pode usar o simulador)
    if is_premium or sim_restantes > 0:
        
        # UI da Sidebar (Status e Logout)
        st.sidebar.header("Conta")
        st.sidebar.markdown(f"**Usuário:** `{st.session_state['user_email']}`")
        if not is_premium:
            st.sidebar.warning(f"Simulações gratuitas restantes: **{sim_restantes}**")
        else:
            st.sidebar.success("✅ Acesso Premium Ilimitado!")
            
        if st.sidebar.button("Logout"):
            db_manager.logout_user() # Usa a nova função de logout
            st.rerun()
            
        # ----------------------------------------------------------------------
        # INÍCIO DO SIMULADOR
        # ----------------------------------------------------------------------
        
        st.title("📊 Simulador de Investimentos - Análise Líquida")
        st.markdown("Configure o cenário exato e compare o resultado líquido contra benchmarks dinâmicos, garantindo a **visão contábil do seu retorno**.")

        # BARRA LATERAL (INPUTS)
        st.sidebar.header("⚙️ Parâmetros Globais")
        valor_inicial = parse_br_currency(st.sidebar.text_input("Valor Inicial (R$)", "10.000,00"))
        dias = st.sidebar.number_input("Prazo (Dias)", min_value=1, value=360, step=30)
        st.sidebar.markdown("---")

        st.sidebar.header("📈 Projeções de Mercado")
        col_proj1, col_proj2 = st.sidebar.columns(2)
        taxa_cdi_proj = parse_br_currency(col_proj1.text_input("CDI/Selic Anual (%)", "13,65", key='proj_cdi'))
        taxa_tesouro_proj = parse_br_currency(col_proj2.text_input("Tesouro Pré Fixo (%)", "12,00", key='proj_tesouro_pre'))
        st.sidebar.markdown("---")

        st.sidebar.subheader("Configuração do Ativo Principal")
        tipo_ativo_selecao = st.sidebar.radio(
            "Tipo de investimento",
            ("CDB/LC/Títulos públicos/Debêntures", "LCI/LCA", "Tesouro")
        )
        # LCI/LCA e Poupança são isentos de IR. Títulos públicos/Debêntures têm IR regressivo.
        is_isento = True if tipo_ativo_selecao == "LCI/LCA" else False

        tipo_rentabilidade = st.sidebar.radio(
            "É PRÉ fixado, PÓS fixado ou IPCA+?",
            ("PRÉ", "PÓS", "IPCA"),
            horizontal=True
        )
        st.sidebar.markdown("---")

        st.sidebar.subheader("Taxas do Ativo Principal")
        params = {}

        if tipo_rentabilidade == "PÓS":
            percentual = st.sidebar.number_input("% do CDI/Selic", 50, 200, 100, 5)
            params['taxa_ref'] = taxa_cdi_proj 
            params['percentual'] = percentual
        elif tipo_rentabilidade == "PRÉ":
            taxa_fixa_str = st.sidebar.text_input("Taxa Fixa Anual (%)", "12,50")
            params['taxa_fixa'] = parse_br_currency(taxa_fixa_str)
        elif tipo_rentabilidade == "IPCA":
            col_ipca1, col_ipca2 = st.sidebar.columns(2)
            ipca_proj_str = col_ipca1.text_input("IPCA Projetado (%)", "5,00")
            taxa_real_str = col_ipca2.text_input("Juro Real (Taxa Fixa %)", "6,00")
            params['ipca_proj'] = parse_br_currency(ipca_proj_str)
            params['taxa_fixa'] = parse_br_currency(taxa_real_str)

        st.sidebar.markdown("---")

        st.sidebar.subheader("Comparativos")
        benchmarks_list = ["Poupança (Benchmark)", "CDB 100% CDI (Pós - Projeção)", "Tesouro Pré Fixo (Projeção)"]
        comparativos_selecionados = st.sidebar.multiselect(
            "Incluir no Gráfico e Tabela:",
            benchmarks_list,
            default=["Poupança (Benchmark)", "CDB 100% CDI (Pós - Projeção)"]
        )

        # Execução e Resultados
        if st.sidebar.button("Calcular Cenário 🚀"):
            
            if valor_inicial <= 0:
                st.warning("Insira um valor inicial positivo.")
                st.stop() 

            nome_ativo = f"{tipo_ativo_selecao} ({tipo_rentabilidade})"
            final_results = {}
            
            try:
                resultado_ativo = calcular_ativo_geral(valor_inicial, dias, tipo_rentabilidade, params, is_isento)
                final_results[nome_ativo] = resultado_ativo
            except Exception as e:
                st.error(f"Erro nos parâmetros de cálculo do Ativo Principal: {e}"); 
                st.stop() 

            # Cálculos de Benchmarks
            if "Poupança (Benchmark)" in comparativos_selecionados:
                final_results["Poupança (Benchmark)"] = calcular_poupanca(valor_inicial, dias)
            if "CDB 100% CDI (Pós - Projeção)" in comparativos_selecionados:
                params_cdb_100 = {'taxa_ref': taxa_cdi_proj, 'percentual': 100} 
                final_results["CDB 100% CDI (Pós - Projeção)"] = calcular_ativo_geral(valor_inicial, dias, "PÓS", params_cdb_100, False)
            if "Tesouro Pré Fixo (Projeção)" in comparativos_selecionados:
                params_tesouro_pre = {'taxa_fixa': taxa_tesouro_proj} 
                final_results["Tesouro Pré Fixo (Projeção)"] = calcular_ativo_geral(valor_inicial, dias, "PRÉ", params_tesouro_pre, False)

            # Dashboard (Renderização dos resultados)
            
            st.header("1. Montante Líquido Final 💰")
            df_barras = pd.DataFrame({
                "Investimento": final_results.keys(),
                "Montante Líquido": [res['montante_liquido'] for res in final_results.values()]
            })
            fig = px.bar(
                df_barras, x="Investimento", y="Montante Líquido", color="Investimento", text_auto=".2s",
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig.update_layout(height=350, showlegend=False)
            fig.update_traces(texttemplate='R$ %{y:,.2f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

            # Tabela Detalhada
            st.subheader("2. Detalhamento Financeiro (Visão Contábil)")
            dados_tabela = []
            metricas = ["Valor Inicial", "Montante BRUTO", "Rendimento Total", "Imposto de Renda", "Rendimento LÍQUIDO", "Taxa Anual Nominal (Estimada)"]
            for metrica in metricas:
                linha = {"Métrica": metrica}
                for nome, res in final_results.items():
                    if metrica == "Valor Inicial": linha[nome] = format_br(valor_inicial)
                    elif metrica == "Montante BRUTO": linha[nome] = format_br(res['rendimento_bruto'] + valor_inicial)
                    elif metrica == "Rendimento Total": linha[nome] = format_br(res['rendimento_bruto'])
                    elif metrica == "Imposto de Renda":
                        if res['aliquota'] == 0.0: linha[nome] = "Isento"
                        else: linha[nome] = f"- {format_br(res['ir_devido'])} ({res['aliquota']}%)"
                    elif metrica == "Rendimento LÍQUIDO": linha[nome] = f"✅ {format_br(res['rendimento_liquido'])}"
                    elif metrica == "Taxa Anual Nominal (Estimada)": linha[nome] = f"{res['taxa_nominal_aa']:.2f}%"
                dados_tabela.append(linha)
            df_exibicao = pd.DataFrame(dados_tabela)
            st.table(df_exibicao.set_index("Métrica"))

            # Gráfico de Evolução (Linhas)
            st.header("3. Curva de Crescimento Patrimonial")
            df_chart = pd.DataFrame({"Dia": final_results[nome_ativo]['df']["Dia"]})
            for nome, res in final_results.items():
                df_chart[nome] = res['df']["Montante Líquido"]
            st.line_chart(df_chart.set_index("Dia"), height=400)
            
            # Mensagem Final
            melhor_ativo_nome = max(final_results, key=lambda k: final_results[k]['montante_liquido'])
            melhor_ativo_valor = final_results[melhor_ativo_nome]['montante_liquido']
            st.success(f"🏆 Decisão Validada: O melhor **resultado líquido** é de **{melhor_ativo_nome}**, com um Montante Final de **{format_br(melhor_ativo_valor)}**.")
            
            st.info(
                f"⚠️ **Disclaimer Contábil:** Os resultados gerados são somente previsões, considerar para fins contábeis o valor líquido.\n\n"
                f"Criado por **Adrian Cardoso**, Analista de Dados e FP&A."
            )
            
            # 4. Decrementar o Limite APÓS o cálculo (se não for premium)
            if not is_premium:
                 db_manager.decrement_simulacoes(st.session_state['user_email'])
                 
    else:
        # Usuário logado, mas limite esgotado
        st.error("Seu limite de simulações gratuitas acabou. 😢")
        st.subheader("Para continuar simulando, considere o plano Premium.")
        st.info("Para este ambiente de teste, faça **Logout** e **Login** novamente para resetar o limite de 5 simulações.")
        
        if st.button("Logout"):
            db_manager.logout_user()
            st.rerun()
        
else:
    # --- 🔓 RENDERIZA A TELA DE LOGIN/CADASTRO (USUÁRIO NÃO AUTENTICADO) ---
    render_login_page()












