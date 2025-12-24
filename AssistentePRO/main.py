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
import zipfile 
import time
from win32api import GetSystemMetrics
from win32con import SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN, SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN

GITHUB_USER = "oSzhul"             
GITHUB_REPO = "Assistente-de-Respostas-Python" 
EXE_NAME_UPDATER = "Updater.exe" 

logging.basicConfig(
    filename='debug_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(console_handler)

logging.info("--- INICIANDO ASSISTENTE PRINCIPAL ---")

def get_local_version():
    """Lê a versão do arquivo Version.txt. Se não existir, retorna v0.0.0"""
    if os.path.exists("Version.txt"):
        try:
            with open("Version.txt", "r") as f:
                ver = f.read().strip()
                logging.info(f"Arquivo Version.txt encontrado: {ver}")
                return ver
        except Exception:
            logging.error("Erro ao ler Version.txt")
    
    logging.warning("Version.txt não encontrado. Assumindo v0.0.0")
    return "v0.0.0" 

CURRENT_VERSION = get_local_version()

class AutoChecker:
    def __init__(self, app_window):
        self.app = app_window
        self.api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

    def check(self):
        try:
            logging.info(f"1. Conectando na API: {self.api_url}")
            response = requests.get(self.api_url, timeout=10)
            
            logging.info(f"2. Status Code do GitHub: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get('tag_name', 'Sem Tag').strip()
                
                logging.info(f"3. Comparando: Local '{CURRENT_VERSION}' vs GitHub '{latest_tag}'")
                
                if latest_tag != CURRENT_VERSION:
                    logging.info("4. Versões diferentes! Procurando arquivo de atualização...")
                    
                    exe_url = ""
                    assets = data.get('assets', [])
                    
                    if not assets:
                        logging.error("ERRO CRÍTICO: Release existe mas a lista de Assets está vazia!")
                    
                    for asset in assets:
                        name = asset.get('name', '').lower()
                        download_url = asset.get('browser_download_url', '')
                        logging.info(f"   - Analisando Asset: {name}")

                        if name.endswith(".zip"):
                            logging.info(f"   -> ZIP ENCONTRADO (Prioridade Máxima): {download_url}")
                            exe_url = download_url
                            break
                        elif name.endswith(".exe") and "updater" not in name:
                            logging.info(f"   -> EXE ENCONTRADO (Alternativa): {download_url}")
                            exe_url = download_url
                        else:
                            logging.info("   -> Ignorado (Filtro)")
                    
                    if exe_url:
                        logging.info("5. Tudo certo. Abrindo Popup.")
                        self.app.show_update_popup(latest_tag, exe_url)
                    else:
                        logging.warning("AVISO: Nova versão existe, mas não achei um .zip ou .exe válido.")
                else:
                    logging.info("4. Versões iguais. Software atualizado.")
            
            elif response.status_code == 404:
                logging.error("ERRO 404: Repo privado ou Release Draft.")
            else:
                logging.error(f"ERRO API: {response.text}")
                
        except Exception as e:
            logging.exception("ERRO CRÍTICO DURANTE O CHECK:")

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
        vl = GetSystemMetrics(SM_XVIRTUALSCREEN)
        vt = GetSystemMetrics(SM_YVIRTUALSCREEN)
        self.destroy()
        self.callback((x1 + vl, y1 + vt, x2 + vl, y2 + vt))

    def cancel_capture(self):
        self.destroy()
        self.parent.deiconify()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.perform_updater_swap()
        
        self.title(f"Assistente Pro ({CURRENT_VERSION})")
        self.geometry("450x800")
        self.attributes("-topmost", True)
        self.api_key = ""
        self.current_url = "" 
        self.load_config()

        self.checker = AutoChecker(self)
        threading.Thread(target=self.checker.check, daemon=True).start()

        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.pack(pady=(10, 5), fill="x", padx=10)
        
        self.entry_key = ctk.CTkEntry(self.frame_top, placeholder_text="Cole sua API Key aqui...", show="*")
        self.entry_key.pack(side="left", expand=True, fill="x")
        ctk.CTkButton(self.frame_top, text="💾", width=40, command=self.save_key).pack(side="left", padx=5)
        
        self.switch_var = ctk.StringVar(value="off")
        ctk.CTkSwitch(self.frame_top, text="Topo", variable=self.switch_var, onvalue="on", offvalue="off", command=self.toggle_top, width=60).pack(side="right")

        self.frame_help = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_help.pack(pady=(0, 10), padx=10, fill="x") 

        self.lbl_help = ctk.CTkLabel(self.frame_help, text="Como gerar uma API Key?", font=("Arial", 11), text_color="gray")
        self.lbl_help.pack(side="left")

        self.lbl_link = ctk.CTkLabel(self.frame_help, text="Google AI Studio", font=("Arial", 11, "underline"), text_color="#3B8ED0", cursor="hand2")
        self.lbl_link.pack(side="left", padx=5)
        self.lbl_link.bind("<Button-1>", lambda e: webbrowser.open("https://oszhul.github.io/Assistente-de-Respostas-Python/root/"))

        if self.api_key: self.entry_key.insert(0, self.api_key)

        ctk.CTkButton(self, text="📸 CAPTURAR QUESTÃO", height=50, fg_color="green", hover_color="darkgreen", font=("Arial", 14, "bold"), command=self.start_capture).pack(pady=5, padx=10, fill="x")
        
        self.lbl_status = ctk.CTkLabel(self, text=f"Versão Instalada: {CURRENT_VERSION}", text_color="gray")
        self.lbl_status.pack()

        self.scroll = ctk.CTkScrollableFrame(self, label_text="Resultado")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.res = self.create_box("🏆 RESPOSTA", 60, "#4CAF50")
        self.expl = self.create_box("📖 EXPLICAÇÃO", 180, "#2196F3")
        self.btn_link = ctk.CTkButton(self.scroll, text="🔗 Abrir Fonte", command=self.open_url)
        self.trans = self.create_box("📝 TRANSCRIÇÃO", 100, "gray")

    def perform_updater_swap(self):
        """Verifica se existe um Updater_new.exe e aplica a atualização"""
        if os.path.exists("Updater_new.exe"):
            logging.info("Detectado Updater_new.exe. Atualizando o Updater...")
            try:

                time.sleep(1)
                
                if os.path.exists(EXE_NAME_UPDATER):
                    os.remove(EXE_NAME_UPDATER)
                
                os.rename("Updater_new.exe", EXE_NAME_UPDATER)
                logging.info("SUCESSO: Updater.exe foi atualizado!")
            except Exception as e:
                logging.error(f"Falha ao trocar Updater: {e}")

    def create_box(self, title, h, color):
        ctk.CTkLabel(self.scroll, text=title, text_color=color, font=("Arial", 12, "bold")).pack(anchor="w", pady=(5,0))
        t = ctk.CTkTextbox(self.scroll, height=h, font=("Arial", 12))
        t.pack(fill="x", pady=5)
        return t

    def show_update_popup(self, version, url):
        self.after(0, lambda: self._popup(version, url))

    def _popup(self, version, url):
        self.attributes("-topmost", False) 
        self.switch_var.set("off")
        
        msg = ctk.CTkToplevel(self)
        msg.title("Atualização Encontrada")
        msg.geometry("350x180")
        msg.attributes("-topmost", True)
        msg.grab_set() 
        
        ctk.CTkLabel(msg, text=f"🎉 Nova versão disponível: {version}", font=("Arial", 14, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(msg, text="O programa será reiniciado para atualizar.", font=("Arial", 11)).pack(pady=(0, 20))
        
        btn_frame = ctk.CTkFrame(msg, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)

        ctk.CTkButton(btn_frame, text="Sim, Atualizar", fg_color="green", command=lambda: self.launch_updater(url, version)).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="Agora não", fg_color="red", command=msg.destroy).pack(side="right", expand=True, padx=5)

    def launch_updater(self, url, version):
        """
        Lógica de Recuperação e Lançamento:
        1. Se Updater.exe não existe, tenta baixar do ZIP (Recuperação).
        2. Roda o Updater.exe passando a URL e Versão.
        """
        if not os.path.exists(EXE_NAME_UPDATER):
            self.recover_updater(url)
            
        if os.path.exists(EXE_NAME_UPDATER):
            logging.info(f"Iniciando {EXE_NAME_UPDATER}...")
            subprocess.Popen([EXE_NAME_UPDATER, url, version])
            self.quit()
            sys.exit() 
        else:
            self.lbl_status.configure(text="Falha crítica: Não consegui encontrar nem recuperar o Updater.", text_color="red")
            logging.error("Falha fatal na recuperação do Updater.")

    def recover_updater(self, url):
        """Baixa o ZIP da atualização e extrai apenas o Updater.exe"""
        self.lbl_status.configure(text="Recuperando Updater ausente...", text_color="orange")
        self.update()
        
        try:
            logging.info("Tentando recuperar Updater.exe do ZIP de atualização...")

            if url.lower().endswith(".zip"):
                r = requests.get(url, stream=True)
                with open("temp_recovery.zip", "wb") as f:
                    for chunk in r.iter_content(chunk_size=4096):
                        f.write(chunk)
                
                with zipfile.ZipFile("temp_recovery.zip", 'r') as z:

                    for name in z.namelist():
                        if os.path.basename(name).lower() == EXE_NAME_UPDATER.lower():
                            with open(EXE_NAME_UPDATER, "wb") as f_out:
                                f_out.write(z.read(name))
                            logging.info(f"Updater.exe recuperado de {name}!")
                            break
                
                if os.path.exists("temp_recovery.zip"): os.remove("temp_recovery.zip")
            else:
                logging.error("A URL de atualização não é um ZIP, impossível recuperar Updater.")
                
        except Exception as e:
            logging.error(f"Erro na recuperação: {e}")

    def toggle_top(self):
        self.attributes("-topmost", self.switch_var.get() == "on")
    
    def load_config(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f: self.api_key = json.load(f).get("api_key", "")
            except: pass

    def save_key(self):
        self.api_key = self.entry_key.get().strip()
        with open("config.json", "w") as f: json.dump({"api_key": self.api_key}, f)
        self.lbl_status.configure(text="API Key Salva!", text_color="green")

    def start_capture(self):
        if not self.api_key:
            self.lbl_status.configure(text="ERRO: Configure sua API Key!", text_color="red")
            return
        self.iconify()
        self.after(200, lambda: ScreenCapture(self, self.process))

    def process(self, coords):
        self.deiconify()
        w, h = coords[2]-coords[0], coords[3]-coords[1]
        if w < 10 or h < 10: return
        
        self.lbl_status.configure(text="Analisando Imagem...", text_color="orange")
        self.res.delete("1.0", "end"); self.expl.delete("1.0", "end"); self.trans.delete("1.0", "end"); self.btn_link.pack_forget()
        
        threading.Thread(target=self.ask_ai, args=(ImageGrab.grab(bbox=coords, all_screens=True),)).start()

    def ask_ai(self, img):
        try:
            client = genai.Client(api_key=self.api_key)
            prompt = """
            Você é um assistente acadêmico. Retorne APENAS JSON:
            {
                "transcricao": "Texto da questão",
                "resposta_curta": "Alternativa Correta",
                "explicacao": "Explicação detalhada",
                "fonte_nome": "Nome do livro/site",
                "url_fonte": "URL válida ou vazio"
            }
            """
            resp = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=[prompt, img], 
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            self.after(0, lambda: self.show_data(resp.text))
        except Exception as e:
            logging.error(f"Erro IA: {e}")
            self.after(0, lambda: self.lbl_status.configure(text="Erro na IA. Veja o log.", text_color="red"))

    def show_data(self, text):
        try:
            d = json.loads(text)
            self.res.insert("end", d.get("resposta_curta", "---"))
            self.expl.insert("end", f"{d.get('explicacao','')}\n\n📚 Fonte: {d.get('fonte_nome','')}")
            self.trans.insert("end", d.get("transcricao", ""))
            
            url = d.get("url_fonte", "").strip()
            if url.startswith("http"):
                self.current_url = url
                self.btn_link.pack(before=self.trans, pady=5)
            
            self.lbl_status.configure(text=f"Pronto ({CURRENT_VERSION})", text_color="green")
        except:
            self.expl.insert("end", text)
            self.lbl_status.configure(text="Erro no JSON", text_color="red")

    def open_url(self): webbrowser.open(self.current_url)

if __name__ == "__main__":
    app = App()
    app.mainloop()