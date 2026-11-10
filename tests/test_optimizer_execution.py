"""Equivalência entre programas compilados com e sem otimização da AST."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from analise import analisar


@pytest.mark.skipif(shutil.which('g++') is None, reason='g++ necessário')
@pytest.mark.parametrize(('code', 'expected'), [
    ('seq { print(3 / 2); print(-3 / 2); print(-3 % 2); print(3 % -2); '
     'print((0.0000001 + 0.0000001) == 0); '
     'print(2.0 / 2.0 / 2); print(-0.0000001 == 0); }',
     ['1', '-1', '-1', '1', '0', '0.5', '0']),
    ('seq { var x = 1; seq { var x = 2; print(x); } print(x); '
     'if (true) { var x = 3; print(x); } print(x); }', ['2', '1', '3', '1']),
    ('seq { par { if (true) { var x = 1; print(x); } } }', ['1']),
    ('seq { var x = 1; if (x == 1) while (false) { print(99); } '
     'print(x); }', ['1']),
    ('seq { var x = 2; print(x && true); print(x || false); '
     'var y = 0.0; print(1 / (y + 0)); }', ['1', '1', 'inf']),
    ('func f() { return 3 / 2; } '
     'func g() { if (false) { return 1.5; } return 1; } '
     'seq { print(f() / 2); print(g() / 2); }', ['0.5', '0.5']),
])
def test_execucao_preservada(tmp_path, code, expected):
    outputs = []
    for optimize in (False, True):
        result = analisar(code, otimizar=optimize)
        assert result['erros'] == [], result['erros']
        source = tmp_path / f'programa_{int(optimize)}.cpp'
        executable = tmp_path / (source.stem + ('.exe' if sys.platform == 'win32' else ''))
        source.write_text(result['cpp'], encoding='utf-8')
        command = ['g++', '-std=c++20', '-O3', str(source), '-o', str(executable), '-pthread']
        if sys.platform == 'win32':
            command.append('-lws2_32')
        compiled = subprocess.run(command, capture_output=True, text=True, timeout=60)
        assert compiled.returncode == 0, compiled.stderr
        run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
        assert run.returncode == 0, run.stderr
        outputs.append(run.stdout.splitlines())
    assert outputs[0] == expected
    assert outputs[1] == outputs[0]
