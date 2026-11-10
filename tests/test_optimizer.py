"""Testes unitários para o otimizador independente de máquina da AST."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analise import analisar
from componente_otimizador import C_Otimizador, IOtimizador
from componente_sintatico import C_Sintatico
from componente_lexico import C_Lexico
from optimizer import ASTOptimizer


class OptimizerTests(unittest.TestCase):
    def setUp(self):
        self.otimizador: IOtimizador = C_Otimizador()

    def _parse(self, code: str):
        tokens = C_Lexico().analise_lexica(code)
        return C_Sintatico().analise_sintatica(tokens)

    def test_constant_folding_arithmetic(self):
        ast = self._parse("seq { var x = 2 + 3 * 4; var y = 10 / 2; var z = 7 % 4; }")
        res = self.otimizador.otimizar(ast)

        # 2 + 12 -> 14, 10 / 2 -> 5, 7 % 4 -> 3
        decls = res.programa_otimizado.statements
        self.assertEqual(decls[0].init_value.value, "14")
        self.assertEqual(decls[1].init_value.value, "5")
        self.assertEqual(decls[2].init_value.value, "3")
        self.assertGreater(res.nos_antes, res.nos_depois)
        self.assertTrue(any("Dobra de constantes" in t for t in res.transformacoes))

    def test_constant_folding_unary(self):
        ast = self._parse("seq { var a = -(-42); var b = !false; }")
        res = self.otimizador.otimizar(ast)
        decls = res.programa_otimizado.statements
        self.assertEqual(decls[0].init_value.value, "42")
        self.assertTrue(decls[1].init_value.value)

    def test_constant_folding_relational_and_logical(self):
        ast = self._parse("seq { var c1 = 10 > 5; var c2 = 3 == 4; var c3 = true && false; var c4 = false || true; }")
        res = self.otimizador.otimizar(ast)
        decls = res.programa_otimizado.statements
        self.assertTrue(decls[0].init_value.value)
        self.assertFalse(decls[1].init_value.value)
        self.assertFalse(decls[2].init_value.value)
        self.assertTrue(decls[3].init_value.value)

    def test_constant_folding_strings(self):
        ast = self._parse('seq { var msg = "Mini" + "Par"; var eq = "a" == "a"; }')
        res = self.otimizador.otimizar(ast)
        decls = res.programa_otimizado.statements
        self.assertEqual(decls[0].init_value.value, "MiniPar")
        self.assertTrue(decls[1].init_value.value)

    def test_algebraic_simplifications_neutral_elements(self):
        ast = self._parse("seq { var x = 10; var a = x + 0; var b = 0 + x; var c = x - 0; var d = x * 1; var e = 1 * x; var f = x / 1; }")
        res = self.otimizador.otimizar(ast)
        decls = res.programa_otimizado.statements[1:]
        for decl in decls:
            # Todos devem ter sido reduzidos diretamente para o identificador 'x'
            self.assertEqual(decl.init_value.__class__.__name__, "IdentifierExpr")
            self.assertEqual(decl.init_value.name, "x")
        self.assertTrue(any("Simplificação algébrica" in t for t in res.transformacoes))

    def test_algebraic_simplifications_absorbent_elements(self):
        ast = self._parse("seq { var x = 10; var z1 = x * 0; var z2 = 0 * x; }")
        res = self.otimizador.otimizar(ast)
        decls = res.programa_otimizado.statements[1:]
        self.assertEqual(decls[0].init_value.value, "0")
        self.assertEqual(decls[1].init_value.value, "0")

    def test_algebraic_simplifications_boolean(self):
        ast = self._parse("seq { var cond = true; var r1 = cond && false; var r2 = cond || true; var r3 = cond && true; var r4 = cond || false; }")
        res = self.otimizador.otimizar(ast)
        decls = res.programa_otimizado.statements[1:]
        self.assertFalse(decls[0].init_value.value)
        self.assertTrue(decls[1].init_value.value)
        self.assertEqual(decls[2].init_value.name, "cond")
        self.assertEqual(decls[3].init_value.name, "cond")

    def test_dead_branch_elimination_if_true(self):
        code = """
        seq {
            if (10 > 2) {
                print("Vivo");
            } else {
                print("Morto");
            }
        }
        """
        ast = self._parse(code)
        res = self.otimizador.otimizar(ast)
        stmts = res.programa_otimizado.statements
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].__class__.__name__, "PrintStmt")
        self.assertEqual(stmts[0].arguments[0].value, "Vivo")
        self.assertTrue(any("Eliminação de ramo morto em if" in t for t in res.transformacoes))

    def test_dead_branch_elimination_if_false_with_else(self):
        code = """
        seq {
            if (false) {
                print("Morto");
            } else {
                print("Vivo");
            }
        }
        """
        ast = self._parse(code)
        res = self.otimizador.otimizar(ast)
        stmts = res.programa_otimizado.statements
        self.assertEqual(len(stmts), 1)
        self.assertEqual(stmts[0].__class__.__name__, "PrintStmt")
        self.assertEqual(stmts[0].arguments[0].value, "Vivo")

    def test_dead_branch_elimination_if_false_without_else(self):
        code = """
        seq {
            var x = 1;
            if (false) {
                print("Inalcançável");
            }
            var y = 2;
        }
        """
        ast = self._parse(code)
        res = self.otimizador.otimizar(ast)
        stmts = res.programa_otimizado.statements
        self.assertEqual(len(stmts), 2)
        self.assertEqual(stmts[0].name, "x")
        self.assertEqual(stmts[1].name, "y")

    def test_dead_while_elimination(self):
        code = """
        seq {
            var a = 1;
            while (false) {
                a = a + 1;
            }
            print(a);
        }
        """
        ast = self._parse(code)
        res = self.otimizador.otimizar(ast)
        stmts = res.programa_otimizado.statements
        self.assertEqual(len(stmts), 2)
        self.assertEqual(stmts[0].name, "a")
        self.assertEqual(stmts[1].__class__.__name__, "PrintStmt")

    def test_pipeline_analisar_comparison(self):
        code = "seq { var x = 2 + 3 * 4; if (true) { print(x + 0); } }"
        res_padrao = analisar(code, otimizar=False)
        res_opt = analisar(code, otimizar=True)

        self.assertFalse(res_padrao["otimizacao"]["ativa"])
        self.assertTrue(res_opt["otimizacao"]["ativa"])
        self.assertGreater(res_opt["otimizacao"]["nos_antes"], res_opt["otimizacao"]["nos_depois"])
        self.assertGreater(res_opt["otimizacao"]["reducao_pct"], 0.0)

        # O TAC com otimização não deve precisar calcular 3 * 4 nem gerar if/goto
        self.assertIn("3 * 4", res_padrao["tac"])
        self.assertNotIn("3 * 4", res_opt["tac"])
        self.assertIn("x = 14", res_opt["tac"])


if __name__ == "__main__":
    unittest.main()
