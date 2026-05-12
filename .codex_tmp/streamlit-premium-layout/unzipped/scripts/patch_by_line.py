#!/usr/bin/env python3
"""
patch_by_line.py — Substitui um bloco de linhas em um arquivo Python.

Uso:
    python3 patch_by_line.py <arquivo> <linha_inicio> <linha_fim> <novo_conteudo>

Ou importar e usar a função patch_lines() diretamente.

Exemplo de uso como script:
    python3 patch_by_line.py /app/app.py 13365 13529 /tmp/novo_bloco.txt
"""

import sys
import hashlib


def patch_lines(filepath: str, start_line: int, end_line: int, new_content: str) -> bool:
    """
    Substitui as linhas [start_line, end_line) pelo new_content.
    
    Args:
        filepath: Caminho do arquivo Python a modificar
        start_line: Linha de início (1-indexed, inclusiva)
        end_line: Linha de fim (1-indexed, exclusiva)
        new_content: Novo conteúdo a inserir no lugar
    
    Returns:
        True se bem-sucedido, False caso contrário
    """
    # Ler arquivo
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total = len(lines)
    print(f"Arquivo: {filepath} ({total} linhas)")
    
    # Validar índices
    start_idx = start_line - 1  # converter para 0-indexed
    end_idx = end_line - 1      # converter para 0-indexed
    
    if start_idx < 0 or end_idx > total or start_idx >= end_idx:
        print(f"ERRO: Índices inválidos ({start_line}-{end_line}) para arquivo com {total} linhas")
        return False
    
    print(f"Substituindo linhas {start_line}-{end_line}:")
    print(f"  Antes: {lines[start_idx][:80].strip()}")
    print(f"  Até:   {lines[end_idx-1][:80].strip()}")
    
    # Fazer backup
    backup_path = filepath + '.bak'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"Backup salvo em: {backup_path}")
    
    # Substituir
    new_lines = lines[:start_idx] + [new_content + '\n'] + lines[end_idx:]
    
    # Validar sintaxe Python
    import ast
    try:
        ast.parse(''.join(new_lines))
        print("✓ Sintaxe Python válida")
    except SyntaxError as e:
        print(f"✗ ERRO de sintaxe: {e}")
        return False
    
    # Salvar
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    # Verificar MD5
    md5 = hashlib.md5(''.join(new_lines).encode()).hexdigest()
    print(f"✓ Arquivo salvo ({len(new_lines)} linhas, MD5: {md5})")
    return True


def find_block(filepath: str, start_pattern: str, end_pattern: str) -> tuple:
    """
    Encontra as linhas de início e fim de um bloco pelo padrão.
    
    Returns:
        (start_line, end_line) em 1-indexed, ou (None, None) se não encontrado
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    start = None
    for i, line in enumerate(lines):
        if start_pattern in line and start is None:
            start = i + 1  # 1-indexed
        if end_pattern in line and start is not None:
            return start, i + 1
    
    return None, None


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    
    filepath = sys.argv[1]
    start_line = int(sys.argv[2])
    end_line = int(sys.argv[3])
    new_content_file = sys.argv[4]
    
    with open(new_content_file, 'r', encoding='utf-8') as f:
        new_content = f.read()
    
    success = patch_lines(filepath, start_line, end_line, new_content)
    sys.exit(0 if success else 1)
