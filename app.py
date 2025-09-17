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
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import atexit
import threading
import time

from conversor_ddl import processar_arquivo_ddl

app = Flask(__name__)
app.secret_key = 'ddl-converter-secret-key-2025'

# Configurações
UPLOAD_FOLDER = 'cache/uploads'
OUTPUT_FOLDER = 'cache/output'
ALLOWED_EXTENSIONS = {'txt', 'ddl'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Variáveis globais para controle de processamento
processing_status = {}
processed_files = set()
session_history = []  # Histórico de arquivos processados na sessão

def allowed_file(filename):
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def setup_directories():
    """Cria diretórios necessários"""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(f"{OUTPUT_FOLDER}/dicionarios", exist_ok=True)
    os.makedirs(f"{OUTPUT_FOLDER}/json", exist_ok=True)

def cleanup_cache():
    """Limpa o cache ao iniciar a aplicação"""
    if os.path.exists('cache'):
        shutil.rmtree('cache')
    setup_directories()
    processed_files.clear()
    processing_status.clear()
    session_history.clear()
    print("[CACHE] Diretório cache limpo na inicialização")

def get_file_hash(filepath):
    """Gera hash simples do arquivo baseado no nome e tamanho"""
    stat = os.stat(filepath)
    return f"{os.path.basename(filepath)}_{stat.st_size}_{int(stat.st_mtime)}"

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
                        
                        # Extrair apenas os nomes dos arquivos para download
                        nome_csv = os.path.basename(resultado['caminho_csv'])
                        nome_json = os.path.basename(resultado['caminho_json'])
                        
                        # Adicionar ao histórico da sessão
                        session_history.append({
                            'nome_arquivo': filename,
                            'nome_tabela': resultado['nome_tabela'],
                            'caminho_csv': nome_csv,
                            'caminho_json': nome_json,
                            'num_colunas': resultado['num_colunas'],
                            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                        })
                        
                        processing_status[thread_id] = {
                            'status': 'completed',
                            'progress': 100,
                            'message': f'Arquivo processado com sucesso! Tabela: {resultado["nome_tabela"]}',
                            'result': {
                                'sucesso': True,
                                'nome_tabela': resultado['nome_tabela'],
                                'caminho_csv': nome_csv,
                                'caminho_json': nome_json,
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
                available_files = os.listdir(app.config['OUTPUT_FOLDER'])
            
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
    """Endpoint para download de todos os arquivos em ZIP"""
    try:
        # Criar arquivo ZIP temporário
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        
        with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
            output_path = Path(app.config['OUTPUT_FOLDER'])
            
            # Adicionar todos os arquivos CSV e JSON
            for file_path in output_path.rglob('*'):
                if file_path.is_file() and file_path.suffix in ['.csv', '.json']:
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

@app.route('/session_history')
def get_session_history():
    """Endpoint para obter histórico da sessão"""
    return jsonify({
        'success': True,
        'history': session_history
    })

@app.route('/clear_cache', methods=['POST'])
def clear_cache():
    """Endpoint para limpar cache manualmente"""
    try:
        cleanup_cache()
        return jsonify({'success': True, 'message': 'Cache limpo com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Limpar cache ao iniciar
cleanup_cache()

# Registrar limpeza de cache ao sair
atexit.register(cleanup_cache)

def open_browser():
    """Abre o navegador automaticamente após 1.5 segundos"""
    time.sleep(1.5)  # Aguarda o servidor iniciar
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print("=== DDL Converter Web Application ===")
    print("Iniciando servidor web...")
    print("Abrindo navegador automaticamente...")
    print("Acesse: http://localhost:5000")
    print("=====================================")
    
    # Iniciar thread para abrir navegador
    threading.Timer(1.5, open_browser).start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
