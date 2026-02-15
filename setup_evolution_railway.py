#!/usr/bin/env python3
"""
Script automático para configurar Evolution API no Railway
"""

import requests
import json
import sys

# Token do Railway
RAILWAY_TOKEN = "f5c1f693-7a75-4d6a-ab9a-42ee36f145aa"
RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"

# Variáveis que precisam ser configuradas
REQUIRED_VARS = {
    "AUTHENTICATION_API_KEY": "Active2024SecureKey!@#",
    "SERVER_URL": "https://evolution-api.up.railway.app",
    "CORS_ORIGIN": "*",
    "CORS_CREDENTIALS": "true",
    "QRCODE_COLOR": "#198754",
    "LOG_LEVEL": "ERROR",
    "LOG_COLOR": "true",
    "STORE_MESSAGES": "true",
    "STORE_CONTACTS": "true",
    "STORE_CHATS": "true",
}

def graphql_request(query, variables=None):
    """Faz uma requisição GraphQL para a API do Railway"""
    headers = {
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(RAILWAY_API_URL, json=payload, headers=headers)
    return response.json()

def get_projects():
    """Lista todos os projetos"""
    query = """
    query {
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
    """
    return graphql_request(query)

def get_service_variables(service_id):
    """Obtém as variáveis de um serviço"""
    query = """
    query Variables($serviceId: String!) {
        variables(serviceId: $serviceId) {
            edges {
                node {
                    id
                    name
                    value
                }
            }
        }
    }
    """
    return graphql_request(query, {"serviceId": service_id})

def upsert_variable(service_id, environment_id, name, value):
    """Cria ou atualiza uma variável de ambiente"""
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
    print("🚀 Iniciando configuração do Evolution API no Railway...\n")
    
    # 1. Listar projetos
    print("📋 Buscando projetos...")
    result = get_projects()
    
    if "errors" in result:
        print("❌ Erro ao acessar a API do Railway:")
        print(json.dumps(result["errors"], indent=2))
        sys.exit(1)
    
    # Procurar pelo projeto evolution-api
    projects = result.get("data", {}).get("projects", {}).get("edges", [])
    
    print(f"✅ Encontrados {len(projects)} projeto(s)\n")
    
    evolution_service = None
    for project in projects:
        project_node = project["node"]
        print(f"📦 Projeto: {project_node['name']} (ID: {project_node['id']})")
        
        services = project_node.get("services", {}).get("edges", [])
        for service in services:
            service_node = service["node"]
            print(f"  └─ Serviço: {service_node['name']} (ID: {service_node['id']})")
            
            # Procurar por serviço que contenha "evolution" no nome
            if "evolution" in service_node["name"].lower():
                evolution_service = service_node
                print(f"  ✅ Serviço Evolution API encontrado!")
    
    if not evolution_service:
        print("\n❌ Nenhum serviço Evolution API encontrado.")
        print("💡 Certifique-se de que o serviço existe e está nomeado corretamente.")
        sys.exit(1)
    
    print(f"\n🔧 Configurando variáveis para o serviço: {evolution_service['name']}")
    print("="*60)
    
    # Configurar cada variável
    for var_name, var_value in REQUIRED_VARS.items():
        print(f"⚙️  Configurando {var_name}...", end=" ")
        
        # Nota: Precisamos do environmentId, vamos tentar com None primeiro
        result = upsert_variable(
            service_id=evolution_service['id'],
            environment_id=None,  # Pode precisar ser ajustado
            name=var_name,
            value=var_value
        )
        
        if "errors" in result:
            print(f"❌ Erro")
            print(f"   {result['errors']}")
        else:
            print("✅ OK")
    
    print("\n" + "="*60)
    print("🎉 Configuração concluída!")
    print("\n📝 Próximos passos:")
    print("1. Aguarde o Railway reiniciar o serviço (1-2 minutos)")
    print("2. Acesse: https://evolution-api.up.railway.app/manager/login")
    print("3. Use a API Key: Active2024SecureKey!@#")
    print("4. Crie uma instância e gere o QR code!")

if __name__ == "__main__":
    main()
