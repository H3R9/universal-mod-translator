"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║      ⚔️  UNIVERSAL MOD TRANSLATOR - GUI VERSION  ⚔️           ║
║                                                               ║
║   Traduza mods de QUALQUER jogo para QUALQUER idioma!        ║
║   Suporta: YAML, JSON, XML, TXT, CSV, INI, TOML              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import json
import yaml
import time
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
import threading
import configparser
import xml.etree.ElementTree as ET
import csv
import re

# Try to import toml (optional)
try:
    import toml
    TOML_AVAILABLE = True
except ImportError:
    TOML_AVAILABLE = False


class UniversalModTranslator:
    """Tradutor universal de mods com suporte a múltiplos formatos"""
    
    SUPPORTED_FORMATS = {
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.json': 'JSON',
        '.xml': 'XML',
        '.txt': 'TXT',
        '.csv': 'CSV',
        '.ini': 'INI',
        '.cfg': 'INI',
        '.toml': 'TOML' if TOML_AVAILABLE else None,
    }
    
    AVAILABLE_LANGUAGES = {
        'pt': 'Português (BR)',
        'en': 'English',
        'es': 'Español',
        'fr': 'Français',
        'de': 'Deutsch',
        'it': 'Italiano',
        'ru': 'Русский',
        'ja': '日本語',
        'ko': '한국어',
        'zh-CN': '中文 (简体)',
        'zh-TW': '中文 (繁體)',
    }
    
    def __init__(self):
        # Usa pasta Cache na raiz do projeto (pasta pai de Scripts)
        base_dir = Path(__file__).parent.parent
        self.cache_file = base_dir / "Cache" / "universal_translations_cache.json"
        self.cache_file.parent.mkdir(exist_ok=True)
        self.cache: Dict[str, str] = self.load_cache()
        
    def load_cache(self) -> Dict[str, str]:
        """Carrega o cache de traduções"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_cache(self):
        """Salva o cache de traduções"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def should_skip(self, text: str) -> bool:
        """Verifica se o texto deve ser ignorado"""
        if not text or not isinstance(text, str):
            return True
        
        text = text.strip()
        
        # Muito curto ou só números
        if len(text) < 2 or text.isdigit() or text.replace('.', '').isdigit():
            return True
        
        # URLs, emails, paths
        if any(x in text for x in ['http://', 'https://', 'www.', '@', 'C:\\', '/']):
            return True
        
        # IDs técnicos (muitos underscores ou padrões técnicos)
        if text.count('_') >= 2 and re.match(r'^[\w\-\[\]]+$', text):
            return True
        
        # Prefixos/sufixos técnicos comuns
        tech_patterns = [
            'piece_', 'rae_', 'sapling_', 'Pickable_', 'IG_', 
            '_TW', '_id', '_ID', 'config_', 'mod_'
        ]
        if any(text.startswith(p) or text.endswith(p) for p in tech_patterns):
            return True
        
        return False
    
    def translate_text(self, text: str, src_lang: str, dest_lang: str) -> str:
        """Traduz um texto com cache e retry"""
        if self.should_skip(text):
            return text
        
        # Chave do cache inclui idiomas
        cache_key = f"{src_lang}:{dest_lang}:{text}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Traduzir com retry
        translator = GoogleTranslator(source=src_lang, target=dest_lang)
        for attempt in range(3):
            try:
                translated = translator.translate(text)
                
                if translated and translated != text:
                    self.cache[cache_key] = translated
                    return translated
                return text
                
            except Exception as e:
                if attempt < 2:
                    time.sleep(0.3 * (attempt + 1))
                else:
                    # Falhou, retorna original
                    return text
        
        return text
    
    def translate_batch(self, texts: List[str], src_lang: str, dest_lang: str) -> Dict[str, str]:
        """Traduz um lote de textos (para paralelização)"""
        translator = GoogleTranslator(source=src_lang, target=dest_lang)
        results = {}
        
        for text in texts:
            if self.should_skip(text):
                results[text] = text
                continue
            
            cache_key = f"{src_lang}:{dest_lang}:{text}"
            
            if cache_key in self.cache:
                results[text] = self.cache[cache_key]
                continue
            
            # Traduzir com retry
            for attempt in range(3):
                try:
                    translated = translator.translate(text)
                    if translated and translated != text:
                        self.cache[cache_key] = translated
                        results[text] = translated
                    else:
                        results[text] = text
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(0.3 * (attempt + 1))
                    else:
                        results[text] = text
        
        return results
    
    # ============= LEITORES DE FORMATOS =============
    
    def read_yaml(self, filepath: Path) -> List[Tuple[str, str]]:
        """Lê arquivo YAML e extrai pares chave-valor"""
        items = []
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.rstrip('\n')
            
            # Preservar comentários e linhas especiais
            if not line.strip() or line.strip().startswith('#') or line.startswith(('? >-', ': >-', '  ')):
                items.append((None, line))
                continue
            
            # Parse linha YAML simples
            if ': ' in line:
                key, value = line.split(': ', 1)
                key = key.strip().strip("'\"")
                value = value.strip().strip("'\"")
                items.append((key, value))
            else:
                items.append((None, line))
        
        return items
    
    def read_json(self, filepath: Path) -> Dict:
        """Lê arquivo JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def read_xml(self, filepath: Path) -> ET.ElementTree:
        """Lê arquivo XML"""
        return ET.parse(filepath)
    
    def read_txt(self, filepath: Path) -> List[str]:
        """Lê arquivo TXT linha por linha"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.readlines()
    
    def read_csv(self, filepath: Path) -> List[List[str]]:
        """Lê arquivo CSV"""
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            return list(csv.reader(f))
    
    def read_ini(self, filepath: Path) -> configparser.ConfigParser:
        """Lê arquivo INI/CFG"""
        config = configparser.ConfigParser()
        config.read(filepath, encoding='utf-8')
        return config
    
    def read_toml(self, filepath: Path) -> Dict:
        """Lê arquivo TOML"""
        if not TOML_AVAILABLE:
            raise ImportError("Instale o módulo 'toml': pip install toml")
        with open(filepath, 'r', encoding='utf-8') as f:
            return toml.load(f)
    
    # ============= ESCRITORES DE FORMATOS =============
    
    def write_yaml(self, filepath: Path, items: List[Tuple[str, str]]):
        """Escreve arquivo YAML"""
        with open(filepath, 'w', encoding='utf-8') as f:
            for key, value in items:
                if key is None:
                    f.write(value + '\n')
                else:
                    # Escapar com aspas se tiver ':'
                    if ':' in value:
                        value = f'"{value}"'
                    f.write(f"{key}: {value}\n")
    
    def write_json(self, filepath: Path, data: Dict):
        """Escreve arquivo JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def write_xml(self, filepath: Path, tree: ET.ElementTree):
        """Escreve arquivo XML"""
        tree.write(filepath, encoding='utf-8', xml_declaration=True)
    
    def write_txt(self, filepath: Path, lines: List[str]):
        """Escreve arquivo TXT"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    def write_csv(self, filepath: Path, rows: List[List[str]]):
        """Escreve arquivo CSV"""
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    
    def write_ini(self, filepath: Path, config: configparser.ConfigParser):
        """Escreve arquivo INI/CFG"""
        with open(filepath, 'w', encoding='utf-8') as f:
            config.write(f)
    
    def write_toml(self, filepath: Path, data: Dict):
        """Escreve arquivo TOML"""
        if not TOML_AVAILABLE:
            raise ImportError("Instale o módulo 'toml': pip install toml")
        with open(filepath, 'w', encoding='utf-8') as f:
            toml.dump(data, f)
    
    # ============= TRADUÇÃO UNIVERSAL =============
    
    def translate_dict(self, data: Dict, src_lang: str, dest_lang: str, 
                      callback=None) -> Dict:
        """Traduz valores de um dicionário recursivamente"""
        if isinstance(data, dict):
            return {k: self.translate_dict(v, src_lang, dest_lang, callback) 
                   for k, v in data.items()}
        elif isinstance(data, list):
            return [self.translate_dict(item, src_lang, dest_lang, callback) 
                   for item in data]
        elif isinstance(data, str):
            translated = self.translate_text(data, src_lang, dest_lang)
            if callback:
                callback()
            return translated
        else:
            return data
    
    def translate_file(self, input_path: Path, output_path: Path, 
                      src_lang: str, dest_lang: str, 
                      progress_callback=None, log_callback=None) -> Tuple[int, int]:
        """Traduz um arquivo automaticamente baseado na extensão"""
        
        file_ext = input_path.suffix.lower()
        format_type = self.SUPPORTED_FORMATS.get(file_ext)
        
        if not format_type:
            raise ValueError(f"Formato não suportado: {file_ext}")
        
        total_items = 0
        translated_items = 0
        
        # YAML (com tradução em lote paralela)
        if format_type == 'YAML':
            items = self.read_yaml(input_path)
            total_items = sum(1 for k, v in items if k is not None)
            
            # FASE 1: Identificar textos para traduzir
            if log_callback:
                log_callback("🔍 Fase 1: Identificando textos para traduzir...")
            
            texts_to_translate = []
            cached_count = 0
            for key, value in items:
                if key is not None and not self.should_skip(value):
                    cache_key = f"{src_lang}:{dest_lang}:{value}"
                    if cache_key not in self.cache:
                        texts_to_translate.append(value)
                    else:
                        cached_count += 1
            
            # Remove duplicatas
            unique_texts = list(dict.fromkeys(texts_to_translate))
            
            if log_callback:
                log_callback(f"   ✓ Encontrados {len(unique_texts)} textos únicos para traduzir")
                log_callback(f"   ✓ Já em cache: {cached_count} | A traduzir agora: {len(unique_texts)}")
            
            # Força update inicial
            if progress_callback:
                progress_callback()
            
            # FASE 2: Traduzir em paralelo se houver textos novos
            if unique_texts:
                if log_callback:
                    log_callback("\n⚡ Fase 2: Traduzindo em paralelo...")
                batch_size = 50
                batches = [unique_texts[i:i+batch_size] for i in range(0, len(unique_texts), batch_size)]
                
                # Avisar sobre fase de tradução paralela
                if progress_callback:
                    # Chama callback para mostrar que está trabalhando
                    for _ in range(min(10, len(unique_texts))):
                        progress_callback()
                
                with ThreadPoolExecutor(max_workers=min(6, len(batches))) as ex:
                    futures = [ex.submit(self.translate_batch, batch, src_lang, dest_lang) for batch in batches]
                    completed = 0
                    for future in as_completed(futures):
                        result = future.result()
                        completed += 1
                        # Atualiza cache com novos resultados
                        for text, translation in result.items():
                            cache_key = f"{src_lang}:{dest_lang}:{text}"
                            self.cache[cache_key] = translation
                        # Atualizar progresso a cada lote concluído
                        if progress_callback:
                            for _ in range(len(result)):
                                progress_callback()
            
            # FASE 3: Gerar arquivo traduzido
            if log_callback:
                log_callback("\n📝 Fase 3: Gerando arquivo traduzido...")
            
            translated_items_list = []
            for key, value in items:
                if key is None:
                    translated_items_list.append((None, value))
                else:
                    translated = self.translate_text(value, src_lang, dest_lang)
                    if translated != value:
                        translated_items += 1
                    translated_items_list.append((key, translated))
                    if progress_callback:
                        progress_callback()
            
            self.write_yaml(output_path, translated_items_list)
        
        # JSON
        elif format_type == 'JSON':
            data = self.read_json(input_path)
            
            def count_strings(obj):
                if isinstance(obj, str):
                    return 1
                elif isinstance(obj, dict):
                    return sum(count_strings(v) for v in obj.values())
                elif isinstance(obj, list):
                    return sum(count_strings(item) for item in obj)
                return 0
            
            total_items = count_strings(data)
            
            translated_data = self.translate_dict(data, src_lang, dest_lang, progress_callback)
            translated_items = total_items  # Simplificado
            
            self.write_json(output_path, translated_data)
        
        # XML
        elif format_type == 'XML':
            tree = self.read_xml(input_path)
            root = tree.getroot()
            
            def translate_element(elem):
                nonlocal total_items, translated_items
                if elem.text and elem.text.strip():
                    total_items += 1
                    original = elem.text
                    elem.text = self.translate_text(elem.text, src_lang, dest_lang)
                    if elem.text != original:
                        translated_items += 1
                    if progress_callback:
                        progress_callback()
                
                for child in elem:
                    translate_element(child)
            
            translate_element(root)
            self.write_xml(output_path, tree)
        
        # TXT
        elif format_type == 'TXT':
            lines = self.read_txt(input_path)
            total_items = len(lines)
            
            translated_lines = []
            for line in lines:
                translated = self.translate_text(line.strip(), src_lang, dest_lang)
                if translated != line.strip():
                    translated_items += 1
                translated_lines.append(translated + '\n')
                if progress_callback:
                    progress_callback()
            
            self.write_txt(output_path, translated_lines)
        
        # CSV
        elif format_type == 'CSV':
            rows = self.read_csv(input_path)
            total_items = sum(len(row) for row in rows)
            
            translated_rows = []
            for row in rows:
                translated_row = []
                for cell in row:
                    translated = self.translate_text(cell, src_lang, dest_lang)
                    if translated != cell:
                        translated_items += 1
                    translated_row.append(translated)
                    if progress_callback:
                        progress_callback()
                translated_rows.append(translated_row)
            
            self.write_csv(output_path, translated_rows)
        
        # INI
        elif format_type == 'INI':
            config = self.read_ini(input_path)
            
            for section in config.sections():
                for key in config[section]:
                    total_items += 1
                    value = config[section][key]
                    translated = self.translate_text(value, src_lang, dest_lang)
                    if translated != value:
                        translated_items += 1
                    config[section][key] = translated
                    if progress_callback:
                        progress_callback()
            
            self.write_ini(output_path, config)
        
        # TOML
        elif format_type == 'TOML':
            data = self.read_toml(input_path)
            total_items = sum(1 for _ in str(data))  # Simplificado
            
            translated_data = self.translate_dict(data, src_lang, dest_lang, progress_callback)
            translated_items = total_items  # Simplificado
            
            self.write_toml(output_path, translated_data)
        
        return total_items, translated_items


class TranslatorGUI:
    """Interface gráfica para o tradutor universal"""
    
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("🌍 Universal Mod Translator")
        self.window.geometry("800x600")
        self.window.resizable(True, True)
        
        self.translator = UniversalModTranslator()
        self.input_file: Optional[Path] = None
        self.output_file: Optional[Path] = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configura a interface gráfica"""
        
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame principal
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Título
        title = ttk.Label(main_frame, text="⚔️ UNIVERSAL MOD TRANSLATOR ⚔️", 
                         font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=3, pady=10)
        
        # Seleção de arquivo de entrada
        ttk.Label(main_frame, text="📁 Arquivo de Entrada:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.input_label = ttk.Label(main_frame, text="Nenhum arquivo selecionado", 
                                     foreground="gray")
        self.input_label.grid(row=2, column=0, columnspan=2, sticky=tk.W)
        ttk.Button(main_frame, text="Selecionar Arquivo", 
                  command=self.select_input_file).grid(row=2, column=2, padx=5)
        
        # Seleção de idiomas
        ttk.Label(main_frame, text="🌐 Idioma de Origem:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.src_lang_var = tk.StringVar(value='en')
        src_lang_combo = ttk.Combobox(main_frame, textvariable=self.src_lang_var, 
                                      values=list(self.translator.AVAILABLE_LANGUAGES.keys()),
                                      state='readonly', width=15)
        src_lang_combo.grid(row=4, column=0, sticky=tk.W)
        
        ttk.Label(main_frame, text="🌐 Idioma de Destino:").grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        self.dest_lang_var = tk.StringVar(value='pt')
        dest_lang_combo = ttk.Combobox(main_frame, textvariable=self.dest_lang_var,
                                       values=list(self.translator.AVAILABLE_LANGUAGES.keys()),
                                       state='readonly', width=15)
        dest_lang_combo.grid(row=4, column=1, sticky=tk.W, padx=5)
        
        # Seleção de arquivo de saída
        ttk.Label(main_frame, text="💾 Arquivo de Saída:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.output_label = ttk.Label(main_frame, text="Será gerado automaticamente", 
                                      foreground="gray")
        self.output_label.grid(row=6, column=0, columnspan=2, sticky=tk.W)
        ttk.Button(main_frame, text="Escolher Local", 
                  command=self.select_output_file).grid(row=6, column=2, padx=5)
        
        # Botão traduzir
        self.translate_btn = ttk.Button(main_frame, text="🚀 INICIAR TRADUÇÃO", 
                                       command=self.start_translation, 
                                       state='disabled')
        self.translate_btn.grid(row=7, column=0, columnspan=3, pady=20)
        
        # Barra de progresso
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                           maximum=100, length=700)
        self.progress_bar.grid(row=8, column=0, columnspan=3, pady=5)
        
        # Label de status
        self.status_label = ttk.Label(main_frame, text="Aguardando seleção de arquivo...", 
                                     foreground="blue")
        self.status_label.grid(row=9, column=0, columnspan=3)
        
        # Log de tradução
        ttk.Label(main_frame, text="📝 Log de Tradução:").grid(row=10, column=0, sticky=tk.W, pady=5)
        self.log_text = scrolledtext.ScrolledText(main_frame, height=10, width=90)
        self.log_text.grid(row=11, column=0, columnspan=3, pady=5)
        
        # Configurar grid
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
    def log(self, message: str):
        """Adiciona mensagem ao log"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.window.update()
    
    def select_input_file(self):
        """Seleciona arquivo de entrada"""
        filetypes = [
            ("Todos suportados", "*.yaml *.yml *.json *.xml *.txt *.csv *.ini *.cfg *.toml"),
            ("YAML", "*.yaml *.yml"),
            ("JSON", "*.json"),
            ("XML", "*.xml"),
            ("TXT", "*.txt"),
            ("CSV", "*.csv"),
            ("INI/CFG", "*.ini *.cfg"),
            ("TOML", "*.toml"),
            ("Todos", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(
            title="Selecione o arquivo de mod para traduzir",
            filetypes=filetypes
        )
        
        if filepath:
            self.input_file = Path(filepath)
            self.input_label.config(text=f"{self.input_file.name}", foreground="black")
            
            # Auto-gerar caminho de saída
            if not self.output_file:
                output_name = f"{self.input_file.stem}_translated{self.input_file.suffix}"
                self.output_file = self.input_file.parent / output_name
                self.output_label.config(text=f"{self.output_file.name}", foreground="black")
            
            self.translate_btn.config(state='normal')
            self.log(f"✅ Arquivo selecionado: {self.input_file.name}")
    
    def select_output_file(self):
        """Seleciona arquivo de saída"""
        if not self.input_file:
            messagebox.showwarning("Aviso", "Selecione o arquivo de entrada primeiro!")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Escolha onde salvar o arquivo traduzido",
            defaultextension=self.input_file.suffix,
            filetypes=[(f"{self.input_file.suffix.upper()}", f"*{self.input_file.suffix}")]
        )
        
        if filepath:
            self.output_file = Path(filepath)
            self.output_label.config(text=f"{self.output_file.name}", foreground="black")
            self.log(f"💾 Saída: {self.output_file.name}")
    
    def start_translation(self):
        """Inicia o processo de tradução em thread separada"""
        if not self.input_file:
            messagebox.showerror("Erro", "Selecione um arquivo de entrada!")
            return
        
        # Desabilitar botão durante tradução
        self.translate_btn.config(state='disabled')
        self.status_label.config(text="🔄 Traduzindo...", foreground="orange")
        self.progress_var.set(0)
        
        # Executar em thread separada
        thread = threading.Thread(target=self.translate_worker, daemon=True)
        thread.start()
    
    def translate_worker(self):
        """Worker thread para tradução"""
        try:
            src_lang = self.src_lang_var.get()
            dest_lang = self.dest_lang_var.get()
            
            self.log(f"\n{'='*60}")
            self.log(f"🚀 INICIANDO TRADUÇÃO")
            self.log(f"{'='*60}")
            self.log(f"📄 Arquivo: {self.input_file.name}")
            self.log(f"🌍 {src_lang} → {dest_lang}")
            self.log(f"📁 Formato: {self.input_file.suffix.upper()}")
            self.log(f"{'='*60}")
            self.log(f"🔍 Analisando arquivo...")
            
            start_time = time.time()
            
            # Callback de progresso
            progress_counter = [0]
            total_items = [0]
            last_log_percent = [0]
            
            def update_progress():
                progress_counter[0] += 1
                if total_items[0] > 0:
                    percent = (progress_counter[0] / total_items[0]) * 100
                    self.progress_var.set(percent)
                    # Atualizar status em tempo real
                    self.status_label.config(text=f"🔄 Traduzindo... {progress_counter[0]}/{total_items[0]} itens ({percent:.1f}%)")
                    # Log a cada 10%
                    if int(percent / 10) > last_log_percent[0]:
                        last_log_percent[0] = int(percent / 10)
                        self.log(f"⏳ Progresso: {percent:.1f}% ({progress_counter[0]}/{total_items[0]})")
                    # Forçar atualização visual
                    self.window.update_idletasks()
            
            self.log("🚀 Iniciando tradução...\n")
            
            # Traduzir
            total, translated = self.translator.translate_file(
                self.input_file,
                self.output_file,
                src_lang,
                dest_lang,
                update_progress,
                self.log  # Passar função de log
            )
            
            total_items[0] = total
            
            elapsed = time.time() - start_time
            
            # Salvar cache
            self.translator.save_cache()
            
            # Finalizar
            self.progress_var.set(100)
            self.status_label.config(text="✅ Tradução concluída!", foreground="green")
            
            self.log(f"\n{'='*60}")
            self.log(f"✅ TRADUÇÃO CONCLUÍDA COM SUCESSO!")
            self.log(f"{'='*60}")
            self.log(f"📊 Estatísticas:")
            self.log(f"   • Total de itens: {total}")
            self.log(f"   • Traduzidos agora: {translated}")
            self.log(f"   • Do cache: {total - translated}")
            if translated > 0 and elapsed > 0:
                taxa = translated / elapsed
                self.log(f"   • Taxa média: {taxa:.1f} traduções/s")
            self.log(f"   • Tempo: {elapsed:.1f}s")
            cache_size = len(self.translator.cache)
            self.log(f"   • Tamanho do cache: {cache_size} entradas")
            self.log(f"\n💾 Arquivo salvo: {self.output_file}")
            self.log(f"{'='*60}\n")
            
            messagebox.showinfo("Sucesso!", 
                              f"Tradução concluída!\n\n"
                              f"✅ {translated} itens traduzidos\n"
                              f"⏱️ Tempo: {elapsed:.1f}s\n\n"
                              f"Arquivo salvo em:\n{self.output_file}")
            
        except Exception as e:
            self.status_label.config(text="❌ Erro na tradução!", foreground="red")
            self.log(f"\n❌ ERRO: {str(e)}")
            messagebox.showerror("Erro", f"Erro durante a tradução:\n\n{str(e)}")
        
        finally:
            self.translate_btn.config(state='normal')
    
    def run(self):
        """Executa a aplicação"""
        self.window.mainloop()


if __name__ == "__main__":
    app = TranslatorGUI()
    app.run()
