"""Atende chamadas fork host de um executável MiniPar previamente compilado."""
import argparse
import math
from pathlib import Path
import re
import socketserver
import subprocess


class Worker(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class Request(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(3)
        try:
            line = self.rfile.readline(4097)
            if len(line) > 4096 or not line.endswith(b"\n"):
                return
            fields = line.decode("ascii").split()
            if (len(fields) < 2 or not re.fullmatch(r"[a-f0-9]{64}", fields[0])
                    or any(not re.fullmatch(r"-?[0-9]{1,10}", f) for f in fields[1:])):
                self.wfile.write(b"ERRO requisicao invalida\n")
                return
            result = subprocess.run(
                [self.server.executable, "--minipar-worker", *fields],
                stdin=subprocess.DEVNULL, capture_output=True, timeout=8,
            )
            output = result.stdout.splitlines()
            if (result.returncode or not output or not output[-1].startswith(b"RESULT ")
                    or not math.isfinite(float(output[-1][7:]))):
                self.wfile.write(b"ERRO tarefa falhou ou executavel incompativel\n")
                return
            self.wfile.write(b"OK " + output[-1][7:] + b"\n")
            print(f"tarefa {fields[1]} executada para {self.client_address[0]}", flush=True)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            try:
                self.wfile.write(b"ERRO falha na execucao remota\n")
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=lambda value: str(Path(value).resolve(strict=True)))
    parser.add_argument("port", type=int)
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args()
    with Worker((args.bind, args.port), Request) as worker:
        worker.executable = args.executable
        print(f"worker escutando em {worker.server_address}", flush=True)
        worker.serve_forever()


if __name__ == "__main__":
    main()
