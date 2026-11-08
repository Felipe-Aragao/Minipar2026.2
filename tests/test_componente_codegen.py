"""Testes unitários do componente de geração de código C++ (ICodegen e C_Codegen)."""
from pathlib import Path
import os
import shutil
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from componente_codegen import C_Codegen, ICodegen
from componente_lexico import C_Lexico
from componente_sintatico import C_Sintatico
from componente_semantico import C_Semantico
from ast_nodes import Program


class ComponenteCodegenTests(unittest.TestCase):
    def setUp(self):
        self.codegen = C_Codegen()
        self.lexico = C_Lexico()
        self.sintatico = C_Sintatico()
        self.semantico = C_Semantico()

    def tearDown(self):
        nome_saida = "test_codegen_temp"
        exe_ext = ".exe" if sys.platform == "win32" else ""
        cpp_file = os.path.join("output", f"{nome_saida}.cpp")
        exe_file = os.path.join("output", f"{nome_saida}{exe_ext}")
        if os.path.exists(cpp_file):
            try:
                os.remove(cpp_file)
            except OSError:
                pass
        if os.path.exists(exe_file):
            try:
                os.remove(exe_file)
            except OSError:
                pass

    def _compilar_ast(self, codigo: str) -> Program:
        tokens = self.lexico.analise_lexica(codigo)
        programa = self.sintatico.analise_sintatica(tokens)
        res = self.semantico.analise_semantica(programa)
        self.assertTrue(res.sucesso, f"Erro semântico no teste: {res.erros}")
        return programa

    def test_conformidade_interface(self):
        """Verifica se C_Codegen realiza formalmente a interface ICodegen."""
        self.assertTrue(issubclass(C_Codegen, ICodegen))
        self.assertIsInstance(self.codegen, ICodegen)

    def test_gerar_texto_em_memoria(self):
        """Verifica se gerar_texto produz o código C++ completo sem gerar arquivo binário."""
        ast = self._compilar_ast('seq { var x = 10 + 20; print("Resultado:", x); }')
        cpp_texto = self.codegen.gerar_texto(ast)

        self.assertIsInstance(cpp_texto, str)
        self.assertIn("int main()", cpp_texto)
        self.assertIn("auto x = (10 + 20);", cpp_texto)
        self.assertIn('"Resultado:"', cpp_texto)

    def test_gerar_codigo_compilacao_gcc(self):
        """Verifica se gerar_codigo salva o arquivo e compila via GCC gerando executável."""
        if shutil.which("g++") is None:
            self.skipTest("g++ não disponível no ambiente para teste de compilação")

        ast = self._compilar_ast('seq { var msg = "Componente Codegen OK"; print(msg); }')
        nome_saida = "test_codegen_temp"
        sucesso = self.codegen.gerar_codigo(ast, nome_saida)
        self.assertTrue(sucesso)

        exe_ext = ".exe" if sys.platform == "win32" else ""
        cpp_file = os.path.join("output", f"{nome_saida}.cpp")
        exe_file = os.path.join("output", f"{nome_saida}{exe_ext}")

        self.assertTrue(os.path.exists(cpp_file))
        self.assertTrue(os.path.exists(exe_file))


if __name__ == "__main__":
    unittest.main()
