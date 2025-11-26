import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
import plotly.express as px 

# Configuração da Página
st.set_page_config(
    page_title="Simulador de Investimentos", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

#  Funções Auxiliares
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

# Funções de Cálculo
# Poupança
def calcular_poupanca(valor_inicial, dias):
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

# Ativos gerais
def calcular_ativo_geral(valor_inicial, dias, tipo_rentabilidade, params, is_isento):
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
        # Fórmula Fisher (1+IPCA) * (1+Juro Real) - 1
        taxa_anual_nominal = ((1 + ipca) * (1 + juro_real)) - 1
        
    # base_dias = 252.0 if tipo_rentabilidade == "PÓS" else 365.0 #
    fator_diario = (1 + taxa_anual_nominal)**(1 / 365.0)
    
    data = []
    montante = valor_inicial
    
    aliquota_ir_fixa = 0.0
    if not is_isento:
        if dias <= 180: aliquota_ir_fixa = 22.5
        elif dias <= 360: aliquota_ir_fixa = 20.0
        elif dias <= 720: aliquota_ir_fixa = 17.5
        else: aliquota_ir_fixa = 15.0

    for d in range(0, dias + 1):
        if d > 0: montante *= fator_diario
        rendimento_total = montante - valor_inicial
        
        montante_liquido_simples = valor_inicial + (rendimento_total * (1 - aliquota_ir_fixa/100.0))
        if is_isento: montante_liquido_simples = montante

        data.append((d, montante, rendimento_total, montante_liquido_simples))
        
    df = pd.DataFrame(data, columns=["Dia", "Montante Bruto", "Rendimento Bruto", "Montante Líquido"])
    
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

# Interface Principal

st.title("📊 Simulador de Investimentos")
st.markdown("Configure o cenário exato e compare o resultado líquido contra benchmarks dinâmicos.")

# ==========================================
# BARRA LATERAL (INPUTS)
# ==========================================

st.sidebar.header("⚙️ Parâmetros Globais")
valor_inicial = parse_br_currency(st.sidebar.text_input("Valor Inicial (R$)", "10.000,00"))
dias = st.sidebar.number_input("Prazo (Dias)", min_value=1, value=360, step=30)
st.sidebar.markdown("---")

# 1. BLOCO: TAXAS DE PROJEÇÃO DE MERCADO (Separado)
st.sidebar.header("📈 Projeções de Mercado")
col_proj1, col_proj2 = st.sidebar.columns(2)
# Projeção CDI
taxa_cdi_proj = parse_br_currency(col_proj1.text_input("CDI/Selic Anual (%)", "13,65", key='proj_cdi'))
# Benchmark
taxa_tesouro_proj = parse_br_currency(col_proj2.text_input("Tesouro Pré Fixo (%)", "12,00", key='proj_tesouro_pre'))

st.sidebar.markdown("---")


# 2. CONFIGURAÇÃO DO ATIVO PRINCIPAL
st.sidebar.subheader("Configuração do Ativo Principal")

tipo_ativo_selecao = st.sidebar.radio(
    "Tipo de investimento",
    ("CDB/LC/Títulos públicos/Debêntures", "LCI/LCA", "Tesouro")
)
is_isento = True if tipo_ativo_selecao == "LCI/LCA" else False

tipo_rentabilidade = st.sidebar.radio(
    "É PRÉ fixado ou PÓS fixado?",
    ("PRÉ", "PÓS", "IPCA"),
    horizontal=True
)

st.sidebar.markdown("---")

# 3. INPUTS DINÂMICOS (APENAS DO ATIVO PRINCIPAL)
st.sidebar.subheader("Taxas do Ativo Principal")
params = {}

if tipo_rentabilidade == "PÓS":
    percentual = st.sidebar.number_input("% do CDI/Selic", 50, 200, 100, 5)
    params['taxa_ref'] = taxa_cdi_proj # Usa a projeção
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

# 4. SELEÇÃO DE COMPARATIVOS (MULTSELECT)
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
    
    # 1. Calcular Ativo Principal
    try:
        resultado_ativo = calcular_ativo_geral(valor_inicial, dias, tipo_rentabilidade, params, is_isento)
        final_results[nome_ativo] = resultado_ativo
    except Exception as e:
         st.error(f"Erro nos parâmetros de cálculo do Ativo Principal: {e}"); st.stop()

    # 2. Calcular TODOS os Benchmarks Ativados

    # a. Poupança
    if "Poupança (Benchmark)" in comparativos_selecionados:
        final_results["Poupança (Benchmark)"] = calcular_poupanca(valor_inicial, dias)

    # b. CDB 100% CDI (Pós - Projeção)
    if "CDB 100% CDI (Pós - Projeção)" in comparativos_selecionados:
        params_cdb_100 = {'taxa_ref': taxa_cdi_proj, 'percentual': 100} # Usa a nova projeção CDI
        final_results["CDB 100% CDI (Pós - Projeção)"] = calcular_ativo_geral(valor_inicial, dias, "PÓS", params_cdb_100, False)

    # c. Tesouro Pré Fixo (Projeção)
    if "Tesouro Pré Fixo (Projeção)" in comparativos_selecionados:
        params_tesouro_pre = {'taxa_fixa': taxa_tesouro_proj} # Usa a nova projeção Tesouro Pré
        final_results["Tesouro Pré Fixo (Projeção)"] = calcular_ativo_geral(valor_inicial, dias, "PRÉ", params_tesouro_pre, False)

    # 3. CONSOLIDAÇÃO

    if not final_results:
        st.warning("Nenhum ativo ou benchmark foi calculado. Verifique suas seleções."); st.stop()


    # DASHBOARD DE RESULTADOS

    # 1. Gráfico de Comparação Final (Barras)
    st.header("1. Montante Líquido Final 💰")
    
    df_barras = pd.DataFrame({
        "Investimento": final_results.keys(),
        "Montante Líquido": [res['montante_liquido'] for res in final_results.values()]
    })
    
    fig = px.bar(
        df_barras, x="Investimento", y="Montante Líquido", 
        color="Investimento", text_auto=".2s",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig.update_layout(height=350, showlegend=False)
    fig.update_traces(texttemplate='R$ %{y:,.2f}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

    # 2. Tabela Detalhada 
    st.subheader("2. Detalhamento Financeiro")
    
    dados_tabela = []
    
    metricas = ["Montante BRUTO", "Rendimento Total", "Imposto de Renda", "Rendimento LÍQUIDO", "Taxa Anual Nominal (Estimada)"]

    for metrica in metricas:
        linha = {"Métrica": metrica}
        for nome, res in final_results.items():
            if metrica == "Montante BRUTO":
                linha[nome] = format_br(res['rendimento_bruto'] + valor_inicial)
            elif metrica == "Rendimento Total":
                linha[nome] = format_br(res['rendimento_bruto'])
            elif metrica == "Imposto de Renda":
                if res['aliquota'] == 0.0:
                    linha[nome] = "Isento"
                else:
                    linha[nome] = f"- {format_br(res['ir_devido'])} ({res['aliquota']}%)"
            elif metrica == "Rendimento LÍQUIDO":
                linha[nome] = f"✅ {format_br(res['rendimento_liquido'])}"
            elif metrica == "Taxa Anual Nominal (Estimada)":
                linha[nome] = f"{res['taxa_nominal_aa']:.2f}%"
        dados_tabela.append(linha)

    df_exibicao = pd.DataFrame(dados_tabela)
    st.table(df_exibicao.set_index("Métrica"))

    st.markdown("---")

    # 3. Gráfico de Evolução (Linhas)
    st.header("3. Curva de Crescimento Patrimonial")
    
    df_chart = pd.DataFrame({"Dia": final_results[nome_ativo]['df']["Dia"]})
    
    for nome, res in final_results.items():
        df_chart[nome] = res['df']["Montante Líquido"]
    st.line_chart(df_chart.set_index("Dia"), height=400)
    
    # Mensagem Final ---
    melhor_ativo_nome = max(final_results, key=lambda k: final_results[k]['montante_liquido'])
    melhor_ativo_valor = final_results[melhor_ativo_nome]['montante_liquido']
    
    st.success(f"✅ Decisão Validada: O melhor **resultado líquido** é de **{melhor_ativo_nome}**, demonstrando um **Montante Final Otimizado** de **{format_br(melhor_ativo_valor)}**.")
    st.info(f"⚠️ **Disclaimer Contábil:** Os resultados gerados são previsões baseadas em projeções de mercado. Para o **Controle Orçamentário**, considere sempre o **Valor Líquido**.")


    st.info(f"Criado por **Adrian Cardoso**, Analista de Dados e FP&A")

            # Executar no terminal --> streamlit run Simulador_Investimentos.py <-- 



