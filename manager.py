import subprocess
import sys
import time
import os
import socket
import msvcrt
import webbrowser
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import questionary

console = Console()
CREATE_NO_WINDOW = 0x08000000
BACKEND_PID_FILE = "backend.pid"
FRONTEND_PID_FILE = "frontend.pid"
FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8001"

def is_port_open(port: int) -> bool:
    # Vite (e outros dev servers Node) às vezes escutam só em IPv6 (::1),
    # então checar apenas 127.0.0.1 pode reportar OFFLINE com o serviço no ar.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        if s.connect_ex(('127.0.0.1', port)) == 0:
            return True
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(('::1', port)) == 0:
                return True
    except OSError:
        pass
    return False

def get_status_panel():
    backend_status = is_port_open(8001)
    frontend_status = is_port_open(5173)

    b_text = "[bold green][ONLINE][/bold green]" if backend_status else "[bold red][OFFLINE][/bold red]"
    f_text = "[bold green][ONLINE][/bold green]" if frontend_status else "[bold red][OFFLINE][/bold red]"

    text = Text.from_markup(
        f"Backend  (Port 8001): {b_text}  [link={BACKEND_URL}]{BACKEND_URL}[/link]\n"
        f"Frontend (Port 5173): {f_text}  [link={FRONTEND_URL}]{FRONTEND_URL}[/link]"
    )
    return Panel(text, title="Bibitinhos Status Panel", expand=False, border_style="cyan")

def write_pid_file(pidfile: str, pid: int):
    with open(pidfile, "w") as f:
        f.write(str(pid))

def read_pid_file(pidfile: str):
    if not os.path.exists(pidfile):
        return None
    try:
        with open(pidfile, "r") as f:
            content = f.read().strip()
            return int(content) if content else None
    except (ValueError, OSError):
        return None

def kill_pid_tree(pid):
    subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)

def start_backend():
    if is_port_open(8001):
        console.print("[yellow]Backend já está rodando.[/yellow]")
        time.sleep(1)
        return
    log = open("backend.log", "a")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", "8001", "--reload"], cwd="backend", stdout=log, stderr=log, creationflags=CREATE_NO_WINDOW)
    write_pid_file(BACKEND_PID_FILE, proc.pid)
    time.sleep(0.5)

def start_frontend():
    if is_port_open(5173):
        console.print("[yellow]Frontend já está rodando.[/yellow]")
        time.sleep(1)
        return
    log = open("frontend.log", "a")
    proc = subprocess.Popen("npm run dev", cwd="frontend", stdout=log, stderr=log, creationflags=CREATE_NO_WINDOW, shell=True)
    write_pid_file(FRONTEND_PID_FILE, proc.pid)
    time.sleep(0.5)

def get_pids_by_port(port: int):
    pids = set()
    try:
        result = subprocess.run(f"netstat -ano | findstr LISTENING | findstr :{port}", shell=True, capture_output=True, text=True)
        for line in result.stdout.strip().split('\n'):
            if f":{port}" in line:
                parts = line.strip().split()
                if len(parts) > 4 and parts[-1].isdigit():
                    pids.add(parts[-1])
    except Exception:
        pass
    return pids

def stop_port(port: int, pidfile: str = None):
    # 1. Mata a árvore inteira a partir do PID raiz gravado ao iniciar o serviço
    #    (necessário pro frontend: cmd.exe -> npm.cmd -> node/vite fica órfão se
    #    só o PID que está de fato escutando a porta for morto).
    if pidfile:
        root_pid = read_pid_file(pidfile)
        if root_pid:
            kill_pid_tree(root_pid)
        if os.path.exists(pidfile):
            os.remove(pidfile)

    # 2. Limpeza: mata qualquer processo remanescente ainda escutando a porta
    #    (cobre processos órfãos de execuções anteriores sem pidfile).
    for pid in get_pids_by_port(port):
        kill_pid_tree(pid)

    # 3. Aguarda a porta ser efetivamente liberada antes de retornar.
    for _ in range(20):
        if not is_port_open(port):
            return True
        time.sleep(0.25)

    console.print(f"[bold red]Aviso: a porta {port} continua ocupada após tentativa de parada.[/bold red]")
    time.sleep(1.5)
    return False

def tail_log(filename):
    console.print(f"\n[cyan]>> Tailing {filename}... Pressione 'q', 'ESC' ou Ctrl+C para voltar ao menu.[/cyan]")
    if not os.path.exists(filename):
        console.print("[red]Arquivo de log não encontrado. O serviço já foi iniciado?[/red]")
        time.sleep(2)
        return
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[-30:]:
            sys.stdout.write(line)
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
                choices=["Start", "Stop", "Abrir Frontend no Navegador", "Build", "Test", "Logs", "Sair"]
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
                        stop_port(8001, BACKEND_PID_FILE)
                        stop_port(5173, FRONTEND_PID_FILE)
                        break
                    elif sub_choice == "Stop Backend":
                        stop_port(8001, BACKEND_PID_FILE)
                        break
                    elif sub_choice == "Stop Frontend":
                        stop_port(5173, FRONTEND_PID_FILE)
                        break
                    elif sub_choice == "Voltar" or sub_choice is None:
                        break
            elif choice == "Abrir Frontend no Navegador":
                if is_port_open(5173):
                    webbrowser.open(FRONTEND_URL)
                else:
                    console.print("[yellow]Frontend está offline. Inicie-o primeiro.[/yellow]")
                    time.sleep(1.5)
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
