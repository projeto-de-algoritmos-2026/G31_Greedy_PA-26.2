import unittest
from pathlib import Path

from src.dados import (ARQUIVO_SETORES, ARQUIVO_UBS, LAT_DF, LON_DF, _no_df,
                       _numero, carregar_setores, carregar_unidades)

def _tem_pyshp() -> bool:
    try:
        import shapefile
    except ImportError:
        return False
    return True


TEM_UBS = ARQUIVO_UBS.exists()

TEM_SETORES = ARQUIVO_SETORES.with_suffix(".shp").exists() and _tem_pyshp()


class TestNumero(unittest.TestCase):

    def test_ponto_decimal(self):
        self.assertAlmostEqual(_numero("-15.7939"), -15.7939)

    def test_virgula_decimal(self):
        self.assertAlmostEqual(_numero("-47,8828"), -47.8828)

    def test_espacos_em_volta(self):
        self.assertAlmostEqual(_numero("  -15,80  "), -15.80)

    def test_vazio_e_none(self):
        self.assertIsNone(_numero(""))
        self.assertIsNone(_numero("   "))
        self.assertIsNone(_numero(None))

    def test_lixo_e_none_em_vez_de_excecao(self):

        self.assertIsNone(_numero("N/A"))
        self.assertIsNone(_numero("-15.7.9"))


class TestCaixaDoDF(unittest.TestCase):

    def test_ponto_no_plano_piloto(self):
        self.assertTrue(_no_df(-15.7939, -47.8828))

    def test_sao_paulo_fica_de_fora(self):
        self.assertFalse(_no_df(-23.5505, -46.6333))

    def test_zero_zero_fica_de_fora(self):
        self.assertFalse(_no_df(0.0, 0.0))


@unittest.skipUnless(TEM_UBS, "data/raw/Unidades_Basicas_Saude-UBS.csv ausente")
class TestUnidades(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.unidades = carregar_unidades()

    def test_quantidade_conhecida(self):

        self.assertEqual(len(self.unidades), 200)

    def test_todas_dentro_do_df(self):
        for u in self.unidades:
            self.assertTrue(_no_df(u.lat, u.lon), f"{u.nome} caiu fora do DF")

    def test_sem_cnes_repetido(self):
        codigos = [u.cnes for u in self.unidades]
        self.assertEqual(len(codigos), len(set(codigos)))

    def test_longitude_negativa(self):

        for u in self.unidades:
            self.assertLess(u.lon, -47.0)


@unittest.skipUnless(TEM_SETORES, "shapefile do IBGE ou pyshp ausente")
class TestSetores(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.setores = carregar_setores()

    def test_quantidade_conhecida(self):
        self.assertEqual(len(self.setores), 5418)

    def test_populacao_bate_com_o_censo(self):
        self.assertEqual(sum(s.populacao for s in self.setores), 2_817_381)

    def test_todo_centroide_cai_dentro_do_df(self):
        fora = [s for s in self.setores if not _no_df(s.lat, s.lon)]
        self.assertEqual(fora, [], f"{len(fora)} centroides fora do DF")

    def test_regioes_administrativas(self):
        self.assertEqual(len({s.regiao for s in self.setores}), 33)

    def test_populacao_nunca_negativa(self):
        for s in self.setores:
            self.assertGreaterEqual(s.populacao, 0)


if __name__ == "__main__":
    unittest.main()
