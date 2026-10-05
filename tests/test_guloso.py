

import unittest

from src.cobertura import montar
from src.dados import Setor, Unidade
from src.guloso import guloso, historico, populacao_coberta


def unidade(nome, lat, lon):
    return Unidade(cnes=nome, nome=nome, bairro="", lat=lat, lon=lon)


def setor(nome, lat, lon, pop):
    return Setor(codigo=nome, regiao="teste", populacao=pop,
                 lat=lat, lon=lon, urbano=True)


class TestGuloso(unittest.TestCase):

    def setUp(self):
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

    def test_escolhe_a_unidade_com_maior_ganho(self):
        self.assertEqual(guloso(self.inst, 1), [0])

    def test_considera_apenas_populacao_nova(self):
        """Depois de A, B não acrescenta nada; C acrescenta 400."""
        self.assertEqual(guloso(self.inst, 2), [0, 2])
        self.assertEqual(populacao_coberta(self.inst, 2), 1400)

    def test_historico_registra_ganho_marginal(self):
        passos = historico(self.inst, 2)
        self.assertEqual([p.unidade for p in passos], [0, 2])
        self.assertEqual([p.ganho for p in passos], [1000, 400])
        self.assertEqual([p.acumulado for p in passos], [1000, 1400])
        self.assertEqual(passos[0].setores_novos, frozenset({0}))
        self.assertEqual(passos[1].setores_novos, frozenset({1}))

    def test_nao_conta_setor_duas_vezes(self):
        self.assertEqual(populacao_coberta(self.inst, 3), 1400)

    def test_k_zero(self):
        self.assertEqual(guloso(self.inst, 0), [])
        self.assertEqual(populacao_coberta(self.inst, 0), 0)
        self.assertEqual(historico(self.inst, 0), [])

    def test_k_maior_que_o_numero_de_unidades(self):
        escolhidas = guloso(self.inst, 99)
        self.assertEqual(len(escolhidas), 3)
        self.assertEqual(set(escolhidas), {0, 1, 2})

    def test_k_negativo_e_erro(self):
        with self.assertRaises(ValueError):
            guloso(self.inst, -1)

    def test_k_nao_inteiro_e_erro(self):
        with self.assertRaises(TypeError):
            guloso(self.inst, 2.0)

    def test_empate_e_deterministico(self):
        inst = montar(
            [unidade("A", -15.800, -47.900), unidade("B", -15.900, -47.900)],
            [setor("a", -15.8005, -47.900, 100),
             setor("b", -15.9005, -47.900, 100)],
            raio_km=1.0,
        )
        self.assertEqual(guloso(inst, 1), [0])

    def test_unidades_sem_cobertura_nao_impedem_o_algoritmo(self):
        inst = montar(
            [unidade("sem cobertura", -16.00, -47.90),
             unidade("com cobertura", -15.80, -47.90)],
            [setor("setor", -15.8005, -47.90, 500)],
            raio_km=1.0,
        )
        self.assertEqual(guloso(inst, 1), [1])

    def test_sem_unidades(self):
        inst = montar([], [setor("setor", -15.8, -47.9, 100)], raio_km=1.0)
        self.assertEqual(guloso(inst, 5), [])
        self.assertEqual(historico(inst, 5), [])


if __name__ == "__main__":
    unittest.main()
