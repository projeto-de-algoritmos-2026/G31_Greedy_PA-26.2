import unittest

from src.cobertura import montar
from src.dados import ARQUIVO_SETORES, ARQUIVO_UBS, Setor, Unidade
from src.linhas_base import (LINHAS_DE_BASE, aleatorias, centro_populacional,
                             maiores_sozinhas, mais_centrais, media_aleatoria)


def _tem_pyshp() -> bool:
    try:
        import shapefile
    except ImportError:
        return False
    return True


TEM_DADOS = (ARQUIVO_UBS.exists()
             and ARQUIVO_SETORES.with_suffix(".shp").exists()
             and _tem_pyshp())


def unidade(nome, lat, lon):
    return Unidade(cnes=nome, nome=nome, bairro="", lat=lat, lon=lon)


def setor(nome, lat, lon, pop):
    return Setor(codigo=nome, regiao="teste", populacao=pop,
                 lat=lat, lon=lon, urbano=True)


class TestMaioresSozinhas(unittest.TestCase):


    def setUp(self):
        self.inst = montar(
            [unidade("A", -15.800, -47.900),
             unidade("B", -15.801, -47.900),
             unidade("C", -15.900, -47.900)],
            [setor("aglomerado", -15.8005, -47.900, 1000),
             setor("isolado", -15.9005, -47.900, 400)],
            raio_km=1.0,
        )

    def test_escolhe_as_duas_sobrepostas(self):
        self.assertEqual(set(maiores_sozinhas(self.inst, 2)), {0, 1})

    def test_e_por_isso_cobre_menos_que_a_escolha_esperta(self):
        boba = self.inst.populacao_de(self.inst.cobertos_por(maiores_sozinhas(self.inst, 2)))
        esperta = self.inst.populacao_de(self.inst.cobertos_por([0, 2]))
        self.assertEqual(boba, 1000)
        self.assertEqual(esperta, 1400)
        self.assertLess(boba, esperta)

    def test_k_maior_que_o_disponivel_devolve_tudo(self):
        self.assertEqual(len(maiores_sozinhas(self.inst, 99)), 3)

    def test_k_zero_devolve_vazio(self):
        self.assertEqual(maiores_sozinhas(self.inst, 0), [])


class TestCentroPopulacional(unittest.TestCase):

    def test_o_centro_pende_para_onde_ha_mais_gente(self):
        inst = montar(
            [unidade("u", -15.85, -47.90)],
            [setor("cheio", -15.80, -47.90, 1000),
             setor("vazio", -15.90, -47.90, 10)],
            raio_km=50.0,
        )
        lat, _ = centro_populacional(inst)
        self.assertLess(abs(lat - (-15.80)), abs(lat - (-15.90)))

    def test_setor_sem_ninguem_nao_puxa_o_centro(self):
        com_vazio = montar(
            [unidade("u", -15.85, -47.90)],
            [setor("cheio", -15.80, -47.90, 1000),
             setor("deserto", -16.00, -47.90, 0)],
            raio_km=50.0,
        )
        self.assertAlmostEqual(centro_populacional(com_vazio)[0], -15.80)

    def test_populacao_zero_e_erro(self):
        inst = montar([unidade("u", -15.8, -47.9)],
                      [setor("a", -15.8, -47.9, 0)], raio_km=1.0)
        with self.assertRaises(ValueError):
            centro_populacional(inst)


class TestMaisCentrais(unittest.TestCase):

    def test_pega_a_mais_perto_de_onde_as_pessoas_estao(self):
        inst = montar(
            [unidade("longe", -16.00, -47.90), unidade("perto", -15.81, -47.90)],
            [setor("aqui", -15.80, -47.90, 1000)],
            raio_km=50.0,
        )
        self.assertEqual(mais_centrais(inst, 1), [1])


class TestAleatorias(unittest.TestCase):

    def setUp(self):
        self.inst = montar(
            [unidade(str(i), -15.8 - i / 100, -47.9) for i in range(10)],
            [setor("a", -15.80, -47.90, 100)],
            raio_km=1.0,
        )

    def test_a_semente_torna_o_sorteio_reproduzivel(self):
        self.assertEqual(aleatorias(self.inst, 4, semente=7),
                         aleatorias(self.inst, 4, semente=7))

    def test_sementes_diferentes_dao_sorteios_diferentes(self):
        a = aleatorias(self.inst, 4, semente=1)
        b = aleatorias(self.inst, 4, semente=2)
        self.assertNotEqual(a, b)

    def test_nunca_repete_unidade(self):
        escolhidas = aleatorias(self.inst, 6, semente=3)
        self.assertEqual(len(escolhidas), len(set(escolhidas)))

    def test_media_e_reproduzivel(self):
        self.assertEqual(media_aleatoria(self.inst, 3, 10, semente=5),
                         media_aleatoria(self.inst, 3, 10, semente=5))

    def test_repeticoes_invalidas_sao_erro(self):
        with self.assertRaises(ValueError):
            media_aleatoria(self.inst, 3, repeticoes=0)


class TestRegistro(unittest.TestCase):


    def test_todas_aceitam_instancia_e_k(self):
        inst = montar([unidade("a", -15.8, -47.9), unidade("b", -15.9, -47.9)],
                      [setor("s", -15.8, -47.9, 100)], raio_km=1.0)
        for nome, escolher in LINHAS_DE_BASE.items():
            escolhidas = escolher(inst, 1)
            self.assertEqual(len(escolhidas), 1, f"{nome} devolveu {escolhidas}")
            self.assertIsInstance(escolhidas, list, nome)


@unittest.skipUnless(TEM_DADOS, "bases brutas ou pyshp ausentes")
class TestComDadosReais(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from src.cobertura import carregar
        cls.inst = carregar(2.0)

    def test_o_centro_populacional_cai_dentro_do_df(self):
        lat, lon = centro_populacional(self.inst)
        self.assertTrue(-16.10 <= lat <= -15.45)
        self.assertTrue(-48.35 <= lon <= -47.25)

    def test_nenhuma_linha_de_base_cobre_o_impossivel(self):
        teto = self.inst.populacao_alcancavel
        for nome, escolher in LINHAS_DE_BASE.items():
            coberta = self.inst.populacao_de(self.inst.cobertos_por(escolher(self.inst, 20)))
            self.assertLessEqual(coberta, teto, nome)


if __name__ == "__main__":
    unittest.main()
