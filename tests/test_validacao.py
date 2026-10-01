"""
Testes da validação.

O foco é a lógica que transforma números em afirmações — a curva, a
comparação com o ótimo e a geração dos arquivos. Os gráficos são
conferidos como XML bem formado e com as séries presentes; a aparência
final é conferida a olho, que é o único jeito honesto.
"""

import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from src.cobertura import montar
from src.dados import Setor, Unidade
from src.guloso import historico
from validacao import (COR, Comparacao, contra_o_otimo, curva, grafico_curva,
                       grafico_ganho, tabela)


def unidade(nome, lat, lon):
    return Unidade(cnes=nome, nome=nome, bairro="", lat=lat, lon=lon)


def setor(nome, lat, lon, pop):
    return Setor(codigo=nome, regiao="teste", populacao=pop,
                 lat=lat, lon=lon, urbano=True)


def instancia_pequena():
    """Cinco unidades em fila, cada uma cobrindo um setor diferente."""
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
        """Acrescentar unidade não pode tirar gente da conta."""
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
        """Se alguém acrescentar uma linha de base sem cor, o gráfico quebra."""
        self.assertEqual(set(self.series), set(COR))


class TestContraOOtimo(unittest.TestCase):

    def test_o_guloso_nunca_passa_do_otimo(self):
        """Se passar, um dos dois está errado."""
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
        """"aleatórias" tem acento, e um "&" num nome quebraria o SVG."""
        svg = grafico_curva(self.series, self.total, 2.0)
        ET.fromstring(svg)
        self.assertNotIn("&a", svg.replace("&amp;", ""))


class TestTabela(unittest.TestCase):

    def test_cita_a_garantia_teorica(self):
        inst = instancia_pequena()
        md = tabela(curva(inst, 4), inst.populacao_total,
                    contra_o_otimo(inst, 3, semente=2), [2, 4])
        self.assertIn("63,21%", md)
        self.assertIn("ótimo", md)


class TestArquivosGerados(unittest.TestCase):
    """O `_main` grava quatro arquivos; aqui só se confere o formato."""

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
