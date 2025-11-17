"""
Gerenciamento de configurações e credenciais do Trello
"""
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    """Classe para gerenciar configurações da aplicação"""
    
    # Credenciais da API do Trello
    TRELLO_API_KEY = os.getenv('TRELLO_API_KEY', '06bde20d213e62b76dfc16aadc659311')
    TRELLO_TOKEN = os.getenv('TRELLO_TOKEN', 'ATTA7330848c309774820f07011274959360731a4993b8692979965382904')
    TRELLO_BOARD_ID = os.getenv('TRELLO_BOARD_ID', 'pOy2Ba0G')
    
    # URL base da API do Trello
    TRELLO_API_BASE_URL = 'https://api.trello.com/1'
    
    @staticmethod
    def is_configured():
        """Verifica se as credenciais necessárias estão configuradas"""
        return all([
            Config.TRELLO_API_KEY,
            Config.TRELLO_TOKEN,
            Config.TRELLO_BOARD_ID
        ])
    
    @staticmethod
    def get_auth_params():
        """Retorna os parâmetros de autenticação para requisições"""
        return {
            'key': Config.TRELLO_API_KEY,
            'token': Config.TRELLO_TOKEN
        }

