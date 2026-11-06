"""Regressões do contrato consumido pela Web 2: python -m unittest discover -s tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analise import analisar
from parser import Parser
from lexer import Lexer


class AnaliseTests(unittest.TestCase):
    def test_pipeline_and_json(self):
        result = analisar('seq { var x = 2 + 4 * 7; print(x); }')
        json.dumps(result)
        self.assertEqual(result['erros'], [])
        self.assertTrue(result['semantica']['sucesso'])
        self.assertEqual(result['ast']['node_type'], 'Program')
        self.assertIn('4 * 7', result['tac'])
        self.assertEqual(result['simbolos'][0]['nome'], 'x')

    def test_lexical_error_stops_parser(self):
        result = analisar('seq { @ }')
        self.assertEqual(result['erros'][0]['fase'], 'lexica')
        self.assertEqual(result['erros'][0]['coluna'], 7)
        self.assertIsNone(result['ast'])

    def test_unterminated_strings(self):
        for source in ['print("abc', 'print("abc' + '\\']:
            with self.subTest(source=source):
                result = analisar(source)
                self.assertEqual(result['erros'][0]['fase'], 'lexica')
                self.assertEqual(result['erros'][0]['coluna'], 7)

    def test_syntax_error_keeps_tokens(self):
        result = analisar('seq {\nvar x = ;\n}')
        self.assertTrue(result['tokens'])
        self.assertEqual(result['erros'][0]['fase'], 'sintatica')
        self.assertEqual(result['erros'][0]['linha'], 2)
        self.assertEqual(result['erros'][0]['coluna'], 9)
        self.assertIsNone(result['semantica']['sucesso'])

    def test_semantic_error_keeps_ast(self):
        result = analisar('seq { print(inexistente); }')
        self.assertIsNotNone(result['ast'])
        self.assertFalse(result['semantica']['sucesso'])
        self.assertEqual(result['erros'][0]['fase'], 'semantica')
        self.assertEqual(result['tac'], '')

    def test_scope_history_and_independent_calls(self):
        result = analisar('seq { var x = 1; seq { var x = 2; } }')
        symbols = result['simbolos']
        self.assertEqual(len(symbols), 2)
        self.assertNotEqual(symbols[0]['escopo'], symbols[1]['escopo'])
        self.assertEqual(analisar('seq {}')['simbolos'], [])

    def test_fork_isolation(self):
        result = analisar('seq { var x = 1; fork core(0) { x = 2; } join; }')
        self.assertTrue(any('Isolamento' in e['mensagem'] for e in result['erros']))

    def test_fork_shadowing_does_not_unlock_external_writes(self):
        for declaration, mutation in [
            ('var x = 1;', 'x = 3;'),
            ('var x = [1];', 'x[0] = 3;'),
            ('var x = new Caixa();', 'x.valor = 3;'),
        ]:
            with self.subTest(mutation=mutation):
                source = ('class Caixa { var valor = 0; } seq { ' + declaration
                          + ' fork core(0) { seq { var x = 2; } ' + mutation + ' } join; }')
                result = analisar(source)
                self.assertTrue(any('Isolamento' in e['mensagem'] for e in result['erros']))

    def test_fork_allows_reads_and_local_writes(self):
        result = analisar('seq { var x = 1; fork core(0) { var y = x; y = 3; seq { var x = 2; x = 4; } } join; x = 5; }')
        self.assertEqual(result['erros'], [])

    def test_nested_fork_rejects_parent_variable_write(self):
        result = analisar('seq { fork core(0) { var x = 1; fork core(1) { x = 2; } join; x = 3; } join; }')
        self.assertEqual(len(result['erros']), 1)
        self.assertIn('Isolamento', result['erros'][0]['mensagem'])

    def test_core_rejects_invalid_constant_destinations(self):
        for destination in ['1.5', '-1', '1 / 2', '2 - 3', '1 / 0', 'true', '"cpu"']:
            with self.subTest(destination=destination):
                result = analisar('seq { fork core(' + destination + ') { print(1); } join; }')
                self.assertTrue(any(e['fase'] == 'semantica' and 'core' in e['mensagem']
                                    for e in result['erros']))

    def test_core_accepts_nonnegative_integers_and_dynamic_expressions(self):
        for destination in ['0', '2', '2.0', '4 / 2', '1 + 2', 'i']:
            with self.subTest(destination=destination):
                result = analisar('seq { var i = 1; fork core(' + destination + ') { print(1); } join; }')
                self.assertEqual(result['erros'], [])

    def test_cli_reports_lexical_errors_without_traceback(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root) as folder:
            path = Path(folder) / 'invalido.minipar'
            for source in ['seq { print("abc', 'seq { print("abc' + '\\', 'seq { @ }']:
                with self.subTest(source=source):
                    path.write_text(source, encoding='utf-8')
                    process = subprocess.run([sys.executable, str(root / 'main.py'), str(path)],
                                             capture_output=True, text=True, timeout=10, cwd=root)
                    self.assertEqual(process.returncode, 1)
                    self.assertIn('[ERRO LEXICO]', process.stderr)
                    self.assertIn('coluna', process.stderr)
                    self.assertNotIn('Traceback', process.stderr)

    def test_unimplemented_tac_keeps_previous_phases(self):
        with patch('componente_tac.TACGenerator.generate_text', side_effect=NotImplementedError('teste')):
            result = analisar('seq {}')
        self.assertTrue(result['semantica']['sucesso'])
        self.assertEqual(result['erros'][0]['fase'], 'tac')

    def test_cli_parser_still_exits(self):
        with self.assertRaises(SystemExit), patch('sys.stderr'):
            Parser(Lexer('seq { var x = ; }').tokenize()).parse()


if __name__ == '__main__':
    unittest.main()
