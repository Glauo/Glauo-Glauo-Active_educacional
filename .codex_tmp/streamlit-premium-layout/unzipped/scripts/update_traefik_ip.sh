#!/bin/bash
# update_traefik_ip.sh
# Mantém o IP do container Streamlit atualizado no Traefik (Easypanel)
# Adicionar ao cron: */5 * * * * /root/update_traefik_ip.sh
#
# Uso: ./update_traefik_ip.sh <nome_do_container>
# Exemplo: ./update_traefik_ip.sh diethealth

CONTAINER="${1:-diethealth}"
TRAEFIK_CONFIG="/etc/easypanel/traefik/config/main.yaml"

# Verificar se o container está rodando
if ! docker ps --filter "name=^${CONTAINER}$" --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "[$(date)] Container $CONTAINER não está rodando" >&2
    exit 1
fi

# Garantir que o container está na rede easypanel
docker network connect easypanel "$CONTAINER" 2>/dev/null || true

# Aguardar o IP ser atribuído
sleep 1

# Obter o IP na rede easypanel
NEW_IP=$(docker inspect "$CONTAINER" --format \
    '{{range $k,$v := .NetworkSettings.Networks}}{{if eq $k "easypanel"}}{{.IPAddress}}{{end}}{{end}}' 2>/dev/null)

if [ -z "$NEW_IP" ]; then
    echo "[$(date)] Não foi possível obter IP do container $CONTAINER na rede easypanel" >&2
    exit 1
fi

# Verificar se o IP já está correto no Traefik
CURRENT_IP=$(grep -oP 'http://\K10\.\d+\.\d+\.\d+(?=:\d+/)' "$TRAEFIK_CONFIG" | head -1)

if [ "$CURRENT_IP" = "$NEW_IP" ]; then
    echo "[$(date)] IP já correto: $NEW_IP"
    exit 0
fi

# Atualizar o IP no Traefik
sed -i "s|http://10\.[0-9]*\.[0-9]*\.[0-9]*/|http://$NEW_IP/|g" "$TRAEFIK_CONFIG"
echo "[$(date)] IP atualizado: $CURRENT_IP -> $NEW_IP"
