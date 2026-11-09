"""Regressões de execução da integração entre front-end e backend."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("g++") is None, reason="g++ necessario para executar C++")


@pytest.mark.parametrize(
    ("codigo", "esperado"),
    [
        ('func mudar(x) { x = 2; return 0; } seq { var x = 1; '
         'par { seq { mudar(x); print(x); } } print(x); }',
         ["2", "1"]),
        ('func mudar(xs) { xs[0] = 2; return 0; } seq { var xs = [1]; '
         'par { seq { mudar(xs); print(xs); } } print(xs); }',
         ["[2]", "[1]"]),
        ('seq { fork { fork { print("filho"); } join; } join; print("fim"); }',
         ["filho", "fim"]),
        ('func trabalho() { var fim = time() + 0.02; while (time() < fim) {} print("concluido"); return 7; } '
         'seq { task t = fork trabalho(); join; print("apos barreira"); print(join(t)); }',
         ["concluido", "apos barreira", "7"]),
        ('seq { seq { var x = 10; fork { print(x); } } join; }',
         ["10"]),
        ('func texto() { return to_string(1.5); } seq { print(texto()); }',
         ["1.500000"]),
        ('seq { var t = fork { print("tarefa"); }; var resultado = join(t); print(resultado); }',
         ["tarefa", "0"]),
        ('seq { var valores = [1, 2]; print("Lista:", valores); }',
         ["Lista: [1, 2]"]),
    ],
)
def test_executavel_preserva_sincronizacao_e_retornos(tmp_path, codigo, esperado):
    fonte = tmp_path / "integracao.minipar"
    fonte.write_text(codigo, encoding="utf-8")
    compilacao = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), str(fonte)],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=60,
    )
    assert compilacao.returncode == 0, compilacao.stdout + compilacao.stderr
    nome = "integracao.exe" if sys.platform == "win32" else "integracao"
    execucao = subprocess.run(
        [str(tmp_path / "output" / nome)], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=5,
    )
    assert execucao.returncode == 0, execucao.stdout + execucao.stderr
    assert execucao.stdout.splitlines() == esperado
