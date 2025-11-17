"""
Dashboard de Estatísticas do Trello
Aplicação Streamlit para visualizar métricas da equipe
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

from config import Config
from trello_api import TrelloAPI
from data_processor import DataProcessor


# Configuração da página
st.set_page_config(
    page_title="Dashboard Trello",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


def show_config_page():
    """Exibe página de configuração quando credenciais não estão definidas"""
    st.title("⚙️ Configuração Necessária")
    st.warning("As credenciais da API do Trello não foram configuradas.")
    
    st.markdown("""
    ### Como configurar:
    
    1. **Obter API Key:**
       - Acesse: https://trello.com/power-ups/admin
       - Clique em "New" para criar um novo Power-Up
       - Copie a **API Key** gerada
    
    2. **Obter Token:**
       - Na mesma página, clique em "Token" 
       - Autorize o acesso
       - Copie o **Token** gerado
    
    3. **Obter Board ID:**
       - Abra seu board no Trello
       - Na URL, copie o ID que aparece após `/b/`: 
       - Exemplo: `https://trello.com/b/ABC123XYZ/nome-board` → ID é `ABC123XYZ`
    
    4. **Configurar o arquivo `.env`:**
       - Crie um arquivo chamado `.env` na raiz do projeto
       - Adicione as seguintes linhas:
       ```
       TRELLO_API_KEY=sua_api_key_aqui
       TRELLO_TOKEN=seu_token_aqui
       TRELLO_BOARD_ID=id_do_board_aqui
       ```
    
    5. **Reinicie a aplicação**
    """)
    
    st.info("📖 Consulte o arquivo README.md para instruções detalhadas.")


@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_trello_data():
    """Carrega dados do Trello com cache"""
    try:
        api = TrelloAPI()
        data = api.get_all_board_data()
        return data, None
    except Exception as e:
        return None, str(e)


def format_number(num):
    """Formata número para exibição"""
    return f"{num:,}".replace(",", ".")


def main():
    """Função principal do dashboard"""
    
    # Verifica se está configurado
    if not Config.is_configured():
        show_config_page()
        return
    
    # Sidebar
    st.sidebar.title("📊 Dashboard Trello")
    st.sidebar.markdown("---")
    
    # Carrega dados
    with st.spinner("Carregando dados do Trello..."):
        trello_data, error = load_trello_data()
    
    if error:
        st.error(f"❌ Erro ao carregar dados: {error}")
        st.info("Verifique suas credenciais no arquivo `.env`")
        return
    
    if not trello_data:
        st.error("❌ Não foi possível carregar os dados do Trello")
        return
    
    # Inicializa processador
    processor = DataProcessor(trello_data)
    
    # Informações do board
    st.sidebar.success(f"✅ Board: **{trello_data['board']['name']}**")
    st.sidebar.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Filtros na sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Filtros")
    
    # Seletor de período
    period_option = st.sidebar.selectbox(
        "Período:",
        ["Último mês", "Últimos 3 meses", "Últimos 6 meses", "Último ano", "Personalizado"]
    )
    
    if period_option == "Personalizado":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("De:", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Até:", datetime.now())
    else:
        days_map = {
            "Último mês": 30,
            "Últimos 3 meses": 90,
            "Últimos 6 meses": 180,
            "Último ano": 365
        }
        days = days_map[period_option]
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()
    
    # Converte para datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Botão para atualizar
    if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Título principal
    st.title(f"📊 Dashboard de Estatísticas - {trello_data['board']['name']}")
    st.markdown(f"**Período:** {start_date.strftime('%d/%m/%Y')} até {end_date.strftime('%d/%m/%Y')}")
    st.markdown("---")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    cards_created = processor.get_cards_created_count(start_datetime, end_datetime)
    cards_completed = processor.get_cards_completed_count(start_datetime, end_datetime)
    cards_in_progress = processor.get_cards_in_progress_count()
    overdue_cards = len(processor.get_overdue_cards())
    
    with col1:
        st.metric(
            label="📝 Cards Criados",
            value=format_number(cards_created)
        )
    
    with col2:
        st.metric(
            label="✅ Cards Concluídos",
            value=format_number(cards_completed)
        )
    
    with col3:
        st.metric(
            label="🔄 Em Andamento",
            value=format_number(cards_in_progress)
        )
    
    with col4:
        st.metric(
            label="⚠️ Atrasados",
            value=format_number(overdue_cards),
            delta=None if overdue_cards == 0 else f"-{overdue_cards}",
            delta_color="inverse"
        )
    
    st.markdown("---")
    
    # Gráficos
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Evolução Temporal", 
        "👥 Por Membro", 
        "🏷️ Por Label",
        "📋 Detalhes"
    ])
    
    # TAB 1: Evolução Temporal
    with tab1:
        st.subheader("📈 Evolução de Cards ao Longo do Tempo")
        
        timeline = processor.get_cards_timeline(start_datetime, end_datetime)
        
        if len(timeline) > 0:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=timeline['date'],
                y=timeline['created'],
                mode='lines+markers',
                name='Criados',
                line=dict(color='#3498db', width=2),
                marker=dict(size=6)
            ))
            
            fig.add_trace(go.Scatter(
                x=timeline['date'],
                y=timeline['completed'],
                mode='lines+markers',
                name='Concluídos',
                line=dict(color='#2ecc71', width=2),
                marker=dict(size=6)
            ))
            
            fig.update_layout(
                xaxis_title="Data",
                yaxis_title="Quantidade de Cards",
                hovermode='x unified',
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado disponível para o período selecionado.")
        
        # Métricas adicionais
        col1, col2 = st.columns(2)
        
        with col1:
            avg_completion_time = processor.get_average_completion_time(start_datetime, end_datetime)
            st.metric(
                label="⏱️ Tempo Médio de Conclusão",
                value=f"{avg_completion_time:.1f} dias" if avg_completion_time > 0 else "N/A"
            )
        
        with col2:
            if cards_created > 0:
                completion_rate = (cards_completed / cards_created) * 100
                st.metric(
                    label="📊 Taxa de Conclusão",
                    value=f"{completion_rate:.1f}%"
                )
            else:
                st.metric(label="📊 Taxa de Conclusão", value="N/A")
    
    # TAB 2: Por Membro
    with tab2:
        st.subheader("👥 Distribuição por Membro da Equipe")
        
        df_members = processor.get_cards_by_member(start_datetime, end_datetime)
        
        if len(df_members) > 0:
            # Gráfico de barras
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=df_members['member'],
                y=df_members['created'],
                name='Criados',
                marker_color='#3498db'
            ))
            
            fig.add_trace(go.Bar(
                x=df_members['member'],
                y=df_members['completed'],
                name='Concluídos',
                marker_color='#2ecc71'
            ))
            
            fig.update_layout(
                xaxis_title="Membro",
                yaxis_title="Quantidade de Cards",
                barmode='group',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Ranking de produtividade
            st.subheader("🏆 Ranking de Produtividade")
            ranking = processor.get_productivity_ranking(start_datetime, end_datetime)
            
            if len(ranking) > 0:
                # Formata DataFrame para exibição
                ranking_display = ranking.copy()
                ranking_display.columns = ['Membro', 'Criados', 'Concluídos', 'Taxa de Conclusão (%)']
                ranking_display.index = range(1, len(ranking_display) + 1)
                
                st.dataframe(
                    ranking_display,
                    use_container_width=True,
                    height=min(400, (len(ranking_display) + 1) * 35 + 3)
                )
        else:
            st.info("Nenhum dado disponível para o período selecionado.")
    
    # TAB 3: Por Label
    with tab3:
        st.subheader("🏷️ Distribuição por Labels")
        
        df_labels = processor.get_cards_by_label(start_datetime, end_datetime)
        
        if len(df_labels) > 0:
            # Gráfico de pizza
            fig = px.pie(
                df_labels,
                values='count',
                names='label',
                title='Cards por Label',
                height=400
            )
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela com detalhes
            st.subheader("📊 Detalhes por Label")
            labels_display = df_labels.copy()
            labels_display.columns = ['Quantidade', 'Label']
            labels_display = labels_display[['Label', 'Quantidade']]
            
            st.dataframe(
                labels_display,
                use_container_width=True,
                height=min(400, (len(labels_display) + 1) * 35 + 3)
            )
        else:
            st.info("Nenhum dado disponível para o período selecionado.")
    
    # TAB 4: Detalhes
    with tab4:
        st.subheader("📋 Informações Detalhadas")
        
        # Cards atrasados
        st.markdown("### ⚠️ Cards Atrasados")
        df_overdue = processor.get_overdue_cards()
        
        if len(df_overdue) > 0:
            overdue_display = df_overdue[['name', 'due_date', 'members', 'list']].copy()
            overdue_display['due_date'] = overdue_display['due_date'].dt.strftime('%d/%m/%Y')
            overdue_display['members'] = overdue_display['members'].apply(
                lambda x: ', '.join(x) if x else 'Sem atribuição'
            )
            overdue_display.columns = ['Card', 'Data Limite', 'Responsáveis', 'Lista']
            
            st.dataframe(
                overdue_display,
                use_container_width=True,
                height=min(400, (len(overdue_display) + 1) * 35 + 3)
            )
        else:
            st.success("✅ Não há cards atrasados!")
        
        st.markdown("---")
        
        # Estatísticas gerais
        st.markdown("### 📊 Estatísticas Gerais")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total de Listas", format_number(len(processor.lists)))
            st.metric("Total de Membros", format_number(len(processor.members)))
        
        with col2:
            st.metric("Total de Cards", format_number(len(processor.df_cards)))
            st.metric("Total de Labels", format_number(len(processor.labels)))


if __name__ == "__main__":
    main()

