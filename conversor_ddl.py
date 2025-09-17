#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conversor de DDL para Configurações MLOps
==========================================

Este script converte arquivos DDL (Data Definition Language) do mainframe DB2
para arquivos de configuração CSV e JSON compatíveis com pipelines MLOps.

Funcionalidades:
- Lê arquivos DDL do mainframe DB2
- Extrai informações de tabelas e colunas
- Gera dicionário CSV para preenchimento manual
- Converte tipos de dados para formato usado por MLOps
- Cria arquivo JSON final com configurações

Uso:
    python conversor_ddl.py

Autor: Felipe Machado
"""

import json
import csv
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


def ler_arquivo_ddl(caminho_arquivo: str) -> str:
    """
    Lê o conteúdo de um arquivo DDL.
    
    Args:
        caminho_arquivo: Caminho para o arquivo DDL
        
    Returns:
        Conteúdo do arquivo como string
        
    Raises:
        FileNotFoundError: Se o arquivo não existir
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
            return arquivo.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo DDL não encontrado: {caminho_arquivo}")


def extrair_nome_tabela(conteudo_ddl: str) -> str:
    """
    Extrai o nome da tabela do DDL.
    
    Args:
        conteudo_ddl: Conteúdo do arquivo DDL
        
    Returns:
        Nome da tabela
        
    Raises:
        ValueError: Se não encontrar CREATE TABLE
    """
    padrao = r"CREATE\s+TABLE\s+(?P<schema>\w+)\.(?P<nome_tabela>\w+)"
    match = re.search(padrao, conteudo_ddl)
    
    if not match:
        raise ValueError("Não foi possível encontrar CREATE TABLE no DDL")
    
    return match.group('nome_tabela')


def extrair_informacoes_tabela(conteudo_ddl: str, nome_tabela: str) -> Dict[str, Any]:
    """
    Extrai todas as informações da tabela do DDL.
    
    Args:
        conteudo_ddl: Conteúdo do arquivo DDL
        nome_tabela: Nome da tabela a ser processada
        
    Returns:
        Dicionário com informações da tabela
    """
    # Extrair informações básicas da tabela
    padrao_create = (
        r"CREATE\s+TABLE\s+(?P<schema>\w+)\." + nome_tabela + r"\s*"
        r"\s*\((?P<colunas>[\W\w]+?)\s*\)\s+"
        r"IN\s+(?P<database>\w+)\.(?P<tablespace>\w+)"
    )
    
    match_create = re.search(padrao_create, conteudo_ddl)
    if not match_create:
        raise ValueError(f"Não foi possível encontrar definição da tabela {nome_tabela}")
    
    # Extrair descrição da tabela
    padrao_label_tabela = (
        rf"LABEL\s+ON\s+TABLE\s+{match_create['schema']}\.{nome_tabela}\s+"
        r"IS\s+'(?P<descricao>.*)'"
    )
    match_label = re.search(padrao_label_tabela, conteudo_ddl)
    descricao_tabela = match_label.group('descricao') if match_label else ""
    
    # Extrair colunas
    colunas = extrair_colunas(match_create['colunas'], conteudo_ddl, match_create['schema'], nome_tabela)
    
    # Extrair índices únicos
    indices_unicos = extrair_indices_unicos(conteudo_ddl, match_create['schema'], nome_tabela)
    
    return {
        'nome': nome_tabela,
        'schema': match_create['schema'],
        'database': match_create['database'],
        'tablespace': match_create['tablespace'],
        'descricao': descricao_tabela,
        'colunas': colunas,
        'indices_unicos': indices_unicos
    }


def extrair_colunas(texto_colunas: str, conteudo_ddl: str, schema: str, nome_tabela: str) -> List[Dict[str, Any]]:
    """
    Extrai informações das colunas da tabela.
    
    Args:
        texto_colunas: Texto contendo definições das colunas
        conteudo_ddl: Conteúdo completo do DDL (para buscar descrições)
        schema: Schema da tabela
        nome_tabela: Nome da tabela
        
    Returns:
        Lista de dicionários com informações das colunas
    """
    colunas = []
    
    # Extrair descrições das colunas
    descricoes_colunas = extrair_descricoes_colunas(conteudo_ddl, schema, nome_tabela)
    
    # Processar cada linha de definição de coluna
    for linha in texto_colunas.split('\n'):
        padrao_coluna = (
            r"(\d{6})?\s*(?P<nome>\w+)\s+(?P<tipo_dado>\w+(\(.*\))?)\s*"
            r"(?P<nullable>(NOT)?\s+NULL)?"
            r"(?P<default>\s+WITH\s+DEFAULT(\s+(?P<valor_default>(\d+)|(\'.*\')))?)?"
        )
        
        match = re.search(padrao_coluna, linha)
        if match:
            nome_coluna = match.group('nome')
            tipo_dado = processar_tipo_dado(match.group('tipo_dado'))
            nullable = not bool(match.group('nullable') and 'NOT' in match.group('nullable'))
            valor_default = processar_valor_default(match.group('valor_default'), tipo_dado['tipo'])
            
            coluna = {
                'nome': nome_coluna,
                'tipo_dado': tipo_dado,
                'nullable': nullable,
                'valor_default': valor_default,
                'descricao': descricoes_colunas.get(nome_coluna, "")
            }
            colunas.append(coluna)
    
    return colunas


def processar_tipo_dado(tipo_string: str) -> Dict[str, Any]:
    """
    Processa string de tipo de dado e extrai informações.
    
    Args:
        tipo_string: String do tipo de dado (ex: VARCHAR(50), DEC(10,2))
        
    Returns:
        Dicionário com tipo, tamanho, precisão e escala
    """
    padrao = r"(?P<tipo>\w+)(\((?P<parametros>.+)\))?"
    match = re.match(padrao, tipo_string)
    
    if not match:
        return {'tipo': tipo_string, 'tamanho': None, 'precisao': None, 'escala': None}
    
    tipo = match.group('tipo')
    parametros = match.group('parametros')
    
    tamanho = None
    precisao = None
    escala = None
    
    if parametros:
        if tipo in ['VARCHAR', 'CHAR']:
            tamanho = int(parametros)
        elif tipo in ['DEC', 'DECIMAL', 'NUMERIC']:
            if ',' in parametros:
                precisao, escala = map(int, parametros.split(','))
            else:
                precisao = int(parametros)
                escala = 0
    
    return {
        'tipo': tipo,
        'tamanho': tamanho,
        'precisao': precisao,
        'escala': escala
    }


def processar_valor_default(valor_default: Optional[str], tipo: str) -> Any:
    """
    Processa valor padrão da coluna.
    
    Args:
        valor_default: Valor padrão como string
        tipo: Tipo da coluna
        
    Returns:
        Valor padrão processado
    """
    if not valor_default:
        return None
    
    valor_limpo = valor_default.strip().replace("'", "")
    
    # Conversões por tipo
    conversoes_default = {
        'VARCHAR': '',
        'CHAR': '',
        'INT': 0,
        'INTEGER': 0,
        'SMALLINT': 0,
        'DEC': 0,
        'DECIMAL': 0,
        'NUMERIC': 0,
        'DATE': 'CURRENT_DATE',
        'TIME': 'CURRENT_TIME',
        'TIMESTAMP': 'CURRENT_TIMESTAMP'
    }
    
    return conversoes_default.get(tipo, valor_limpo)


def extrair_descricoes_colunas(conteudo_ddl: str, schema: str, nome_tabela: str) -> Dict[str, str]:
    """
    Extrai descrições das colunas do DDL.
    
    Args:
        conteudo_ddl: Conteúdo do DDL
        schema: Schema da tabela
        nome_tabela: Nome da tabela
        
    Returns:
        Dicionário mapeando nome da coluna para sua descrição
    """
    padrao_labels = (
        rf"LABEL\s+ON\s+{schema}\.{nome_tabela}\s*"
        r"\((?P<colunas>(\s*\w+\s+IS\s+'.+?'\s*,?\s*\d*\s*)+)\s*\);"
    )
    
    match = re.search(padrao_labels, conteudo_ddl)
    if not match:
        print(f"Aviso: Não foram encontradas descrições para as colunas da tabela {nome_tabela}")
        return {}
    
    descricoes = {}
    texto_colunas = match.group('colunas')
    
    for linha in texto_colunas.split('\n'):
        padrao_descricao = r"\s*\d*\s*(?P<nome>\w+)\s+IS\s+'(?P<descricao>[\w\W]+?)'"
        match_desc = re.search(padrao_descricao, linha)
        
        if match_desc:
            nome = match_desc.group('nome')
            descricao = match_desc.group('descricao').strip()
            descricoes[nome] = descricao
    
    return descricoes


def extrair_indices_unicos(conteudo_ddl: str, schema: str, nome_tabela: str) -> List[Dict[str, Any]]:
    """
    Extrai informações dos índices únicos da tabela.
    
    Args:
        conteudo_ddl: Conteúdo do DDL
        schema: Schema da tabela
        nome_tabela: Nome da tabela
        
    Returns:
        Lista de dicionários com informações dos índices
    """
    padrao_indice = (
        r"CREATE\s+UNIQUE\s+INDEX\s+"
        r"(?P<schema_indice>\w+)\.(?P<nome_indice>\w+)\s+"
        rf"ON\s+{schema}\.{nome_tabela}\s*"
        r"\((?P<colunas>[\w\W]+?)\)"
    )
    
    indices = []
    
    for match in re.finditer(padrao_indice, conteudo_ddl):
        colunas_indice = []
        texto_colunas = match.group('colunas')
        
        for col_match in re.finditer(r"(?P<nome>\w+)(\s+(?P<ordem>ASC|DESC))?,?", texto_colunas):
            colunas_indice.append(col_match.group('nome'))
        
        indice = {
            'schema': match.group('schema_indice'),
            'nome': match.group('nome_indice'),
            'colunas': colunas_indice
        }
        indices.append(indice)
    
    return indices


def converter_tipo_para_mlops(tipo_dado: Dict[str, Any]) -> str:
    """
    Converte tipo de dado do mainframe para tipo MLOps.
    
    Args:
        tipo_dado: Dicionário com informações do tipo
        
    Returns:
        Tipo de dado no formato MLOps
    """
    tipo = tipo_dado['tipo']
    precisao = tipo_dado['precisao']
    escala = tipo_dado['escala']
    
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
    
    if tipo in ['DEC', 'DECIMAL', 'NUMERIC']:
        return f"decimal({precisao}, {escala})"
    
    return mapeamento_tipos.get(tipo, 'string')


def gerar_curacoes(tipo_original: str) -> List[Dict[str, Any]]:
    """
    Gera curações baseadas no tipo de dado original.
    
    Args:
        tipo_original: Tipo de dado original do mainframe
        
    Returns:
        Lista de curações a serem aplicadas
    """
    curacoes = []
    
    if tipo_original == "INTEGER":
        curacoes.append({
            "name": "StringToType",
            "input": "integer",
            "runOn": ["kafka", "unload"]
        })
    elif tipo_original == "SMALLINT":
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
        Lista com campos de auditoria
    """
    return [
        {
            "name": "AUD_ENTTYP",
            "type": "string",
            "nullable": False,
            "metadata": {
                "description": "Código que identifica no destino o evento ocorrido na tabela origem do db2mf",
                "inputType": "string",
                "outputType": "string",
                "renameTo": "co_aud_enttyp",
                "jsonParameterName": "string"
            }
        },
        {
            "name": "AUD_APPLY_TIMESTAMP",
            "type": "timestamp",
            "nullable": False,
            "metadata": {
                "description": "Timestamp indicando quando ocorreu atualização na tabela origem db2mf",
                "inputType": "string",
                "outputType": "timestamp",
                "renameTo": "ts_aud_apply",
                "jsonParameterName": "string"
            }
        }
    ]


def criar_dicionario_csv(info_tabela: Dict[str, Any], caminho_saida: str) -> None:
    """
    Cria arquivo CSV com dicionário da tabela para preenchimento manual.
    
    Args:
        info_tabela: Informações da tabela
        caminho_saida: Caminho onde salvar o arquivo CSV
    """
    linhas = []
    
    for coluna in info_tabela['colunas']:
        linha = {
            'tabela': info_tabela['nome'],
            'descricao_mf': info_tabela['descricao'],
            'descricao': '',  # Para preenchimento manual
            'coluna_mf': coluna['nome'],
            'coluna': '',  # Para preenchimento manual
            'descricao_coluna_mf': coluna['descricao'],
            'descricao_coluna': ''  # Para preenchimento manual
        }
        linhas.append(linha)
    
    # Criar diretório se não existir
    Path(caminho_saida).parent.mkdir(parents=True, exist_ok=True)
    
    with open(caminho_saida, 'w', newline='', encoding='utf-8') as arquivo:
        campos = linhas[0].keys()
        writer = csv.DictWriter(arquivo, fieldnames=campos, delimiter=';')
        writer.writeheader()
        writer.writerows(linhas)


def ler_dicionario_csv(caminho_arquivo: str) -> List[Dict[str, str]]:
    """
    Lê dicionário CSV preenchido.
    
    Args:
        caminho_arquivo: Caminho do arquivo CSV
        
    Returns:
        Lista de dicionários com dados do CSV
        
    Raises:
        ValueError: Se algum campo obrigatório estiver vazio
    """
    with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
        reader = csv.DictReader(arquivo, delimiter=';')
        dados = list(reader)
    
    # Validar preenchimento
    for linha in dados:
        for campo, valor in linha.items():
            if not valor or valor.strip() == '':
                raise ValueError(
                    f"Campo '{campo}' da coluna '{linha.get('coluna_mf', 'N/A')}' está vazio. "
                    f"Preencha o dicionário antes de continuar."
                )
    
    return dados


def criar_configuracao_mlops(info_tabela: Dict[str, Any], dicionario: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Cria configuração MLOps baseada na tabela e dicionário.
    
    Args:
        info_tabela: Informações da tabela extraídas do DDL
        dicionario: Dados do dicionário CSV preenchido
        
    Returns:
        Configuração MLOps em formato de dicionário
    """
    # Obter chave da tabela (primeira chave única encontrada)
    chave_tabela = []
    if info_tabela['indices_unicos']:
        chave_tabela = info_tabela['indices_unicos'][0]['colunas']
    
    campos = []
    
    # Criar mapeamento do dicionário para busca rápida
    dict_map = {item['coluna_mf']: item for item in dicionario}
    
    # Processar apenas as colunas que existem no dicionário
    for coluna in info_tabela['colunas']:
        if coluna['nome'] not in dict_map:
            print(f"[AVISO] Coluna '{coluna['nome']}' não encontrada no dicionário - pulando...")
            continue
            
        dados_dict = dict_map[coluna['nome']]
        
        # Converter tipo para MLOps
        tipo_mlops = converter_tipo_para_mlops(coluna['tipo_dado'])
        
        # Criar campo
        campo = {
            "name": coluna['nome'],
            "type": tipo_mlops,
            "nullable": coluna['nullable'],
            "metadata": {
                "description": dados_dict['descricao_coluna'],
                "inputType": coluna['tipo_dado']['tipo'],
                "outputType": tipo_mlops,
                "renameTo": dados_dict['coluna'],
                "jsonParameterName": "int" if coluna['tipo_dado']['tipo'] in ['INTEGER', 'INT', 'SMALLINT'] else "string"
            }
        }
        
        # Adicionar curações se necessário
        curacoes = gerar_curacoes(coluna['tipo_dado']['tipo'])
        if curacoes:
            campo["metadata"]["curations"] = curacoes
        
        campos.append(campo)
    
    # Adicionar campos de auditoria
    campos.extend(gerar_campos_auditoria())
    
    # Criar configuração final
    configuracao = {
        info_tabela['nome']: {
            "delimiter": "|",
            "format": "csv",
            "tableKey": chave_tabela,
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


def buscar_arquivos_ddl(pasta_ddls: str = "ddls") -> List[str]:
    """
    Busca automaticamente arquivos DDL na pasta especificada.
    
    Args:
        pasta_ddls: Caminho da pasta com arquivos DDL
        
    Returns:
        Lista de caminhos para arquivos DDL encontrados
    """
    pasta_ddls = Path(pasta_ddls)
    if not pasta_ddls.exists():
        return []
    
    arquivos_ddl = []
    for arquivo in pasta_ddls.glob("*.txt"):
        arquivos_ddl.append(str(arquivo))
    
    return arquivos_ddl


def gerar_dicionario_automatico(info_tabela: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Gera dicionário automaticamente sem necessidade de preenchimento manual.
    
    Args:
        info_tabela: Informações da tabela extraídas do DDL
        
    Returns:
        Lista de dicionários com dados preenchidos automaticamente
    """
    dicionario = []
    
    for coluna in info_tabela['colunas']:
        # Gerar nome da coluna no formato snake_case
        nome_coluna_mlops = coluna['nome'].lower()
        
        # Usar descrição original ou gerar uma padrão
        descricao_coluna = coluna['descricao'] if coluna['descricao'] else f"Campo {coluna['nome']}"
        
        linha = {
            'tabela': info_tabela['nome'],
            'descricao_mf': info_tabela['descricao'],
            'descricao': f"Tabela {info_tabela['nome']} - {info_tabela['descricao']}" if info_tabela['descricao'] else f"Tabela {info_tabela['nome']}",
            'coluna_mf': coluna['nome'],
            'coluna': nome_coluna_mlops,
            'descricao_coluna_mf': coluna['descricao'] if coluna['descricao'] else "",
            'descricao_coluna': descricao_coluna
        }
        dicionario.append(linha)
    
    return dicionario


def processar_arquivo_ddl(caminho_ddl: str, pasta_saida: str = "output") -> Dict[str, Any]:
    """
    Processa um único arquivo DDL e retorna informações do processamento.
    
    Args:
        caminho_ddl: Caminho para o arquivo DDL
        pasta_saida: Pasta onde salvar os arquivos de saída
        
    Returns:
        Dicionário com informações do processamento
    """
    try:
        # Ler e processar DDL
        conteudo_ddl = ler_arquivo_ddl(caminho_ddl)
        nome_tabela = extrair_nome_tabela(conteudo_ddl)
        info_tabela = extrair_informacoes_tabela(conteudo_ddl, nome_tabela)
        
        # Gerar dicionário automaticamente
        dicionario = gerar_dicionario_automatico(info_tabela)
        
        # Salvar CSV para referência
        caminho_csv = f"{pasta_saida}/dicionarios/{nome_tabela}.csv"
        criar_dicionario_csv(info_tabela, caminho_csv)
        
        # Criar configuração MLOps diretamente
        configuracao = criar_configuracao_mlops(info_tabela, dicionario)
        
        # Salvar arquivo JSON
        caminho_json = f"{pasta_saida}/json/{nome_tabela.lower()}.json"
        salvar_configuracao_json(configuracao, caminho_json)
        
        return {
            'sucesso': True,
            'nome_tabela': nome_tabela,
            'caminho_csv': caminho_csv,
            'caminho_json': caminho_json,
            'num_colunas': len(info_tabela['colunas']),
            'erro': None
        }
        
    except Exception as e:
        return {
            'sucesso': False,
            'nome_tabela': None,
            'caminho_csv': None,
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
    Função principal do conversor DDL para MLOps - Versão Automatizada.
    """
    print("=== Conversor DDL para Configuracoes MLOps - Automatico ===\n")
    
    try:
        # Buscar arquivos DDL automaticamente
        print("[INICIANDO] Busca de arquivos DDL na pasta ddls/...")
        arquivos_ddl = buscar_arquivos_ddl()
        
        if not arquivos_ddl:
            print("[ERRO] Nenhum arquivo DDL encontrado na pasta ddls/")
            print("Coloque seus arquivos .txt na pasta ddls/ e execute novamente.")
            return
        
        # Validar se há apenas 1 arquivo DDL
        if len(arquivos_ddl) > 1:
            print(f"[AVISO] Encontrados {len(arquivos_ddl)} arquivos DDL:")
            for arquivo in arquivos_ddl:
                print(f"   - {arquivo}")
            print("\nATENCAO: Coloque apenas 1 arquivo DDL por vez na pasta ddls/")
            print("Remova os arquivos extras e execute novamente.")
            return
        
        print(f"[ENCONTRADO] 1 arquivo DDL: {arquivos_ddl[0]}")
        
        # Processar o arquivo DDL
        caminho_ddl = arquivos_ddl[0]
        print(f"\n[INICIANDO PROCESSAMENTO] {caminho_ddl}")
        print("="*60)
        
        resultado = processar_arquivo_ddl(caminho_ddl)
        
        if resultado['sucesso']:
            # Mensagem final de sucesso
            print("\n" + "="*60)
            print("[PROCESSO CONCLUIDO COM SUCESSO]")
            print("="*60)
            print(f"Tabela processada: {resultado['nome_tabela']}")
            print(f"CSV gerado: {resultado['caminho_csv']}")
            print(f"JSON MLOps: {resultado['caminho_json']}")
            print("Arquivos prontos para uso!")
            print("="*60)
        else:
            exibir_erro_critico(resultado['erro'])
        
    except Exception as e:
        exibir_erro_critico(str(e))
        return


if __name__ == "__main__":
    main()
