#!/usr/bin/env python3
"""
Script v2 - Configuração Evolution API com environments
"""

import requests
import json

RAILWAY_TOKEN = "f5c1f693-7a75-4d6a-ab9a-42ee36f145aa"
RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"
SERVICE_ID = "a57e56b7-23ab-4fb2-8c80-d98c7d83b997"  # ID do evolution-api encontrado

REQUIRED_VARS = {
    "AUTHENTICATION_API_KEY": "Active2024SecureKey!@#",
    "SERVER_URL": "https://evolution-api.up.railway.app",
    "CORS_ORIGIN": "*",
    "CORS_CREDENTIALS": "true",
}

def graphql_request(query, variables=None):
    headers = {
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    response = requests.post(RAILWAY_API_URL, json=payload, headers=headers)
    return response.json()

def get_environments(project_id):
    """Obtém os environments de um projeto"""
    query = """
    query Project($id: String!) {
        project(id: $id) {
            id
            name
            environments {
                edges {
                    node {
                        id
                        name
                    }
                }
            }
        }
    }
    """
    return graphql_request(query, {"id": project_id})

def upsert_variable_v2(environment_id, service_id, name, value):
    """Versão 2 da mutation para criar variáveis"""
    mutation = """
    mutation VariableUpsert($input: VariableUpsertInput!) {
        variableUpsert(input: $input)
    }
    """
    
    variables = {
        "input": {
            "environmentId": environment_id,
            "serviceId": service_id,
            "name": name,
            "value": value
        }
    }
    
    return graphql_request(mutation, variables)

def main():
    print("🚀 Configuração Evolution API v2\n")
    
    # Buscar environments do projeto
    project_id = "5e8fc7c5-2377-41c4-bc47-b4b4fec75408"  # comfortable-liberation
    
    print("🔍 Buscando environments do projeto...")
    result = get_environments(project_id)
    
    if "errors" in result:
        print("❌ Erro:", result["errors"])
        return
    
    environments = result.get("data", {}).get("project", {}).get("environments", {}).get("edges", [])
    
    if not environments:
        print("❌ Nenhum environment encontrado")
        return
    
    print(f"✅ Encontrados {len(environments)} environment(s):\n")
    for env in environments:
        env_node = env["node"]
        print(f"  - {env_node['name']} (ID: {env_node['id']})")
    
    # Usar o primeiro environment (geralmente "production")
    env_id = environments[0]["node"]["id"]
    env_name = environments[0]["node"]["name"]
    
    print(f"\n🎯 Usando environment: {env_name}")
    print("="*60)
    
    for var_name, var_value in REQUIRED_VARS.items():
        print(f"⚙️  {var_name}...", end=" ")
        result = upsert_variable_v2(env_id, SERVICE_ID, var_name, var_value)
        
        if "errors" in result:
            print(f"❌")
            print(f"   Erro: {result['errors']}")
        else:
            print("✅")
    
    print("="*60)
    print("\n🎉 Processo concluído!")
    print("\n📋 Instruções:")
    print("1. Aguarde 1-2 minutos para o Railway reiniciar")
    print("2. Acesse: https://evolution-api.up.railway.app/manager/login")
    print("3. API Key: Active2024SecureKey!@#")

if __name__ == "__main__":
    main()
