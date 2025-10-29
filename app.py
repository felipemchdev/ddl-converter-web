#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DDL Converter Web Application
============================

Aplicação web para conversão de arquivos DDL para configurações MLOps
com interface estilo FreeConverter.com

Autor: Felipe Machado
"""

import os
import shutil
import tempfile
import zipfile
import webbrowser
import json
import csv
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import atexit
import threading
import time

from conversor_ddl import processar_arquivo_ddl, extrair_nome_tabela, ler_arquivo_ddl, extrair_informacoes_tabela
from comparador_json import processar_comparacao

app = Flask(__name__)
app.secret_key = 'ddl-converter-secret-key-2025'

# Configurações - Usar Path para garantir caminhos corretos
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / 'cache'
UPLOAD_FOLDER = str(CACHE_DIR / 'uploads')
OUTPUT_FOLDER = str(CACHE_DIR / 'output')
ALLOWED_EXTENSIONS = {'txt', 'ddl', 'sql', 'json'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

print(f"[INIT] BASE_DIR: {BASE_DIR}")
print(f"[INIT] UPLOAD_FOLDER: {UPLOAD_FOLDER}")
print(f"[INIT] OUTPUT_FOLDER: {OUTPUT_FOLDER}")

# Variáveis globais para controle de processamento
processing_status = {}
processed_files = set()

def get_safe_path(*parts):
    """Cria um caminho seguro usando Path"""
    return str(Path(*parts))

def allowed_file(filename):
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def setup_directories():
    """Cria diretórios necessários com permissões apropriadas"""
    try:
        # Garante que o diretório base existe
        CACHE_DIR.mkdir(parents=True, exist_ok=True, mode=0o755)
        
        # Cria os subdiretórios
        upload_path = Path(UPLOAD_FOLDER)
        output_path = Path(OUTPUT_FOLDER)
        
        # Garante permissões corretas
        upload_path.mkdir(parents=True, exist_ok=True, mode=0o755)
        output_path.mkdir(parents=True, exist_ok=True, mode=0o755)
        
        # Verifica permissões de escrita
        can_write = os.access(str(upload_path), os.W_OK) and os.access(str(output_path), os.W_OK)
        
        print(f"[SETUP] CACHE_DIR: {CACHE_DIR.absolute()}")
        print(f"[SETUP] UPLOAD_FOLDER: {upload_path.absolute()} (acesso escrita: {'sim' if os.access(str(upload_path), os.W_OK) else 'não'})")
        print(f"[SETUP] OUTPUT_FOLDER: {output_path.absolute()} (acesso escrita: {'sim' if os.access(str(output_path), os.W_OK) else 'não'})")
        
        if not can_write:
            print("[ERRO] Sem permissão de escrita nos diretórios necessários")
            
        return can_write
        
    except Exception as e:
        error_msg = f"Erro ao configurar diretórios: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_cache():
    """Limpa o cache ao iniciar a aplicação"""
    cache_path = str(CACHE_DIR)
    if os.path.exists(cache_path):
        shutil.rmtree(cache_path)
    setup_directories()
    processed_files.clear()
    processing_status.clear()
    print(f"[CACHE] Diretório cache limpo: {cache_path}")

def get_file_hash(filepath):
    """Gera hash simples do arquivo baseado no nome e tamanho"""
    stat = os.stat(filepath)
    return f"{os.path.basename(filepath)}_{stat.st_size}_{int(stat.st_mtime)}"

# Rotas da aplicação
@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Endpoint para upload de arquivos"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})
        
        uploaded_files = []
        skipped_files = []
        
        for file in files:
            if file and file.filename != '':
                if not allowed_file(file.filename):
                    continue
                
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Salvar arquivo
                file.save(filepath)
                
                # Verificar se já foi processado
                file_hash = get_file_hash(filepath)
                if file_hash in processed_files:
                    skipped_files.append(filename)
                    os.remove(filepath)  # Remove arquivo duplicado
                    continue
                
                uploaded_files.append({
                    'filename': filename,
                    'filepath': filepath,
                    'hash': file_hash
                })
        
        return jsonify({
            'success': True,
            'uploaded_files': uploaded_files,
            'skipped_files': skipped_files,
            'message': f'{len(uploaded_files)} arquivos enviados com sucesso'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/process', methods=['POST'])
def process_files():
    """Endpoint para processar arquivos DDL"""
    try:
        data = request.get_json()
        files_to_process = data.get('files', [])
        
        if not files_to_process:
            return jsonify({'success': False, 'error': 'Nenhum arquivo para processar'})
        
        # Iniciar processamento em thread separada
        thread_id = str(int(time.time()))
        processing_status[thread_id] = {
            'status': 'processing',
            'total': len(files_to_process),
            'completed': 0,
            'results': [],
            'errors': []
        }
        
        def process_in_background():
            for file_info in files_to_process:
                try:
                    filepath = file_info['filepath']
                    file_hash = file_info['hash']
                    
                    # Processar arquivo
                    resultado = processar_arquivo_ddl(filepath, app.config['OUTPUT_FOLDER'])
                    
                    if resultado['sucesso']:
                        # Marcar como processado
                        processed_files.add(file_hash)
                        
                        # Extrair apenas o nome do arquivo para download
                        nome_csv = os.path.basename(resultado['caminho_csv'])
                        
                        
                        processing_status[thread_id] = {
                            'status': 'completed',
                            'progress': 100,
                            'message': f'Arquivo processado com sucesso! Tabela: {resultado["nome_tabela"]}',
                            'result': {
                                'sucesso': True,
                                'nome_tabela': resultado['nome_tabela'],
                                'caminho_csv': nome_csv,
                                'num_colunas': resultado['num_colunas']
                            }
                        }
                    else:
                        processing_status[thread_id]['errors'].append({
                            'filename': file_info['filename'],
                            'error': resultado['erro']
                        })
                    
                    processing_status[thread_id]['completed'] += 1
                    
                except Exception as e:
                    processing_status[thread_id]['errors'].append({
                        'filename': file_info['filename'],
                        'error': str(e)
                    })
                    processing_status[thread_id]['completed'] += 1
            
            processing_status[thread_id]['status'] = 'completed'
        
        thread = threading.Thread(target=process_in_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'thread_id': thread_id,
            'message': 'Processamento iniciado'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/status/<thread_id>')
def get_status(thread_id):
    """Endpoint para verificar status do processamento"""
    if thread_id not in processing_status:
        return jsonify({'success': False, 'error': 'Thread não encontrada'})
    
    return jsonify({
        'success': True,
        'status': processing_status[thread_id]
    })

@app.route('/download/<path:filename>')
def download_file(filename):
    """Endpoint para download de arquivos gerados"""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        # Debug: log do caminho do arquivo
        print(f"[DEBUG] Tentando baixar: {filename}")
        print(f"[DEBUG] Caminho completo: {file_path}")
        print(f"[DEBUG] Arquivo existe: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            # Listar arquivos disponíveis para debug
            available_files = []
            if os.path.exists(app.config['OUTPUT_FOLDER']):
                available_files = [f for f in os.listdir(app.config['OUTPUT_FOLDER']) if f.endswith('.csv')]
            
            print(f"[DEBUG] Arquivos disponíveis: {available_files}")
            return jsonify({
                'success': False, 
                'error': f'Arquivo não encontrado: {filename}',
                'available_files': available_files
            })
    except Exception as e:
        print(f"[ERROR] Erro no download: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download_all')
def download_all():
    """Endpoint para download de todos os arquivos CSV em ZIP"""
    try:
        # Criar arquivo ZIP temporário
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
            output_path = Path(app.config['OUTPUT_FOLDER'])
            
            # Adicionar todos os arquivos CSV
            for file_path in output_path.rglob('*'):
                if file_path.is_file() and file_path.suffix == '.csv':
                    arcname = file_path.relative_to(output_path)
                    zipf.write(file_path, arcname)
        
        return send_file(
            temp_zip.name,
            as_attachment=True,
            download_name=f'ddl_converted_files_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/compare', methods=['POST'])
def compare_json_ddl():
    """Endpoint para comparar JSON antigo com DDL novo"""
    try:
        if 'ddl_file' not in request.files or 'json_file' not in request.files:
            return jsonify({'success': False, 'error': 'Arquivos DDL e JSON são obrigatórios'})
        
        ddl_file = request.files['ddl_file']
        json_file = request.files['json_file']
        
        if ddl_file.filename == '' or json_file.filename == '':
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})
        
        # Salvar arquivos temporários
        ddl_filename = secure_filename(ddl_file.filename)
        json_filename = secure_filename(json_file.filename)
        
        # Garantir que o diretório de upload existe
        Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
        
        # Usar get_safe_path para caminhos corretos
        ddl_path = get_safe_path(app.config['UPLOAD_FOLDER'], ddl_filename)
        json_path = get_safe_path(app.config['UPLOAD_FOLDER'], json_filename)
        
        print(f"[DEBUG] Salvando DDL em: {ddl_path}")
        print(f"[DEBUG] Salvando JSON em: {json_path}")
        
        ddl_file.save(ddl_path)
        json_file.save(json_path)
        
        print(f"[DEBUG] DDL salvo: {os.path.exists(ddl_path)}")
        print(f"[DEBUG] JSON salvo: {os.path.exists(json_path)}")
        
        # Processar DDL
        conteudo_ddl = ler_arquivo_ddl(ddl_path)
        nome_tabela = extrair_nome_tabela(conteudo_ddl)
        info_tabela = extrair_informacoes_tabela(conteudo_ddl, nome_tabela)
        
        # Garantir que a chave 'descricao' existe no dicionário
        if 'descricao' not in info_tabela:
            info_tabela['descricao'] = ''
        
        # Garantir que OUTPUT_FOLDER existe
        output_dir = Path(app.config['OUTPUT_FOLDER'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Comparar com JSON antigo
        csv_path = output_dir / f"{nome_tabela}_comparado.csv"
        print(f"[DEBUG] Iniciando comparação...")
        print(f"[DEBUG] DDL: {ddl_path}")
        print(f"[DEBUG] JSON: {json_path}")
        print(f"[DEBUG] CSV saída: {csv_path}")
        print(f"[DEBUG] Info tabela: {info_tabela}")
        
        resultado = processar_comparacao(ddl_path, json_path, info_tabela, str(csv_path))
        
        print(f"[DEBUG] Resultado: {resultado['sucesso']}")
        
        if resultado['sucesso']:
            print(f"[DEBUG] Retornando dados CSV: {len(resultado['dados_csv'])} linhas")
            return jsonify({
                'success': True,
                'nome_tabela': resultado['nome_tabela'],
                'num_colunas': resultado['num_colunas'],
                'num_colunas_novas': resultado['num_colunas_novas'],
                'num_colunas_existentes': resultado['num_colunas_existentes'],
                'dados_csv': resultado['dados_csv']
            })
        else:
            print(f"[DEBUG] Erro: {resultado['erro']}")
            return jsonify({'success': False, 'error': resultado['erro']})
        
    except Exception as e:
        print(f"[ERROR] Exceção: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/salvar_csv_json', methods=['POST'])
def salvar_csv_json():
    """
    Endpoint para salvar CSV editado e gerar JSON
    
    Recebe os dados do CSV, salva em um arquivo temporário e gera o JSON final.
    Retorna o caminho do arquivo JSON gerado ou uma mensagem de erro.
    """
    print("\n[DEBUG] Iniciando processamento de salvar_csv_json")
    
    try:
        # Validar dados de entrada
        data = request.get_json()
        print(f"[DEBUG] Dados recebidos: {json.dumps(data, indent=2)[:500]}...")  # Limita o tamanho do log
        
        if not data or 'dados_csv' not in data or 'nome_tabela' not in data:
            error_msg = 'Dados inválidos. É necessário fornecer dados_csv e nome_tabela.'
            print(f"[ERRO] {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        dados_csv = data['dados_csv']
        nome_tabela = data['nome_tabela'].strip()
        
        print(f"[DEBUG] Nome da tabela: {nome_tabela}")
        print(f"[DEBUG] Quantidade de linhas CSV: {len(dados_csv) if dados_csv else 0}")
        
        if not dados_csv or not isinstance(dados_csv, list):
            error_msg = 'Dados do CSV inválidos ou vazios.'
            print(f"[ERRO] {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        if not nome_tabela:
            error_msg = 'Nome da tabela não fornecido.'
            print(f"[ERRO] {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Garantir que o diretório de saída existe e tem permissão
        output_dir = Path(app.config['OUTPUT_FOLDER']).resolve()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            # Testar permissão de escrita
            test_file = output_dir / '.permission_test'
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            error_msg = f'Erro ao acessar o diretório de saída {output_dir}: {str(e)}'
            print(f"[ERRO] {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500
        
        print(f"[DEBUG] Diretório de saída: {output_dir}")
        print(f"[DEBUG] Permissão de escrita: {'sim' if os.access(str(output_dir), os.W_OK) else 'não'}")
        
        # Nome do arquivo de saída
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"{nome_tabela}_{timestamp}.json"
        caminho_json = output_dir / nome_arquivo
        
        print(f"[DEBUG] Caminho do JSON de saída: {caminho_json}")
        
        # Salvar CSV temporário
        temp_csv = output_dir / f"temp_{timestamp}.csv"
        print(f"[DEBUG] Salvando CSV temporário em: {temp_csv}")
        
        try:
            with open(temp_csv, 'w', newline='', encoding='utf-8') as f:
                if dados_csv:
                    # Escrever cabeçalhos com delimitador ';'
                    writer = csv.DictWriter(f, fieldnames=dados_csv[0].keys(), delimiter=';')
                    writer.writeheader()
                    # Escrever dados
                    writer.writerows(dados_csv)
                    print(f"[DEBUG] CSV temporário salvo com sucesso: {temp_csv}")
        except Exception as e:
            error_msg = f'Erro ao salvar CSV temporário: {str(e)}'
            print(f"[ERRO] {error_msg}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': error_msg}), 500
            
        # Gerar JSON a partir do CSV
        try:
            print("[DEBUG] Procurando arquivo JSON antigo...")
            
            # Encontrar o arquivo JSON antigo
            json_antigo = None
            upload_dir = Path(app.config['UPLOAD_FOLDER']).resolve()
            
            print(f"[DEBUG] Procurando JSON em: {upload_dir}")
            
            # Listar arquivos JSON no diretório de upload
            json_files = list(upload_dir.glob('*.json'))
            print(f"[DEBUG] Arquivos JSON encontrados: {[f.name for f in json_files]}")
            
            if json_files:
                json_antigo = str(json_files[0])
                print(f"[DEBUG] Usando JSON antigo: {json_antigo}")
            else:
                print("[DEBUG] Nenhum arquivo JSON antigo encontrado")
            
            # Processar CSV para JSON
            print("[DEBUG] Iniciando processamento do CSV para JSON...")
            
            # Importar a função de geração de JSON
            from json_generator import processar_csv_para_json
            
            # Chamar a função para processar o CSV e gerar o JSON
            print(f"[DEBUG] Chamando processar_csv_para_json com: {temp_csv}, {nome_tabela}, {caminho_json}, {json_antigo}")
            
            resultado_json = processar_csv_para_json(
                str(temp_csv),
                str(caminho_json),
                json_antigo
            )
            
            print(f"[DEBUG] Resultado da geração do JSON: {resultado_json}")
            
            # Verificar se o processamento foi bem-sucedido (usando a chave 'sucesso' em vez de 'success')
            if not resultado_json.get('sucesso', False):
                error_msg = resultado_json.get('erro', 'Erro desconhecido ao processar o JSON')
                print(f"[ERRO] {error_msg}")
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 500
            
            # Verificar se o arquivo foi criado
            if not caminho_json.exists():
                error_msg = f'Erro: O arquivo JSON não foi gerado em {caminho_json}'
                print(f"[ERRO] {error_msg}")
                
                # Tentar listar o diretório para debug
                try:
                    files = list(output_dir.glob('*'))
                    print(f"[DEBUG] Conteúdo do diretório {output_dir}: {[f.name for f in files]}")
                except Exception as e:
                    print(f"[DEBUG] Não foi possível listar o diretório: {str(e)}")
                
                return jsonify({
                    'success': False,
                    'error': error_msg,
                    'available_files': [f.name for f in files] if 'files' in locals() else []
                }), 500
            
            # Verificar se o arquivo tem conteúdo
            file_size = caminho_json.stat().st_size
            if file_size == 0:
                error_msg = f'Erro: O arquivo JSON está vazio: {caminho_json}'
                print(f"[ERRO] {error_msg}")
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 500
            
            print(f"[SUCESSO] JSON gerado com sucesso em: {caminho_json} (tamanho: {file_size} bytes)")
            
            # Retornar sucesso
            response_data = {
                'success': True,
                'json_filename': nome_arquivo,
                'message': 'JSON gerado com sucesso!',
                'file_size': file_size,
                'file_path': str(caminho_json)
            }
            
            print(f"[DEBUG] Resposta de sucesso: {json.dumps(response_data, indent=2)}")
            
            return jsonify(response_data)
            
        except Exception as e:
            error_msg = f'Erro ao processar o CSV: {str(e)}'
            print(f"[ERRO] {error_msg}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                'success': False,
                'error': error_msg,
                'traceback': str(traceback.format_exc())
            }), 500
            
        finally:
            # Remover CSV temporário
            try:
                if temp_csv.exists():
                    temp_csv.unlink()
                    print(f"[DEBUG] Arquivo temporário removido: {temp_csv}")
            except Exception as e:
                print(f"[AVISO] Não foi possível remover o arquivo temporário {temp_csv}: {str(e)}")
            
    except Exception as e:
        error_msg = f'Erro inesperado: {str(e)}'
        print(f"[ERRO] {error_msg}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': error_msg,
            'traceback': str(traceback.format_exc())
        }), 500

@app.route('/download_json/<path:filename>')
def download_json(filename):
    """
    Endpoint para download de arquivo JSON
    
    Verifica se o arquivo existe no diretório de saída e o envia como anexo.
    """
    print(f"\n[DEBUG] Iniciando download do arquivo: {filename}")
    
    try:
        # Garantir que o nome do arquivo seja seguro
        if not filename or not isinstance(filename, str) or '..' in filename or filename.startswith('/'):
            error_msg = f'Nome de arquivo inválido: {filename}'
            print(f"[ERRO] {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        # Construir o caminho completo do arquivo de forma segura
        output_dir = Path(app.config['OUTPUT_FOLDER']).resolve()
        file_path = output_dir / Path(filename).name  # Usar apenas o nome do arquivo, ignorando qualquer caminho
        
        print(f"[DEBUG] Procurando arquivo em: {file_path}")
        
        # Verificar se o diretório de saída existe
        if not output_dir.exists():
            error_msg = f'Diretório de saída não encontrado: {output_dir}'
            print(f"[ERRO] {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 404
            
        print(f"[DEBUG] Diretório de saída existe: {output_dir}")
        
        # Listar arquivos no diretório para debug
        try:
            available_files = [f.name for f in output_dir.glob('*') if f.is_file()]
            print(f"[DEBUG] Arquivos disponíveis em {output_dir}: {available_files}")
        except Exception as e:
            print(f"[AVISO] Não foi possível listar arquivos em {output_dir}: {str(e)}")
        
        # Verificar se o arquivo existe
        if not file_path.exists():
            error_msg = f'Arquivo não encontrado: {file_path}'
            print(f"[ERRO] {error_msg}")
            return jsonify({
                'success': False, 
                'error': error_msg,
                'available_files': available_files if 'available_files' in locals() else []
            }), 404
            
        print(f"[DEBUG] Arquivo encontrado: {file_path} (tamanho: {file_path.stat().st_size} bytes)")
            
        # Verificar se é um arquivo
        if not file_path.is_file():
            error_msg = f'O caminho especificado não é um arquivo: {file_path}'
            print(f"[ERRO] {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        # Verificar permissões de leitura
        if not os.access(str(file_path), os.R_OK):
            error_msg = f'Permissão negada para ler o arquivo: {file_path}'
            print(f"[ERRO] {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 403
        
        # Verificar se o arquivo está vazio
        if file_path.stat().st_size == 0:
            error_msg = f'O arquivo está vazio: {file_path}'
            print(f"[ERRO] {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        print(f"[DEBUG] Enviando arquivo: {file_path} (tamanho: {file_path.stat().st_size} bytes)")
        
        # Forçar o download como anexo
        try:
            from flask import send_file, Response
            import mimetypes
            
            # Garantir que o caminho é seguro e absoluto
            safe_path = (output_dir / filename).resolve()
            if not safe_path.exists():
                return jsonify({'success': False, 'error': 'Arquivo não encontrado'}), 404
                
            print(f"[DEBUG] Enviando arquivo seguro: {safe_path}")
            
            # Determinar o tipo MIME
            mimetype = 'application/json'
            
            # Ler o conteúdo do arquivo
            with open(safe_path, 'rb') as f:
                file_content = f.read()
            
            # Criar resposta com o conteúdo do arquivo
            response = Response(
                file_content,
                mimetype=mimetype,
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
            
            print(f"[SUCESSO] Arquivo enviado com sucesso: {filename}")
            return response
            
        except Exception as e:
            error_msg = f'Erro ao enviar o arquivo: {str(e)}'
            print(f"[ERRO] {error_msg}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': error_msg}), 500
        
    except Exception as e:
        error_msg = f'Erro inesperado ao processar o download: {str(e)}'
        print(f"[ERRO] {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/clear_cache', methods=['POST'])
def clear_cache():
    """Endpoint para limpar cache manualmente"""
    try:
        cleanup_cache()
        return jsonify({'success': True, 'message': 'Cache limpo com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Inicialização da aplicação
def init_app():
    """Inicializa a aplicação"""
    # Criar diretórios necessários
    setup_directories()
    
    print("\n=== DDL Converter Web Application ===")
    print("Diretórios configurados:")
    print(f"- Upload: {app.config['UPLOAD_FOLDER']}")
    print(f"- Saída: {app.config['OUTPUT_FOLDER']}")
    print("\nAcesse: http://localhost:5000")

def open_browser():
    """Abre o navegador automaticamente após 1.5 segundos"""
    time.sleep(1.5)
    webbrowser.open_new('http://localhost:5000')

if __name__ == '__main__':
    # Inicializar a aplicação
    init_app()
    
    # Iniciar o navegador em uma thread separada
    threading.Thread(target=open_browser).start()
    
    # Iniciar o servidor Flask
    app.run(debug=True, use_reloader=False, port=5000)
