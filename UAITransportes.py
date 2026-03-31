import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path

# Configurações do Streamlit
st.set_page_config(page_title="UAI Transportes", layout="wide")

# Carregar os dados
@st.cache_data
def carregar_dados():
    # Usar caminhos absolutos
    dir_atual = Path(__file__).parent
    dados_cadastrais = pd.read_excel(dir_atual / 'DadosCadastrais.xlsx')
    dados_frete = pd.read_excel(dir_atual / 'DadosFrete.xlsx')
    dados_bordo = pd.read_csv(dir_atual / 'Diário de Bordo.txt', delimiter=';')
    
    # Limpar e processar dados
    dados_cadastrais = dados_cadastrais.dropna(axis=1, how='all')
    dados_frete = dados_frete.dropna(axis=1, how='all')
    dados_bordo = dados_bordo.dropna(axis=1, how='all')
    
    # Converter colunas de ID para object
    if 'IDCliente' in dados_cadastrais.columns:
        dados_cadastrais['IDCliente'] = dados_cadastrais['IDCliente'].astype('object')
    if 'IDMotorista' in dados_cadastrais.columns:
        dados_cadastrais['IDMotorista'] = dados_cadastrais['IDMotorista'].astype('object')
    if 'IDVeiculo' in dados_cadastrais.columns:
        dados_cadastrais['IDVeiculo'] = dados_cadastrais['IDVeiculo'].astype('object')
    
    if 'IDVeiculo' in dados_frete.columns:
        dados_frete['IDVeiculo'] = dados_frete['IDVeiculo'].astype('object')
    if 'IDCliente' in dados_frete.columns:
        dados_frete['IDCliente'] = dados_frete['IDCliente'].astype('object')
    
    # NOTA: Frete, Peso em Kg e Valor da Mercadoria já vêm como float64, não precisam conversão
    
    # Doc Fiscal deve ser numérico para fazer merge
    if 'Doc Fiscal' in dados_frete.columns:
        dados_frete['Doc Fiscal'] = pd.to_numeric(dados_frete['Doc Fiscal'], errors='coerce')
    if 'Doc Fiscal' in dados_bordo.columns:
        dados_bordo['Doc Fiscal'] = pd.to_numeric(dados_bordo['Doc Fiscal'], errors='coerce')
    
    # Converter datas
    if 'Data' in dados_frete.columns:
        dados_frete['Data'] = pd.to_datetime(dados_frete['Data'])
    
    # Converter valores de despesa (formato brasileiro com vírgula)
    for col in ['Combustivel', 'Manutenção', 'Custos Motorista', 'Litros']:
        if col in dados_bordo.columns:
            dados_bordo[col] = pd.to_numeric(
                dados_bordo[col].astype(str).str.replace('.', '').str.replace(',', '.'),
                errors='coerce'
            )
    
    # Merge dos dados: Frete + Bordo (por Doc Fiscal)
    dados_completos = dados_frete.merge(dados_bordo, on='Doc Fiscal', how='left')
    
    # Calcular despesa total (preenchendo NaN com 0)
    dados_completos['Despesa Total'] = (
        pd.to_numeric(dados_completos['Combustivel'], errors='coerce').fillna(0) + 
        pd.to_numeric(dados_completos['Manutenção'], errors='coerce').fillna(0) + 
        pd.to_numeric(dados_completos['Custos Motorista'], errors='coerce').fillna(0)
    )
    
    return dados_cadastrais, dados_frete, dados_bordo, dados_completos

# Carregar dados
dados_cadastrais, dados_frete, dados_bordo, dados_completos = carregar_dados()

# Título e descrição
st.title("📊 Dashboard UAI Transportes")
st.markdown("Análise de Faturamento, Frotas e Custos")
st.markdown("---")

# ==================== PERGUNTA 1 ====================
st.header("1️⃣ Pior Mês em Faturamento")
try:
    df_q1 = dados_frete.copy()
    df_q1['YearMonth'] = df_q1['Data'].dt.to_period('M')
    
    # Agrupar faturamento e viagens
    faturamento_mensal = df_q1.groupby('YearMonth')['Frete'].sum()
    viagens_mensal = df_q1.groupby('YearMonth').size()
    
    # Criar DataFrame alinhado
    dados_mes = pd.DataFrame({
        'Faturamento': faturamento_mensal,
        'Viagens': viagens_mensal
    })
    
    # Ordenar por faturamento
    dados_mes = dados_mes.sort_values('Faturamento')
    
    pior_mes = dados_mes.index[0]
    valor_pior_mes = dados_mes['Faturamento'].iloc[0]
    
    # Converter index de Period para string para o gráfico
    faturamento_grafico = dados_mes['Faturamento']
    faturamento_grafico.index = faturamento_grafico.index.astype(str)
    
    viagens_grafico = dados_mes['Viagens']
    viagens_grafico.index = viagens_grafico.index.astype(str)
    
    # Criar cores: vermelho para o pior mês, azul para os outros
    cores = ['red' if mes == str(pior_mes) else 'steelblue' for mes in faturamento_grafico.index]
    
    fig = go.Figure(data=[
        go.Bar(
            x=faturamento_grafico.index,
            y=faturamento_grafico.values,
            marker_color=cores,
            text=[f'R$ {v:,.0f}' for v in faturamento_grafico.values],
            textposition='outside',
            customdata=viagens_grafico.values,
            hovertemplate='<b>%{x}</b><br>Faturamento: R$ %{y:,.2f}<br>Viagens: %{customdata:.0f}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title="Faturamento Mensal",
        xaxis_title="Mês",
        yaxis_title="Faturamento (R$)",
        showlegend=False,
        hovermode='x unified',
        xaxis={'tickangle': -45}
    )
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Erro Q1: {e}")

st.markdown("---")

# ==================== PERGUNTA 3 ====================
st.header("3️⃣ Toneladas por Tipo de Veículo - Todos os Meses")
try:
    df_q3 = dados_frete.merge(dados_cadastrais[['IDVeiculo', 'Tipo Veículo']], on='IDVeiculo', how='left')
    
    # Criar coluna de mês
    df_q3['YearMonth'] = df_q3['Data'].dt.to_period('M')
    
    # Agrupar por mês e tipo de veículo
    peso_por_mes_tipo = df_q3.groupby(['YearMonth', 'Tipo Veículo'])['Peso em Kg'].sum() / 1000
    
    # Converter para DataFrame
    peso_df = peso_por_mes_tipo.reset_index()
    peso_df.columns = ['Mês', 'Tipo Veículo', 'Toneladas']
    peso_df['Mês'] = peso_df['Mês'].astype(str)
    
    # Criar figura com plotly graph_objects
    fig = go.Figure()
    
    # Definir cores para cada tipo de veículo
    cores_veiculo = {
        'cavalo': 'red',
        'cam': 'steelblue',
        'toco': 'green',
        'truck': 'navy'
    }
    
    # Adicionar barras para Cavalo
    cavalo_data = peso_df[peso_df['Tipo Veículo'].str.strip().str.lower() == 'cavalo']
    fig.add_trace(go.Bar(
        x=cavalo_data['Mês'],
        y=cavalo_data['Toneladas'],
        name='Cavalo',
        marker_color=cores_veiculo['cavalo'],
        text=[f'{v:.1f} t' for v in cavalo_data['Toneladas']],
        textposition='outside',
        hovertemplate='<b>%{x} - Cavalo</b><br>Toneladas: %{y:.2f}<extra></extra>'
    ))
    
    # Adicionar barras para outros tipos
    for tipo in ['Cam', 'Toco', 'Truck']:
        tipo_lower = tipo.lower()
        tipo_data = peso_df[peso_df['Tipo Veículo'].str.strip() == tipo]
        fig.add_trace(go.Bar(
            x=tipo_data['Mês'],
            y=tipo_data['Toneladas'],
            name=tipo,
            marker_color=cores_veiculo[tipo_lower],
            text=[f'{v:.1f} t' for v in tipo_data['Toneladas']],
            textposition='outside',
            hovertemplate=f'<b>%{{x}} - {tipo}</b><br>Toneladas: %{{y:.2f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title="Toneladas Transportadas por Tipo de Veículo (Todos os Meses) - Destaque: Janeiro 2021",
        xaxis_title="Mês",
        yaxis_title="Toneladas (ton)",
        barmode='group',
        showlegend=True,
        hovermode='x unified',
        xaxis={'tickangle': -45},
        height=500,
        xaxis_type='category'
    )
    
    # Adicionar retângulo destacando janeiro 2021 (12º mês do índice)
    # Com 20 meses totais, janeiro 2021 é o 13º (índice 12)
    meses_list = sorted(peso_df['Mês'].unique())
    if '2021-01' in meses_list:
        idx_jan = meses_list.index('2021-01')
        # Adicionar retângulo semitransparente
        fig.add_vrect(
            x0=idx_jan - 0.4,
            x1=idx_jan + 0.4,
            fillcolor='orange',
            opacity=0.1,
            line_width=2,
            line_color='orange',
            line_dash='dash',
            annotation_text='Janeiro 2021',
            annotation_position='top'
        )
    
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Erro Q3: {e}")

st.markdown("---")

# ==================== PERGUNTA 4 ====================
st.header("4️⃣ Entregas por Semestre - 2020 e 2021")
try:
    df_q4 = dados_frete.copy()
    
    # Calcular entregas por semestre
    semestres = []
    entregas = []
    
    # H1 2020
    h1_2020 = df_q4[
        (df_q4['Data'].dt.year == 2020) & 
        (df_q4['Data'].dt.month <= 6)
    ].shape[0]
    semestres.append('1º Semestre 2020')
    entregas.append(h1_2020)
    
    # H2 2020
    h2_2020 = df_q4[
        (df_q4['Data'].dt.year == 2020) & 
        (df_q4['Data'].dt.month > 6)
    ].shape[0]
    semestres.append('2º Semestre 2020')
    entregas.append(h2_2020)
    
    # H1 2021
    h1_2021 = df_q4[
        (df_q4['Data'].dt.year == 2021) & 
        (df_q4['Data'].dt.month <= 6)
    ].shape[0]
    semestres.append('1º Semestre 2021')
    entregas.append(h1_2021)
    
    # H2 2021
    h2_2021 = df_q4[
        (df_q4['Data'].dt.year == 2021) & 
        (df_q4['Data'].dt.month > 6)
    ].shape[0]
    semestres.append('2º Semestre 2021')
    entregas.append(h2_2021)
    
    # Criar gráfico de linha
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=semestres,
        y=entregas,
        mode='lines+markers+text',
        name='Entregas',
        line=dict(color='steelblue', width=3),
        marker=dict(size=10),
        text=[f'{e:,}' for e in entregas],
        textposition='top center',
        hovertemplate='<b>%{x}</b><br>Entregas: %{y:,}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Entregas por Semestre",
        xaxis_title="Semestre",
        yaxis_title="Quantidade de Entregas",
        showlegend=False,
        hovermode='x unified',
        height=400
    )
    
    # Destacar H1 2021
    if '1º Semestre 2021' in semestres:
        idx_h1_2021 = semestres.index('1º Semestre 2021')
        fig.add_vrect(
            x0=idx_h1_2021 - 0.4,
            x1=idx_h1_2021 + 0.4,
            fillcolor='red',
            opacity=0.15,
            line_width=2,
            line_color='red',
            line_dash='dash'
        )
    
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Erro Q4: {e}")

st.markdown("---")

# ==================== PERGUNTA 5 ====================
st.header("5️⃣ Peso Total por Trimestre - 2020 e 2021")
try:
    df_q5 = dados_frete.copy()
    
    # Calcular peso por trimestre
    trimestres = []
    pesos = []
    
    # Q1 2020
    q1_2020 = df_q5[
        (df_q5['Data'].dt.year == 2020) & 
        (df_q5['Data'].dt.month.isin([1, 2, 3]))
    ]['Peso em Kg'].sum() / 1000
    trimestres.append('1º Trimestre 2020')
    pesos.append(q1_2020)
    
    # Q2 2020
    q2_2020 = df_q5[
        (df_q5['Data'].dt.year == 2020) & 
        (df_q5['Data'].dt.month.isin([4, 5, 6]))
    ]['Peso em Kg'].sum() / 1000
    trimestres.append('2º Trimestre 2020')
    pesos.append(q2_2020)
    
    # Q3 2020
    q3_2020 = df_q5[
        (df_q5['Data'].dt.year == 2020) & 
        (df_q5['Data'].dt.month.isin([7, 8, 9]))
    ]['Peso em Kg'].sum() / 1000
    trimestres.append('3º Trimestre 2020')
    pesos.append(q3_2020)
    
    # Q4 2020
    q4_2020 = df_q5[
        (df_q5['Data'].dt.year == 2020) & 
        (df_q5['Data'].dt.month.isin([10, 11, 12]))
    ]['Peso em Kg'].sum() / 1000
    trimestres.append('4º Trimestre 2020')
    pesos.append(q4_2020)
    
    # Q1 2021
    q1_2021 = df_q5[
        (df_q5['Data'].dt.year == 2021) & 
        (df_q5['Data'].dt.month.isin([1, 2, 3]))
    ]['Peso em Kg'].sum() / 1000
    trimestres.append('1º Trimestre 2021')
    pesos.append(q1_2021)
    
    # Q2 2021
    q2_2021 = df_q5[
        (df_q5['Data'].dt.year == 2021) & 
        (df_q5['Data'].dt.month.isin([4, 5, 6]))
    ]['Peso em Kg'].sum() / 1000
    trimestres.append('2º Trimestre 2021')
    pesos.append(q2_2021)
    
    # Q3 2021
    q3_2021 = df_q5[
        (df_q5['Data'].dt.year == 2021) & 
        (df_q5['Data'].dt.month.isin([7, 8, 9]))
    ]['Peso em Kg'].sum() / 1000
    trimestres.append('3º Trimestre 2021')
    pesos.append(q3_2021)
    
    # Criar gráfico de linha
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trimestres,
        y=pesos,
        mode='lines+markers+text',
        name='Peso',
        line=dict(color='steelblue', width=3),
        marker=dict(size=10),
        text=[f'{p:,.0f} t' for p in pesos],
        textposition='top center',
        hovertemplate='<b>%{x}</b><br>Peso: %{y:,.0f} ton<extra></extra>'
    ))
    
    fig.update_layout(
        title="Peso Total por Trimestre",
        xaxis_title="Trimestre",
        yaxis_title="Peso (ton)",
        showlegend=False,
        hovermode='x unified',
        height=400
    )
    
    # Destacar Q2 2020
    if '2º Trimestre 2020' in trimestres:
        idx_q2_2020 = trimestres.index('2º Trimestre 2020')
        fig.add_vrect(
            x0=idx_q2_2020 - 0.4,
            x1=idx_q2_2020 + 0.4,
            fillcolor='red',
            opacity=0.15,
            line_width=2,
            line_color='red',
            line_dash='dash'
        )
    
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Erro Q5: {e}")

st.markdown("---")

# ==================== PERGUNTA 6 ====================
st.header("6️⃣ Despesas Frota - Q1 2021 vs Q1 2020")
try:
    df_q6 = dados_completos.copy()
    
    despesas_q1_2021 = df_q6[
        (df_q6['Data'].dt.year == 2021) & 
        (df_q6['Data'].dt.month.isin([1, 2, 3]))
    ]['Despesa Total'].sum()
    
    despesas_q1_2020 = df_q6[
        (df_q6['Data'].dt.year == 2020) & 
        (df_q6['Data'].dt.month.isin([1, 2, 3]))
    ]['Despesa Total'].sum()
    
    variacao = ((despesas_q1_2021 - despesas_q1_2020) / despesas_q1_2020 * 100) if despesas_q1_2020 > 0 else 0
    
    # Criar gráfico de barras
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=['Q1 2020', 'Q1 2021'],
        y=[despesas_q1_2020, despesas_q1_2021],
        marker_color=['steelblue', 'darkblue'],
        text=[f'R$ {despesas_q1_2020:,.2f}', f'R$ {despesas_q1_2021:,.2f}'],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Despesa: R$ %{y:,.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Despesas Frota - Comparação Q1 2020 vs Q1 2021",
        xaxis_title="Período",
        yaxis_title="Despesa (R$)",
        showlegend=False,
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Exibir variação percentual
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Q1 2020", f"R$ {despesas_q1_2020:,.2f}")
    with col2:
        st.metric("Q1 2021", f"R$ {despesas_q1_2021:,.2f}")
    with col3:
        st.metric("Variação", f"{variacao:.2f}%", delta_color="inverse")
except Exception as e:
    st.error(f"Erro Q6: {e}")

st.markdown("---")

# ==================== PERGUNTA 7 ====================
st.header("7️⃣ Custo por Tipo de Veículo - Todos os Meses")
try:
    df_q7 = dados_completos.merge(dados_cadastrais[['IDVeiculo', 'Tipo Veículo']], on='IDVeiculo', how='left')
    
    # Criar coluna de mês
    df_q7['YearMonth'] = df_q7['Data'].dt.to_period('M')
    
    # Agrupar por mês e tipo de veículo
    custo_por_mes_tipo = df_q7.groupby(['YearMonth', 'Tipo Veículo'])['Despesa Total'].sum()
    
    # Converter para DataFrame
    custo_df = custo_por_mes_tipo.reset_index()
    custo_df.columns = ['Mês', 'Tipo Veículo', 'Custo']
    custo_df['Mês'] = custo_df['Mês'].astype(str)
    
    # Criar figura com plotly graph_objects
    fig = go.Figure()
    
    # Definir cores para cada tipo de veículo
    cores_veiculo = {
        'cavalo': 'red',
        'cam': 'steelblue',
        'toco': 'green',
        'truck': 'navy'
    }
    
    # Adicionar barras para Cavalo
    cavalo_data = custo_df[custo_df['Tipo Veículo'].str.strip().str.lower() == 'cavalo']
    fig.add_trace(go.Bar(
        x=cavalo_data['Mês'],
        y=cavalo_data['Custo'],
        name='Cavalo',
        marker_color=cores_veiculo['cavalo'],
        text=[f'R$ {v:,.0f}' for v in cavalo_data['Custo']],
        textposition='outside',
        hovertemplate='<b>%{x} - Cavalo</b><br>Custo: R$ %{y:,.2f}<extra></extra>'
    ))
    
    # Adicionar barras para outros tipos
    for tipo in ['Cam', 'Toco', 'Truck']:
        tipo_lower = tipo.lower()
        tipo_data = custo_df[custo_df['Tipo Veículo'].str.strip() == tipo]
        fig.add_trace(go.Bar(
            x=tipo_data['Mês'],
            y=tipo_data['Custo'],
            name=tipo,
            marker_color=cores_veiculo[tipo_lower],
            text=[f'R$ {v:,.0f}' for v in tipo_data['Custo']],
            textposition='outside',
            hovertemplate=f'<b>%{{x}} - {tipo}</b><br>Custo: R$ %{{y:,.2f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title="Custo Total por Tipo de Veículo (Todos os Meses)",
        xaxis_title="Mês",
        yaxis_title="Custo (R$)",
        barmode='group',
        showlegend=True,
        hovermode='x unified',
        xaxis={'tickangle': -45},
        height=500,
        xaxis_type='category'
    )
    
    # Adicionar retângulo destacando fevereiro 2021
    meses_list = sorted(custo_df['Mês'].unique())
    if '2021-02' in meses_list:
        idx_fev = meses_list.index('2021-02')
        fig.add_vrect(
            x0=idx_fev - 0.4,
            x1=idx_fev + 0.4,
            fillcolor='orange',
            opacity=0.1,
            line_width=2,
            line_color='orange',
            line_dash='dash'
        )
    
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Erro Q7: {e}")

st.markdown("---")

# ==================== PERGUNTA 8 ====================
st.header("8️⃣ Veículos em SP - Quantidade por Mês")
try:
    df_q8 = dados_frete.merge(dados_cadastrais[['IDCliente', 'UF']], on='IDCliente', how='left')
    
    # Criar coluna de mês
    df_q8['YearMonth'] = df_q8['Data'].dt.strftime('%Y-%m')
    
    # Agrupar por mês e contar veículos únicos de SP
    veiculos_por_mes = df_q8[df_q8['UF'] == 'SP'].groupby('YearMonth')['IDVeiculo'].nunique().reset_index()
    veiculos_por_mes.columns = ['Mês', 'Quantidade Veículos']
    
    # Criar gráfico de barras
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=veiculos_por_mes['Mês'],
        y=veiculos_por_mes['Quantidade Veículos'],
        marker_color='steelblue',
        text=[f'{int(v)}' for v in veiculos_por_mes['Quantidade Veículos']],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Veículos: %{y:.0f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Quantidade de Veículos Utilizados em Entregas para SP por Mês",
        xaxis_title="Mês",
        yaxis_title="Quantidade de Veículos",
        showlegend=False,
        hovermode='x unified',
        xaxis={'tickangle': -45},
        height=400,
        xaxis_type='category'
    )
    
    # Destacar julho de 2021
    meses_list = list(veiculos_por_mes['Mês'].unique())
    if '2021-07' in meses_list:
        idx_jul = meses_list.index('2021-07')
        fig.add_vrect(
            x0=idx_jul - 0.4,
            x1=idx_jul + 0.4,
            fillcolor='red',
            opacity=0.15,
            line_width=2,
            line_color='red',
            line_dash='dash'
        )
    
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Erro Q8: {e}")

st.markdown("---")

# ==================== PERGUNTA 9 ====================
st.header("9️⃣ Despesas por Tipo de Veículo - Todos os Trimestres")
try:
    df_q9 = dados_completos.copy()
    df_q9_merge = df_q9.merge(dados_cadastrais[['IDVeiculo', 'Tipo Veículo']], on='IDVeiculo', how='left')
    
    # Criar coluna de trimestre
    df_q9_merge['Trimestre'] = df_q9_merge['Data'].dt.to_period('Q')
    
    # Agrupar por trimestre e tipo de veículo
    despesa_por_tri_tipo = df_q9_merge.groupby(['Trimestre', 'Tipo Veículo'])['Despesa Total'].sum()
    
    # Converter para DataFrame
    despesa_df = despesa_por_tri_tipo.reset_index()
    despesa_df.columns = ['Trimestre', 'Tipo Veículo', 'Despesa']
    despesa_df['Trimestre'] = despesa_df['Trimestre'].astype(str)
    
    # Criar figura com plotly graph_objects
    fig = go.Figure()
    
    # Definir cores para cada tipo de veículo
    cores_veiculo = {
        'cavalo': 'red',
        'cam': 'steelblue',
        'toco': 'green',
        'truck': 'navy'
    }
    
    # Adicionar barras para Cavalo
    cavalo_data = despesa_df[despesa_df['Tipo Veículo'].str.strip().str.lower() == 'cavalo']
    fig.add_trace(go.Bar(
        x=cavalo_data['Trimestre'],
        y=cavalo_data['Despesa'],
        name='Cavalo',
        marker_color=cores_veiculo['cavalo'],
        text=[f'R$ {v:,.0f}' for v in cavalo_data['Despesa']],
        textposition='outside',
        hovertemplate='<b>%{x} - Cavalo</b><br>Despesa: R$ %{y:,.2f}<extra></extra>'
    ))
    
    # Adicionar barras para outros tipos
    for tipo in ['Cam', 'Toco', 'Truck']:
        tipo_lower = tipo.lower()
        tipo_data = despesa_df[despesa_df['Tipo Veículo'].str.strip() == tipo]
        fig.add_trace(go.Bar(
            x=tipo_data['Trimestre'],
            y=tipo_data['Despesa'],
            name=tipo,
            marker_color=cores_veiculo[tipo_lower],
            text=[f'R$ {v:,.0f}' for v in tipo_data['Despesa']],
            textposition='outside',
            hovertemplate=f'<b>%{{x}} - {tipo}</b><br>Despesa: R$ %{{y:,.2f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title="Despesas Totais por Tipo de Veículo (Todos os Trimestres)",
        xaxis_title="Trimestre",
        yaxis_title="Despesa (R$)",
        barmode='group',
        showlegend=True,
        hovermode='x unified',
        xaxis={'tickangle': -45},
        height=500,
        xaxis_type='category'
    )
    
    # Destacar Q1 2021
    trimestres_list = sorted(despesa_df['Trimestre'].unique())
    if '2021Q1' in trimestres_list:
        idx_q1_2021 = trimestres_list.index('2021Q1')
        fig.add_vrect(
            x0=idx_q1_2021 - 0.4,
            x1=idx_q1_2021 + 0.4,
            fillcolor='orange',
            opacity=0.1,
            line_width=2,
            line_color='orange',
            line_dash='dash'
        )
    
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Erro Q9: {e}")

st.markdown("---")

# ==================== PERGUNTA 10 ====================
st.header("🔟 Resultado Líquido - H1 2020")
try:
    df_q10_fatura = dados_frete[dados_frete['Data'].dt.year == 2020].copy()
    df_q10_fatura = df_q10_fatura[df_q10_fatura['Data'].dt.month <= 6]
    
    df_q10_custo = dados_completos[dados_completos['Data'].dt.year == 2020].copy()
    df_q10_custo = df_q10_custo[df_q10_custo['Data'].dt.month <= 6]
    
    receita_h1_2020 = df_q10_fatura['Frete'].sum()
    despesa_h1_2020 = df_q10_custo['Despesa Total'].sum()
    resultado_liquido = receita_h1_2020 - despesa_h1_2020
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Receita", f"R$ {receita_h1_2020:,.2f}")
    with col2:
        st.metric("Despesa", f"R$ {despesa_h1_2020:,.2f}")
    with col3:
        st.metric("Resultado Líquido", f"R$ {resultado_liquido:,.2f}")
except Exception as e:
    st.error(f"Erro Q10: {e}")

st.markdown("---")

# ==================== PERGUNTA 11 ====================
st.header("1️⃣1️⃣ Maior Quantidade de Entregas - Q2 2021")
try:
    df_q11 = dados_frete.copy()
    df_q2_2021 = df_q11[
        (df_q11['Data'].dt.year == 2021) & 
        (df_q11['Data'].dt.month.isin([4, 5, 6]))
    ]
    
    entregas_veiculo = df_q2_2021['IDVeiculo'].value_counts()
    
    if len(entregas_veiculo) > 0:
        veiculo_maior = entregas_veiculo.index[0]
        qtd_maior = entregas_veiculo.iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Veículo", veiculo_maior)
        with col2:
            st.metric("Entregas", qtd_maior)
        
        fig = px.bar(entregas_veiculo.head(10), title="Top 10 Veículos - Entregas Q2 2021",
                     labels={'value': 'Entregas', 'index': 'ID Veículo'})
        st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Erro Q11: {e}")

st.markdown("---")

# ==================== PERGUNTA 12 ====================
st.header("1️⃣2️⃣ Variação Mensal Receita - Março para Abril 2021")
try:
    df_q12 = dados_frete.copy()
    
    receita_marco_2021 = df_q12[
        (df_q12['Data'].dt.year == 2021) & 
        (df_q12['Data'].dt.month == 3)
    ]['Frete'].sum()
    
    receita_abril_2021 = df_q12[
        (df_q12['Data'].dt.year == 2021) & 
        (df_q12['Data'].dt.month == 4)
    ]['Frete'].sum()
    
    variacao_marco_abril = ((receita_abril_2021 - receita_marco_2021) / receita_marco_2021 * 100) if receita_marco_2021 > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Março 2021", f"R$ {receita_marco_2021:,.2f}")
    with col2:
        st.metric("Abril 2021", f"R$ {receita_abril_2021:,.2f}")
    with col3:
        st.metric("Variação", f"{variacao_marco_abril:.2f}%", delta_color="inverse")
except Exception as e:
    st.error(f"Erro Q12: {e}")

st.markdown("---")

# ==================== PERGUNTA 13 ====================
st.header("1️⃣3️⃣ Ticket Médio por Veículo - Q1 2021")
try:
    df_q13 = dados_frete.copy()
    
    df_q1_2021 = df_q13[
        (df_q13['Data'].dt.year == 2021) & 
        (df_q13['Data'].dt.month.isin([1, 2, 3]))
    ]
    
    ticket_medio = df_q1_2021.groupby('IDVeiculo').agg({
        'Frete': 'sum',
        'IDCliente': 'count'
    }).rename(columns={'IDCliente': 'Entregas'})
    
    ticket_medio['TicketMedio'] = ticket_medio['Frete'] / ticket_medio['Entregas']
    ticket_medio = ticket_medio.sort_values('TicketMedio', ascending=False)
    
    st.write("**Top 10 Veículos - Ticket Médio Q1 2021**")
    st.dataframe(ticket_medio.head(10), use_container_width=True)
    
    fig = px.bar(ticket_medio.head(10)['TicketMedio'], 
                 title="Top 10 Veículos por Ticket Médio - Q1 2021",
                 labels={'value': 'Ticket Médio (R$)', 'index': 'ID Veículo'})
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error(f"Erro Q13: {e}")

st.markdown("---")
st.markdown("✅ Dashboard Atualizado com Sucesso!") 