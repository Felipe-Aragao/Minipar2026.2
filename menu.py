import os
import sys
import subprocess
import glob
import re

from main import compile_file
from program_analyzer import get_program_spec
from test_orchestrator import (
    prepare_test_execution,
    finalize_test_execution,
    check_active_session_for_new_terminal,
    join_session,
    get_terminal_id,
    set_session_phase,
    append_session_log,
    record_execution_output,
    run_joiner_progress_monitor,
    _load_session,
)


def executar_binario(output_name: str, interactive: bool = False) -> str:
    """Executa o binario. Modo interativo quando o programa usa input()."""
    exe_ext = ".exe" if sys.platform == "win32" else ""
    exe_path = os.path.join("output", f"{output_name}{exe_ext}")

    if not os.path.exists(exe_path):
        print(f"[ERRO] Executavel {exe_path} nao encontrado apos compilacao.")
        return ""

    abs_exe_path = os.path.abspath(exe_path)
    print(f"\n--- Executando {output_name} ---")
    set_session_phase("executing", f"Executando {output_name}...", percent=85)
    append_session_log(f"Executando {output_name}.")

    try:
        if interactive:
            # stdin conectado ao terminal - necessario para input() no codigo MiniPar
            result = subprocess.run([abs_exe_path], text=True)
            if result.returncode != 0:
                print(f"[ERRO] Programa encerrou com codigo {result.returncode}.")
            return ""
        # Programas sem input(): captura saida para exibir nos terminais participantes
        result = subprocess.run(
            [abs_exe_path],
            text=True,
            capture_output=True,
        )
        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr
        if output.strip():
            print(output)
            record_execution_output(output)
        return output
    except Exception as e:
        print(f"[ERRO] Falha ao executar {exe_path}: {e}")
        return ""
    finally:
        print("-" * 40)


def _exibir_info_teste(test_path: str) -> None:
    spec = get_program_spec(test_path)
    print(f"\n  Programa: {spec.get('titulo', '')}")
    if spec.get("requires_input"):
        print(f"  Entradas input() detectadas: {spec.get('input_count', 0)}")
    if spec.get("multi_computer"):
        mc = spec["multi_computer"]
        print(f"  Multi-terminal: {mc['count']} participante(s)")


def rodar_teste(test_path: str) -> None:
    base_name = os.path.basename(test_path).replace(".minipar", "")

    _exibir_info_teste(test_path)

    proceed, interactive, is_joiner = prepare_test_execution(test_path)
    if not proceed:
        return

    if is_joiner:
        # Participante ja acompanhou via run_joiner_progress_monitor - nao reexecuta
        print(f"\n  Terminal participante: {get_terminal_id()}\n")
        return

    set_session_phase("compiling", "Compilando...", percent=55)
    append_session_log("Compilacao iniciada.")
    success = compile_file(test_path, base_name)
    if success:
        set_session_phase("compiling", "Compilacao concluida.", percent=80)
        append_session_log("Compilacao concluida.")
        output = executar_binario(base_name, interactive=interactive)
        finalize_test_execution(test_path, output)
    else:
        append_session_log("Erro na compilacao.")
        print(f"[AVISO] Pulando execucao de {test_path} devido a erro de compilacao.")


def obter_testes() -> list:
    """Retorna a lista dos 11 testes oficiais da pasta tests/oficiais/ em ordem numerica (1 a 11)."""
    oficiais_dir = os.path.join("tests", "oficiais")
    def num_key(p):
        m = re.search(r'\d+', os.path.basename(p))
        return int(m.group(0)) if m else 999

    if os.path.isdir(oficiais_dir):
        return sorted(glob.glob(os.path.join(oficiais_dir, "*.minipar")), key=num_key)

    tests_dir = "tests"
    if not os.path.exists(tests_dir):
        print(f"[ERRO] Diretorio '{tests_dir}' nao encontrado!")
        return []
    return sorted(glob.glob(os.path.join(tests_dir, "*.minipar")), key=num_key)


def rodar_todos():
    testes = obter_testes()
    if not testes:
        return
    print(f"\n=== Rodando todos os testes oficiais ({len(testes)} encontrados) ===")
    for teste in testes:
        rodar_teste(teste)


def escolher_teste():
    testes = obter_testes()
    if not testes:
        return

    print("\n=== Escolha um teste oficial para rodar ===")
    for i, teste in enumerate(testes):
        nome = os.path.basename(teste)
        spec = get_program_spec(teste)
        tags = []
        if spec.get("requires_input"):
            tags.append(f"{spec['input_count']} input(s)")
        if spec.get("multi_computer"):
            tags.append(f"{spec['multi_computer']['count']} terminais")
        tag_str = f"  [{', '.join(tags)}]" if tags else ""
        print(f"[{i + 1}] {nome}{tag_str}")

    try:
        escolha = int(input("\nDigite o numero do teste: "))
        if 1 <= escolha <= len(testes):
            rodar_teste(testes[escolha - 1])
        else:
            print("[ERRO] Escolha invalida.")
    except ValueError:
        print("[ERRO] Por favor, digite um numero valido.")


def _verificar_sessao_ao_iniciar() -> None:
    """Novo terminal que entra no menu durante execucao multi-terminal em andamento."""
    action, session = check_active_session_for_new_terminal()
    if action == "join" and session:
        join_session(session)
        session = _load_session() or session
        print(f"\n  [OK] Participante conectado: {get_terminal_id()}\n")
        run_joiner_progress_monitor(session)
    elif action == "independent":
        print("\n  [INFO] Modo independente.\n")


def exibir_menu():
    _verificar_sessao_ao_iniciar()

    while True:
        print("\n" + "=" * 45)
        print(" Menu de Testes Oficiais - MiniPar 2026.2")
        print("=" * 45)
        print("1 - Rodar todos os 11 testes oficiais")
        print("2 - Escolher 1 teste oficial para rodar (1 a 11)")
        print("0 - Sair")
        print("=" * 45)

        opcao = input("Escolha uma opcao: ")

        if opcao == "1":
            rodar_todos()
        elif opcao == "2":
            escolher_teste()
        elif opcao == "0":
            print("Saindo...")
            break
        else:
            print("Opcao invalida. Tente novamente.")


if __name__ == "__main__":
    exibir_menu()
