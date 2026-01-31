@echo off
REM Build Harmonic Stack Models - Windows
REM Ghost in the Machine Labs

cd /d "%~dp0"

echo ============================================
echo   HARMONIC STACK MODEL BUILDER
echo   Ghost in the Machine Labs
echo ============================================
echo.

REM Check Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Ollama is not running
    echo Start Ollama with: ollama serve
    pause
    exit /b 1
)

echo Pulling base models...
echo.

ollama pull qwen3:4b
ollama pull qwen3:8b
ollama pull qwen3:14b

echo.
echo Building Harmonic Stack models...
echo.

echo Building executive...
ollama create executive -f models\executive.Modelfile
echo   Done.
echo.

echo Building operator...
ollama create operator -f models\operator.Modelfile
echo   Done.
echo.

echo Building technical_director...
ollama create technical_director -f models\technical_director.Modelfile
echo   Done.
echo.

echo Building research_director...
ollama create research_director -f models\research_director.Modelfile
echo   Done.
echo.

echo Building creative_director...
ollama create creative_director -f models\creative_director.Modelfile
echo   Done.
echo.

echo Building coder...
ollama create coder -f models\coder.Modelfile
echo   Done.
echo.

echo Building analyst...
ollama create analyst -f models\analyst.Modelfile
echo   Done.
echo.

echo ============================================
echo   BUILD COMPLETE
echo ============================================
echo.
echo Available models:
ollama list
echo.
echo Run 'python harmonic_launcher.py --start --preload' to deploy the stack.
pause
