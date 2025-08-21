import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import pyaudio
import wave
import speech_recognition as sr
import anthropic
import os
from datetime import datetime
import numpy as np
import sounddevice as sd
import subprocess
import platform
import re
import time
import soundfile as sf
from config import ANTHROPIC_API_KEY

# Importações opcionais para funcionalidades específicas
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from docx import Document
except ImportError:
    Document = None

# Removido soundcard - não é necessário

class AudioTranscriberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Transcritor de Áudio com Claude API - Microfone + Sistema")
        self.root.geometry("900x800")
        
        # Configurações de áudio otimizadas
        self.chunk = 512  # Reduzir chunk size para menor latência
        self.format = pyaudio.paInt16
        self.channels = 2
        self.rate = 16000  # Usar 16kHz em vez de 44.1kHz para transcrição mais rápida
        self.recording = False
        self.audio_frames_mic = []
        self.audio_frames_system = []
        self.combined_audio = []
        
        # Cliente Claude API
        self.client = anthropic.Anthropic(
            api_key = ANTHROPIC_API_KEY
        )
        
        # Otimização: Cache para respostas da API
        self.response_cache = {}
        
        # Otimização: Thread pool para operações paralelas
        self.thread_pool = []
        
        # Variáveis
        self.selected_document_path = None
        self.document_content = ""
        self.document_loaded = False
        self.audio_devices = self.get_audio_devices()
        self.selected_mic_device = None
        self.selected_system_device = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar redimensionamento
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=2)  # Mais espaço para documento
        main_frame.rowconfigure(4, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        # Seção de documento
        doc_frame = ttk.LabelFrame(main_frame, text="Documento", padding="5")
        doc_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        doc_frame.columnconfigure(1, weight=1)
        
        ttk.Button(doc_frame, text="Selecionar PDF/Documento", 
                  command=self.select_document).grid(row=0, column=0, padx=(0, 10))
        
        self.doc_label = ttk.Label(doc_frame, text="Nenhum documento selecionado")
        self.doc_label.grid(row=0, column=1, sticky=tk.W)
        
        # Adicionar progress bar para conversão
        self.conversion_progress = ttk.Progressbar(doc_frame, mode='indeterminate')
        self.conversion_progress.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        self.conversion_progress.grid_remove()  # Ocultar inicialmente
        
        # Label para mostrar status da conversão
        self.conversion_status = ttk.Label(doc_frame, text="")
        self.conversion_status.grid(row=2, column=0, columnspan=2, sticky=tk.W)
        
        # Text widget para mostrar prévia do conteúdo convertido
        preview_frame = ttk.LabelFrame(doc_frame, text="Prévia do Conteúdo Convertido")
        preview_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        self.content_preview = scrolledtext.ScrolledText(
            preview_frame, height=4, wrap=tk.WORD, state=tk.DISABLED
        )
        self.content_preview.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Seção de configuração de áudio
        audio_config_frame = ttk.LabelFrame(main_frame, text="Configuração de Áudio", padding="5")
        audio_config_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        audio_config_frame.columnconfigure(2, weight=1)
        audio_config_frame.columnconfigure(4, weight=1)
        
        # Checkbox para usar microfone
        self.use_mic_var = tk.BooleanVar(value=True)
        self.use_mic_check = ttk.Checkbutton(audio_config_frame, text="Usar Microfone", 
                                            variable=self.use_mic_var)
        self.use_mic_check.grid(row=0, column=0, padx=(0, 10))
        
        ttk.Label(audio_config_frame, text="Microfone:").grid(row=0, column=1, padx=(0, 5))
        self.mic_combo = ttk.Combobox(audio_config_frame, state="readonly")
        self.mic_combo.grid(row=0, column=2, padx=(0, 20), sticky=(tk.W, tk.E))
        
        ttk.Label(audio_config_frame, text="Áudio Sistema:").grid(row=0, column=3, padx=(0, 5))
        self.system_combo = ttk.Combobox(audio_config_frame, state="readonly")
        self.system_combo.grid(row=0, column=4, sticky=(tk.W, tk.E))
        
        ttk.Button(audio_config_frame, text="🔄 Atualizar Dispositivos", 
                   command=self.refresh_audio_devices).grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(audio_config_frame, text="📋 Listar Todos os Dispositivos", 
                   command=self.list_all_devices).grid(row=1, column=2, columnspan=2, pady=(10, 0))
        
        self.populate_audio_devices()
        
        # Seção de áudio
        audio_frame = ttk.LabelFrame(main_frame, text="Gravação de Áudio", padding="5")
        audio_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.record_button = ttk.Button(audio_frame, text="🎤 Começar a Gravar", 
                                        command=self.toggle_recording)
        self.record_button.grid(row=0, column=0, padx=(0, 10))
        
        self.status_label = ttk.Label(audio_frame, text="Pronto para gravar")
        self.status_label.grid(row=0, column=1)
        
        # Seção de transcrição
        transcription_frame = ttk.LabelFrame(main_frame, text="Transcrição do Áudio", padding="5")
        transcription_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        transcription_frame.columnconfigure(0, weight=1)
        transcription_frame.rowconfigure(0, weight=1)
        
        self.transcription_text = scrolledtext.ScrolledText(
            transcription_frame, height=6, wrap=tk.WORD
        )
        self.transcription_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Botão para processar com Claude
        ttk.Button(main_frame, text="📤 Enviar para Claude", 
                  command=self.process_with_claude).grid(row=5, column=0, pady=(0, 10))
        
        # Seção de resposta do Claude
        response_frame = ttk.LabelFrame(main_frame, text="Resposta do Claude", padding="5")
        response_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        response_frame.columnconfigure(0, weight=1)
        response_frame.rowconfigure(0, weight=1)
        
        self.response_text = scrolledtext.ScrolledText(
            response_frame, height=8, wrap=tk.WORD
        )
        self.response_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
    def select_document(self):
        """Seleciona e converte um documento imediatamente"""
        file_path = filedialog.askopenfilename(
            title="Selecionar Documento",
            filetypes=[
                ("PDFs", "*.pdf"),
                ("Arquivos de texto", "*.txt"),
                ("Documentos Word", "*.docx"),
                ("Todos os arquivos", "*.*")
            ]
        )
        
        if file_path:
            self.selected_document_path = file_path
            filename = os.path.basename(file_path)
            self.doc_label.config(text=f"Convertendo: {filename}")
            
            # Mostrar progress bar
            self.conversion_progress.grid()
            self.conversion_progress.start()
            self.conversion_status.config(text="Convertendo documento para texto...")
            
            # Converter documento em thread separada
            threading.Thread(target=self.convert_document, args=(file_path,), daemon=True).start()
    
    def convert_document(self, file_path):
        """Converte o documento para texto em background"""
        try:
            filename = os.path.basename(file_path)
            
            if file_path.endswith('.pdf'):
                self.document_content = self.extract_pdf_text(file_path)
            elif file_path.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as file:
                    self.document_content = file.read()
            elif file_path.endswith('.docx'):
                if Document is not None:
                    doc = Document(file_path)
                    self.document_content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                else:
                    self.root.after(0, lambda: messagebox.showerror("Erro", "Para arquivos .docx, instale: pip install python-docx"))
                    return
            else:
                # Tentar ler como texto
                with open(file_path, 'r', encoding='utf-8') as file:
                    self.document_content = file.read()
            
            # Atualizar interface na thread principal
            self.root.after(0, lambda: self.document_conversion_complete(filename))
            
        except Exception as e:
            error_msg = f"Erro ao converter documento: {str(e)}"
            self.root.after(0, lambda: self.document_conversion_error(error_msg))
    
    def extract_pdf_text(self, pdf_path):
        """Extrai texto de PDF usando múltiplas bibliotecas como fallback - OTIMIZADO"""
        text_content = ""
        
        # Tentar com PyMuPDF primeiro (mais rápido)
        if fitz is not None:
            try:
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    page_text = page.get_text()
                    if page_text.strip():
                        text_content += f"\n--- Página {page_num + 1} ---\n"
                        text_content += page_text + '\n'
                doc.close()
                
                if text_content.strip():
                    return text_content
                    
            except Exception as e:
                print(f"Erro PyMuPDF: {e}")
        
        # Tentar com PyPDF2 como segunda opção
        if PyPDF2 is not None:
            try:
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num, page in enumerate(pdf_reader.pages):
                        page_text = page.extract_text()
                        if page_text.strip():  # Se há texto na página
                            text_content += f"\n--- Página {page_num + 1} ---\n"
                            text_content += page_text + '\n'
                
                if text_content.strip():
                    return text_content
                    
            except Exception as e:
                print(f"Erro PyPDF2: {e}")
        
        # Tentar com pdfplumber como terceira opção
        if pdfplumber is not None:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text_content += f"\n--- Página {page_num + 1} ---\n"
                            text_content += page_text + '\n'
                
                if text_content.strip():
                    return text_content
                    
            except Exception as e:
                print(f"Erro pdfplumber: {e}")
        
        # Se nenhuma biblioteca funcionou
        if not text_content.strip():
            raise Exception("Não foi possível extrair texto do PDF. Instale uma das bibliotecas: pip install PyPDF2 ou pip install pdfplumber ou pip install PyMuPDF")
        
        return text_content
    
    def document_conversion_complete(self, filename):
        """Callback quando conversão do documento é concluída"""
        # Parar progress bar
        self.conversion_progress.stop()
        self.conversion_progress.grid_remove()
        
        # Atualizar labels
        char_count = len(self.document_content)
        word_count = len(self.document_content.split())
        
        self.doc_label.config(text=f"✅ {filename}")
        self.conversion_status.config(
            text=f"Conversão concluída: {char_count:,} caracteres, {word_count:,} palavras"
        )
        
        # Mostrar prévia do conteúdo
        self.content_preview.config(state=tk.NORMAL)
        self.content_preview.delete(1.0, tk.END)
        
        # Mostrar primeiros 500 caracteres como prévia
        preview_text = self.document_content[:500]
        if len(self.document_content) > 500:
            preview_text += "... (conteúdo truncado para prévia)"
            
        self.content_preview.insert(tk.END, preview_text)
        self.content_preview.config(state=tk.DISABLED)
        
        self.document_loaded = True
        messagebox.showinfo("Sucesso", f"Documento convertido com sucesso!\n{char_count:,} caracteres extraídos.")
    
    def document_conversion_error(self, error_msg):
        """Callback quando há erro na conversão"""
        # Parar progress bar
        self.conversion_progress.stop()
        self.conversion_progress.grid_remove()
        
        # Mostrar erro
        self.doc_label.config(text="❌ Erro na conversão")
        self.conversion_status.config(text=error_msg)
        
        self.document_loaded = False
        messagebox.showerror("Erro", error_msg)
    
    def get_audio_devices(self):
        """Obtém lista de dispositivos de áudio disponíveis usando PyAudio"""
        try:
            p = pyaudio.PyAudio()
            input_devices = []
            output_devices = []
            
            print("🔍 Detectando dispositivos de áudio com PyAudio...")
            
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                device_name = device_info['name']
                input_channels = device_info['maxInputChannels']
                output_channels = device_info['maxOutputChannels']
                
                print(f"  Dispositivo {i}: {device_name}")
                print(f"    Canais de entrada: {input_channels}")
                print(f"    Canais de saída: {output_channels}")
                
                # Dispositivos de entrada (microfones)
                if input_channels > 0:
                    input_devices.append({
                        'index': i,
                        'name': device_name,
                        'channels': input_channels,
                        'hostapi': device_info['hostApi']
                    })
                    print(f"    ✅ Adicionado como dispositivo de entrada")
                
                # Dispositivos de saída
                if output_channels > 0:
                    output_devices.append({
                        'index': i,
                        'name': device_name,
                        'channels': output_channels,
                        'hostapi': device_info['hostApi']
                    })
                    print(f"    ✅ Adicionado como dispositivo de saída")
            
            p.terminate()
            
            print(f"📋 Total de dispositivos encontrados:")
            print(f"  Entrada (microfones): {len(input_devices)}")
            print(f"  Saída (alto-falantes): {len(output_devices)}")
            
            return {
                'input': input_devices,
                'output': output_devices
            }
        except Exception as e:
            print(f"❌ Erro ao obter dispositivos: {e}")
            return {'input': [], 'output': []}
    
    def populate_audio_devices(self):
        """Popula as comboboxes com dispositivos disponíveis"""
        print("🎤 Populando comboboxes de dispositivos de áudio...")
        
        # Microfone (dispositivos de entrada)
        mic_options = []
        for device in self.audio_devices['input']:
            mic_options.append(f"{device['name']} (ID: {device['index']})")
            print(f"  🎤 Microfone: {device['name']} (ID: {device['index']})")
        
        self.mic_combo['values'] = mic_options
        if mic_options:
            self.mic_combo.set(mic_options[0])
            print(f"  ✅ Combobox de microfone populada com {len(mic_options)} dispositivos")
        else:
            print("  ⚠️ Nenhum dispositivo de microfone encontrado")
        
        # Áudio do sistema (dispositivos de saída + dispositivos especiais)
        system_options = []
        
        # Adicionar dispositivos de saída como opções de sistema
        for device in self.audio_devices['output']:
            device_name_lower = device['name'].lower()
            
            # Palavras-chave para detectar microfones e excluí-los
            mic_keywords = ['microfone', 'mic', 'headset mic', 'headphone mic']
            is_microphone = any(keyword in device_name_lower for keyword in mic_keywords)
            
            if not is_microphone:
                system_options.append(f"{device['name']} (ID: {device['index']})")
                print(f"  🔊 Sistema: {device['name']} (ID: {device['index']})")
        
        # Adicionar opções especiais para captura de áudio do sistema
        system_options.extend([
            "Microsoft Sound Mapper (Padrão)",
            "Driver de Captura (Padrão)",
            "Stereo Mix (se disponível)"
        ])
        
        # Se não encontrou dispositivos específicos, adicionar opções genéricas
        if len(system_options) <= 3:  # Só as opções especiais
            system_options.extend([
                "Nenhum dispositivo de sistema encontrado",
                "Apenas Microfone"
            ])
        
        self.system_combo['values'] = system_options
        if system_options:
            self.system_combo.set(system_options[0])
            print(f"  ✅ Combobox de sistema populada com {len(system_options)} opções")
        else:
            print("  ⚠️ Nenhuma opção de sistema encontrada")
        
        print("🎵 População de dispositivos concluída!")
    
    def debug_audio_devices(self):
        """Função para debug dos dispositivos de áudio"""
        print("\n🔍 DEBUG: Dispositivos de áudio detectados")
        print("=" * 50)
        
        print("🎤 DISPOSITIVOS DE ENTRADA (MICROFONES):")
        if self.audio_devices['input']:
            for device in self.audio_devices['input']:
                print(f"  ✅ {device['name']} (ID: {device['index']}) - {device['channels']} canais")
        else:
            print("  ❌ Nenhum dispositivo de entrada encontrado")
        
        print("\n🔊 DISPOSITIVOS DE SAÍDA (ALTO-FALANTES):")
        if self.audio_devices['output']:
            for device in self.audio_devices['output']:
                print(f"  ✅ {device['name']} (ID: {device['index']}) - {device['channels']} canais")
        else:
            print("  ❌ Nenhum dispositivo de saída encontrado")
        
        print("\n📋 COMO ESTÃO AS COMBOBOXES:")
        print(f"  Microfone: {self.mic_combo.get()}")
        print(f"  Sistema: {self.system_combo.get()}")
        print("=" * 50)
    
    def refresh_audio_devices(self):
        """Atualiza a lista de dispositivos de áudio"""
        self.audio_devices = self.get_audio_devices()
        self.populate_audio_devices()
        self.debug_audio_devices()  # Debug após atualização
        messagebox.showinfo("Sucesso", "Dispositivos de áudio atualizados!")
    
    def list_all_devices(self):
        """Lista todos os dispositivos de áudio disponíveis"""
        try:
            p = pyaudio.PyAudio()
            device_list = "📋 TODOS OS DISPOSITIVOS DE ÁUDIO DISPONÍVEIS:\n\n"
            
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                device_name = device_info['name']
                input_channels = device_info['maxInputChannels']
                output_channels = device_info['maxOutputChannels']
                
                device_list += f"Dispositivo {i}:\n"
                device_list += f"  Nome: {device_name}\n"
                device_list += f"  Canais de entrada: {input_channels}\n"
                device_list += f"  Canais de saída: {output_channels}\n"
                device_list += f"  Host API: {device_info['hostApi']}\n"
                device_list += "-" * 50 + "\n"
            
            p.terminate()
            
            # Mostrar em uma janela de texto
            device_window = tk.Toplevel(self.root)
            device_window.title("Dispositivos de Áudio")
            device_window.geometry("600x500")
            
            text_widget = scrolledtext.ScrolledText(device_window, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(tk.END, device_list)
            text_widget.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao listar dispositivos: {str(e)}")
                
    def toggle_recording(self):
        """Inicia ou para a gravação"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
            
    def start_recording(self):
        """Inicia a gravação em uma thread separada"""
        # Verificar se pelo menos um dispositivo está selecionado
        use_mic = self.use_mic_var.get()
        system_text = self.system_combo.get()
        
        if not use_mic and (not system_text or "Nenhum dispositivo" in system_text):
            messagebox.showwarning("Aviso", "Selecione pelo menos um dispositivo de áudio!")
            return
            
        if use_mic and not self.mic_combo.get():
            messagebox.showwarning("Aviso", "Selecione um dispositivo de microfone!")
            return
            
        self.recording = True
        
        # Atualizar texto do botão baseado no que será gravado
        if use_mic and system_text and "Nenhum dispositivo" not in system_text:
            self.record_button.config(text="🛑 Parar Gravação (Mic + Sistema)")
            self.status_label.config(text="Gravando microfone + sistema...")
        elif use_mic:
            self.record_button.config(text="🛑 Parar Gravação (Apenas Mic)")
            self.status_label.config(text="Gravando apenas microfone...")
        else:
            self.record_button.config(text="🛑 Parar Gravação (Apenas Sistema)")
            self.status_label.config(text="Gravando apenas sistema...")
            
        self.audio_frames_mic = []
        self.audio_frames_system = []
        self.combined_audio = []
        
        # Iniciar gravação em thread separada
        threading.Thread(target=self.record_audio_combined, daemon=True).start()
        
    def record_audio_combined(self):
        """Grava áudio do microfone e do sistema simultaneamente"""
        try:
            use_mic = self.use_mic_var.get()
            system_text = self.system_combo.get()
            
            # Gravar microfone se selecionado
            if use_mic:
                mic_text = self.mic_combo.get()
                mic_index = None
                if mic_text:
                    # Extrair ID do dispositivo do texto
                    match = re.search(r'ID: (\d+)', mic_text)
                    if match:
                        mic_index = int(match.group(1))
                
                duration_chunk = 0.1  # 100ms chunks
                
                def mic_callback(indata, frames, time, status):
                    if status:
                        print(f"Mic status: {status}")
                    if self.recording:
                        self.audio_frames_mic.append(indata.copy())
                
                # Iniciar gravação do microfone
                mic_stream = sd.InputStream(
                    device=mic_index,
                    channels=1,
                    samplerate=self.rate,
                    callback=mic_callback,
                    blocksize=int(self.rate * duration_chunk)
                )
                
                # Se também vai gravar sistema, fazer simultaneamente
                if system_text and "Nenhum dispositivo" not in system_text:
                    system_method = self.get_system_audio_method()
                    
                    with mic_stream:
                        if system_method == "wasapi":
                            self.record_system_audio_wasapi()
                        elif system_method == "soundflower":
                            self.record_system_audio_soundflower()
                        else:
                            # Fallback: só gravar microfone
                            self.record_mic_only()
                else:
                    # Só gravar microfone
                    with mic_stream:
                        self.record_mic_only()
            else:
                # Só gravar sistema
                if system_text and "Nenhum dispositivo" not in system_text:
                    system_method = self.get_system_audio_method()
                    
                    if system_method == "wasapi":
                        self.record_system_audio_wasapi()
                    elif system_method == "soundflower":
                        self.record_system_audio_soundflower()
                    else:
                        # Fallback: não gravar nada
                        while self.recording:
                            time.sleep(0.1)
                else:
                    # Não gravar nada
                    while self.recording:
                        time.sleep(0.1)
                    
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro de Áudio", f"Erro na gravação: {str(e)}"))
    
    def get_system_audio_method(self):
        """Determina o método para capturar áudio do sistema baseado no OS"""
        system = platform.system().lower()
        if system == "windows":
            return "wasapi"
        elif system == "darwin":  # macOS
            return "soundflower"
        else:  # Linux
            return "pulse"
    
    def record_system_audio_wasapi(self):
        """Grava áudio do sistema no Windows - VERSÃO MELHORADA"""
        try:
            if platform.system().lower() != "windows":
                self.record_mic_only()
                return
                
            # Obter dispositivo selecionado na combobox
            system_text = self.system_combo.get()
            system_index = None
            
            if system_text and "ID:" in system_text:
                # Extrair ID do dispositivo do texto
                match = re.search(r'ID: (\d+)', system_text)
                if match:
                    system_index = int(match.group(1))
                    print(f"🎵 Usando dispositivo selecionado: {system_text}")
                    
                    # Verificar se não é um microfone
                    if any(keyword in system_text.lower() for keyword in ['microfone', 'mic', 'headset', 'logi']):
                        print("⚠️ Dispositivo selecionado é um microfone, não um dispositivo de sistema")
                        print("💡 Selecione um dispositivo como 'Microsoft Sound Mapper' ou 'Driver de captura'")
                        self.record_mic_only()
                        return
                else:
                    print("⚠️ Não foi possível extrair ID do dispositivo selecionado")
                    self.record_mic_only()
                    return
            else:
                print("⚠️ Nenhum dispositivo de sistema selecionado")
                self.record_mic_only()
                return
            
            # Verificar se o dispositivo é válido
            p = pyaudio.PyAudio()
            try:
                device_info = p.get_device_info_by_index(system_index)
                device_name = device_info['name']
                input_channels = device_info['maxInputChannels']
                output_channels = device_info['maxOutputChannels']
                
                print(f"🔍 Verificando dispositivo: {device_name}")
                print(f"  Canais de entrada: {input_channels}")
                print(f"  Canais de saída: {output_channels}")
                
                # Verificar se o dispositivo tem entrada OU saída
                if input_channels == 0 and output_channels == 0:
                    print("❌ Dispositivo selecionado não tem canais de entrada nem saída")
                    self.record_mic_only()
                    return
                
                # Determinar se é dispositivo de entrada ou saída
                is_output_device = output_channels > 0 and input_channels == 0
                is_input_device = input_channels > 0
                
                if is_output_device:
                    print(f"🎵 Dispositivo de saída detectado: {device_name}")
                    print("🔄 Tentando gravar dispositivo de saída usando loopback...")
                    
                    # Para dispositivos de saída, tentar usar WASAPI loopback
                    try:
                        # Tentar abrir stream de entrada com loopback
                        stream = p.open(
                            format=self.format,
                            channels=min(2, output_channels),  # Usar canais de saída
                            rate=self.rate,
                            input=True,
                            input_device_index=system_index,
                            frames_per_buffer=self.chunk
                        )
                        print(f"✅ Stream de loopback aberto para: {device_name}")
                    except Exception as e:
                        print(f"❌ Erro ao abrir loopback para dispositivo de saída: {e}")
                        print("💡 Tentando método alternativo...")
                        
                        # Método alternativo: usar sounddevice para loopback
                        try:
                            def output_callback(indata, frames, time, status):
                                if status:
                                    print(f"Output status: {status}")
                                if self.recording:
                                    self.audio_frames_system.append(indata.copy())
                            
                            # Usar sounddevice para loopback
                            with sd.InputStream(
                                device=system_index,
                                channels=min(2, output_channels),
                                samplerate=self.rate,
                                callback=output_callback,
                                blocksize=int(self.rate * 0.1)
                            ):
                                while self.recording:
                                    time.sleep(0.1)
                            return
                        except Exception as e2:
                            print(f"❌ Método alternativo também falhou: {e2}")
                            self.record_mic_only()
                            return
                elif is_input_device:
                    # Dispositivo de entrada normal
                    stream = p.open(
                        format=self.format,
                        channels=min(2, input_channels),  # Usar máximo 2 canais
                        rate=self.rate,
                        input=True,
                        input_device_index=system_index,
                        frames_per_buffer=self.chunk
                    )
                    print(f"✅ Stream de entrada aberto para: {device_name}")
                else:
                    print("❌ Dispositivo não tem canais de entrada nem saída válidos")
                    self.record_mic_only()
                    return
                
                print(f"🎤 Gravando áudio do sistema usando: {device_name}")
                while self.recording:
                    try:
                        data = stream.read(self.chunk, exception_on_overflow=False)
                        audio_data = np.frombuffer(data, dtype=np.int16)
                        self.audio_frames_system.append(audio_data)
                    except Exception as e:
                        print(f"❌ Erro ao ler áudio do sistema: {e}")
                        break
                
                stream.stop_stream()
                stream.close()
                print("✅ Gravação do sistema concluída")
                
            except Exception as e:
                print(f"❌ Erro ao abrir dispositivo {system_index}: {e}")
                self.record_mic_only()
            finally:
                p.terminate()
                
        except Exception as e:
            print(f"❌ Erro ao gravar áudio do sistema: {e}")
            self.record_mic_only()
    
    def record_system_audio_soundflower(self):
        """Grava áudio do sistema no macOS"""
        # Para macOS, precisa do Soundflower ou BlackHole
        self.record_mic_only()
    
    def record_mic_only(self):
        """Fallback: grava apenas o microfone"""
        while self.recording:
            time.sleep(0.1)
            
    def stop_recording(self):
        """Para a gravação e processa o áudio"""
        self.recording = False
        self.record_button.config(text="🎤 Começar a Gravar")
        self.status_label.config(text="Processando áudio...")
        
        # Processar áudio em thread separada
        threading.Thread(target=self.process_audio, daemon=True).start()
        
    def process_audio(self):
        """Salva o áudio e faz a transcrição com otimizações"""
        try:
            # Verificar se há áudio válido antes de processar
            use_mic = self.use_mic_var.get()
            
            print(f"🔍 Verificando áudio - Use mic: {use_mic}")
            print(f"  Frames mic: {len(self.audio_frames_mic) if self.audio_frames_mic else 0}")
            print(f"  Frames system: {len(self.audio_frames_system) if self.audio_frames_system else 0}")
            
            if use_mic and (not self.audio_frames_mic or len(self.audio_frames_mic) < 5):
                self.root.after(0, lambda: self.update_transcription("Gravação muito curta ou sem áudio do microfone"))
                self.root.after(0, lambda: self.status_label.config(text="Pronto para gravar"))
                return
                
            if not use_mic and (not self.audio_frames_system or len(self.audio_frames_system) < 5):
                self.root.after(0, lambda: self.update_transcription("Gravação muito curta ou sem áudio do sistema"))
                self.root.after(0, lambda: self.status_label.config(text="Pronto para gravar"))
                return

            # Salvar arquivo de áudio temporário
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"temp_audio_{timestamp}.wav"
            
            # Preparar áudio baseado no que foi gravado
            print("🎵 Preparando áudio para processamento...")
            
            if use_mic and self.audio_frames_mic:
                print("  Usando áudio do microfone")
                combined_audio_data = np.concatenate(self.audio_frames_mic, axis=0)
            elif self.audio_frames_system:
                print("  Usando áudio do sistema")
                combined_audio_data = np.concatenate(self.audio_frames_system, axis=0)
            else:
                print("  ❌ Nenhum áudio disponível")
                self.root.after(0, lambda: self.update_transcription("Nenhum áudio gravado"))
                self.root.after(0, lambda: self.status_label.config(text="Pronto para gravar"))
                return
                
            print(f"  Áudio preparado - Shape: {combined_audio_data.shape}")
            
            # Se temos áudio do sistema E microfone, misturar
            if use_mic and self.audio_frames_system:
                try:
                    system_audio_data = np.concatenate(self.audio_frames_system, axis=0)
                    # Ajustar tamanhos se necessário
                    min_len = min(len(combined_audio_data), len(system_audio_data))
                    combined_audio_data = combined_audio_data[:min_len]
                    system_audio_data = system_audio_data[:min_len]
                    
                    # Verificar dimensões dos arrays antes de misturar
                    print(f"Mic shape: {combined_audio_data.shape}")
                    print(f"System shape: {system_audio_data.shape}")
                    
                    # Misturar os áudios (50% cada)
                    if len(system_audio_data.shape) > 1 and system_audio_data.shape[1] == 2:
                        # Sistema stereo
                        if len(combined_audio_data.shape) == 1:
                            # Mic mono - converter para stereo
                            mic_stereo = np.column_stack((combined_audio_data, combined_audio_data))
                            combined_audio_data = (mic_stereo * 0.5 + system_audio_data * 0.5)
                        elif combined_audio_data.shape[1] == 1:
                            # Mic mono - converter para stereo
                            mic_stereo = np.column_stack((combined_audio_data.flatten(), combined_audio_data.flatten()))
                            combined_audio_data = (mic_stereo * 0.5 + system_audio_data * 0.5)
                        else:
                            # Ambos stereo
                            combined_audio_data = (combined_audio_data * 0.5 + system_audio_data * 0.5)
                    else:
                        # Ambos mono ou sistema mono
                        if len(combined_audio_data.shape) > 1:
                            combined_audio_data = combined_audio_data.flatten()
                        if len(system_audio_data.shape) > 1:
                            system_audio_data = system_audio_data.flatten()
                        combined_audio_data = (combined_audio_data * 0.5 + system_audio_data * 0.5)
                        
                except Exception as e:
                    print(f"Erro ao misturar áudios: {e}")
                    print(f"Detalhes do erro: {type(e).__name__}")
                    import traceback
                    traceback.print_exc()
            
            # Salvar usando soundfile
            print(f"💾 Salvando arquivo: {audio_filename}")
            try:
                sf.write(audio_filename, combined_audio_data, self.rate)
                print(f"  ✅ Arquivo salvo com sucesso")
            except Exception as e:
                print(f"  ❌ Erro ao salvar arquivo: {e}")
                self.root.after(0, lambda: self.update_transcription(f"Erro ao salvar áudio: {str(e)}"))
                self.root.after(0, lambda: self.status_label.config(text="Pronto para gravar"))
                return
            
            # Transcrever áudio com otimizações
            print("🎤 Iniciando transcrição...")
            
            if os.path.exists(audio_filename) and os.path.getsize(audio_filename) > 44:  # Mais que header WAV
                print(f"  Arquivo existe - Tamanho: {os.path.getsize(audio_filename)} bytes")
                
                try:
                    recognizer = sr.Recognizer()
                    # Otimização 2: Configurações mais rápidas para transcrição
                    recognizer.energy_threshold = 300  # Reduzir sensibilidade
                    recognizer.dynamic_energy_threshold = False  # Desabilitar ajuste dinâmico
                    
                    print("  Carregando arquivo de áudio...")
                    with sr.AudioFile(audio_filename) as source:
                        audio_data = recognizer.record(source)
                    
                    print("  Enviando para transcrição...")
                    # Otimização 3: Usar configurações mais rápidas
                    transcription = recognizer.recognize_google(
                        audio_data, 
                        language='pt-BR',
                        show_all=False  # Não retornar alternativas
                    )
                    
                    print(f"  ✅ Transcrição concluída: {transcription[:50]}...")
                    # Atualizar interface na thread principal
                    self.root.after(0, lambda: self.update_transcription(transcription))
                    
                except sr.UnknownValueError:
                    print("  ❌ Não foi possível entender o áudio")
                    self.root.after(0, lambda: self.update_transcription("Não foi possível entender o áudio"))
                except sr.RequestError as e:
                    print(f"  ❌ Erro no serviço de reconhecimento: {e}")
                    self.root.after(0, lambda: self.update_transcription(f"Erro no serviço de reconhecimento: {e}"))
                except Exception as e:
                    print(f"  ❌ Erro inesperado na transcrição: {e}")
                    self.root.after(0, lambda: self.update_transcription(f"Erro na transcrição: {str(e)}"))
            else:
                print(f"  ❌ Arquivo não existe ou muito pequeno")
                self.root.after(0, lambda: self.update_transcription("Nenhum áudio gravado"))
            
            # Remover arquivo temporário
            print("🧹 Limpando arquivo temporário...")
            if os.path.exists(audio_filename):
                try:
                    os.remove(audio_filename)
                    print("  ✅ Arquivo removido")
                except Exception as e:
                    print(f"  ⚠️ Erro ao remover arquivo: {e}")
            else:
                print("  ⚠️ Arquivo não encontrado para remoção")
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro ao processar áudio: {str(e)}"))
        
        self.root.after(0, lambda: self.status_label.config(text="Pronto para gravar"))
        
    def update_transcription(self, text):
        """Atualiza o texto da transcrição"""
        self.transcription_text.delete(1.0, tk.END)
        self.transcription_text.insert(tk.END, text)
        
    def process_with_claude(self):
        """Envia a transcrição e documento para Claude com cache e otimizações"""
        transcription = self.transcription_text.get(1.0, tk.END).strip()
        
        if not transcription:
            messagebox.showwarning("Aviso", "Nenhuma transcrição disponível!")
            return
            
        if not self.document_loaded or not self.document_content:
            messagebox.showwarning("Aviso", "Nenhum documento carregado e convertido!")
            return
        
        # Otimização: Verificar cache
        cache_key = f"{hash(self.document_content[:1000])}_{hash(transcription)}"
        if cache_key in self.response_cache:
            self.response_text.delete(1.0, tk.END)
            self.response_text.insert(tk.END, self.response_cache[cache_key])
            return
        
        # Limpar threads antigas
        self.cleanup_threads()
        
        # Processar com Claude em thread separada
        thread = threading.Thread(target=self.send_to_claude, args=(transcription, cache_key), daemon=True)
        self.thread_pool.append(thread)
        thread.start()
        
        # Mostrar status
        self.response_text.delete(1.0, tk.END)
        self.response_text.insert(tk.END, "Processando com Claude...")
        
    def send_to_claude(self, transcription, cache_key=None):
        """Envia dados para Claude API com prompt estruturado e otimizações"""
        try:
            # Construir prompt conforme especificado
            prompt = f"""{self.document_content}

INSTRUÇÕES PARA RESPOSTA:
- Use o documento como base principal
- Adicione informações complementares úteis quando relevante
- Mantenha a resposta concisa (máximo 1000 tokens)
- Priorize clareza e objetividade mas linguagem acessivel

PERGUNTA: {transcription}

RESPOSTA:"""
            
            # Otimização: Usar modelo mais rápido e configurações otimizadas
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Modelo mais rápido que sonnet
                max_tokens=1500,  # Reduzir tokens para resposta mais rápida
                temperature=0.3,  # Menos criatividade = mais velocidade
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            response = message.content[0].text
            
            # Otimização: Salvar no cache se cache_key for fornecido
            if cache_key:
                self.response_cache[cache_key] = response
                # Limitar tamanho do cache para evitar vazamento de memória
                if len(self.response_cache) > 50:
                    # Remover entrada mais antiga
                    oldest_key = next(iter(self.response_cache))
                    del self.response_cache[oldest_key]
            
            # Atualizar interface na thread principal
            self.root.after(0, lambda: self.update_response(response))
            
        except Exception as e:
            error_msg = f"Erro ao processar com Claude: {str(e)}"
            self.root.after(0, lambda: self.update_response(error_msg))
            
    def cleanup_threads(self):
        """Limpa threads antigas para evitar vazamento de memória"""
        self.thread_pool = [t for t in self.thread_pool if t.is_alive()]
    
    def update_response(self, text):
        """Atualiza o texto da resposta"""
        self.response_text.delete(1.0, tk.END)
        self.response_text.insert(tk.END, text)

def main():
    # Verificar dependências essenciais
    missing_deps = []
    
    # Verificar dependências que são importadas diretamente
    try:
        import pyaudio
    except ImportError:
        missing_deps.append("pyaudio")
    
    try:
        import speech_recognition
    except ImportError:
        missing_deps.append("speech_recognition")
    
    try:
        import anthropic
    except ImportError:
        missing_deps.append("anthropic")
    
    try:
        import sounddevice
    except ImportError:
        missing_deps.append("sounddevice")
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        import soundfile
    except ImportError:
        missing_deps.append("soundfile")
    
    if missing_deps:
        print(f"Dependências faltando: {', '.join(missing_deps)}")
        print("\nInstale as dependências necessárias:")
        print("pip install pyaudio speechrecognition anthropic sounddevice numpy soundfile")
        print("pip install python-docx  # (opcional para documentos Word)")
        print("\nPara melhor extração de PDF (escolha uma):")
        print("pip install PyPDF2")
        print("pip install pdfplumber") 
        print("pip install PyMuPDF")
        print("\nPara captura de áudio do sistema:")
        print("Windows: Ative o 'Stereo Mix' nas configurações de som")
        print("macOS: Instale BlackHole ou Soundflower")
        print("Linux: pip install python-pulse-simple")
        return
    
    root = tk.Tk()
    app = AudioTranscriberApp(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Aplicação encerrada pelo usuário")

if __name__ == "__main__":
    main()
