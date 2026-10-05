import math
import unittest

from src.geometria import centroide, distancia_km


class TestCentroide(unittest.TestCase):

    def test_quadrado(self):

        quadrado = [(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]
        x, y = centroide(quadrado)
        self.assertAlmostEqual(x, 0.5)
        self.assertAlmostEqual(y, 0.5)

    def test_triangulo(self):

        triangulo = [(0, 0), (6, 0), (0, 9), (0, 0)]
        x, y = centroide(triangulo)
        self.assertAlmostEqual(x, 2.0)
        self.assertAlmostEqual(y, 3.0)

    def test_orientacao_nao_muda_o_resultado(self):

        horario = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
        anti = list(reversed(horario))
        self.assertEqual(centroide(horario), centroide(anti))

    def test_buraco_desloca_o_centro(self):

        externo = [(0, 0), (0, 4), (4, 4), (4, 0), (0, 0)]
        buraco = [(1, 1), (2, 1), (2, 2), (1, 2), (1, 1)]
        x, _ = centroide(externo + buraco, [0, len(externo)])
        self.assertGreater(x, 2.0, "o centro devia fugir do buraco à esquerda")

    def test_poligono_degenerado_nao_divide_por_zero(self):

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

        d = distancia_km(-15.7939, -47.8828, -23.5505, -46.6333)
        self.assertAlmostEqual(d, 870, delta=15)

    def test_um_grau_de_latitude_vale_111_km(self):

        self.assertAlmostEqual(distancia_km(-15.0, -47.9, -16.0, -47.9), 111.2, delta=0.5)

    def test_um_grau_de_longitude_encolhe_longe_do_equador(self):

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
