"""
Módulo de Integração Evolution API - Active Educacional
Permite enviar mensagens via WhatsApp através do Evolution API
"""

import requests
import json
from typing import Optional, Dict, List


class EvolutionAPI:
    """Cliente para interagir com o Evolution API"""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Inicializa o cliente Evolution API
        
        Args:
            base_url: URL base do Evolution API (ex: https://evolution-api.up.railway.app)
            api_key: Chave de autenticação da API
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "apikey": api_key,
            "Content-Type": "application/json"
        }
    
    def create_instance(self, instance_name: str) -> Dict:
        """
        Cria uma nova instância do WhatsApp
        
        Args:
            instance_name: Nome da instância (ex: "active_educacional")
            
        Returns:
            Dicionário com os dados da instância criada
        """
        url = f"{self.base_url}/instance/create"
        payload = {
            "instanceName": instance_name,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_qrcode(self, instance_name: str) -> Dict:
        """
        Obtém o QR code de uma instância
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            Dicionário com o QR code em base64
        """
        url = f"{self.base_url}/instance/connect/{instance_name}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_instance_status(self, instance_name: str) -> Dict:
        """
        Verifica o status de conexão de uma instância
        
        Args:
            instance_name: Nome da instância
            
        Returns:
            Dicionário com o status da instância
        """
        url = f"{self.base_url}/instance/connectionState/{instance_name}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def send_text_message(self, instance_name: str, number: str, message: str) -> Dict:
        """
        Envia uma mensagem de texto via WhatsApp
        
        Args:
            instance_name: Nome da instância conectada
            number: Número do destinatário (formato: 5511999999999)
            message: Texto da mensagem
            
        Returns:
            Dicionário com a resposta do envio
        """
        url = f"{self.base_url}/message/sendText/{instance_name}"
        payload = {
            "number": number,
            "text": message
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def send_message_to_group(self, instance_name: str, group_id: str, message: str) -> Dict:
        """
        Envia mensagem para um grupo do WhatsApp
        
        Args:
            instance_name: Nome da instância conectada
            group_id: ID do grupo
            message: Texto da mensagem
            
        Returns:
            Dicionário com a resposta do envio
        """
        url = f"{self.base_url}/message/sendText/{instance_name}"
        payload = {
            "number": group_id,
            "text": message
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def send_bulk_messages(self, instance_name: str, contacts: List[Dict[str, str]]) -> List[Dict]:
        """
        Envia mensagens em massa
        
        Args:
            instance_name: Nome da instância conectada
            contacts: Lista de dicionários com 'number' e 'message'
                     Ex: [{"number": "5511999999999", "message": "Olá!"}]
            
        Returns:
            Lista com as respostas de cada envio
        """
        results = []
        for contact in contacts:
            try:
                result = self.send_text_message(
                    instance_name,
                    contact["number"],
                    contact["message"]
                )
                results.append({
                    "number": contact["number"],
                    "status": "success",
                    "response": result
                })
            except Exception as e:
                results.append({
                    "number": contact["number"],
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    def list_instances(self) -> List[Dict]:
        """
        Lista todas as instâncias criadas
        
        Returns:
            Lista de instâncias
        """
        url = f"{self.base_url}/instance/fetchInstances"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()


# Configuração padrão para o projeto Active Educacional
EVOLUTION_CONFIG = {
    "base_url": "https://evolution-api.up.railway.app",
    "api_key": "Active2024SecureKey!@#",
    "instance_name": "active_educacional"
}


def get_evolution_client() -> EvolutionAPI:
    """
    Retorna uma instância configurada do cliente Evolution API
    
    Returns:
        Cliente EvolutionAPI pronto para uso
    """
    return EvolutionAPI(
        base_url=EVOLUTION_CONFIG["base_url"],
        api_key=EVOLUTION_CONFIG["api_key"]
    )


# Exemplo de uso
if __name__ == "__main__":
    # Inicializar cliente
    client = get_evolution_client()
    
    print("🔌 Testando conexão com Evolution API...")
    
    try:
        # Listar instâncias
        instances = client.list_instances()
        print(f"✅ Conexão OK! Instâncias encontradas: {len(instances)}")
        
        if instances:
            for inst in instances:
                print(f"  - {inst.get('instance', {}).get('instanceName', 'N/A')}")
        else:
            print("  (Nenhuma instância criada ainda)")
            
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        print("\n💡 Certifique-se de que:")
        print("  1. O Evolution API está rodando no Railway")
        print("  2. As variáveis de ambiente foram configuradas")
        print("  3. A API Key está correta")
