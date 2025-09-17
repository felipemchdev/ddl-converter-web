#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DDL Converter - Inicializador Automático
========================================

Script para inicializar automaticamente o DDL Converter Web App
- Verifica se Python está instalado
- Instala dependências automaticamente
- Inicia a aplicação web
- Abre o navegador automaticamente

Para usar: Duplo clique neste arquivo!

Autor: Felipe Machado - Serasa Experian
Data: 15/09/2025
"""

import sys
import subprocess
import os
import time
import webbrowser
from pathlib import Path

def print_banner():
    """Exibe banner de inicialização"""
    print("=" * 60)
    print("🚀 DDL CONVERTER WEB APPLICATION")
    print("=" * 60)
    print("📋 Inicializador Automático")
    print("👤 Desenvolvido por Felipe Machado - Serasa Experian")
    print("📅 Data: 15/09/2025")
    print("=" * 60)
    print()

def check_python():
    """Verifica se Python está instalado"""
    print("🔍 Verificando instalação do Python...")
    
    try:
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            print(f"✅ Python {version.major}.{version.minor}.{version.micro} encontrado!")
            return True
        else:
            print(f"❌ Python {version.major}.{version.minor} é muito antigo!")
            print("   Necessário Python 3.8 ou superior")
            return False
    except Exception as e:
        print(f"❌ Erro ao verificar Python: {e}")
        return False

def install_dependencies():
    """Instala dependências automaticamente"""
    print("\n📦 Verificando e instalando dependências...")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ Arquivo requirements.txt não encontrado!")
        return False
    
    try:
        # Verificar se Flask já está instalado
        try:
            import flask
            print("✅ Flask já está instalado!")
            return True
        except ImportError:
            print("📥 Instalando Flask e dependências...")
            
        # Instalar dependências
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--user"
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            print("✅ Dependências instaladas com sucesso!")
            return True
        else:
            print("❌ Erro ao instalar dependências:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout ao instalar dependências (>2 minutos)")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def start_application():
    """Inicia a aplicação web"""
    print("\n🚀 Iniciando DDL Converter Web App...")
    
    app_file = Path("app.py")
    if not app_file.exists():
        print("❌ Arquivo app.py não encontrado!")
        return False
    
    try:
        print("🌐 Servidor web iniciando...")
        print("📱 O navegador abrirá automaticamente em alguns segundos...")
        print("🔗 URL: http://localhost:5000")
        print("\n" + "=" * 60)
        print("💡 DICA: Para parar o servidor, pressione Ctrl+C")
        print("=" * 60)
        print()
        
        # Aguardar um pouco antes de iniciar
        time.sleep(2)
        
        # Executar app.py
        subprocess.run([sys.executable, "app.py"], check=True)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor interrompido pelo usuário")
        print("👋 Obrigado por usar o DDL Converter!")
        return True
    except Exception as e:
        print(f"❌ Erro ao iniciar aplicação: {e}")
        return False

def show_error_help():
    """Mostra ajuda em caso de erro"""
    print("\n" + "=" * 60)
    print("🆘 PRECISA DE AJUDA?")
    print("=" * 60)
    print("📋 Problemas comuns e soluções:")
    print()
    print("1️⃣ Python não instalado:")
    print("   • Baixe em: https://python.org")
    print("   • Marque 'Add to PATH' durante instalação")
    print()
    print("2️⃣ Erro de permissão:")
    print("   • Execute como Administrador")
    print("   • Clique com botão direito → 'Executar como administrador'")
    print()
    print("3️⃣ Erro de internet:")
    print("   • Verifique conexão com internet")
    print("   • Necessário para baixar dependências")
    print()
    print("📞 Suporte técnico:")
    print("   📧 felipe.machado2@experian.com")
    print("=" * 60)

def main():
    """Função principal"""
    try:
        print_banner()
        
        # Verificar Python
        if not check_python():
            show_error_help()
            input("\n⏸️  Pressione Enter para sair...")
            return
        
        # Instalar dependências
        if not install_dependencies():
            show_error_help()
            input("\n⏸️  Pressione Enter para sair...")
            return
        
        # Iniciar aplicação
        start_application()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Processo interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        show_error_help()
    finally:
        input("\n⏸️  Pressione Enter para sair...")

if __name__ == "__main__":
    main()
