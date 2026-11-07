"""
Executa todos os programas de tests/*.minipar e compara com tests/expected_results/.

Para cada teste:
  1. Compila com  python main.py tests/<nome>.minipar
  2. Executa o binario gerado em output/ (com stdin, se o teste precisar)
  3. Compara a saida com <nome>.expected.txt  (se existir)
  4. Compara o TAC gerado com <nome>.expected.tac  (se existir)
  5. Confere trechos obrigatorios (CHECKS) nos testes sem arquivo esperado

Uso (a partir da raiz do repositorio):
  python tests/run_all.py                  # roda todos
  python tests/run_all.py teste3 teste7    # so os que contem esses textos no nome
  python tests/run_all.py -v               # mostra detalhes das falhas
  python tests/run_all.py --no-compile     # reaproveita binarios ja gerados
  python tests/run_all.py --timeout 30     # limite de tempo por execucao (s)
  python tests/run_all.py --retries 2      # tenta de novo testes que deram TIMEOUT

Codigo de saida: 0 se tudo passou, 1 se algo falhou (serve para CI).

Como a comparacao funciona
  Os arquivos .expected.txt sao TRECHOS da saida (ex.: o teste 3 so traz algumas
  iteracoes). Entao cada linha esperada precisa aparecer na saida real, NA ORDEM,
  mas podem existir linhas extras entre elas. Acentos, espacos repetidos e \\r
  sao ignorados. Numeros sao comparados como texto (0.5000 != 0.5), a menos que
  o teste esteja em TOLERANCE (ai compara com margem numerica).
"""
import argparse
import os
import re
import subprocess
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.join(ROOT, "tests")
EXPECTED_DIR = os.path.join(TESTS_DIR, "expected_results")
INPUTS_DIR = os.path.join(TESTS_DIR, "inputs")   
OUTPUT_DIR = os.path.join(ROOT, "output")
EXE_EXT = ".exe" if sys.platform == "win32" else ""

# ----------------------------------------------------------------------------
# CONFIGURACAO POR TESTE 
# ----------------------------------------------------------------------------
# Texto enviado ao stdin do programa.
INPUTS = {
    "teste1_calculadora_cliente_servidor": "+\n3\n4\n",
    "teste5_recomendacao": "\n".join(
        # Smartphone, Jeans, Micro-ondas e Ficcao comprados 
        "1" if i in (0, 5, 9, 12) else "0" for i in range(16)) + "\n",
    "teste6_quicksort_classes": "10 -3 -40 80 70 -100\n",
    "teste_bnf_controles_input": "Ana\n",
}

# Testes cuja saida varia (random): numeros comparados com esta margem absoluta.
TOLERANCE = {
    "teste4_rede_neural_xor": 0.05,
}

# Para testes SEM .expected.txt: trechos que devem aparecer na saida.
CHECKS = {
    "teste1_calculadora_cliente_servidor": ["Resultado: 7"],
    "teste2_fatorial_fibonacci_par": ["Fatorial de 5: 120"],
    "teste_adicional1_paralelismo_3_computadores": [
        "PC1 QuickSort: [33,12,98,5,61] -> [5,12,33,61,98]",
        "PC3 Fatorial: 5! = 120",
    ],
    "teste_bnf_controles_input": ["Controle OK"],
}

# ----------------------------------------------------------------------------
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def norm(s):
    """Tira acentos, \\r e espacos repetidos."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.replace("\r", "")).strip()


def line_matches(expected, actual, tol):
    e, a = norm(expected), norm(actual)
    if tol is None:
        return e == a
    en, an = NUM_RE.findall(e), NUM_RE.findall(a)
    if NUM_RE.sub("#", e) != NUM_RE.sub("#", a) or len(en) != len(an):
        return False
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(en, an))


def compare_subsequence(expected_text, actual_text, tol, ignore_lines=()):
    """Retorna lista de linhas esperadas que NAO foram encontradas (em ordem)."""
    ignore = {norm(l) for l in ignore_lines if l.strip()}
    actual = actual_text.splitlines()
    pos, missing = 0, []
    for exp in expected_text.splitlines():
        if not exp.strip() or norm(exp) in ignore:
            continue
        for k in range(pos, len(actual)):
            if line_matches(exp, actual[k], tol):
                pos = k + 1
                break
        else:
            missing.append(exp)
    return missing


def compare_exact(expected_text, actual_text):
    """Compara linha a linha ignorando \\r e espacos no fim. Retorna primeira diferenca."""
    e = [l.rstrip() for l in expected_text.replace("\r", "").splitlines()]
    a = [l.rstrip() for l in actual_text.replace("\r", "").splitlines()]
    for i in range(max(len(e), len(a))):
        le = e[i] if i < len(e) else "<fim do arquivo>"
        la = a[i] if i < len(a) else "<fim do arquivo>"
        if le != la:
            return f"linha {i + 1}: esperado {le!r} / obtido {la!r}"
    return None


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def run(cmd, stdin_text, timeout):
    try:
        p = subprocess.run(cmd, input=stdin_text, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, cwd=ROOT)
        return p.returncode, (p.stdout or "") + (p.stderr or ""), False
    except subprocess.TimeoutExpired as ex:
        out = (ex.stdout.decode("utf-8", "replace") if isinstance(ex.stdout, bytes) else ex.stdout) or ""
        return -1, out, True


def run_test(name, args):
    """Retorna (status, [detalhes]).  status: PASSOU, FALHOU, ERRO_COMPILACAO, CRASH, TIMEOUT, SEM_VERIFICACAO"""
    src = os.path.join(TESTS_DIR, name + ".minipar")
    details = []

    # 1) compilar
    if not args.no_compile:
        rc, out, to = run([sys.executable, os.path.join(ROOT, "main.py"), src], "", args.timeout * 4)
        if to or rc != 0:
            tail = [l for l in out.strip().splitlines() if l.strip()][-6:]
            details += ["compilacao falhou:"] + ["  " + l for l in tail]
            if "ws2_32" in out:
                details.append("  DICA: src/codegen.py fixa '-lws2_32' e '.exe' (so Windows).")
            return "ERRO_COMPILACAO", details

    exe = os.path.join(OUTPUT_DIR, name + EXE_EXT)
    if not os.path.isfile(exe):
        return "ERRO_COMPILACAO", [f"binario nao encontrado: {os.path.relpath(exe, ROOT)}"]

    # 2) executar
    in_file = os.path.join(INPUTS_DIR, name + ".in")
    stdin_text = read(in_file) if os.path.isfile(in_file) else INPUTS.get(name, "")
    rc, out, to = run([exe], stdin_text, args.timeout)
    if args.verbose:
        details.append("--- saida real ---")
        details += ["  | " + l for l in out.splitlines()[:40]]
        if len(out.splitlines()) > 40:
            details.append("  | ... (%d linhas no total)" % len(out.splitlines()))
    if to:
        return "TIMEOUT", details + [f"passou de {args.timeout}s (deadlock em canal/thread? loop infinito?)"]
    if rc != 0:
        last = [l for l in out.strip().splitlines() if l.strip()][-2:]
        return "CRASH", details + [f"codigo de saida {rc}"] + ["  " + l for l in last]

    failed, checked = False, False

    # 3) saida esperada
    exp_txt = os.path.join(EXPECTED_DIR, name + ".expected.txt")
    if os.path.isfile(exp_txt):
        checked = True
        missing = compare_subsequence(read(exp_txt), out, TOLERANCE.get(name), stdin_text.splitlines())
        if missing:
            failed = True
            total = len([l for l in read(exp_txt).splitlines() if l.strip()])
            details.append(f"saida: {len(missing)} de {total} linhas esperadas nao encontradas (primeiras):")
            details += ["  esperado: " + m for m in missing[:6]]

    # 4) TAC esperado
    exp_tac = os.path.join(EXPECTED_DIR, name + ".expected.tac")
    if os.path.isfile(exp_tac):
        tac_path = os.path.join(OUTPUT_DIR, name + ".tac")
        if not os.path.isfile(tac_path):
            failed = True
            details.append("TAC nao foi gerado")
        elif args.verbose:
            diff = compare_exact(read(exp_tac), read(tac_path))
            if diff:
                details.append("(info) TAC gerado difere do de referencia: " + diff)

    # 5) trechos obrigatorios
    if name in CHECKS:
        checked = True
        norm_out = norm(out)
        for needle in CHECKS[name]:
            if norm(needle) not in norm_out:
                failed = True
                details.append(f"trecho obrigatorio ausente: {needle!r}")

    if failed:
        return "FALHOU", details
    return ("PASSOU" if checked else "SEM_VERIFICACAO"), details


def main():
    ap = argparse.ArgumentParser(description="Roda todos os testes MiniPar e compara com expected_results/")
    ap.add_argument("filtros", nargs="*", help="so testes cujo nome contenha algum destes textos")
    ap.add_argument("-v", "--verbose", action="store_true", help="mostra a saida real de cada teste")
    ap.add_argument("--no-compile", action="store_true", help="nao recompila, usa output/ existente")
    ap.add_argument("--timeout", type=int, default=20, help="segundos por execucao (padrao 20)")
    ap.add_argument("--retries", type=int, default=0,
                    help="reexecuta (sem recompilar) testes que deram TIMEOUT; util p/ testes com sockets instaveis")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    names = sorted(f[:-8] for f in os.listdir(TESTS_DIR) if f.endswith(".minipar"))
    if args.filtros:
        names = [n for n in names if any(f in n for f in args.filtros)]
    if not names:
        print("Nenhum teste encontrado.")
        return 1

    label = {"PASSOU": "[ OK ]", "FALHOU": "[FAIL]", "ERRO_COMPILACAO": "[COMP]",
             "CRASH": "[CRSH]", "TIMEOUT": "[TIME]", "SEM_VERIFICACAO": "[ -- ]"}
    results = []
    for n in names:
        status, details = run_test(n, args)
        tries = 0
        while status == "TIMEOUT" and tries < args.retries:
            tries += 1
            again = argparse.Namespace(**{**vars(args), "no_compile": True})
            status, details = run_test(n, again)
        if tries:
            details.insert(0, f"(reexecutado {tries}x apos TIMEOUT)")
        results.append((n, status))
        print(f"{label[status]} {n}")
        for d in details:
            print("       " + d)

    print("\n" + "=" * 60)
    counts = {}
    for _, s in results:
        counts[s] = counts.get(s, 0) + 1
    ordem = ["PASSOU", "FALHOU", "CRASH", "TIMEOUT", "ERRO_COMPILACAO", "SEM_VERIFICACAO"]
    print("  " + " | ".join(f"{s}: {counts[s]}" for s in ordem if s in counts) + f"  (total {len(results)})")
    if counts.get("SEM_VERIFICACAO", 0):
        print("  [ -- ] = compilou e rodou, mas o teste nao tem saida esperada nem CHECKS")
    bad = sum(1 for _, s in results if s not in ("PASSOU", "SEM_VERIFICACAO"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
