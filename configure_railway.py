#!/usr/bin/env python3
"""
Script para configurar variáveis de ambiente no Railway via API GraphQL
"""

import requests
import json

# Token do Railway fornecido pelo usuário
RAILWAY_TOKEN = "f5c1f693-7a75-4d6a-ab9a-42ee36f145aa"
RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"

def get_projects():
    """Lista todos os projetos do usuário"""
    query = """
    query {
        me {
            projects {
                edges {
                    node {
                        id
                        name
                        services {
                            edges {
                                node {
                                    id
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        RAILWAY_API_URL,
        json={"query": query},
        headers=headers
    )
    
    return response.json()

def set_variable(service_id, key, value):
    """Define uma variável de ambiente para um serviço"""
    mutation = """
    mutation VariableUpsert($input: VariableUpsertInput!) {
        variableUpsert(input: $input)
    }
    """
    
    variables = {
        "input": {
            "serviceId": service_id,
            "name": key,
            "value": value
        }
    }
    
    headers = {
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        RAILWAY_API_URL,
        json={"query": mutation, "variables": variables},
        headers=headers
    )
    
    return response.json()

if __name__ == "__main__":
    print("🔍 Buscando projetos no Railway...")
    result = get_projects()
    
    if "errors" in result:
        print("❌ Erro ao acessar a API do Railway:")
        print(json.dumps(result["errors"], indent=2))
        print("\n⚠️  O token fornecido pode não ter as permissões necessárias.")
        print("💡 Solução: Gere um novo token em https://railway.app/account/tokens")
    else:
        print("✅ Projetos encontrados:")
        print(json.dumps(result, indent=2))
        
        # Aqui você pode adicionar a lógica para configurar as variáveis
        # após identificar o projeto e serviço corretos
