@echo off
chcp 65001 > nul
cls
echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                                                               ║
echo ║      🌍  UNIVERSAL MOD TRANSLATOR - MODO GUI  🌍              ║
echo ║        (Interface Gráfica - Qualquer Jogo/Mod)               ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo 🎮 JOGOS SUPORTADOS:
echo    - Valheim, Minecraft, Skyrim, Stardew Valley
echo    - Terraria, Rimworld, Factorio, e MUITO MAIS!
echo.
echo 📁 FORMATOS SUPORTADOS:
echo    - YAML (.yaml, .yml)
echo    - JSON (.json)
echo    - XML (.xml)
echo    - TXT (.txt)
echo    - CSV (.csv)
echo    - INI/CFG (.ini, .cfg)
echo    - TOML (.toml)
echo.
echo 🌐 IDIOMAS:
echo    - Traduz de/para qualquer idioma
echo    - Português, Inglês, Espanhol, Francês, etc.
echo.
echo 🎯 O QUE FAZ:
echo    - Abre interface gráfica
echo    - Você seleciona o arquivo manualmente
echo    - Escolhe os idiomas
echo    - Tradução com progresso visual
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
echo 🚀 ABRINDO INTERFACE GRÁFICA...
echo.
timeout /t 2 /nobreak > nul

REM Executar o tradutor GUI
python Scripts\UniversalModTranslator.py

REM Se houver erro, mostrar mensagem
if %errorlevel% neq 0 (
    echo.
    echo ═══════════════════════════════════════════════════════════════
    echo.
    echo ❌ Erro ao executar o programa!
    echo.
    echo POSSÍVEIS SOLUÇÕES:
    echo.
    echo 1. ERRO: "ModuleNotFoundError: No module named 'tkinter'"
    echo    → No Windows: tkinter vem com Python, reinstale Python
    echo    → No Linux: sudo apt-get install python3-tk
    echo.
    echo 2. ERRO: "ModuleNotFoundError: No module named 'yaml'"
    echo    → Execute: pip install pyyaml
    echo.
    echo 3. ERRO: Outro erro
    echo    → Verifique as mensagens acima
    echo.
    pause
)
