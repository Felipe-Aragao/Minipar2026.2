from flask import Flask, render_template, request, jsonify, send_file
from contextlib import contextmanager
from io import BytesIO
from tempfile import TemporaryDirectory
from werkzeug.utils import secure_filename
import subprocess
import os
import sys
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.join(BASE_DIR, 'src') not in sys.path:
    sys.path.insert(0, os.path.join(BASE_DIR, 'src'))
from analise import analisar

from test_orchestrator import (
    get_spec_summary,
    finalize_test_execution,
    check_active_session_for_new_terminal,
    join_session,
    get_terminal_id,
    create_session,
    clear_session,
    set_session_phase,
    append_session_log,
    record_execution_output,
    _load_session,
    _save_session,
)

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Configuração de Diretórios
TESTS_DIR = os.path.join(BASE_DIR, 'tests')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
TEMP_DIR = os.path.join(BASE_DIR, 'temp_code')

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/')
@app.route('/didatico')
def didatico():
    """Segunda Interface Web do MiniPar 2026.2 (Educacional/Didática)."""
    return render_template('didatico.html')

@app.route('/ide')
def ide():
    """Primeira Interface Web do MiniPar (IDE do Desenvolvedor de 2026.1)."""
    return render_template('index.html')

@app.route('/api/analisar', methods=['POST'])
def api_analisar():
    """Executa a análise modular por fases (Léxico, Sintático, Semântico, TAC, C++) em memória."""
    try:
        codigo, _, _ = _web_payload()
        resultado = analisar(codigo)
        return jsonify(resultado)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({
            "tokens": [],
            "ast": None,
            "simbolos": [],
            "semantica": {"sucesso": None},
            "tac": "",
            "cpp": "",
            "erros": [{"fase": "sistema", "linha": None, "coluna": None, "mensagem": str(e)}]
        }), 500

def _web_payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('code'), str):
        raise ValueError("Envie o codigo fonte no campo 'code'.")
    filename = data.get('filename', 'programa_minipar.minipar')
    if not isinstance(filename, str) or '/' in filename or chr(92) in filename:
        raise ValueError("Nome de arquivo invalido.")
    filename = secure_filename(filename) or 'programa_minipar.minipar'
    if not filename.endswith('.minipar'):
        filename += '.minipar'
    inputs = data.get('inputs', [])
    if not isinstance(inputs, list) or not all(isinstance(item, str) for item in inputs):
        raise ValueError("As entradas devem ser uma lista de linhas de texto.")
    return data['code'], filename, inputs


@contextmanager
def _compiled_program(code):
    """Compilação isolada para evitar resultados antigos ou arquivos de outra requisição."""
    jobs_dir = os.path.join(OUTPUT_DIR, 'web_jobs')
    os.makedirs(jobs_dir, exist_ok=True)
    with TemporaryDirectory(prefix='minipar_', dir=jobs_dir) as job:
        source = os.path.join(job, 'programa.minipar')
        with open(source, 'w', encoding='utf-8') as stream:
            stream.write(code)
        process = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, 'main.py'), source],
            cwd=job, capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=60,
        )
        generated = os.path.join(job, 'output', 'programa')
        artifacts = {}
        for extension in ('cpp', 'tac'):
            path = generated + '.' + extension
            artifacts[extension] = ''
            if os.path.isfile(path):
                with open(path, encoding='utf-8') as stream:
                    artifacts[extension] = stream.read()
        executable = generated + ('.exe' if sys.platform == 'win32' else '')
        yield process, executable, artifacts, job


@app.route('/api/download_exe', methods=['POST'])
def download_exe():
    """Compila em diretório exclusivo e envia somente o binário desta requisição."""
    try:
        code, filename, _ = _web_payload()
        with _compiled_program(code) as (process, executable, _, job):
            if process.returncode != 0:
                return jsonify(success=False, error=process.stdout + process.stderr), 400
            if not os.path.isfile(executable):
                return jsonify(success=False, error="Executavel nao foi gerado."), 500
            with open(executable, 'rb') as stream:
                binary = BytesIO(stream.read())
        extension = '.exe' if sys.platform == 'win32' else ''
        return send_file(binary, as_attachment=True,
                         download_name=os.path.splitext(filename)[0] + extension,
                         mimetype='application/octet-stream')
    except ValueError as error:
        return jsonify(success=False, error=str(error)), 400
    except subprocess.TimeoutExpired:
        return jsonify(success=False, error="Tempo limite de compilacao excedido."), 504
    except OSError as error:
        return jsonify(success=False, error=str(error)), 500


@app.route('/api/tests', methods=['GET'])
def get_tests():
    # Retorna os testes ordenados alfabeticamente
    tests = [os.path.basename(f) for f in glob.glob(os.path.join(TESTS_DIR, '*.minipar'))]
    return jsonify({"tests": sorted(tests)})

@app.route('/api/get_test', methods=['POST'])
def get_test():
    filename = request.json.get('filename')
    filepath = os.path.join(TESTS_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return jsonify({"code": f.read()})
    return jsonify({"error": "Arquivo não encontrado"}), 404

@app.route('/api/test_spec', methods=['POST'])
def get_test_spec_api():
    """Requisitos detectados automaticamente pelo program_analyzer."""
    filename = request.json.get('filename')
    spec = get_spec_summary(filename)
    if spec:
        return jsonify(spec)
    return jsonify({"requires_input": False, "multi_computer": None})


@app.route('/api/session', methods=['GET'])
def get_session():
    action, session = check_active_session_for_new_terminal()
    if session:
        return jsonify({
            "active": session.get("status") not in ("completed", "cancelled"),
            "session": session,
            "terminal_id": get_terminal_id(),
            "needs_choice": action is not None,
        })
    return jsonify({"active": False, "terminal_id": get_terminal_id()})


@app.route('/api/session/join', methods=['POST'])
def session_join():
    _, session = check_active_session_for_new_terminal()
    if session:
        join_session(session)
        return jsonify({"success": True, "session": session})
    return jsonify({"success": False, "error": "Nenhuma sessão ativa"}), 404


@app.route('/api/session/create', methods=['POST'])
def session_create():
    filename = request.json.get('filename')
    path = os.path.join(TESTS_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"success": False, "error": "Arquivo não encontrado"}), 404
    from program_analyzer import get_program_spec
    spec = get_program_spec(path)
    if not spec.get('multi_computer'):
        return jsonify({"success": False, "error": "Programa não requer multi-terminal"}), 400
    session = create_session(path, spec)
    return jsonify({"success": True, "session": session})


@app.route('/api/session/ready', methods=['POST'])
def session_ready():
    session = _load_session()
    if session:
        session["status"] = "running"
        _save_session(session)
        return jsonify({"success": True})
    return jsonify({"success": False}), 404


@app.route('/api/session/clear', methods=['POST'])
def session_clear():
    clear_session()
    return jsonify({"success": True})


@app.route('/api/compile', methods=['POST'])
def compile_code():
    """Mantém a API da IDE antiga e executa o programa da interface didática."""
    try:
        code, filename, inputs = _web_payload()
        set_session_phase("compiling", "Compilando codigo MiniPar...", percent=60)
        append_session_log("Compilacao iniciada via IDE Web.")
        with _compiled_program(code) as (process, executable, artifacts, job):
            output = process.stdout + process.stderr
            success = process.returncode == 0
            returncode = None
            execution_stdout = ''
            if success and not os.path.isfile(executable):
                success = False
                output += "\nExecutavel nao foi gerado."
            if success:
                set_session_phase("executing", "Executando programa...", percent=90)
                output += "\n--- Executando " + os.path.splitext(filename)[0] + " ---\n"
                try:
                    execution = subprocess.run(
                        [executable], cwd=BASE_DIR, input='\n'.join(inputs) + ('\n' if inputs else ''),
                        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60,
                    )
                    returncode = execution.returncode
                    success = returncode == 0
                    execution_stdout = execution.stdout
                    output += execution.stdout + execution.stderr
                    if not success:
                        output += f"\nPrograma encerrou com codigo {returncode}."
                    record_execution_output(execution.stdout)
                except subprocess.TimeoutExpired:
                    success = False
                    output += "\nTempo limite de execucao excedido."
                source = os.path.join(TESTS_DIR, filename)
                if os.path.isfile(source):
                    finalize_test_execution(source, output)
            return jsonify(stdout=output if success else '', stderr=output if not success else '',
                           cpp=artifacts['cpp'], tac=artifacts['tac'], success=success,
                           returncode=returncode, execution_stdout=execution_stdout)
    except ValueError as error:
        return jsonify(success=False, error=str(error)), 400
    except subprocess.TimeoutExpired:
        return jsonify(success=False, error="Tempo limite de compilacao excedido."), 504
    except OSError as error:
        return jsonify(success=False, error=str(error)), 500


if __name__ == '__main__':
    # Roda a IDE silenciosamente
    app.run(debug=False, port=5000)