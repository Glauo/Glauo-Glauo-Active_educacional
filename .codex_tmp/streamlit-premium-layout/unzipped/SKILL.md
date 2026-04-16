---
name: streamlit-premium-layout
description: 'Melhorar o layout visual de aplicações Streamlit hospedadas em servidores com Docker + Traefik + Easypanel. Use quando o usuário solicitar melhorias visuais, redesign de landing page, troca de logos, ajuste de botões, CSS premium, versão mobile, ou qualquer alteração estética em apps Streamlit em produção. Cobre injeção de CSS via st.markdown, substituição cirúrgica de HTML por número de linha, deploy via docker cp + restart, reconexão de rede Traefik, e criação de prévias HTML estáticas para aprovação antes do deploy.'
---

# Streamlit Premium Layout

Skill para melhorar o visual de apps Streamlit em produção sem quebrar funcionalidades internas.

## Contexto de Infraestrutura

Ambiente típico desta skill:
- **App**: Streamlit rodando em container Docker
- **Proxy reverso**: Traefik gerenciado pelo Easypanel
- **Config Traefik**: `/etc/easypanel/traefik/config/main.yaml`
- **Acesso**: SSH com `sshpass` + `docker cp` para transferir arquivos

## Workflow

### 1. Diagnóstico

```bash
# Container ativo
docker ps --filter name=<projeto> --format '{{.Names}}: {{.Status}}'

# Arquivo Python principal
docker exec <container> ls /app/

# Roteamento Traefik
grep -A5 '<projeto>' /etc/easypanel/traefik/config/main.yaml
```

### 2. Analisar antes de modificar

Identificar antes de qualquer patch:
- **Prefixo CSS** real do HTML (ex: `dhx-`, `dh-`, `lp-`) — inspecionar DOM com `browser_console_exec`
- **Linhas exatas** do bloco a modificar:
  ```bash
  docker exec <container> grep -n 'st.markdown\|_html_block\|dhx-shell' /app/<arquivo>.py | head -20
  ```
- **Estrutura do topbar**: `st.columns()`, `st.container()`, ou HTML puro

### 3. Criar prévia HTML para aprovação

**Sempre criar um HTML estático para aprovação antes de aplicar no servidor.**

Abrir no navegador local (`file:///home/ubuntu/preview.html`) e aguardar aprovação explícita do usuário antes de fazer deploy.

### 4. Aplicar patches — substituição por número de linha

```python
# Executar dentro do container via: docker exec <container> python3 /tmp/patch.py
with open('/app/<arquivo>.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = <linha_inicio - 1>  # 0-indexed
end_idx = <linha_fim>           # exclusive

novo_bloco = '''    st.markdown(
        _html_block(f"""
<div class="novo-html">...</div>
"""),
        unsafe_allow_html=True,
    )
'''

new_lines = lines[:start_idx] + [novo_bloco + '\n'] + lines[end_idx:]

with open('/app/<arquivo>.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
```

**Validar sintaxe antes de enviar:**
```bash
python3 -c "import ast; ast.parse(open('/tmp/patch.py').read())" && echo OK
```

### 5. Deploy

```bash
# 1. Copiar script para o container e executar
docker cp /tmp/patch.py <container>:/tmp/patch.py
docker exec <container> python3 /tmp/patch.py

# 2. Verificar MD5 (deve ser igual ao arquivo fonte)
docker exec <container> md5sum /app/<arquivo>.py

# 3. Reiniciar
docker restart <container>

# 4. Reconectar à rede do Traefik (obrigatório após restart)
docker network connect easypanel <container>

# 5. Atualizar IP no Traefik
NEW_IP=$(docker inspect <container> --format \
  '{{range $k,$v := .NetworkSettings.Networks}}{{if eq $k "easypanel"}}{{.IPAddress}}{{end}}{{end}}')
sed -i "s|http://10.11.3.[0-9]*/|http://$NEW_IP/|g" \
  /etc/easypanel/traefik/config/main.yaml
```

### 6. Problema do baseUrlPath

Se o Streamlit usa `baseUrlPath = "app"` no `config.toml`:
- **Não tente remover** — o Dockerfile sobrescreve a cada restart
- **Solução**: ajustar o Traefik para usar `/app/` no backend:
  ```bash
  sed -i 's|"url": "http://<IP>:8501/"|"url": "http://<IP>:8501/app/"|g' \
    /etc/easypanel/traefik/config/main.yaml
  ```

## CSS Premium — Padrões Reutilizáveis

### Header fixo premium

```css
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
[data-testid="stHeader"] { background: transparent !important; }

.dh-nav-bar {
  position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 32px; height: 64px;
  background: rgba(8, 18, 28, 0.92);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(67, 197, 158, 0.12);
}
```

### Botões discretos

```css
.dh-btn-ghost {
  background: transparent; color: rgba(255,255,255,0.75); border: none;
  font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase;
  padding: 6px 14px; cursor: pointer;
}
.dh-btn-solid {
  background: #1a9e6e; color: #fff; border: none; border-radius: 6px;
  font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase;
  padding: 7px 16px; cursor: pointer;
}
```

### Popover premium

```css
[data-testid="stPopover"] > div {
  background: rgba(8, 18, 28, 0.97) !important;
  border: 1px solid rgba(67, 197, 158, 0.2) !important;
  backdrop-filter: blur(20px) !important;
  border-radius: 14px !important;
  box-shadow: 0 24px 64px rgba(0,0,0,0.6) !important;
}
```

### Grid responsivo 3×2

```css
.dhx-feat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
@media (max-width: 900px) { .dhx-feat-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .dhx-feat-grid { grid-template-columns: 1fr; } }
```

## Armadilhas Comuns

| Problema | Causa | Solução |
|---|---|---|
| CSS não aplica | Prefixo errado (ex: `dh-` vs `dhx-`) | Inspecionar DOM real com `browser_console_exec` |
| `stHorizontalBlock` oculto | CSS anterior com `display: none !important` | `grep -n 'display: none' arquivo.py` e remover |
| 502 após restart | Traefik com IP antigo | Reconectar rede + atualizar IP no `main.yaml` |
| 504 Timeout | Container fora da rede easypanel | `docker network connect easypanel <container>` |
| Botões `st.popover` largos | `use_container_width=True` | Alterar para `False` no código Python |
| Layout antigo após deploy | `docker cp` copiou para caminho errado | Verificar MD5 dentro do container após cópia |
| `baseUrlPath` volta após restart | Dockerfile sobrescreve `config.toml` | Ajustar Traefik para usar `/app/` no backend |

## Script de Manutenção do Traefik (cron)

Ver `scripts/update_traefik_ip.sh` — manter o IP do container atualizado automaticamente a cada 5 minutos.

## Checklist de Deploy

- [ ] Prévia HTML aprovada pelo usuário
- [ ] Backup feito (`cp arquivo.py arquivo.py.bak`)
- [ ] Sintaxe Python validada
- [ ] Arquivo copiado para dentro do container
- [ ] MD5 verificado dentro do container
- [ ] Container reiniciado
- [ ] Rede reconectada (`docker network connect easypanel`)
- [ ] IP atualizado no Traefik
- [ ] Site testado (`curl -s -o /dev/null -w '%{http_code}' https://dominio.com`)
- [ ] Visual confirmado no navegador
