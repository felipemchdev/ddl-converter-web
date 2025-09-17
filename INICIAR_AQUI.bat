@echo off
chcp 65001 >nul
title DDL Converter - Inicializador

echo.
echo ================================================================
echo 🚀 DDL CONVERTER WEB APPLICATION
echo ================================================================
echo 📋 Inicializador Automático - Windows
echo 👤 Desenvolvido por Felipe Machado - Serasa Experian  
echo 📅 Data: 15/09/2025
echo ================================================================
echo.

echo 🔍 Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python não encontrado!
    echo.
    echo 📥 Por favor, instale Python primeiro:
    echo    1. Acesse: https://python.org
    echo    2. Baixe a versão mais recente
    echo    3. IMPORTANTE: Marque "Add to PATH" durante a instalação
    echo.
    pause
    exit /b 1
)

echo ✅ Python encontrado!
echo.

echo 🚀 Iniciando DDL Converter...
python iniciar_ddl_converter.py

echo.
echo 👋 Obrigado por usar o DDL Converter!
pause
