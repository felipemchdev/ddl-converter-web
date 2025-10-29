#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de JSON MLOps a partir de CSV
======================================

Este script lê um arquivo CSV preenchido e gera o arquivo JSON
com configurações MLOps.

Funcionalidades:
- Lê arquivo CSV com dicionário preenchido
- Extrai informações de tipos de dados
- Gera arquivo JSON com configurações MLOps
- Usa a coluna 'rename_to' para gerar o parâmetro renameTo

Uso:
    python json_generator.py <caminho_csv> <caminho_saida_json>

Autor: Felipe Machado
"""

import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


def ler_csv_preenchido(caminho_arquivo: str) -> List[Dict[str, str]]:
    """
    Lê arquivo CSV preenchido com dicionário.
    
    Args:
        caminho_arquivo: Caminho do arquivo CSV
        
    Returns:
        Lista de dicionários com dados do CSV
        
    Raises:
        FileNotFoundError: Se o arquivo não existir
        ValueError: Se algum campo obrigatório estiver vazio
    """
    if not Path(caminho_arquivo).exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {caminho_arquivo}")
    
    with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
        reader = csv.DictReader(arquivo, delimiter=';')
        dados = list(reader)
    
    if not dados:
        raise ValueError("Arquivo CSV vazio")
    
    # Validar preenchimento dos campos obrigatórios
    # descricao_oficial pode ficar vazia (será tratada adiante)
    campos_obrigatorios = ['coluna_mf', 'rename_to']
    for linha_num, linha in enumerate(dados, start=2):  # Começa em 2 (header é 1)
        coluna_mf = linha.get('coluna_mf', '').strip()
        
        # Ignorar colunas removidas
        if '[REMOVIDA]' in coluna_mf:
            continue
        
        for campo in campos_obrigatorios:
            if campo not in linha:
                raise ValueError(f"Campo obrigatório '{campo}' não encontrado no CSV")
            
            valor = linha.get(campo, '').strip()
            if not valor:
                raise ValueError(
                    f"Campo '{campo}' da coluna '{coluna_mf}' "
                    f"(linha {linha_num}) está vazio. Preencha o dicionário antes de continuar."
                )
    
    return dados


def converter_tipo_para_mlops(tipo_dado: str) -> str:
    """
    Converte tipo de dado do mainframe para tipo MLOps.
    
    Args:
        tipo_dado: Tipo de dado original
        
    Returns:
        Tipo de dado no formato MLOps
    """
    mapeamento_tipos = {
        'DATE': 'date',
        'CHAR': 'string',
        'VARCHAR': 'string',
        'TIMESTAMP': 'timestamp',
        'TIME': 'string',
        'INTEGER': 'integer',
        'INT': 'integer',
        'SMALLINT': 'integer',
    }
    
    return mapeamento_tipos.get(tipo_dado, 'string')


def gerar_curacoes(tipo_original: str) -> List[Dict[str, Any]]:
    """
    Gera curações baseadas no tipo de dado original.
    
    Args:
        tipo_original: Tipo de dado original do mainframe
        
    Returns:
        Lista de curações a serem aplicadas
    """
    curacoes = []
    
    if tipo_original in ['INTEGER', 'INT', 'SMALLINT']:
        curacoes.append({
            "name": "StringToType",
            "input": "integer",
            "runOn": ["kafka", "unload"]
        })
    elif tipo_original == "DATE":
        curacoes.append({
            "name": "StringToDate",
            "input": "dd.MM.yyyy",
            "runOn": ["unload"]
        })
    
    return curacoes


def gerar_campos_auditoria() -> List[Dict[str, Any]]:
    """
    Gera campos padrão de auditoria.
    
    Returns:
        Lista com campos de auditoria (vazia - não adiciona automaticamente)
    
    Nota: Campos de auditoria não são mais adicionados automaticamente.
    Eles são copiados do JSON antigo se existirem lá.
    """
    return []


def criar_configuracao_mlops(dados_csv: List[Dict[str, str]], nome_tabela: str) -> Dict[str, Any]:
    """
    Cria configuração MLOps baseada nos dados do CSV.
    
    Args:
        dados_csv: Dados lidos do arquivo CSV
        nome_tabela: Nome da tabela
        
    Returns:
        Configuração MLOps em formato de dicionário
    """
    campos = []
    
    # Processar cada linha do CSV
    for linha in dados_csv:
        coluna_mf = linha.get('coluna_mf', '').strip()
        rename_to = linha.get('rename_to', '').strip()
        descricao_oficial = linha.get('descricao_oficial', '').strip()
        tipo_original = linha.get('tipo_original', 'string').strip()
        
        # Ignorar colunas removidas
        if '[REMOVIDA]' in coluna_mf:
            print(f"[AVISO] Ignorando coluna removida: {coluna_mf}")
            continue
        
        # Exigir apenas coluna e rename_to; descricao_oficial pode ficar vazia
        if not coluna_mf or not rename_to:
            print(f"[AVISO] Pulando linha incompleta (coluna ou rename_to vazios): {coluna_mf}")
            continue
        
        # Converter tipo para MLOps
        tipo_mlops = converter_tipo_para_mlops(tipo_original)
        
        # Determinar jsonParameterName baseado no tipo
        json_param_name = "int" if tipo_original in ['INTEGER', 'INT', 'SMALLINT'] else "string"
        
        # Criar campo
        campo = {
            "name": coluna_mf,
            "type": tipo_mlops,
            "nullable": True,
            "metadata": {
                "description": descricao_oficial,
                "inputType": tipo_original,
                "outputType": tipo_mlops,
                "renameTo": rename_to,
                "jsonParameterName": json_param_name
            }
        }
        
        # Adicionar curações se necessário
        curacoes = gerar_curacoes(tipo_original)
        if curacoes:
            campo["metadata"]["curations"] = curacoes
        
        campos.append(campo)
    
    # Adicionar campos de auditoria
    campos.extend(gerar_campos_auditoria())
    
    # Criar configuração final
    configuracao = {
        nome_tabela: {
            "delimiter": "|",
            "format": "csv",
            "tableKey": [],
            "structure": {
                "type": "struct",
                "fields": campos
            }
        }
    }
    
    return configuracao


def salvar_configuracao_json(configuracao: Dict[str, Any], caminho_saida: str) -> None:
    """
    Salva configuração MLOps em arquivo JSON.
    
    Args:
        configuracao: Configuração MLOps
        caminho_saida: Caminho onde salvar o arquivo
    """
    Path(caminho_saida).parent.mkdir(parents=True, exist_ok=True)
    
    with open(caminho_saida, 'w', encoding='utf-8') as arquivo:
        json.dump(configuracao, arquivo, indent=4, ensure_ascii=False)


def processar_csv_para_json(caminho_csv: str, caminho_json_saida: str, caminho_json_antigo: str = None) -> Dict[str, Any]:
    """
    Processa um arquivo CSV e gera o arquivo JSON correspondente.
    
    Args:
        caminho_csv: Caminho para o arquivo CSV
        caminho_json_saida: Caminho onde salvar o arquivo JSON
        caminho_json_antigo: Caminho do JSON antigo (opcional, para verificar campos de auditoria)
        
    Returns:
        Dicionário com informações do processamento
    """
    try:
        # Ler CSV
        dados_csv = ler_csv_preenchido(caminho_csv)
        
        # Extrair nome da tabela do CSV ou do nome do arquivo
        nome_tabela = Path(caminho_csv).stem.upper()
        
        # Criar configuração MLOps
        configuracao = criar_configuracao_mlops(dados_csv, nome_tabela)
        
        # Se houver JSON antigo, adicionar campos de auditoria que existem nele
        if caminho_json_antigo and Path(caminho_json_antigo).exists():
            try:
                with open(caminho_json_antigo, 'r', encoding='utf-8') as f:
                    json_antigo = json.load(f)
                
                # Procurar campos de auditoria no JSON antigo
                for tabela_nome, tabela_info in json_antigo.items():
                    if isinstance(tabela_info, dict) and 'structure' in tabela_info:
                        estrutura = tabela_info['structure']
                        if 'fields' in estrutura:
                            campos_auditoria = []
                            for campo in estrutura['fields']:
                                nome_campo = campo.get('name', '')
                                if nome_campo.startswith('AUD_'):
                                    campos_auditoria.append(campo)
                            
                            # Adicionar campos de auditoria ao JSON novo
                            if campos_auditoria and nome_tabela in configuracao:
                                configuracao[nome_tabela]['structure']['fields'].extend(campos_auditoria)
            except Exception as e:
                print(f"[AVISO] Não foi possível ler campos de auditoria do JSON antigo: {str(e)}")
        
        # Salvar JSON
        salvar_configuracao_json(configuracao, caminho_json_saida)
        
        return {
            'sucesso': True,
            'nome_tabela': nome_tabela,
            'caminho_json': caminho_json_saida,
            'num_colunas': len(dados_csv),
            'erro': None
        }
        
    except Exception as e:
        return {
            'sucesso': False,
            'nome_tabela': None,
            'caminho_json': None,
            'num_colunas': 0,
            'erro': str(e)
        }


def exibir_erro_critico(mensagem_erro: str):
    """
    Exibe erro crítico com informações de contato.
    
    Args:
        mensagem_erro: Mensagem de erro a ser exibida
    """
    print("\n" + "="*70)
    print("ERRO CRITICO - CONTATE O SUPORTE")
    print("="*70)
    print(f"Erro: {mensagem_erro}")
    print("\nEm caso de problemas desconhecidos, contate:")
    print("   felipe.machado2@experian.com")
    print("="*70)


def main():
    """
    Função principal do gerador JSON MLOps a partir de CSV.
    """
    import sys
    
    print("=== Gerador JSON MLOps a partir de CSV ===\n")
    
    # Validar argumentos
    if len(sys.argv) < 3:
        print("Uso: python json_generator.py <caminho_csv> <caminho_saida_json>")
        print("\nExemplo:")
        print("  python json_generator.py ../cache/output/TABELA.csv ./output/tabela.json")
        return
    
    caminho_csv = sys.argv[1]
    caminho_json_saida = sys.argv[2]
    
    try:
        print(f"[LENDO] Arquivo CSV: {caminho_csv}")
        resultado = processar_csv_para_json(caminho_csv, caminho_json_saida)
        
        if resultado['sucesso']:
            print("\n" + "="*60)
            print("[PROCESSO CONCLUIDO COM SUCESSO]")
            print("="*60)
            print(f"Tabela: {resultado['nome_tabela']}")
            print(f"Colunas processadas: {resultado['num_colunas']}")
            print(f"JSON gerado: {resultado['caminho_json']}")
            print("="*60)
        else:
            exibir_erro_critico(resultado['erro'])
        
    except Exception as e:
        exibir_erro_critico(str(e))


if __name__ == "__main__":
    main()
