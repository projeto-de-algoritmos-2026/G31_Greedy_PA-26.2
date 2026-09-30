"""
Testes da estrutura de cobertura.

A maior parte roda sobre instâncias montadas à mão, com pontos em
coordenadas escolhidas para as distâncias serem previsíveis. Os testes que
usam as bases reais são pulados quando os arquivos não estão presentes.
"""

import unittest

from src.cobertura import Instancia, montar
from src.dados import ARQUIVO_SETORES, ARQUIVO_UBS, Setor, Unidade

def _tem_pyshp() -> bool:
    try:
        import shapefile  # noqa: F401
    except ImportError:
        return False
    return True


TEM_DADOS = (ARQUIVO_UBS.exists()
             and ARQUIVO_SETORES.with_suffix(".shp").exists()
             and _tem_pyshp())


def unidade(nome: str, lat: float, lon: float) -> Unidade:
    return Unidade(cnes=nome, nome=nome, bairro="", lat=lat, lon=lon)


def setor(nome: str, lat: float, lon: float, pop: int) -> Setor:
    return Setor(codigo=nome, regiao="teste", populacao=pop,
                 lat=lat, lon=lon, urbano=True)


class TestMontar(unittest.TestCase):
    """
    Geometria de referência, perto do Plano Piloto.

    Um grau de latitude vale ~111 km, então 0,01 grau vale ~1,11 km. Os
    pontos abaixo ficam a distâncias conhecidas de propósito.
    """

    def setUp(self):
        self.unidades = [unidade("A", -15.80, -47.90), unidade("B", -15.90, -47.90)]
        self.setores = [
            setor("perto_de_A", -15.805, -47.90, 100),   # ~0,55 km de A
            setor("perto_de_B", -15.895, -47.90, 200),   # ~0,55 km de B
            setor("longe",      -15.50, -47.90, 300),    # ~33 km de A
        ]

    def test_raio_pequeno_separa_os_dois_grupos(self):
        inst = montar(self.unidades, self.setores, raio_km=1.0)
        self.assertEqual(inst.coberturas[0], frozenset({0}))
        self.assertEqual(inst.coberturas[1], frozenset({1}))

    def test_raio_grande_faz_todo_mundo_cobrir_todo_mundo(self):
        inst = montar(self.unidades, self.setores, raio_km=50.0)
        self.assertEqual(inst.coberturas[0], frozenset({0, 1, 2}))

    def test_setor_fora_de_alcance_nao_entra_em_ninguem(self):
        inst = montar(self.unidades, self.setores, raio_km=1.0)
        self.assertNotIn(2, inst.cobertos_por([0, 1]))

    def test_raio_zero_ou_negativo_e_erro(self):
        for r in (0.0, -1.0):
            with self.assertRaises(ValueError):
                montar(self.unidades, self.setores, raio_km=r)

    def test_sem_unidades_cobre_ninguem(self):
        inst = montar([], self.setores, raio_km=5.0)
        self.assertEqual(inst.coberturas, [])
        self.assertEqual(inst.populacao_alcancavel, 0)


class TestContas(unittest.TestCase):

    def setUp(self):
        self.inst = montar(
            [unidade("A", -15.80, -47.90), unidade("B", -15.90, -47.90)],
            [setor("a", -15.805, -47.90, 100),
             setor("b", -15.895, -47.90, 200),
             setor("c", -15.50, -47.90, 300)],
            raio_km=1.0,
        )

    def test_populacao_total_conta_ate_quem_ninguem_alcanca(self):
        self.assertEqual(self.inst.populacao_total, 600)

    def test_populacao_alcancavel_e_menor_que_o_total(self):
        """O teto do problema não é a população inteira."""
        self.assertEqual(self.inst.populacao_alcancavel, 300)
        self.assertLess(self.inst.populacao_alcancavel, self.inst.populacao_total)

    def test_uniao_nao_conta_setor_duas_vezes(self):
        sobrepostas = montar(
            [unidade("A", -15.80, -47.90), unidade("B", -15.801, -47.90)],
            [setor("unico", -15.8005, -47.90, 500)],
            raio_km=1.0,
        )
        self.assertEqual(sobrepostas.populacao_de(sobrepostas.cobertos_por([0, 1])), 500)

    def test_conjunto_vazio_cobre_zero(self):
        self.assertEqual(self.inst.populacao_de(set()), 0)
        self.assertEqual(self.inst.cobertos_por([]), set())


@unittest.skipUnless(TEM_DADOS, "bases brutas ou pyshp ausentes")
class TestComDadosReais(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from src.cobertura import carregar
        cls.inst = carregar(2.0)

    def test_tamanho_da_instancia(self):
        self.assertEqual(len(self.inst.unidades), 200)
        self.assertEqual(len(self.inst.setores), 5418)

    def test_nem_toda_populacao_e_alcancavel(self):
        """
        Com raio de 2 km, as 200 unidades juntas chegam a cerca de 90% do
        DF. É por isso que o problema é de cobertura MÁXIMA e não de
        cobertura de conjuntos: não existe solução que cubra todo mundo.
        """
        fracao = self.inst.populacao_alcancavel / self.inst.populacao_total
        self.assertLess(fracao, 1.0)
        self.assertAlmostEqual(fracao, 0.90, delta=0.03)

    def test_raio_maior_cobre_mais(self):
        from src.cobertura import montar
        menor = montar(self.inst.unidades, self.inst.setores, 1.0)
        self.assertLess(menor.populacao_alcancavel, self.inst.populacao_alcancavel)


if __name__ == "__main__":
    unittest.main()
