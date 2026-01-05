import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from datetime import datetime, timedelta

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IA Analytics 360º - Concessionária", layout="wide", page_icon="📊")

# --- 2. CONFIGURAÇÃO DA API (GROQ) ---
try:
    if "GROQ_API" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API"]
    else:
        os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")
except Exception:
    pass

llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.1)

# --- 3. CARREGAMENTO DE DADOS ---
@st.cache_data
def carregar_dados():
    try:
        est_pecas = pd.read_csv("estoque_pecas.csv", sep=None, engine='python')
        hist_servicos = pd.read_csv("historico_servicos.csv", sep=None, engine='python')
        vendas_pecas = pd.read_csv("vendas_pecas.csv", sep=None, engine='python')
        vendas_veiculos = pd.read_csv("vendas_veiculos.csv", sep=None, engine='python')
        vendas_veiculos['Data_da_Venda'] = pd.to_datetime(vendas_veiculos['Data_da_Venda'])
        return est_pecas, hist_servicos, vendas_pecas, vendas_veiculos
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None

dfs_raw = carregar_dados()

# --- 4. TÍTULO E INTRODUÇÃO (MOVIDO PARA FORA DO IF PARA GARANTIR EXIBIÇÃO) ---
st.title("🚗 IA Analytics: Performance 360º")

with st.expander("ℹ️ Sobre o Sistema", expanded=True):
    st.markdown("""
    O sistema consolida automaticamente suas quatro principais planilhas de operação. 
    Ele fornece uma visão fixa da oficina e do estoque para você nunca perder de vista o capital parado. 
    Através de filtros inteligentes, ele permite auditar a performance individual de cada vendedor no tempo. 
    Por fim, ele utiliza um motor de Inteligência Artificial de última geração que funciona como um consultor financeiro, 
    capaz de ler todos esses números e responder dúvidas estratégicas em segundos, como se você estivesse conversando com um analista humano especializado.
    """)

st.markdown("---")

if dfs_raw:
    est_pecas, hist_servicos, vendas_pecas, vendas_veiculos = dfs_raw

    # --- 5. INDICADORES FIXOS (ESTOQUE E SERVIÇOS) ---
    st.subheader("📦 Gestão de Estoque (Geral da Loja)")
    ce1, ce2 = st.columns(2)
    with ce1:
        aging_geral = vendas_veiculos['Dias_que_o_Carro_Ficou_no_Estoque'].mean()
        st.metric("Aging Médio Geral", f"{aging_geral:.1f} dias", 
                  help="Base: vendas_veiculos.csv | Cálculo: Média de dias que os veículos vendidos permaneceram em estoque.")
    with ce2:
        valor_obsoleto = est_pecas[est_pecas['Peca_Esta_Obsoleta'] == True]['Valor_Total_Estoque'].sum()
        st.metric("Capital Obsoleto (Peças)", f"R$ {valor_obsoleto:,.2f}", 
                  help="Base: estoque_pecas.csv | Cálculo: Soma do valor total das peças marcadas como 'Obsoleta'.")

    st.subheader("🛠️ Vendas de Serviço e Oficina (Geral da Loja)")
    cs1, cs2 = st.columns(2)
    with cs1:
        ticket_oficina = hist_servicos['Valor_Total_Do_Servico_Realizado'].mean()
        st.metric("Ticket Médio Oficina", f"R$ {ticket_oficina:,.2f}", 
                  help="Base: historico_servicos.csv | Cálculo: Faturamento total de serviços / Quantidade de O.S.")
    with cs2:
        vendas_assist = vendas_pecas[vendas_pecas['Departamento_da_Venda'].str.contains('ASSISTENCIA', na=False, case=False)]['Valor_da_Venda'].sum()
        penetracao_pecas = vendas_assist / len(hist_servicos) if len(hist_servicos) > 0 else 0
        st.metric("Peças por O.S.", f"R$ {penetracao_pecas:,.2f}", 
                  help="Base: vendas_pecas.csv e hist_servicos.csv | Cálculo: Venda de peças em assistência / Número de passagens.")

    st.markdown("---")

    # --- 6. FILTROS ESTRATÉGICOS ---
    st.subheader("🎯 Filtros para Vendas e Gráficos")
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    
    data_fim_padrao = vendas_veiculos["Data_da_Venda"].max().date()
    data_inicio_padrao = data_fim_padrao - timedelta(days=365)

    with col_f1:
        vendedores = ["Todos"] + sorted(vendas_veiculos["Nome_do_Vendedor_que_Realizou_a_Venda"].unique().tolist())
        vendedor_sel = st.selectbox("Filtrar Vendedor", vendedores)
    with col_f2:
        periodo = st.date_input("Filtrar Período", [data_inicio_padrao, data_fim_padrao])
    
    df_vendas_filtrado = vendas_veiculos.copy()
    if vendedor_sel != "Todos":
        df_vendas_filtrado = df_vendas_filtrado[df_vendas_filtrado["Nome_do_Vendedor_que_Realizou_a_Venda"] == vendedor_sel]
    if len(periodo) == 2:
        df_vendas_filtrado = df_vendas_filtrado[(df_vendas_filtrado["Data_da_Venda"].dt.date >= periodo[0]) & (df_vendas_filtrado["Data_da_Venda"].dt.date <= periodo[1])]

    with col_f3:
        st.write("")
        st.write("")
        st.download_button("📥 Exportar Filtro", data=df_vendas_filtrado.to_csv(index=False).encode('utf-8'), file_name='vendas_detalhadas.csv')

    # --- 7. PERFORMANCE DE VENDAS DE VEÍCULOS (DINÂMICO) ---
    st.subheader("📈 Performance de Vendas de Veículos (Filtrado)")
    cv1, cv2 = st.columns(2)
    with cv1:
        margem_v = (df_vendas_filtrado['Lucro_Bruto'].sum() / df_vendas_filtrado['Valor_da_Venda'].sum()) * 100 if df_vendas_filtrado['Valor_da_Venda'].sum() > 0 else 0
        st.metric("Margem Veículos", f"{margem_v:.2f}%", 
                  help="Base: vendas_veiculos.csv | Cálculo: (Lucro / Venda) * 100 no contexto filtrado.")
    with cv2:
        venda_total = df_vendas_filtrado['Valor_da_Venda'].sum()
        st.metric("Volume de Vendas", f"R$ {venda_total:,.2f}", 
                  help="Base: vendas_veiculos.csv | Soma do faturamento bruto no contexto filtrado.")

    # --- 8. ABAS DE GRÁFICOS (DINÂMICOS) ---
    aba1, aba2 = st.tabs(["📅 Evolução Mensal de Vendas", "📊 Mix por Categoria"])
    
    with aba1:
        st.markdown("### Performance Mensal: Faturamento vs. Rentabilidade")
        st.info("""
        **Base de Dados:** `vendas_veiculos.csv` | **Interpretação:** Compare faturamento (Barras) e margem (Linha). Quedas na linha com aumento de barras indicam volume obtido através de descontos excessivos.
        """)
        
        df_mensal = df_vendas_filtrado.copy()
        df_mensal['Mes_Ano'] = df_mensal['Data_da_Venda'].dt.to_period('M').astype(str)
        evo_mensal = df_mensal.groupby("Mes_Ano").agg({"Valor_da_Venda": "sum", "Margem_Percentual": "mean"}).reset_index().sort_values("Mes_Ano")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=evo_mensal["Mes_Ano"], y=evo_mensal["Valor_da_Venda"], name="Faturamento (R$)", marker_color='#1f77b4'))
        fig.add_trace(go.Scatter(x=evo_mensal["Mes_Ano"], y=evo_mensal["Margem_Percentual"], name="Margem (%)", yaxis='y2', line=dict(color='red', width=3)))
        fig.update_layout(template="plotly_dark", yaxis2=dict(overlaying="y", side="right", title="Margem (%)"))
        st.plotly_chart(fig, use_container_width=True)

    with aba2:
        st.markdown("### Rentabilidade por Categoria de Veículo")
        st.info("**Base de Dados:** `vendas_veiculos.csv` | **Interpretação:** Identifique quais categorias trazem maior Lucro Bruto acumulado.")
        lucro_c = df_vendas_filtrado.groupby("Categoria_do_Veiculo")["Lucro_Bruto"].sum().reset_index().sort_values(by="Lucro_Bruto")
        fig_c = px.bar(lucro_c, y="Categoria_do_Veiculo", x="Lucro_Bruto", orientation='h', color="Lucro_Bruto", color_continuous_scale="Greens", template="plotly_dark")
        st.plotly_chart(fig_c, use_container_width=True)

    st.markdown("---")

    # --- 9. CONSULTORIA ESTRATÉGICA IA ---
    st.subheader("🤖 Consultor de Operações IA")
    
    with st.expander("ℹ️ O que o modelo consegue responder?", expanded=True):
        st.markdown("""
        ### 1. Análise de Performance de Vendedores
        O agente tem acesso ao faturamento e lucro bruto mensal de cada vendedor.
        * **Ranking de Lucro:** "Quem foi o vendedor mais rentável de 2024 até agora?"
        * **Comparativo Direto:** "O vendedor [Nome A] fatura mais que o [Nome B], mas quem tem a melhor margem de lucro?"

        ### 2. Diagnóstico de Estoque e Capital
        O agente conhece o Aging Médio e o valor do Capital Obsoleto.
        * **Custo de Oportunidade:** "Considerando que temos R$ [Valor] em peças obsoletas, qual o impacto disso na saúde financeira da loja?"

        ### 3. Eficiência da Oficina e Pós-Venda
        O agente recebeu o Ticket Médio e a métrica de Peças por O.S.
        * **Aumento de Receita:** "Como podemos aumentar o ticket médio da oficina baseado nos indicadores atuais?"

        ### 4. Consultoria Estratégica (CFO/CEO)
        * **Análise de Risco:** "Atue como meu CFO e me diga: onde estamos perdendo dinheiro hoje?"
        """)

    pergunta = st.text_input("Digite sua dúvida estratégica abaixo:", placeholder="Ex: Quem vendeu mais em janeiro de 2024?")

    if pergunta:
        with st.spinner("IA processando dados estratégicos..."):
            df_resumo_ia = vendas_veiculos.groupby(["Nome_do_Vendedor_que_Realizou_a_Venda", vendas_veiculos['Data_da_Venda'].dt.strftime('%Y-%m')]).agg({
                "Valor_da_Venda": "sum", "Lucro_Bruto": "sum"
            }).reset_index().sort_values(by="Valor_da_Venda", ascending=False)

            texto_compacto = df_resumo_ia.head(60).to_string(index=False)

            contexto_ia = f"""
            Atue como CFO. Analise o resumo (Vendedor, Mês, Venda, Lucro):
            {texto_compacto}
            Estatísticas: Aging {aging_geral:.1f}d | Obsoleto R${valor_obsoleto:,.2f} | Oficina R${ticket_oficina:,.2f}.
            Pergunta: {pergunta}
            Instrução: Responda de forma curta e executiva.
            """
            try:
                resposta = llm.invoke([HumanMessage(content=contexto_ia)])
                st.info(resposta.content)
            except Exception as e:
                st.error(f"Erro na IA: {e}")
else:
    st.error("Arquivos de dados não encontrados na pasta raiz.")