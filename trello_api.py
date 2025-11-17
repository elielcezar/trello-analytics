"""
Módulo para integração com a API do Trello
"""
import requests
from datetime import datetime
from typing import List, Dict, Optional
from config import Config


class TrelloAPI:
    """Classe para interagir com a API do Trello"""
    
    def __init__(self):
        self.base_url = Config.TRELLO_API_BASE_URL
        self.auth_params = Config.get_auth_params()
        self.board_id = Config.TRELLO_BOARD_ID
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Faz uma requisição à API do Trello
        
        Args:
            endpoint: Endpoint da API (ex: '/boards/123/cards')
            params: Parâmetros adicionais da requisição
        
        Returns:
            Resposta da API em formato JSON
        """
        url = f"{self.base_url}{endpoint}"
        
        # Combina parâmetros de autenticação com parâmetros adicionais
        request_params = {**self.auth_params}
        if params:
            request_params.update(params)
        
        try:
            response = requests.get(url, params=request_params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro ao fazer requisição para {url}: {str(e)}")
    
    def get_board_info(self) -> Dict:
        """
        Obtém informações sobre o board
        
        Returns:
            Dicionário com informações do board
        """
        endpoint = f"/boards/{self.board_id}"
        params = {'fields': 'name,desc,url'}
        return self._make_request(endpoint, params)
    
    def get_lists(self) -> List[Dict]:
        """
        Obtém todas as listas do board
        
        Returns:
            Lista de dicionários com informações das listas
        """
        endpoint = f"/boards/{self.board_id}/lists"
        params = {'fields': 'name,closed,pos'}
        return self._make_request(endpoint, params)
    
    def get_members(self) -> List[Dict]:
        """
        Obtém todos os membros do board
        
        Returns:
            Lista de dicionários com informações dos membros
        """
        endpoint = f"/boards/{self.board_id}/members"
        params = {'fields': 'fullName,username,avatarUrl'}
        return self._make_request(endpoint, params)
    
    def get_cards(self, include_closed: bool = False) -> List[Dict]:
        """
        Obtém todos os cards do board
        
        Args:
            include_closed: Se True, inclui cards arquivados
        
        Returns:
            Lista de dicionários com informações dos cards
        """
        endpoint = f"/boards/{self.board_id}/cards"
        params = {
            'fields': 'name,desc,due,dueComplete,idList,idMembers,labels,dateLastActivity,closed',
            'members': 'true',
            'member_fields': 'fullName,username'
        }
        
        if include_closed:
            params['filter'] = 'all'
        else:
            params['filter'] = 'open'
        
        return self._make_request(endpoint, params)
    
    def get_card_actions(self, card_id: str) -> List[Dict]:
        """
        Obtém o histórico de ações de um card específico
        
        Args:
            card_id: ID do card
        
        Returns:
            Lista de ações do card
        """
        endpoint = f"/cards/{card_id}/actions"
        params = {
            'filter': 'createCard,updateCard:idList,updateCard:closed',
            'fields': 'type,date,data',
            'member': 'true',
            'member_fields': 'fullName,username'
        }
        return self._make_request(endpoint, params)
    
    def get_labels(self) -> List[Dict]:
        """
        Obtém todos os labels do board
        
        Returns:
            Lista de dicionários com informações dos labels
        """
        endpoint = f"/boards/{self.board_id}/labels"
        params = {'fields': 'name,color'}
        return self._make_request(endpoint, params)
    
    def get_all_board_data(self) -> Dict:
        """
        Obtém todos os dados relevantes do board em uma única chamada
        
        Returns:
            Dicionário com todos os dados do board
        """
        board_info = self.get_board_info()
        lists = self.get_lists()
        members = self.get_members()
        cards = self.get_cards(include_closed=False)  # Apenas cards ativos (não arquivados)
        labels = self.get_labels()
        
        # Para cada card, obtém as ações (histórico)
        for card in cards:
            try:
                card['actions'] = self.get_card_actions(card['id'])
            except Exception as e:
                print(f"Aviso: Não foi possível obter ações do card {card['id']}: {str(e)}")
                card['actions'] = []
        
        return {
            'board': board_info,
            'lists': lists,
            'members': members,
            'cards': cards,
            'labels': labels,
            'fetched_at': datetime.now().isoformat()
        }
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Testa a conexão com a API do Trello
        
        Returns:
            Tupla (sucesso, mensagem)
        """
        try:
            board_info = self.get_board_info()
            return True, f"Conexão bem-sucedida! Board: {board_info['name']}"
        except Exception as e:
            return False, f"Erro na conexão: {str(e)}"

