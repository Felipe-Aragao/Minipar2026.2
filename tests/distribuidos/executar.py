"""Compila e executa os papéis de rede dos testes 1 e 2 em um ou dois PCs."""
from pathlib import Path
import argparse
import datetime
import ipaddress
import json
import platform
import re
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def compile_role(test, role, job):
    source = HERE / f'teste{test:02d}_pc_{role}.minipar'
    p = subprocess.run([sys.executable, str(ROOT / 'main.py'), str(source), 'rede'],
                       cwd=job, capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=90)
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    return job / 'output' / ('rede.exe' if sys.platform == 'win32' else 'rede')


def verify(test, role, output):
    if test == 1:
        label = 'PC A recebeu:' if role == 'a' else 'PC B calculou:'
        match = re.search(re.escape(label) + r'\s*([^\r\n]+)', output)
        try:
            return match is not None and float(match.group(1).strip()) == 12.0
        except ValueError:
            return False
    if role == 'a':
        factorial = re.search(r'Fatorial de 5:\s*([^\r\n]+)', output)
        fibonacci = re.search(r'PC A recebeu Fibonacci:\s*([^\r\n]+)', output)
        return (factorial is not None and factorial.group(1).strip() == '120'
                and fibonacci is not None and fibonacci.group(1).split() == ['0', '1', '1', '2', '3', '5', '8', '13'])
    match = re.search(r'PC B - Fibonacci:\s*([^\r\n]+)', output)
    return match is not None and match.group(1).split() == ['0', '1', '1', '2', '3', '5', '8', '13']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--teste', type=int, choices=[1, 2], required=True)
    ap.add_argument('--papel', choices=['a', 'b'])
    ap.add_argument('--ip-par', help='IPv4 do outro computador')
    ap.add_argument('--local', action='store_true', help='dois processos em loopback; não comprova dois PCs')
    args = ap.parse_args()
    if args.local and (args.papel or args.ip_par):
        ap.error('--local não recebe --papel nem --ip-par')
    if not args.local and (not args.papel or not args.ip_par):
        ap.error('informe --papel e --ip-par, ou use --local')
    if not args.local:
        address = ipaddress.ip_address(args.ip_par)
        if address.version != 4 or address.is_loopback or address.is_unspecified:
            ap.error('use um IPv4 alcançável da outra máquina, diferente de localhost')
    jobs = ROOT / 'output' / 'testes_distribuidos'
    jobs.mkdir(parents=True, exist_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix='rede_', dir=jobs) as temporary:
        work = Path(temporary)
        roles = ['b', 'a'] if args.local else [args.papel]
        executables = {}
        for role in roles:
            job = work / role
            job.mkdir()
            executables[role] = compile_role(args.teste, role, job)
        if args.local:
            server = subprocess.Popen([str(executables['b'])], cwd=work,
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True,
                                      encoding='utf-8', errors='replace')
            try:
                server.stdin.write('127.0.0.1\n')
                server.stdin.flush()
                client = subprocess.run([str(executables['a'])], cwd=work,
                                        input='127.0.0.1\n', capture_output=True,
                                        text=True, encoding='utf-8', errors='replace', timeout=30)
                stdout, stderr = server.communicate(timeout=30)
                records = [('a', client.returncode, client.stdout, client.stderr),
                           ('b', server.returncode, stdout, stderr)]
            finally:
                if server.poll() is None:
                    server.kill()
                    server.communicate()
        else:
            print('Executando. Inicie também o papel correspondente no outro PC.', flush=True)
            result = subprocess.run([str(executables[args.papel])], cwd=work,
                                    input=args.ip_par + '\n', capture_output=True,
                                    text=True, encoding='utf-8', errors='replace', timeout=90)
            records = [(args.papel, result.returncode, result.stdout, result.stderr)]
    success = all(code == 0 and verify(args.teste, role, out) for role, code, out, err in records)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    log = jobs / f'teste{args.teste:02d}_{"local" if args.local else args.papel}_{stamp}.json'
    log.write_text(json.dumps({'data_utc': stamp, 'maquina': socket.gethostname(),
                              'sistema': platform.platform(), 'python': sys.version,
                              'modo': 'loopback' if args.local else 'rede', 'ip_par': args.ip_par,
                              'teste': args.teste, 'sucesso': success,
                              'resultados': [{'papel': role, 'retorno': code, 'stdout': out, 'stderr': err}
                                             for role, code, out, err in records]},
                             ensure_ascii=False, indent=2), encoding='utf-8')
    for role, code, out, err in records:
        print(f'--- PC {role.upper()} ---\n{out}{err}')
    print(('PASSOU' if success else 'FALHOU') + f' | Evidência: {log}')
    if args.local:
        print('Ensaio local em uma máquina; não comprova dois computadores.')
    return 0 if success else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as error:
        print(f'ERRO: {error}', file=sys.stderr)
        raise SystemExit(1)
