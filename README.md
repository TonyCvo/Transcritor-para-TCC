# 🎤 Transcritor de Áudio com Claude API para pesquisa em documentos

Um aplicativo desktop em Python para transcrição de áudio em tempo real com integração à Claude API, capaz de capturar áudio do microfone e do sistema simultaneamente, o audio integra um prompt que também envia um documento, de forma que se alguém perguntar algo sobre o documento numa reunião o Claude é capaz de responder.

## ✨ Funcionalidades

- **🎤 Gravação de Áudio Dupla**: Opção de captura simultânea de microfone e áudio do sistema
- **📄 Processamento de Documentos**: Suporte para PDF, DOCX e TXT como contexto
- **🤖 Integração Claude API**: Respostas inteligentes baseadas no documento fornecido
- **🎵 Detecção Automática de Dispositivos**: Lista todos os dispositivos de áudio disponíveis
- **⚡ Otimizações de Performance**: Cache de respostas e configurações otimizadas
- **🔄 Interface Intuitiva**: GUI moderna com Tkinter

## 🚀 Instalação

### 1. Clone ou baixe o projeto
```bash
# Se usando git
git clone https://github.com/TonyCvo/Transcritor-para-TCC.git'

# Ou simplesmente baixe os arquivos
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure sua API Key
Edite o arquivo `iniciar.py` e substitua a API key:
```python
self.client = anthropic.Anthropic(
    api_key="sua-api-key-aqui"
)
```

## 📋 Dependências

### Essenciais
- `pyaudio` - Captura de áudio
- `speechrecognition` - Reconhecimento de fala
- `anthropic` - Cliente Claude API
- `sounddevice` - Dispositivos de áudio
- `numpy` - Processamento de dados
- `soundfile` - Manipulação de arquivos de áudio

### Opcionais (para documentos)
- `PyMuPDF` - Extração de PDF (recomendado)
- `PyPDF2` - Alternativa para PDF
- `pdfplumber` - Outra alternativa para PDF
- `python-docx` - Documentos Word

## 🎯 Como Usar

### 1. Iniciar o Aplicativo
```bash
python "iniciar.py"
```

### 2. Configurar Dispositivos
- **Usar Microfone**: Marque a caixa para incluir áudio do microfone
- **Áudio Sistema**: Selecione um dispositivo para capturar áudio do sistema
- **Atualizar Dispositivos**: Clique para recarregar a lista de dispositivos

### 3. Carregar Documento (Opcional)
- Clique em "Selecionar PDF/Documento"
- Escolha um arquivo PDF, DOCX ou TXT
- O documento será convertido e usado como contexto para as respostas

### 4. Gravar Áudio
- Clique em "🎤 Começar a Gravar"
- Fale ou reproduza áudio
- Clique em "🛑 Parar Gravação" quando terminar

### 5. Processar com Claude
- Clique em "📤 Enviar para Claude"
- A transcrição será enviada junto com o documento como contexto
- A resposta aparecerá na seção "Resposta do Claude"

## 🔧 Configuração de Áudio do Sistema

### Windows
Para capturar áudio do sistema (conversa de reuniões, apresentações, música, vídeos, etc.):

1. **Ativar Stereo Mix**:
   - Configurações de Som → Som → Configurações de Som
   - Aba "Gravação" → Clique com botão direito → "Mostrar dispositivos desabilitados"
   - Ative "Stereo Mix"

2. **Dispositivos Alternativos**:
   - Microsoft Sound Mapper - Input
   - Driver de captura de som primário
   - What U Hear (Creative Sound Blaster)

### macOS
- Instale BlackHole ou Soundflower
- Configure como dispositivo de saída

### Linux
```bash
pip install python-pulse-simple
```

## 🎵 Dispositivos Suportados

### Microfones
- Qualquer dispositivo de entrada de áudio
- Headsets USB/Bluetooth
- Microfones integrados

### Sistema
- Alto-falantes
- Fones de ouvido
- Dispositivos de loopback
- Drivers de captura

## ⚙️ Configurações Avançadas

### Otimizações de Performance
- **Taxa de Amostragem**: 16kHz (otimizado para transcrição)
- **Chunk Size**: 512 samples (baixa latência)
- **Cache**: 50 respostas em memória
- **Threading**: Operações não-bloqueantes

### Modelo Claude
- **Modelo**: claude-3-haiku-20240307 (rápido)
- **Max Tokens**: 1500
- **Temperature**: 0.3 (respostas consistentes)

## 🐛 Solução de Problemas

### Erro de Dependências
```bash
# Se houver erro com pyaudio no Windows
pip install pipwin
pipwin install pyaudio

# Ou use conda
conda install pyaudio
```

### Dispositivos Não Detectados
1. Clique em "📋 Listar Todos os Dispositivos"
2. Verifique se o dispositivo aparece na lista
3. Tente "🔄 Atualizar Dispositivos"

### Erro de Transcrição
- Verifique a conexão com a internet
- Confirme se a API key está correta
- Teste com áudio mais claro e sem ruído

### Áudio do Sistema Não Funciona
- Ative "Stereo Mix" nas configurações do Windows
- Teste diferentes dispositivos na combobox
- Verifique se há áudio tocando no sistema

## 📝 Exemplo de Uso

1. **Carregar um PDF** sobre inteligência artificial
2. **Selecionar microfone** e **Microsoft Sound Mapper**
3. **Gravar** uma pergunta sobre IA
4. **Enviar para Claude** - receberá resposta baseada no PDF + informações complementares

## 🤝 Contribuições

Sinta-se à vontade para:
- Reportar bugs
- Sugerir melhorias
- Adicionar novas funcionalidades
- Melhorar a documentação

## 📄 Licença

Este projeto é de uso livre para fins educacionais e pessoais.

## 🔗 Links Úteis

- [Claude API Documentation](https://docs.anthropic.com/)
- [PyAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/)
- [SpeechRecognition Documentation](https://pypi.org/project/SpeechRecognition/)

---

**Desenvolvido com ❤️ em Python**
