"""
Módulo para processamento de dados e cálculo de métricas
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import Counter


class DataProcessor:
    """Classe para processar dados do Trello e calcular métricas"""
    
    def __init__(self, trello_data: Dict):
        """
        Inicializa o processador com dados do Trello
        
        Args:
            trello_data: Dicionário com dados do board retornado por TrelloAPI
        """
        self.board = trello_data['board']
        self.lists = trello_data['lists']
        self.members = trello_data['members']
        self.cards = trello_data['cards']
        self.labels = trello_data['labels']
        
        # Cria dicionários de lookup
        self.lists_dict = {lst['id']: lst['name'] for lst in self.lists}
        self.members_dict = {member['id']: member['fullName'] for member in self.members}
        
        # Converte cards para DataFrame
        self.df_cards = self._create_cards_dataframe()
    
    def _create_cards_dataframe(self) -> pd.DataFrame:
        """
        Cria um DataFrame pandas com informações dos cards
        
        Returns:
            DataFrame com informações processadas dos cards
        """
        cards_data = []
        
        for card in self.cards:
            # Ignora cards arquivados (caso ainda venham da API)
            if card.get('closed', False):
                continue
            # Extrai data de criação das ações
            created_date = None
            completed_date = None
            
            # Nome da lista atual
            list_name = self.lists_dict.get(card.get('idList'), 'Desconhecida')
            
            if card.get('actions'):
                # Ordena ações por data
                sorted_actions = sorted(card['actions'], key=lambda x: x['date'])
                
                # Encontra data de criação
                for action in sorted_actions:
                    if action['type'] == 'createCard':
                        created_date = datetime.fromisoformat(action['date'].replace('Z', '+00:00'))
                        break
            
            # Se não encontrou data de criação nas ações, usa dateLastActivity
            if not created_date and card.get('dateLastActivity'):
                created_date = datetime.fromisoformat(card['dateLastActivity'].replace('Z', '+00:00'))
            
            # Verifica se o card está na lista "Concluído" (case-insensitive e com trim)
            if list_name.strip().lower() == 'concluído':
                if card.get('actions'):
                    sorted_actions = sorted(card['actions'], key=lambda x: x['date'])
                    # Encontra quando foi movido para a lista "Concluído"
                    for action in reversed(sorted_actions):
                        if action['type'] == 'updateCard' and 'listAfter' in action.get('data', {}):
                            action_list_name = action['data']['listAfter']['name'].strip().lower()
                            if action_list_name == 'concluído':
                                completed_date = datetime.fromisoformat(action['date'].replace('Z', '+00:00'))
                                break
                
                # Se não encontrou nas ações mas está na lista "Concluído", usa dateLastActivity como fallback
                if not completed_date and card.get('dateLastActivity'):
                    completed_date = datetime.fromisoformat(card['dateLastActivity'].replace('Z', '+00:00'))
            
            # Informações sobre deadline
            due_date = None
            is_overdue = False
            if card.get('due'):
                due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
                is_overdue = not card.get('dueComplete', False) and due_date < datetime.now(due_date.tzinfo)
            
            # Membros responsáveis
            member_names = [self.members_dict.get(mid, 'Desconhecido') for mid in card.get('idMembers', [])]
            
            # Labels
            label_names = [label['name'] for label in card.get('labels', []) if label.get('name')]
            
            # Calcula tempo de conclusão
            completion_time_days = None
            if created_date and completed_date:
                completion_time_days = (completed_date - created_date).total_seconds() / 86400
            
            cards_data.append({
                'id': card['id'],
                'name': card['name'],
                'list': list_name,
                'created_date': created_date,
                'completed_date': completed_date,
                'due_date': due_date,
                'is_overdue': is_overdue,
                'is_closed': card.get('closed', False),
                'members': member_names,
                'member_count': len(member_names),
                'labels': label_names,
                'label_count': len(label_names),
                'completion_time_days': completion_time_days
            })
        
        return pd.DataFrame(cards_data)
    
    def filter_by_date_range(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Filtra cards por período
        
        Args:
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            DataFrame filtrado
        """
        df = self.df_cards.copy()
        
        # Converte datas para timezone-aware (UTC) se necessário
        if start_date.tzinfo is None:
            import pytz
            start_date = pytz.UTC.localize(start_date)
        if end_date.tzinfo is None:
            import pytz
            end_date = pytz.UTC.localize(end_date)
        
        # Filtra cards criados no período
        mask = (df['created_date'] >= start_date) & (df['created_date'] <= end_date)
        
        return df[mask]
    
    def get_cards_created_count(self, start_date: datetime, end_date: datetime) -> int:
        """
        Conta cards criados no período
        
        Args:
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            Número de cards criados
        """
        df_filtered = self.filter_by_date_range(start_date, end_date)
        return len(df_filtered)
    
    def get_cards_completed_count(self, start_date: datetime, end_date: datetime) -> int:
        """
        Conta cards concluídos no período
        
        Args:
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            Número de cards concluídos
        """
        import pytz
        df = self.df_cards.copy()
        
        # Converte datas para timezone-aware (UTC) se necessário
        if start_date.tzinfo is None:
            start_date = pytz.UTC.localize(start_date)
        if end_date.tzinfo is None:
            end_date = pytz.UTC.localize(end_date)
        
        mask = (df['completed_date'] >= start_date) & (df['completed_date'] <= end_date)
        return len(df[mask])
    
    def get_cards_in_progress_count(self) -> int:
        """
        Conta cards atualmente em andamento (na lista "Fazendo")
        
        Returns:
            Número de cards em andamento
        """
        df = self.df_cards.copy()
        # Cards na lista "Fazendo"
        mask = df['list'].str.strip().str.lower() == 'fazendo'
        return len(df[mask])
    
    def get_overdue_cards(self) -> pd.DataFrame:
        """
        Retorna cards atrasados
        
        Returns:
            DataFrame com cards atrasados
        """
        df = self.df_cards.copy()
        return df[df['is_overdue']].sort_values('due_date')
    
    def get_cards_by_member(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Agrupa cards por membro no período
        
        Args:
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            DataFrame com contagem por membro
        """
        df_filtered = self.filter_by_date_range(start_date, end_date)
        
        # Expande lista de membros
        member_cards = []
        for _, row in df_filtered.iterrows():
            if row['members']:
                for member in row['members']:
                    member_cards.append({
                        'member': member,
                        'created': 1,
                        'completed': 1 if pd.notna(row['completed_date']) else 0
                    })
            else:
                member_cards.append({
                    'member': 'Sem atribuição',
                    'created': 1,
                    'completed': 1 if pd.notna(row['completed_date']) else 0
                })
        
        if not member_cards:
            return pd.DataFrame(columns=['member', 'created', 'completed'])
        
        df_members = pd.DataFrame(member_cards)
        return df_members.groupby('member').sum().reset_index().sort_values('created', ascending=False)
    
    def get_cards_by_label(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Agrupa cards por label no período
        
        Args:
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            DataFrame com contagem por label
        """
        df_filtered = self.filter_by_date_range(start_date, end_date)
        
        # Expande lista de labels
        label_cards = []
        for _, row in df_filtered.iterrows():
            if row['labels']:
                for label in row['labels']:
                    label_cards.append(label)
            else:
                label_cards.append('Sem label')
        
        if not label_cards:
            return pd.DataFrame(columns=['label', 'count'])
        
        label_counts = Counter(label_cards)
        df_labels = pd.DataFrame.from_dict(label_counts, orient='index', columns=['count'])
        df_labels['label'] = df_labels.index
        return df_labels.reset_index(drop=True).sort_values('count', ascending=False)
    
    def get_average_completion_time(self, start_date: datetime, end_date: datetime) -> float:
        """
        Calcula tempo médio de conclusão de cards (em dias)
        
        Args:
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            Tempo médio em dias
        """
        import pytz
        df = self.df_cards.copy()
        
        # Converte datas para timezone-aware (UTC) se necessário
        if start_date.tzinfo is None:
            start_date = pytz.UTC.localize(start_date)
        if end_date.tzinfo is None:
            end_date = pytz.UTC.localize(end_date)
        
        mask = (df['completed_date'] >= start_date) & (df['completed_date'] <= end_date)
        df_completed = df[mask]
        
        if len(df_completed) == 0:
            return 0.0
        
        return df_completed['completion_time_days'].mean()
    
    def get_cards_timeline(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Cria timeline de cards criados e concluídos por dia
        
        Args:
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            DataFrame com contagens diárias
        """
        import pytz
        df = self.df_cards.copy()
        
        # Converte datas para timezone-aware (UTC) se necessário
        if start_date.tzinfo is None:
            start_date = pytz.UTC.localize(start_date)
        if end_date.tzinfo is None:
            end_date = pytz.UTC.localize(end_date)
        
        # Cria range de datas
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        timeline = pd.DataFrame({'date': date_range, 'created': 0, 'completed': 0})
        
        # Conta cards criados por dia
        df_created = df[df['created_date'].notna()].copy()
        if len(df_created) > 0:
            # Garante que a coluna é datetime antes de usar .dt
            df_created['created_date'] = pd.to_datetime(df_created['created_date'])
            df_created['date'] = df_created['created_date'].dt.date
            created_counts = df_created.groupby('date').size()
        else:
            created_counts = pd.Series(dtype=int)
        
        # Conta cards concluídos por dia
        df_completed = df[df['completed_date'].notna()].copy()
        if len(df_completed) > 0:
            # Garante que a coluna é datetime antes de usar .dt
            df_completed['completed_date'] = pd.to_datetime(df_completed['completed_date'])
            df_completed['date'] = df_completed['completed_date'].dt.date
            completed_counts = df_completed.groupby('date').size()
        else:
            completed_counts = pd.Series(dtype=int)
        
        # Preenche timeline
        for date in timeline['date']:
            date_obj = date.date()
            if date_obj in created_counts.index:
                timeline.loc[timeline['date'] == date, 'created'] = created_counts[date_obj]
            if date_obj in completed_counts.index:
                timeline.loc[timeline['date'] == date, 'completed'] = completed_counts[date_obj]
        
        return timeline
    
    def get_productivity_ranking(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Cria ranking de produtividade dos membros
        
        Args:
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            DataFrame com ranking de produtividade
        """
        df_members = self.get_cards_by_member(start_date, end_date)
        
        if len(df_members) == 0:
            return pd.DataFrame(columns=['member', 'created', 'completed', 'completion_rate'])
        
        # Calcula taxa de conclusão
        df_members['completion_rate'] = (df_members['completed'] / df_members['created'] * 100).round(1)
        
        # Ordena por cards concluídos
        return df_members.sort_values('completed', ascending=False)

