
import unittest
 
from src.cobertura import montar
from src.dados import Setor, Unidade
from src.mochila import custo_simulado, guloso_mochila, otimo_mochila, valor_local
 
 
def unidade(nome, lat, lon):
    return Unidade(cnes=nome, nome=nome, bairro="", lat=lat, lon=lon)
 
 
def setor(nome, lat, lon, pop):
    return Setor(codigo=nome, regiao="teste", populacao=pop,
                 lat=lat, lon=lon, urbano=True)
 
 
class TestOtimoMochila(unittest.TestCase):
    """
    Instância clássica de livro-texto (Kleinberg & Tardos, cap. 11):
    itens (valor, custo) = (60,10), (100,20), (120,30); capacidade 50.
    Ótimo conhecido de antemão: itens 2 e 3, valor 220.
    """
 
    def test_instancia_classica(self):
        valores = [60, 100, 120]
        custos = [10, 20, 30]
        resultado = otimo_mochila(valores, custos, orcamento=50)
        self.assertEqual(resultado.valor_total, 220)
        self.assertEqual(sorted(resultado.escolhidas), [1, 2])
        self.assertLessEqual(resultado.custo_total, 50)
 
    def test_orcamento_zero_nao_escolhe_nada(self):
        resultado = otimo_mochila([10, 20], [5, 5], orcamento=0)
        self.assertEqual(resultado.escolhidas, [])
        self.assertEqual(resultado.valor_total, 0)
 
    def test_nenhum_item_cabe(self):
        resultado = otimo_mochila([100], [50], orcamento=10)
        self.assertEqual(resultado.escolhidas, [])
 
    def test_orcamento_grande_pega_tudo(self):
        valores = [10, 20, 30]
        custos = [1, 2, 3]
        resultado = otimo_mochila(valores, custos, orcamento=100)
        self.assertEqual(sorted(resultado.escolhidas), [0, 1, 2])
        self.assertEqual(resultado.valor_total, 60)
 
 
class TestGulosoMochila(unittest.TestCase):
 
    def test_nunca_ultrapassa_o_orcamento(self):
        valores = [60, 100, 120, 55, 40]
        custos = [10, 20, 30, 15, 8]
        resultado = guloso_mochila(valores, custos, orcamento=50)
        self.assertLessEqual(resultado.custo_total, 50)
 
    def test_nunca_passa_do_otimo(self):
        """O guloso (com a correção do item isolado) nunca bate o ótimo."""
        valores = [60, 100, 120, 55, 40, 70, 90]
        custos = [10, 20, 30, 15, 8, 25, 18]
        orcamento = 50
        guloso = guloso_mochila(valores, custos, orcamento)
        otimo = otimo_mochila(valores, custos, orcamento)
        self.assertLessEqual(guloso.valor_total, otimo.valor_total)
 
    def test_respeita_garantia_de_metade_do_otimo(self):
        """
        A correção do melhor item isolado garante pelo menos 1/2 do ótimo
        (Kleinberg & Tardos, cap. 11) — testado numa bateria de instâncias
        sintéticas, não só uma.
        """
        import random
        sorteio = random.Random(99)
        for _ in range(30):
            n = sorteio.randint(3, 12)
            valores = [sorteio.randint(10, 200) for _ in range(n)]
            custos = [sorteio.randint(5, 50) for _ in range(n)]
            orcamento = sorteio.randint(20, 100)
 
            guloso = guloso_mochila(valores, custos, orcamento)
            otimo = otimo_mochila(valores, custos, orcamento)
 
            if otimo.valor_total > 0:
                razao = guloso.valor_total / otimo.valor_total
                self.assertGreaterEqual(razao, 0.5 - 1e-9)
 
    def test_item_caro_e_valioso_nao_e_ignorado(self):
        """
        O caso que o guloso puro (sem a correção) erraria: um item caro e
        valioso, mas sozinho, perde pra vários itens baratos de razão
        melhor — a correção do melhor isolado resgata ele quando vale
        mais que a soma dos baratos.
        """
        valores = [100, 1, 1, 1, 1]
        custos = [100, 1, 1, 1, 1]
        resultado = guloso_mochila(valores, custos, orcamento=100)
        self.assertEqual(resultado.valor_total, 100)
 
 
class TestValorECusto(unittest.TestCase):
 
    def setUp(self):
        self.inst = montar(
            [unidade("A", -15.8000, -47.9000), unidade("B", -15.9000, -47.9000)],
            [setor("perto_de_A", -15.8005, -47.9000, 1000),
             setor("perto_de_B", -15.9005, -47.9000, 400)],
            raio_km=2.0,
        )
 
    def test_valor_local_e_a_populacao_do_setor_mais_proximo(self):
        valores = valor_local(self.inst)
        self.assertEqual(valores, [1000, 400])
 
    def test_custo_simulado_e_deterministico(self):
        c1 = custo_simulado(self.inst, semente=7)
        c2 = custo_simulado(self.inst, semente=7)
        self.assertEqual(c1, c2)
 
    def test_custo_simulado_varia_com_a_semente(self):
        c1 = custo_simulado(self.inst, semente=1)
        c2 = custo_simulado(self.inst, semente=2)
        self.assertNotEqual(c1, c2)
 
    def test_custo_e_sempre_positivo(self):
        for c in custo_simulado(self.inst):
            self.assertGreater(c, 0)
 
 
if __name__ == "__main__":
    unittest.main()
 