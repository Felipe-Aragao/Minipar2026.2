"""Verificações da integração das interfaces com o compilador e o executável."""
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_interfaces_e_bibliotecas_locais_disponiveis(client):
    for route in ('/', '/didatico', '/ide'):
        response = client.get(route)
        assert response.status_code == 200
        assert b'/static/vendor/codemirror.min.js' in response.data
    assert b'didatico.js' in client.get('/').data
    assert b'/static/js/script.js' in client.get('/ide').data
    for asset in ('d3.min.js', 'codemirror.min.js', 'clike.min.js', 'codemirror.min.css'):
        assert client.get('/static/vendor/' + asset).status_code == 200


def test_analise_web_entrega_todas_as_fases_e_posicoes(client):
    result = client.post('/api/analisar', json={'code': 'seq { var x = 42; print(x); }'})
    assert result.status_code == 200
    data = result.json
    assert data['erros'] == [] and data['semantica']['sucesso'] is True
    assert data['tokens'] and data['ast']['node_type'] == 'Program'
    assert data['simbolos'][0]['nome'] == 'x'
    assert data['simbolos'][0]['coluna'] == 11
    assert 'print x' in data['tac'] and 'int main()' in data['cpp']


def test_analise_web_com_otimizacao(client):
    result = client.post('/api/analisar', json={
        'code': 'seq { var x = 2 + 3 * 4; print(x + 0); }',
        'otimizar': True
    })
    assert result.status_code == 200
    data = result.json
    assert data['erros'] == []
    assert data['otimizacao']['ativa'] is True
    assert data['otimizacao']['nos_antes'] > data['otimizacao']['nos_depois']
    assert data['otimizacao']['reducao_pct'] > 0
    assert 'x = 14' in data['tac']
    assert 'x + 0' in data['tac']


@pytest.mark.parametrize(('code', 'phase', 'semantic'), [
    ('seq { var x = ; }', 'sintatica', None),
    ('seq { print(ausente); }', 'semantica', False),
])
def test_erro_web_impede_fases_posteriores(client, code, phase, semantic):
    data = client.post('/api/analisar', json={'code': code}).json
    assert data['semantica']['sucesso'] is semantic
    assert data['erros'][0]['fase'] == phase
    assert data['erros'][0]['coluna'] is not None
    assert data['tac'] == '' and data['cpp'] == ''


def test_erro_codegen_preserva_ast_simbolos_e_tac(client):
    with patch('componente_codegen.C_Codegen.gerar_texto', side_effect=RuntimeError('falha controlada')):
        data = client.post('/api/analisar', json={'code': 'seq { var x = 42; print(x); }'}).json
    assert data['semantica']['sucesso'] is True
    assert data['ast'] and data['simbolos'] and data['tac']
    assert data['cpp'] == ''
    assert data['erros'] == [{'fase': 'codegen', 'linha': None, 'coluna': None,
                              'mensagem': 'falha controlada'}]


@pytest.mark.skipif(shutil.which('g++') is None, reason='g++ necessario')
def test_execucao_web_preserva_espacos_virgulas_e_entrada_vazia(client):
    expression = '((10 -8*7)+4)*2, exemplo com espacos'
    response = client.post('/api/compile', json={
        'code': 'seq { print(input()); print("Vazia:", len(input())); }',
        'filename': 'entrada.minipar', 'inputs': [expression, ''],
    })
    data = response.json
    assert response.status_code == 200 and data['success'], data
    assert data['execution_stdout'].splitlines() == [expression, 'Vazia: 0']
    assert data['cpp'] and data['tac'] and data['returncode'] == 0


@pytest.mark.skipif(shutil.which('g++') is None, reason='g++ necessario')
def test_download_binario_executa_e_erro_nao_reutiliza_arquivo_antigo(client, tmp_path):
    payload = {'code': 'seq { print(42); }', 'filename': 'download.minipar'}
    response = client.post('/api/download_exe', json=payload)
    assert response.status_code == 200
    assert 'attachment' in response.headers['Content-Disposition']
    extension = '.exe' if sys.platform == 'win32' else ''
    assert 'download' + extension in response.headers['Content-Disposition']
    assert response.data.startswith(b'MZ' if sys.platform == 'win32' else b'\x7fELF')
    executable = tmp_path / ('download' + extension)
    executable.write_bytes(response.data)
    executable.chmod(0o755)
    result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0 and result.stdout.strip() == '42'
    failed = client.post('/api/download_exe', json={**payload, 'code': 'seq { print(ausente); }'})
    assert failed.status_code == 400 and failed.json['success'] is False


@pytest.mark.skipif(shutil.which('g++') is None, reason='g++ necessario')
def test_execucao_com_codigo_de_erro_nao_e_marcada_como_sucesso(client):
    data = client.post('/api/compile', json={'code': 'seq { return 7; }'}).json
    assert data['success'] is False and data['returncode'] == 7
    assert 'codigo 7' in data['stderr']


@pytest.mark.skipif(shutil.which('g++') is None, reason='g++ necessario')
def test_execucao_web_com_otimizador(client):
    response = client.post('/api/compile', json={
        'code': 'seq { var x = 2 + 3 * 4; print(x + 0); }',
        'filename': 'teste_opt.minipar',
        'otimizar': True
    })
    data = response.json
    assert response.status_code == 200 and data['success'], data
    assert data['execution_stdout'].strip() == '14'


def test_rejeita_payload_invalido_e_nome_com_caminho(client):
    for payload in ({'code': 1}, {'code': 'seq {}', 'filename': '../fora.minipar'},
                    {'code': 'seq {}', 'inputs': 'entrada'}):
        response = client.post('/api/compile', json=payload)
        assert response.status_code == 400 and response.json['success'] is False
