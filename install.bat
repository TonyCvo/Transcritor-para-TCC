@echo off
echo ========================================
echo    Instalador do Transcritor de Audio
echo ========================================
echo.

echo Instalando dependencias essenciais...
pip install pyaudio SpeechRecognition anthropic sounddevice numpy soundfile

echo.
echo Instalando dependencias opcionais para PDF...
pip install PyMuPDF

echo.
echo Instalando dependencias para documentos Word...
pip install python-docx

echo.
echo ========================================
echo    Instalacao concluida!
echo ========================================
echo.
echo Para executar o programa:
echo python "TCC 2.py"
echo.
echo Lembre-se de configurar sua API key no arquivo!
echo.
pause
