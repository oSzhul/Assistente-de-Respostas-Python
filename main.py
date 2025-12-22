import customtkinter as ctk
import tkinter as tk
from PIL import ImageGrab, Image
from google import genai
from google.genai import types
import threading
import json
import os
import logging
import ctypes 
import webbrowser
import requests
import sys
import subprocess
from win32api import GetSystemMetrics
from win32con import SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN, SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN

# --- CONFIGURAÇÕES DO PROJETO ---
CURRENT_VERSION = "v1.0.0"
GITHUB_USER = "oSzhul"
GITHUB_REPO = "Assistente-de-Respostas-Python"
# -------------------------------

# --- Configuração de Logs ---
logging.basicConfig(
    filename='debug_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Classe de Atualização Automática ---
class AutoUpdater:
    def __init__(self, current_version, user, repo, app_window):
        self.current_version = current_version
        self.user = user
        self.repo = repo
        self.app = app_window
        self.api_url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"

    def check_for_updates(self):
        """Verifica se há uma versão nova no GitHub (rodar em thread separada)"""
        try:
            logging.info("Verificando atualizações no GitHub...")
            response = requests.get(self.api_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                latest_tag = data['v1.0.0']

                if latest_tag != self.current_version:
                    logging.info(f"Nova versão encontrada: {latest_tag}")

                    exe_url = ""
                    for asset in data['assets']:
                        if asset['name'].endswith(".exe"):
                            exe_url = asset['browser_download_url']
                            break
                    
                    if exe_url:
                        self.app.show_update_popup(latest_tag, exe_url)
            else:
                logging.warning(f"Github API respondeu: {response.status_code}")
                
        except Exception as e:
            logging.error(f"Erro ao verificar updates: {e}")

    def download_and_install(self, url):
        """Baixa o novo exe e cria o script de troca."""
        try:

            r = requests.get(url, stream=True)
            with open("update_new.exe", 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logging.info("Download concluído. Iniciando script de troca...")

            current_exe = os.path.basename(sys.executable)
            bat_script = f"""
            @echo off
            timeout /t 2 >nul
            del "{current_exe}"
            move "update_new.exe" "{current_exe}"
            start "" "{current_exe}"
            del "%~f0"
            """
            
            with open("updater.bat", "w") as f:
                f.write(bat_script)

            subprocess.Popen("updater.bat", shell=True)
            sys.exit() # Adeus!
            
        except Exception as e:
            logging.error(f"Erro na instalação: {e}")
            self.app.label_status.configure(text=f"Erro update: {e}", text_color="red")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

class ScreenCapture(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__()
        self.parent = parent
        self.callback = callback
        self.overrideredirect(True)
        self.attributes("-alpha", 0.3)
        self.attributes("-topmost", True)
        self.config(cursor="cross")
        
        virtual_width = GetSystemMetrics(SM_CXVIRTUALSCREEN)
        virtual_height = GetSystemMetrics(SM_CYVIRTUALSCREEN)
        virtual_left = GetSystemMetrics(SM_XVIRTUALSCREEN)
        virtual_top = GetSystemMetrics(SM_YVIRTUALSCREEN)
        self.geometry(f"{virtual_width}x{virtual_height}+{virtual_left}+{virtual_top}")
        
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self.cancel_capture())

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="red", width=3)

    def on_drag(self, event):
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)
        
        virtual_left = GetSystemMetrics(SM_XVIRTUALSCREEN)
        virtual_top = GetSystemMetrics(SM_YVIRTUALSCREEN)
        global_coords = (x1 + virtual_left, y1 + virtual_top, x2 + virtual_left, y2 + virtual_top)
        
        self.destroy()
        self.callback(global_coords)

    def cancel_capture(self):
        self.destroy()
        self.parent.deiconify()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Assistente Pro ({CURRENT_VERSION})")
        self.geometry("450x800")
        self.attributes("-topmost", True)

        self.api_key = ""
        self.current_url = "" 
        self.load_config()

        # Inicia verificação de Update em Background
        self.updater = AutoUpdater(CURRENT_VERSION, GITHUB_USER, GITHUB_REPO, self)
        threading.Thread(target=self.updater.check_for_updates, daemon=True).start()

        # --- LAYOUT ---
        self.frame_top_container = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top_container.pack(pady=10, padx=10, fill="x")

        self.frame_api_column = ctk.CTkFrame(self.frame_top_container, fg_color="transparent")
        self.frame_api_column.pack(side="left", fill="x", expand=True)

        self.lbl_instruction = ctk.CTkLabel(self.frame_api_column, text="Insira sua API key abaixo:", font=("Arial", 11), text_color="silver")
        self.lbl_instruction.pack(anchor="w", padx=2)

        self.frame_input_row = ctk.CTkFrame(self.frame_api_column, fg_color="transparent")
        self.frame_input_row.pack(fill="x", pady=2)
        
        self.entry_key = ctk.CTkEntry(self.frame_input_row, placeholder_text="Cole a chave AIza...", show="*", height=30)
        self.entry_key.pack(side="left", expand=True, fill="x")
        
        self.btn_save_key = ctk.CTkButton(self.frame_input_row, text="💾", width=35, height=30, command=self.save_key)
        self.btn_save_key.pack(side="left", padx=(5, 0))

        self.frame_help_row = ctk.CTkFrame(self.frame_api_column, fg_color="transparent")
        self.frame_help_row.pack(anchor="w", pady=(2, 0))

        self.lbl_help = ctk.CTkLabel(self.frame_help_row, text="Como gerar uma API Key Gemini?", font=("Arial", 10), text_color="gray")
        self.lbl_help.pack(side="left")

        self.lbl_link = ctk.CTkLabel(self.frame_help_row, text="Google AI Studio", font=("Arial", 10, "underline"), text_color="#3B8ED0", cursor="hand2")
        self.lbl_link.pack(side="left", padx=5)
        self.lbl_link.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/app/apikey"))

        if self.api_key:
            self.entry_key.insert(0, self.api_key)

        self.frame_switch = ctk.CTkFrame(self.frame_top_container, fg_color="transparent")
        self.frame_switch.pack(side="right", anchor="n") 

        self.switch_var = ctk.StringVar(value="on")
        self.switch_topmost = ctk.CTkSwitch(
            self.frame_switch, 
            text="📌 Topo", 
            command=self.toggle_topmost,
            variable=self.switch_var, 
            onvalue="on", 
            offvalue="off",
            width=50
        )
        self.switch_topmost.pack()

        self.btn_capture = ctk.CTkButton(self, text="📸 CAPTURAR QUESTÃO", height=45, fg_color="green", hover_color="darkgreen", font=("Arial", 15, "bold"), command=self.start_capture)
        self.btn_capture.pack(pady=10, padx=10, fill="x")

        self.label_status = ctk.CTkLabel(self, text=f"Versão {CURRENT_VERSION}", text_color="gray", font=("Arial", 12))
        self.label_status.pack(pady=(0, 5))

        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Análise da IA")
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_res_title = ctk.CTkLabel(self.scroll_frame, text="🏆 RESPOSTA CORRETA", font=("Arial", 12, "bold"), text_color="#4CAF50")
        self.lbl_res_title.pack(anchor="w", pady=(5, 0))
        self.txt_resposta = ctk.CTkTextbox(self.scroll_frame, height=50, font=("Arial", 16, "bold"), fg_color="#1e1e1e", border_color="#4CAF50", border_width=2)
        self.txt_resposta.pack(fill="x", pady=5)

        self.lbl_exp_title = ctk.CTkLabel(self.scroll_frame, text="📖 EXPLICAÇÃO", font=("Arial", 12, "bold"), text_color="#2196F3")
        self.lbl_exp_title.pack(anchor="w", pady=(10, 0))
        self.txt_explicacao = ctk.CTkTextbox(self.scroll_frame, height=180, font=("Arial", 13))
        self.txt_explicacao.pack(fill="x", pady=5)

        self.btn_link_source = ctk.CTkButton(self.scroll_frame, text="🔗 Abrir Fonte no Navegador", fg_color="#005577", hover_color="#004466", command=self.open_url)

        self.lbl_trans_title = ctk.CTkLabel(self.scroll_frame, text="📝 TRANSCRIÇÃO", font=("Arial", 12, "bold"), text_color="gray")
        self.lbl_trans_title.pack(anchor="w", pady=(10, 0))
        self.txt_transcricao = ctk.CTkTextbox(self.scroll_frame, height=100, font=("Consolas", 11), text_color="silver")
        self.txt_transcricao.pack(fill="x", pady=5)

    def show_update_popup(self, version, url):
        """Mostra janela perguntando se quer atualizar."""
        
        self.after(0, lambda: self._create_popup(version, url))
        
    def _create_popup(self, version, url):
        msg = ctk.CTkToplevel(self)
        msg.title("Atualização Disponível")
        msg.geometry("300x150")
        msg.attributes("-topmost", True)
        
        lbl = ctk.CTkLabel(msg, text=f"Nova versão encontrada: {version}\nDeseja atualizar agora?", font=("Arial", 12))
        lbl.pack(pady=20)
        
        btn_yes = ctk.CTkButton(msg, text="Sim, Atualizar", fg_color="green", command=lambda: [msg.destroy(), self.start_update(url)])
        btn_yes.pack(side="left", padx=20, pady=10)
        
        btn_no = ctk.CTkButton(msg, text="Não", fg_color="red", command=msg.destroy)
        btn_no.pack(side="right", padx=20, pady=10)

    def start_update(self, url):
        self.label_status.configure(text="Baixando atualização... Aguarde.", text_color="orange")
        threading.Thread(target=self.updater.download_and_install, args=(url,)).start()

    def toggle_topmost(self):
        if self.switch_var.get() == "on":
            self.attributes("-topmost", True)
        else:
            self.attributes("-topmost", False)

    def load_config(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    data = json.load(f)
                    self.api_key = data.get("api_key", "")
            except: pass

    def save_key(self):
        key = self.entry_key.get().strip()
        if key:
            self.api_key = key
            with open("config.json", "w") as f:
                json.dump({"api_key": key}, f)
            self.label_status.configure(text="Chave salva!", text_color="green")

    def start_capture(self):
        if not self.api_key:
            self.label_status.configure(text="ERRO: Configure sua API Key!", text_color="red")
            return
        self.iconify()
        self.after(200, lambda: ScreenCapture(self, self.process_capture))

    def process_capture(self, coords):
        self.deiconify()
        width = coords[2] - coords[0]
        height = coords[3] - coords[1]
        if width < 10 or height < 10: return

        try:
            img = ImageGrab.grab(bbox=coords, all_screens=True)
            self.label_status.configure(text="Processando IA...", text_color="orange")
            self.txt_resposta.delete("1.0", "end")
            self.txt_explicacao.delete("1.0", "end")
            self.txt_transcricao.delete("1.0", "end")
            self.btn_link_source.pack_forget() 
            threading.Thread(target=self.ask_gemini, args=(img,)).start()
        except Exception as e:
            self.label_status.configure(text=f"Erro captura: {e}", text_color="red")

    def ask_gemini(self, image):
        try:
            client = genai.Client(api_key=self.api_key)
            prompt_text = """
            Você é um assistente acadêmico especialista.
            Analise a imagem e retorne APENAS um JSON válido com os campos:
            {
                "transcricao": "Texto da questão",
                "resposta_curta": "Apenas a alternativa correta",
                "explicacao": "Explicação didática",
                "fonte_nome": "Nome do livro ou site",
                "url_fonte": "URL direta e válida para o assunto (comece com http), ou deixe vazio se não houver"
            }
            """
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt_text, image],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            self.after(0, lambda: self.distribute_response(response.text))
        except Exception as e:
            self.after(0, lambda: self.label_status.configure(text=f"Erro IA: {e}", text_color="red"))

    def distribute_response(self, json_text):
        try:
            data = json.loads(json_text)
            self.txt_resposta.insert("end", data.get("resposta_curta", "---"))
            expl = data.get("explicacao", "")
            fonte_nome = data.get("fonte_nome", "")
            self.txt_explicacao.insert("end", f"{expl}\n\n📚 Fonte citada: {fonte_nome}")
            self.txt_transcricao.insert("end", data.get("transcricao", ""))
            url = data.get("url_fonte", "").strip()
            if url and url.startswith("http"):
                self.current_url = url 
                self.btn_link_source.pack(pady=5, fill="x", before=self.lbl_trans_title)
            self.label_status.configure(text=f"Versão {CURRENT_VERSION} - Pronto", text_color="green")
        except:
            self.txt_explicacao.insert("end", json_text)

    def open_url(self):
        if self.current_url: webbrowser.open(self.current_url)

if __name__ == "__main__":
    app = App()
    app.mainloop()