"""Testes da busca exaustiva usada como referência do guloso."""

import unittest

from src.cobertura import montar
from src.dados import Setor, Unidade
from src.exato import exato, populacao_coberta
from src.guloso import populacao_coberta as populacao_gulosa


def unidade(nome, lat, lon):
    return Unidade(cnes=nome, nome=nome, bairro="", lat=lat, lon=lon)


def setor(nome, lat, lon, pop):
    return Setor(codigo=nome, regiao="teste", populacao=pop,
                 lat=lat, lon=lon, urbano=True)


class TestExato(unittest.TestCase):

    def setUp(self):
        # A e B são grandes e sobrepostas; C é menor e independente.
        # Para k=2, A+C (1.400) é melhor que A+B (1.000).
        self.inst = montar(
            [
                unidade("A", -15.8000, -47.9000),
                unidade("B", -15.8010, -47.9000),
                unidade("C", -15.9000, -47.9000),
            ],
            [
                setor("aglomerado", -15.8005, -47.9000, 1000),
                setor("isolado", -15.9005, -47.9000, 400),
            ],
            raio_km=1.0,
        )

    def test_encontra_o_otimo(self):
        self.assertEqual(populacao_coberta(self.inst, 2), 1400)
        self.assertEqual(exato(self.inst, 2), [0, 2])

    def test_k_zero(self):
        self.assertEqual(exato(self.inst, 0), [])
        self.assertEqual(populacao_coberta(self.inst, 0), 0)

    def test_k_maior_que_o_numero_de_unidades(self):
        self.assertEqual(exato(self.inst, 99), [0, 1, 2])

    def test_k_negativo_e_erro(self):
        with self.assertRaises(ValueError):
            exato(self.inst, -1)

    def test_k_nao_inteiro_e_erro(self):
        with self.assertRaises(TypeError):
            exato(self.inst, 2.0)

    def test_guloso_nao_passa_do_otimo(self):
        for k in range(4):
            self.assertLessEqual(
                populacao_gulosa(self.inst, k),
                populacao_coberta(self.inst, k),
            )

    def test_guloso_encontra_o_otimo_nesta_instancia(self):
        for k in range(4):
            self.assertEqual(
                populacao_gulosa(self.inst, k),
                populacao_coberta(self.inst, k),
            )

    def test_exato_em_instancia_sem_unidades(self):
        inst = montar([], [setor("setor", -15.8, -47.9, 100)], raio_km=1.0)
        self.assertEqual(exato(inst, 5), [])


if __name__ == "__main__":
    unittest.main()
