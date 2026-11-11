import sys
import os

# Resolve os imports a partir do projeto, mesmo quando o terminal está em outra pasta.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'src'))

from componente_lexico import C_Lexico, ILexico
from componente_semantico import C_Semantico, ISemantico
from componente_sintatico import C_Sintatico, ISintatico
from componente_otimizador import C_Otimizador, IOtimizador
from componente_tac import C_TAC, ITAC
from lexer import LexError, TokenType
from parser import ParseError
from componente_codegen import C_Codegen, ICodegen

# A CLI interrompe o pipeline quando uma fase encontra erros e só chama o GCC após validar o programa.
def compile_file(source_path: str, output_name: str, otimizar: bool = False) -> bool:
    """Processa as Fases do Compilador em um arquivo alvo."""
    print(f"\n=== Compilando: {source_path} ===")
    try:
        with open(source_path, encoding="utf-8") as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"[ERRO] Arquivo nao encontrado: {source_path}", file=sys.stderr)
        return False

    print("[Fase 1] Analise Lexica e Sintatica...")
    lexico: ILexico = C_Lexico()
    try:
        tokens = lexico.analise_lexica(source_code)
    except LexError as error:
        print(f"[ERRO LEXICO] Linha {error.line}, coluna {error.col}: {error}", file=sys.stderr)
        return False
    invalid_tokens = [token for token in tokens if token.type == TokenType.UNKNOWN]
    if invalid_tokens:
        for token in invalid_tokens:
            print(f"[ERRO LEXICO] Linha {token.line}, coluna {token.col}: Caractere nao reconhecido: {token.lexeme!r}", file=sys.stderr)
        return False

    sintatico: ISintatico = C_Sintatico()
    try:
        program = sintatico.analise_sintatica(tokens)
    except ParseError as error:
        print(f"[ERRO SINTATICO] Linha {error.line}, coluna {error.col}: {error}", file=sys.stderr)
        return False

    print("[Fase 2] Analise Semantica e Tabela de Simbolos...")
    semantico: ISemantico = C_Semantico(emitir_diagnosticos=True)
    validacao = semantico.analise_semantica(program)
    if not validacao.sucesso:
        print("[ERRO] Falha na Analise Semantica. Compilacao abortada.", file=sys.stderr)
        return False

    if otimizar:
        print("[Fase Intermediária] Otimização Independente de Máquina (Middle-end)...")
        otimizador: IOtimizador = C_Otimizador()
        res_opt = otimizador.otimizar(program)
        program = res_opt.programa_otimizado
        reducao = 0.0
        if res_opt.nos_antes > 0:
            reducao = round((1.0 - (res_opt.nos_depois / res_opt.nos_antes)) * 100.0, 1)
        print(f"[Otimizador] Nós da AST: {res_opt.nos_antes} -> {res_opt.nos_depois} ({reducao}% de redução)")
        if res_opt.transformacoes:
            print(f"[Otimizador] {len(res_opt.transformacoes)} transformação(ões) aplicada(s).")

    print("[Fase 3] Geracao de Codigo Intermediario (TAC - 3 enderecos)...")
    tac: ITAC = C_TAC()
    tac_path = tac.gerar_arquivo(program, output_name)
    print(f"[TAC] Arquivo gerado: {tac_path}")

    print("[Fase 4] Transpilacao e Chamada do GCC (-O3)...")
    codegen: ICodegen = C_Codegen()
    return codegen.gerar_codigo(program, output_name)


# O menu oferece acesso aos testes no terminal e às duas interfaces servidas pelo Flask.
def start_interactive():
    """Inicia a tela de seleção inicial do sistema."""
    from test_orchestrator import (
        check_active_session_for_new_terminal,
        join_session,
        get_terminal_id,
        run_joiner_progress_monitor,
        _load_session,
    )

    # Segundo terminal detectou sessão ativa — entra como participante antes do menu
    action, session = check_active_session_for_new_terminal()
    if action == "join" and session:
        join_session(session)
        session = _load_session() or session
        print("\n" + "=" * 45)
        print("  MINIPAR — PARTICIPANTE DE TESTE")
        print("=" * 45)
        print(f"\n  Terminal identificado: {get_terminal_id()}")
        print(f"  Teste em andamento: {session.get('titulo', session.get('test_file', ''))}")
        print("\n  Monitor de progresso iniciado...\n")
        run_joiner_progress_monitor(session)
    elif action == "independent":
        print("\n  [INFO] Sessão em andamento ignorada — modo independente.\n")

    print("\n" + "=" * 45)
    print("      MINIPAR COMPILER & IDE")
    print("=" * 45)
    print("\nComo você deseja rodar o sistema?\n")
    print("[1] - Modo Terminal (Menu Interativo)")
    print("[2] - Modo Web Interface (IDE no Navegador)\n")
    
    escolha = input("Digite a sua escolha (1 ou 2): ").strip()
    
    if escolha == '1':
        print("\nIniciando modo Terminal...\n")
        try:
            import menu
            menu.exibir_menu()
        except ImportError as e:
            print(f"[ERRO] Falha ao carregar o menu: {e}")
            
    elif escolha == '2':
        print("\nIniciando Servidor Web MiniPar 2026.2...")
        print("  -> Modo Didático (Educacional): http://127.0.0.1:5000/")
        print("  -> Modo Desenvolvedor (IDE 2026.1): http://127.0.0.1:5000/ide\n")
        try:
            from app import app
            # Executa o Flask. Deixamos debug=False para o terminal ficar mais limpo
            app.run(host="127.0.0.1", port=5000, debug=False)
        except ImportError as e:
            print(f"[ERRO] Falha ao carregar a interface web: {e}")
        except Exception as e:
            print(f"[ERRO] Erro ao iniciar o servidor Flask: {e}")
    else:
        print("\n[ERRO] Escolha inválida. Finalizando o sistema.")


# A opção de otimização é separada dos argumentos de caminho e nome do executável.
def main() -> int:
    args = sys.argv[1:]
    otimizar = False
    if "-O" in args or "--optimize" in args:
        otimizar = True
        args = [a for a in args if a not in ("-O", "--optimize")]

    # Se rodar sem argumentos (ex: `python main.py`), inicia a interface de escolha
    if not args:
        start_interactive()
        return 0

    source_path = args[0]
    if len(args) > 1:
        output_name = args[1]
    else:
        base_file = os.path.basename(source_path)
        output_name = base_file.replace('.minipar', '')

    print("=== Compilador MiniPar ===")
    success = compile_file(source_path, output_name, otimizar=otimizar)
    
    if success:
        print("=== Processo Finalizado ===")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
