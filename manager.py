import subprocess
import sys
import time
import os
import socket
import msvcrt
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import questionary

console = Console()
CREATE_NO_WINDOW = 0x08000000

def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.1)
        return s.connect_ex(('127.0.0.1', port)) == 0

def get_status_panel():
    backend_status = is_port_open(8000)
    frontend_status = is_port_open(5173)
    
    b_text = "[bold green][ONLINE][/bold green]" if backend_status else "[bold red][OFFLINE][/bold red]"
    f_text = "[bold green][ONLINE][/bold green]" if frontend_status else "[bold red][OFFLINE][/bold red]"
    
    text = Text.from_markup(f"Backend (Port 8000): {b_text}\nFrontend (Port 5173): {f_text}")
    return Panel(text, title="Bibitinhos Status Panel", expand=False, border_style="cyan")

def start_backend():
    if is_port_open(8000):
        return
    log = open("backend.log", "a")
    subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--reload"], cwd="backend", stdout=log, stderr=log, creationflags=CREATE_NO_WINDOW)
    time.sleep(0.5)

def start_frontend():
    if is_port_open(5173):
        return
    log = open("frontend.log", "a")
    subprocess.Popen("npm run dev", cwd="frontend", stdout=log, stderr=log, creationflags=CREATE_NO_WINDOW, shell=True)
    time.sleep(0.5)

def get_pid_by_port(port: int):
    try:
        result = subprocess.run(f"netstat -ano | findstr LISTENING | findstr :{port}", shell=True, capture_output=True, text=True)
        for line in result.stdout.strip().split('\n'):
            if f":{port}" in line:
                parts = line.strip().split()
                if len(parts) > 4:
                    return parts[-1]
    except:
        pass
    return None

def stop_port(port: int):
    pid = get_pid_by_port(port)
    if pid:
        subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
        time.sleep(0.5)

def tail_log(filename):
    console.print(f"\n[cyan]>> Tailing {filename}... Pressione 'q', 'ESC' ou Ctrl+C para voltar ao menu.[/cyan]")
    if not os.path.exists(filename):
        console.print("[red]Arquivo de log não encontrado. O serviço já foi iniciado?[/red]")
        time.sleep(2)
        return
    with open(filename, 'r', encoding='utf-8') as f:
        f.seek(0, 2)
        try:
            while True:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key in (b'q', b'Q', b'\x1b', b'\x03'):
                        break
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                sys.stdout.write(line)
                sys.stdout.flush()
        except KeyboardInterrupt:
            pass

def run_tests_backend():
    console.print("\n[cyan]>> Rodando Pytest (Backend)...[/cyan]")
    subprocess.run([sys.executable, "-m", "pytest", "tests/"], cwd="backend")
    questionary.press_any_key_to_continue("Pressione Enter para voltar...").ask()

def run_tests_frontend():
    console.print("\n[cyan]>> Rodando Vitest (Frontend)...[/cyan]")
    subprocess.run("npm run test", cwd="frontend", shell=True)
    questionary.press_any_key_to_continue("Pressione Enter para voltar...").ask()

def run_build_frontend():
    console.print("\n[cyan]>> Compilando Frontend para Produção...[/cyan]")
    subprocess.run("npm run build", cwd="frontend", shell=True)
    questionary.press_any_key_to_continue("Pressione Enter para voltar...").ask()

def main():
    while True:
        try:
            console.clear()
            console.print(get_status_panel())
            
            choice = questionary.select(
                "Tela Inicial:",
                choices=["Start", "Stop", "Build", "Test", "Logs", "Sair"]
            ).ask()
            
            if choice == "Start":
                while True:
                    sub_choice = questionary.select("Menu Start:", choices=["Start Tudo", "Start Backend", "Start Frontend", "Voltar"]).ask()
                    if sub_choice == "Start Tudo":
                        start_backend()
                        start_frontend()
                        break
                    elif sub_choice == "Start Backend":
                        start_backend()
                        break
                    elif sub_choice == "Start Frontend":
                        start_frontend()
                        break
                    elif sub_choice == "Voltar" or sub_choice is None:
                        break
            elif choice == "Stop":
                while True:
                    sub_choice = questionary.select("Menu Stop:", choices=["Stop Tudo", "Stop Backend", "Stop Frontend", "Voltar"]).ask()
                    if sub_choice == "Stop Tudo":
                        stop_port(8000)
                        stop_port(5173)
                        break
                    elif sub_choice == "Stop Backend":
                        stop_port(8000)
                        break
                    elif sub_choice == "Stop Frontend":
                        stop_port(5173)
                        break
                    elif sub_choice == "Voltar" or sub_choice is None:
                        break
            elif choice == "Build":
                sub_choice = questionary.select("Menu Build:", choices=["Build Frontend", "Voltar"]).ask()
                if sub_choice == "Build Frontend":
                    run_build_frontend()
            elif choice == "Test":
                while True:
                    sub_choice = questionary.select("Menu Test:", choices=["Testar Tudo", "Pytest (Backend)", "Vitest (Frontend)", "Voltar"]).ask()
                    if sub_choice == "Testar Tudo":
                        run_tests_backend()
                        run_tests_frontend()
                    elif sub_choice == "Pytest (Backend)":
                        run_tests_backend()
                    elif sub_choice == "Vitest (Frontend)":
                        run_tests_frontend()
                    elif sub_choice == "Voltar" or sub_choice is None:
                        break
            elif choice == "Logs":
                while True:
                    sub_choice = questionary.select("Menu Logs:", choices=["Log Backend", "Log Frontend", "Voltar"]).ask()
                    if sub_choice == "Log Backend":
                        tail_log("backend.log")
                    elif sub_choice == "Log Frontend":
                        tail_log("frontend.log")
                    elif sub_choice == "Voltar" or sub_choice is None:
                        break
            elif choice == "Sair" or choice is None:
                console.print("[bold yellow]Saindo da aplicação manager...[/bold yellow]")
                break
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Saindo (Ctrl+C detectado)...[/bold yellow]")
            break

if __name__ == "__main__":
    main()
