"""
Testes da geometria.

Tudo aqui roda sobre figuras com resposta conhecida de antemão — quadrado,
triângulo, distâncias entre cidades reais. Quando um teste falha, o erro
está na fórmula, nunca na expectativa.
"""

import math
import unittest

from src.geometria import centroide, distancia_km


class TestCentroide(unittest.TestCase):

    def test_quadrado(self):
        """O centro de um quadrado unitário é (0,5 · 0,5)."""
        quadrado = [(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]
        x, y = centroide(quadrado)
        self.assertAlmostEqual(x, 0.5)
        self.assertAlmostEqual(y, 0.5)

    def test_triangulo(self):
        """O centroide de um triângulo é a média dos três vértices."""
        triangulo = [(0, 0), (6, 0), (0, 9), (0, 0)]
        x, y = centroide(triangulo)
        self.assertAlmostEqual(x, 2.0)
        self.assertAlmostEqual(y, 3.0)

    def test_orientacao_nao_muda_o_resultado(self):
        """Horário ou anti-horário dão o mesmo centro; só o sinal da área muda."""
        horario = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        anti = list(reversed(horario))
        self.assertEqual(centroide(horario), centroide(anti))

    def test_buraco_desloca_o_centro(self):
        """
        Um anel interno é percorrido ao contrário e entra com área negativa,
        então o centro se afasta dele sem a gente tratar buraco à mão.
        """
        externo = [(0, 0), (0, 4), (4, 4), (4, 0), (0, 0)]
        buraco = [(1, 1), (2, 1), (2, 2), (1, 2), (1, 1)]
        x, _ = centroide(externo + buraco, [0, len(externo)])
        self.assertGreater(x, 2.0, "o centro devia fugir do buraco à esquerda")

    def test_poligono_degenerado_nao_divide_por_zero(self):
        """Área zero existe em base real; cai na média dos vértices."""
        linha = [(0, 0), (1, 1), (2, 2), (0, 0)]
        x, y = centroide(linha)
        self.assertTrue(math.isfinite(x) and math.isfinite(y))

    def test_poligono_vazio_e_erro(self):
        with self.assertRaises(ValueError):
            centroide([])


class TestDistancia(unittest.TestCase):

    def test_mesmo_ponto_e_zero(self):
        self.assertAlmostEqual(distancia_km(-15.8, -47.9, -15.8, -47.9), 0.0)

    def test_brasilia_sao_paulo(self):
        """Distância em linha reta conhecida: cerca de 870 km."""
        d = distancia_km(-15.7939, -47.8828, -23.5505, -46.6333)
        self.assertAlmostEqual(d, 870, delta=15)

    def test_um_grau_de_latitude_vale_111_km(self):
        """Verdade em qualquer longitude — meridianos não convergem."""
        self.assertAlmostEqual(distancia_km(-15.0, -47.9, -16.0, -47.9), 111.2, delta=0.5)

    def test_um_grau_de_longitude_encolhe_longe_do_equador(self):
        """
        No equador vale 111 km; na latitude do DF, 107. É por isso que
        Pitágoras em graus não serve aqui.
        """
        no_equador = distancia_km(0.0, 0.0, 0.0, 1.0)
        no_df = distancia_km(-15.8, -47.0, -15.8, -48.0)
        self.assertAlmostEqual(no_equador, 111.2, delta=0.5)
        self.assertAlmostEqual(no_df, 107.0, delta=0.5)
        self.assertLess(no_df, no_equador)

    def test_simetrica(self):
        ida = distancia_km(-15.8, -47.9, -16.0, -48.1)
        volta = distancia_km(-16.0, -48.1, -15.8, -47.9)
        self.assertAlmostEqual(ida, volta)


if __name__ == "__main__":
    unittest.main()
