import customtkinter as ctk
import requests
import sys
import os
import time
import subprocess
import threading
import zipfile
import shutil

# Configuração visual
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class UpdaterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Argumentos: 1=URL, 2=Versão
        self.download_url = sys.argv[1] if len(sys.argv) > 1 else ""
        self.new_version = sys.argv[2] if len(sys.argv) > 2 else "v?.?.?"
        
        self.target_exe = "Assistente_Final.exe" 
        self.my_exe_name = "Updater.exe" # Nome dele mesmo

        self.title("Atualizador Automático")
        self.geometry("400x300")
        self.resizable(False, False)
        
        self.label_title = ctk.CTkLabel(self, text=f"Baixando Versão {self.new_version}", font=("Arial", 16, "bold"))
        self.label_title.pack(pady=(20, 10))
        
        self.label_status = ctk.CTkLabel(self, text="Inicializando...", text_color="gray")
        self.label_status.pack(pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self, width=300)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)
        
        self.btn_finish = ctk.CTkButton(self, text="Abrir Assistente", state="disabled", fg_color="gray", command=self.launch_app)
        self.btn_finish.pack(pady=20)

        if self.download_url:
            threading.Thread(target=self.run_update_process, daemon=True).start()
        else:
            self.label_status.configure(text="Erro: Sem link de download.", text_color="red")

    def run_update_process(self):
        try:
            self.update_status("Aguardando Assistente fechar...")
            time.sleep(2) # Garante que o Assistente fechou

            # Baixa o arquivo (ZIP ou EXE)
            is_zip = self.download_url.lower().endswith(".zip")
            temp_filename = "update_package.zip" if is_zip else "update_temp.exe"
            
            self.update_status("Baixando atualização...")
            response = requests.get(self.download_url, stream=True)
            total_length = int(response.headers.get('content-length', 0))
            dl = 0
            
            with open(temp_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=4096):
                    dl += len(chunk)
                    f.write(chunk)
                    if total_length > 0:
                        self.update_ui_progress(dl / total_length)

            self.update_status("Instalando...")
            time.sleep(1)

            # --- LÓGICA INTELIGENTE DE EXTRAÇÃO ---
            if is_zip:
                try:
                    with zipfile.ZipFile(temp_filename, 'r') as z:
                        for file_info in z.infolist():
                            filename = file_info.filename
                            
                            # Se o arquivo no ZIP for o próprio Updater
                            if filename.lower() == self.my_exe_name.lower():
                                # Extrai com nome temporário (Updater_new.exe)
                                logging_msg = "Nova versão do Updater detectada."
                                with open("Updater_new.exe", "wb") as f_out:
                                    f_out.write(z.read(filename))
                            else:
                                # Se for qualquer outro arquivo (Assistente, DLLs), extrai normal
                                z.extract(file_info, ".")
                                
                except Exception as e:
                    raise Exception(f"Erro ZIP: {e}")
                finally:
                    if os.path.exists(temp_filename): os.remove(temp_filename)
            else:
                # Se baixou um EXE direto (modo antigo), substitui o Assistente
                if os.path.exists(self.target_exe):
                    try: os.remove(self.target_exe)
                    except: pass
                os.rename(temp_filename, self.target_exe)

            # Atualiza registro
            self.update_status("Finalizando...")
            with open("Version.txt", "w") as f:
                f.write(self.new_version)
                
            self.update_status("Sucesso! Pode abrir o Assistente.")
            self.after(0, lambda: self.btn_finish.configure(state="normal", fg_color="green", text="Abrir Assistente Agora"))
            
        except Exception as e:
            self.update_status(f"Erro: {str(e)}")
            # Limpeza de emergência
            if os.path.exists("update_package.zip"): os.remove("update_package.zip")

    def update_status(self, text):
        self.after(0, lambda: self.label_status.configure(text=text))

    def update_ui_progress(self, val):
        self.after(0, lambda: self.progress_bar.set(val))

    def launch_app(self):
        if os.path.exists(self.target_exe):
            subprocess.Popen(self.target_exe)
            self.destroy() # Updater fecha aqui
        else:
            self.label_status.configure(text=f"Erro: {self.target_exe} não encontrado.", text_color="red")

if __name__ == "__main__":
    app = UpdaterApp()
    app.mainloop()