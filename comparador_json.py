#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparador de JSON Antigo com DDL Novo
=======================================

Este módulo compara um JSON antigo com um DDL novo e gera um CSV
com as colunas mapeadas do JSON antigo e as novas em branco.

Funcionalidades:
- Lê JSON antigo e extrai mapeamento de rename_to
- Lê DDL novo e extrai colunas
- Compara e mescla informações
- Gera CSV com colunas antigas mapeadas e novas em branco

Autor: Felipe Machado
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional


def ler_json_antigo(caminho_json: str) -> Dict[str, Any]:
    """
    Lê arquivo JSON antigo e extrai informações.
    
    Args:
        caminho_json: Caminho do arquivo JSON antigo
        
    Returns:
        Dicionário com informações do JSON
        
    Raises:
        FileNotFoundError: Se o arquivo não existir
        ValueError: Se o JSON for inválido
    """
    if not Path(caminho_json).exists():
        raise FileNotFoundError(f"Arquivo JSON não encontrado: {caminho_json}")
    
    try:
        with open(caminho_json, 'r', encoding='utf-8') as arquivo:
            dados = json.load(arquivo)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON inválido: {str(e)}")
    
    return dados


def extrair_mapeamento_json(dados_json: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Extrai mapeamento de colunas do JSON antigo.
    
    Args:
        dados_json: Dados do JSON antigo
        
    Returns:
        Dicionário mapeando coluna_mf → {rename_to, description, inputType}
    """
    mapeamento = {}
    
    # Navegar pela estrutura do JSON
    for tabela_nome, tabela_info in dados_json.items():
        if isinstance(tabela_info, dict) and 'structure' in tabela_info:
            estrutura = tabela_info['structure']
            if 'fields' in estrutura:
                for campo in estrutura['fields']:
                    nome_original = campo.get('name', '')
                    metadata = campo.get('metadata', {})
                    
                    mapeamento[nome_original] = {
                        'rename_to': metadata.get('renameTo', ''),
                        'description': metadata.get('description', ''),
                        'inputType': metadata.get('inputType', 'string'),
                        'outputType': metadata.get('outputType', 'string')
                    }
    
    return mapeamento


def extrair_colunas_ddl(info_tabela: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extrai colunas do DDL processado.
    
    Args:
        info_tabela: Informações da tabela do DDL
        
    Returns:
        Lista de colunas com nome e descrição
    """
    colunas = []
    
    for coluna in info_tabela.get('colunas', []):
        colunas.append({
            'nome': coluna['nome'],
            'descricao': coluna.get('descricao', ''),
            'tipo': coluna['tipo_dado']['tipo']
        })
    
    return colunas


def comparar_e_mesclar(colunas_ddl: List[Dict[str, str]], 
                       mapeamento_json: Dict[str, Dict[str, str]],
                       nome_tabela: str,
                       descricao_tabela: str) -> List[Dict[str, str]]:
    """
    Compara colunas do DDL com mapeamento do JSON antigo.
    
    Args:
        colunas_ddl: Colunas extraídas do DDL novo
        mapeamento_json: Mapeamento do JSON antigo
        nome_tabela: Nome da tabela
        descricao_tabela: Descrição da tabela
        
    Returns:
        Lista de dicionários para o CSV
    """
    resultado = []
    
    # Adicionar colunas do DDL
    for coluna in colunas_ddl:
        nome_coluna = coluna['nome']
        tipo_coluna = coluna['tipo']
        
        # Verificar se a coluna existe no JSON antigo
        if nome_coluna in mapeamento_json:
            # Se existe, usar os dados do JSON
            mapeamento = mapeamento_json[nome_coluna]
            resultado.append({
                'tabela': nome_tabela,
                'descricao_mf': descricao_tabela,
                'coluna_mf': nome_coluna,
                'rename_to': mapeamento.get('rename_to', ''),
                'descricao_coluna_mf': mapeamento.get('description', ''),
                'descricao_oficial': mapeamento.get('description', ''),
                'tipo_original': tipo_coluna  # Garantir que está usando o tipo do DDL
            })
        else:
            # Se não existe, adicionar como nova coluna
            resultado.append({
                'tabela': nome_tabela,
                'descricao_mf': descricao_tabela,
                'coluna_mf': nome_coluna,
                'rename_to': '',
                'descricao_coluna_mf': '',
                'descricao_oficial': '',
                'tipo_original': tipo_coluna  # Garantir que está usando o tipo do DDL
            })
    
    # Adicionar colunas que existem no JSON antigo mas não no DDL novo (para referência)
    colunas_ddl_nomes = {c['nome'] for c in colunas_ddl}
    for nome_coluna_antiga in mapeamento_json.keys():
        if nome_coluna_antiga not in colunas_ddl_nomes:
            # Coluna removida do DDL - adicionar com aviso
            dados_antigos = mapeamento_json[nome_coluna_antiga]
            linha = {
                'tabela': nome_tabela,
                'descricao_mf': descricao_tabela + ' [REMOVIDA DO DDL]',
                'coluna_mf': nome_coluna_antiga + ' [REMOVIDA]',
                'rename_to': dados_antigos.get('rename_to', ''),
                'descricao_coluna_mf': '[COLUNA REMOVIDA]',
                'descricao_oficial': dados_antigos.get('description', ''),
                'tipo_original': dados_antigos.get('inputType', 'string')  # Tipo original do JSON
            }
            resultado.append(linha)
    
    return resultado


def gerar_csv_comparado(dados_csv: List[Dict[str, str]], 
                       caminho_saida: str) -> None:
    """
    Gera arquivo CSV com dados comparados.
    
    Args:
        dados_csv: Dados para o CSV
        caminho_saida: Caminho onde salvar o arquivo
    """
    if not dados_csv:
        raise ValueError("Nenhum dado para gerar CSV")
    
    Path(caminho_saida).parent.mkdir(parents=True, exist_ok=True)
    
    with open(caminho_saida, 'w', newline='', encoding='utf-8') as arquivo:
        campos = dados_csv[0].keys()
        writer = csv.DictWriter(arquivo, fieldnames=campos, delimiter=';')
        writer.writeheader()
        writer.writerows(dados_csv)


def processar_comparacao(caminho_ddl: str, 
                        caminho_json_antigo: str,
                        info_tabela: Dict[str, Any],
                        caminho_csv_saida: str) -> Dict[str, Any]:
    """
    Processa comparação entre DDL novo e JSON antigo.
    
    Args:
        caminho_ddl: Caminho do arquivo DDL
        caminho_json_antigo: Caminho do JSON antigo
        info_tabela: Informações da tabela extraídas do DDL
        caminho_csv_saida: Caminho onde salvar o CSV
        
    Returns:
        Dicionário com informações do processamento
    """
    try:
        # Ler JSON antigo
        dados_json = ler_json_antigo(caminho_json_antigo)
        
        # Extrair mapeamento do JSON antigo
        mapeamento_json = extrair_mapeamento_json(dados_json)
        
        # Extrair colunas do DDL
        colunas_ddl = extrair_colunas_ddl(info_tabela)
        
        # Comparar e mesclar
        nome_tabela = info_tabela['nome']
        descricao_tabela = info_tabela['descricao']
        
        dados_csv = comparar_e_mesclar(colunas_ddl, mapeamento_json, 
                                       nome_tabela, descricao_tabela)
        
        # Gerar CSV
        gerar_csv_comparado(dados_csv, caminho_csv_saida)
        
        return {
            'sucesso': True,
            'nome_tabela': nome_tabela,
            'caminho_csv': caminho_csv_saida,
            'num_colunas': len(colunas_ddl),
            'num_colunas_novas': sum(1 for d in dados_csv if not d['rename_to']),
            'num_colunas_existentes': sum(1 for d in dados_csv if d['rename_to']),
            'dados_csv': dados_csv,
            'erro': None
        }
        
    except Exception as e:
        return {
            'sucesso': False,
            'nome_tabela': None,
            'caminho_csv': None,
            'num_colunas': 0,
            'num_colunas_novas': 0,
            'num_colunas_existentes': 0,
            'dados_csv': [],
            'erro': str(e)
        }
