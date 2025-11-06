@echo off
chcp 65001 > nul
cls
echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                                                               ║
echo ║         ⛨  VALHEIM TRANSLATOR - MODO CLI  ⛨                   ║
echo ║            (Tradução Automática - SEM Interface)             ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo 📋 REQUISITOS:
echo    - Arquivo 'collected_items.yaml' na pasta 'Original'
echo.
echo 🎯 O QUE FAZ:
echo    - Traduz automaticamente YAML do Valheim
echo    - Inglês → Português BR
echo    - Usa cache (super rápido em atualizações)
echo    - Salva em 'Traduzido\translations.yaml'
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python não encontrado!
    echo.
    echo Instale Python 3.7+ em: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo ✅ Python OK
echo.

REM Verificar se arquivo de entrada existe
if not exist "Original\collected_items.yaml" (
    echo ❌ ERRO: Arquivo não encontrado!
    echo.
    echo Você precisa colocar o arquivo 'collected_items.yaml'
    echo na pasta 'Original\' antes de executar este script.
    echo.
    echo Para obter o arquivo:
    echo    1. Jogue Valheim com o mod Autolocalization
    echo    2. O arquivo será criado automaticamente
    echo    3. Copie de: C:\Program Files ^(x86^)\Steam\steamapps\common\
    echo       Valheim\BepInEx\config\Autolocalization\collected_items.yaml
    echo.
    pause
    exit /b 1
)

echo ✅ Arquivo de entrada encontrado
echo.

REM Verificar/Instalar dependências
echo 📦 Verificando dependências Python...
pip show deep-translator >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Instalando deep-translator...
    pip install --quiet deep-translator
)

pip show pyyaml >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Instalando pyyaml...
    pip install --quiet pyyaml
)

echo ✅ Dependências OK
echo.
echo ═══════════════════════════════════════════════════════════════
echo.
echo 🚀 INICIANDO TRADUÇÃO...
echo.

REM Executar o tradutor
python Scripts\ValheiMTranslator.py

echo.
echo ═══════════════════════════════════════════════════════════════
echo.

if %errorlevel% equ 0 (
    echo ✅ TRADUÇÃO CONCLUÍDA COM SUCESSO!
    echo.
    echo 📂 Arquivo traduzido em: Traduzido\translations.yaml
    echo.
    echo 📋 PRÓXIMOS PASSOS:
    echo    1. Copie o arquivo 'Traduzido\translations.yaml'
    echo    2. Cole em: C:\Program Files ^(x86^)\Steam\steamapps\common\
    echo       Valheim\BepInEx\config\Autolocalization\translations.yaml
    echo    3. Reinicie o Valheim
    echo.
) else (
    echo ❌ Erro durante a tradução!
    echo.
    echo Verifique as mensagens acima para mais detalhes.
    echo.
)

pause
