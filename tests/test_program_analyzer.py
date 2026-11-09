"""Testes unitarios para o analisador estatico de programas MiniPar (program_analyzer)."""
from pathlib import Path
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from program_analyzer import analyze_program, get_program_spec


class TestProgramAnalyzer(unittest.TestCase):
    def test_teste1_local_concurrent_no_multi_computer(self):
        spec = get_program_spec(str(ROOT / "tests" / "teste1_calculadora_cliente_servidor.minipar"))
        self.assertTrue(spec["has_par"])
        self.assertEqual(spec["channel_count"], 4)
        self.assertEqual(spec["input_count"], 3)
        self.assertTrue(spec["requires_input"])
        # Nao deve solicitar multi-terminal externo pois roda cliente e servidor em par
        self.assertIsNone(spec["multi_computer"])

    def test_teste_adicional1_local_concurrent_no_multi_computer(self):
        spec = get_program_spec(str(ROOT / "tests" / "teste_adicional1_paralelismo_3_computadores.minipar"))
        self.assertTrue(spec["has_par"])
        self.assertEqual(spec["channel_count"], 3)
        # Nao deve solicitar multi-terminal externo pois roda em par
        self.assertIsNone(spec["multi_computer"])

    def test_external_client_only_send_requires_multi_computer(self):
        code = '''
        seq {
            var c = c_channel("127.0.0.1", 6000);
            send(c, "dados");
        }
        '''
        with tempfile.NamedTemporaryFile("w", suffix=".minipar", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = f.name
        try:
            spec = analyze_program(temp_path)
            self.assertFalse(spec["has_par"])
            self.assertEqual(spec["channel_count"], 1)
            self.assertIsNotNone(spec["multi_computer"])
            self.assertTrue(spec["multi_computer"]["required"])
            self.assertEqual(spec["multi_computer"]["count"], 2)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_external_server_only_receive_requires_multi_computer(self):
        code = '''
        seq {
            var c = c_channel("127.0.0.1", 6000);
            var x = receive(c);
            print(x);
        }
        '''
        with tempfile.NamedTemporaryFile("w", suffix=".minipar", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = f.name
        try:
            spec = analyze_program(temp_path)
            self.assertFalse(spec["has_par"])
            self.assertEqual(spec["channel_count"], 1)
            self.assertIsNotNone(spec["multi_computer"])
            self.assertTrue(spec["multi_computer"]["required"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_send_and_receive_without_par_requires_multi_computer(self):
        code = '''
        seq {
            var c1 = c_channel("127.0.0.1", 6001);
            var c2 = c_channel("127.0.0.1", 6002);
            send(c1, "msg");
            var res = receive(c2);
        }
        '''
        with tempfile.NamedTemporaryFile("w", suffix=".minipar", delete=False, encoding="utf-8") as f:
            f.write(code)
            temp_path = f.name
        try:
            spec = analyze_program(temp_path)
            self.assertFalse(spec["has_par"])
            self.assertEqual(spec["channel_count"], 2)
            self.assertIsNotNone(spec["multi_computer"])
            self.assertTrue(spec["multi_computer"]["required"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_nonexistent_file_returns_default_spec(self):
        spec = get_program_spec("arquivo_inexistente.minipar")
        self.assertIsNone(spec["multi_computer"])
        self.assertFalse(spec["requires_input"])
        self.assertEqual(spec["channel_count"], 0)


if __name__ == "__main__":
    unittest.main()
