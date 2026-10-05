import contextlib
import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from src.cobertura import montar
from src.dados import Setor, Unidade
from src.guloso import guloso, historico
from validacao import (COR, SEM_COBERTURA, Comparacao, _desenhar_mapa,
                       contra_o_otimo, curva, grafico_curva, grafico_ganho,
                       grafico_mapa, tabela)


def unidade(nome, lat, lon):
    return Unidade(cnes=nome, nome=nome, bairro="", lat=lat, lon=lon)


def setor(nome, lat, lon, pop):
    return Setor(codigo=nome, regiao="teste", populacao=pop,
                 lat=lat, lon=lon, urbano=True)


def instancia_pequena():

    return montar(
        [unidade(f"u{i}", -15.80 - i / 50, -47.90) for i in range(5)],
        [setor(f"s{i}", -15.80 - i / 50, -47.90, 100 * (i + 1)) for i in range(5)],
        raio_km=1.0,
    )


class TestCurva(unittest.TestCase):

    def setUp(self):
        self.inst = instancia_pequena()
        self.series = curva(self.inst, 4)

    def test_tem_o_guloso_e_todas_as_linhas_de_base(self):
        self.assertIn("guloso", self.series)
        self.assertGreaterEqual(len(self.series), 4)

    def test_todas_as_series_tem_o_mesmo_comprimento(self):
        tamanhos = {len(v) for v in self.series.values()}
        self.assertEqual(len(tamanhos), 1)

    def test_a_cobertura_nunca_diminui_com_mais_unidades(self):

        for nome, valores in self.series.items():
            for anterior, atual in zip(valores, valores[1:]):
                self.assertGreaterEqual(atual, anterior, nome)

    def test_o_guloso_nunca_perde_para_uma_linha_de_base(self):
        for nome, valores in self.series.items():
            if nome == "guloso":
                continue
            for k, (g, b) in enumerate(zip(self.series["guloso"], valores), 1):
                self.assertGreaterEqual(g, b, f"{nome} passou o guloso em k={k}")

    def test_cada_cor_tem_uma_serie_e_vice_versa(self):

        self.assertEqual(set(self.series), set(COR))


class TestContraOOtimo(unittest.TestCase):

    def test_o_guloso_nunca_passa_do_otimo(self):

        inst = instancia_pequena()
        for c in contra_o_otimo(inst, instancias=4, semente=1):
            self.assertLessEqual(c.guloso, c.otimo)
            self.assertLessEqual(c.razao, 1.0)

    def test_a_semente_torna_a_comparacao_reproduzivel(self):
        inst = instancia_pequena()
        a = contra_o_otimo(inst, instancias=3, semente=9)
        b = contra_o_otimo(inst, instancias=3, semente=9)
        self.assertEqual([vars(c) for c in a], [vars(c) for c in b])

    def test_razao_com_otimo_zero_nao_divide_por_zero(self):
        self.assertEqual(Comparacao(candidatos=5, k=2, guloso=0, otimo=0).razao, 1.0)


class TestGraficos(unittest.TestCase):

    def setUp(self):
        self.inst = instancia_pequena()
        self.series = curva(self.inst, 4)
        self.total = self.inst.populacao_total

    def test_a_curva_e_xml_bem_formado(self):
        ET.fromstring(grafico_curva(self.series, self.total, 2.0))

    def test_o_ganho_e_xml_bem_formado(self):
        ET.fromstring(grafico_ganho(historico(self.inst, 4), self.total))

    def test_toda_serie_aparece_no_desenho(self):
        svg = grafico_curva(self.series, self.total, 2.0)
        for nome, cor in COR.items():
            self.assertIn(cor, svg, f"a cor de {nome} sumiu")
            self.assertIn(nome, svg, f"o rótulo de {nome} sumiu")

    def test_caractere_especial_no_rotulo_nao_quebra_o_xml(self):
        svg = grafico_curva(self.series, self.total, 2.0)
        ET.fromstring(svg)
        self.assertNotIn("&a", svg.replace("&amp;", ""))


class TestMapa(unittest.TestCase):


    def setUp(self):
        self.inst = instancia_pequena()
        self.escolhidas = guloso(self.inst, 2)

    def test_e_xml_bem_formado(self):
        ET.fromstring(grafico_mapa(self.inst, self.escolhidas))

    def test_as_duas_categorias_aparecem(self):
        svg = grafico_mapa(self.inst, self.escolhidas)
        self.assertIn(COR["guloso"], svg)
        self.assertIn(SEM_COBERTURA, svg)

    def test_sem_nenhuma_escolhida_nao_quebra(self):

        svg = grafico_mapa(self.inst, [])
        ET.fromstring(svg)
        self.assertIn(SEM_COBERTURA, svg)

    def test_todo_setor_com_gente_vira_um_ponto(self):

        svg = grafico_mapa(self.inst, self.escolhidas)
        circulos = len(ET.fromstring(svg).findall(
            "{http://www.w3.org/2000/svg}circle"))
        com_gente = sum(1 for s in self.inst.setores if s.populacao > 0)
        self.assertEqual(circulos, com_gente + 2 * len(self.escolhidas) + 3)

    def test_o_enquadramento_nao_muda_com_o_k(self):

        def cinzas(k):
            svg = ET.fromstring(grafico_mapa(self.inst, guloso(self.inst, k)))
            return {(c.get("cx"), c.get("cy"))
                    for c in svg.findall("{http://www.w3.org/2000/svg}circle")
                    if c.get("fill") == SEM_COBERTURA}


        self.assertLess(len(cinzas(1)), len(cinzas(0)))
        self.assertTrue(cinzas(1) < cinzas(0))

    def test_um_setor_so_nao_divide_por_zero(self):

        inst = montar([unidade("u", -15.8, -47.9)],
                      [setor("s", -15.8, -47.9, 100)], raio_km=1.0)
        ET.fromstring(grafico_mapa(inst, [0]))


class TestDesenharMapa(unittest.TestCase):


    def _desenhar(self, inst, base, k) -> str:

        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            _desenhar_mapa(inst, base, k)
        return saida.getvalue()

    def test_grava_um_arquivo_com_o_k_no_nome(self):
        inst = instancia_pequena()
        with tempfile.TemporaryDirectory() as pasta:
            base = Path(pasta) / "v_raio2"
            self._desenhar(inst, base, 3)
            destino = base.with_name("v_raio2_mapa_k3.svg")
            self.assertTrue(destino.exists())
            ET.fromstring(destino.read_text(encoding="utf-8"))

    def test_diz_quanta_gente_alcancou(self):
        inst = instancia_pequena()
        with tempfile.TemporaryDirectory() as pasta:
            impresso = self._desenhar(inst, Path(pasta) / "v", 3)
        coberta = inst.populacao_de(inst.cobertos_por(guloso(inst, 3)))
        self.assertIn(f"{coberta:,}".replace(",", "."), impresso)

    def test_dois_k_diferentes_nao_se_apagam(self):
        inst = instancia_pequena()
        with tempfile.TemporaryDirectory() as pasta:
            base = Path(pasta) / "v_raio2"
            self._desenhar(inst, base, 2)
            self._desenhar(inst, base, 4)
            gravados = sorted(p.name for p in Path(pasta).glob("*.svg"))
        self.assertEqual(gravados, ["v_raio2_mapa_k2.svg", "v_raio2_mapa_k4.svg"])

    def test_o_atalho_do_guloso_bate_com_o_historico(self):

        inst = instancia_pequena()
        self.assertEqual(guloso(inst, 3),
                         [p.unidade for p in historico(inst, 3)])


class TestTabela(unittest.TestCase):

    def test_cita_a_garantia_teorica(self):
        inst = instancia_pequena()
        md = tabela(curva(inst, 4), inst.populacao_total,
                    contra_o_otimo(inst, 3, semente=2), [2, 4])
        self.assertIn("63,21%", md)
        self.assertIn("ótimo", md)


class TestArquivosGerados(unittest.TestCase):


    def test_o_json_e_lido_de_volta(self):
        inst = instancia_pequena()
        dados = {
            "raio_km": 2.0,
            "series": curva(inst, 3),
            "contra_o_otimo": [vars(c) | {"razao": c.razao}
                               for c in contra_o_otimo(inst, 2, semente=4)],
        }
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta) / "v.json"
            destino.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
            lido = json.loads(destino.read_text(encoding="utf-8"))
        self.assertEqual(lido["series"]["guloso"], dados["series"]["guloso"])


if __name__ == "__main__":
    unittest.main()
