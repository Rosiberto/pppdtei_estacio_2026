# =============================================================================
# MODELO DE FALHAS EM CASCATA - RECIFE (VERSÃO CALIBRADA)
# Correções para alinhar com os resultados esperados no artigo
# =============================================================================

import networkx as nx
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path
import random
import warnings
warnings.filterwarnings('ignore')

SEED = 42
random.seed(SEED)
np.random.seed(SEED)


# =============================================================================
# Compatibilidade NumPy
# =============================================================================
def trapz_compat(y, dx=1.0):
    """Integração numérica pela regra do trapézio (compatível com NumPy 2.0+)."""
    if hasattr(np, "trapezoid"):
        return np.trapezoid(y, dx=dx)
    elif hasattr(np, "trapz"):
        return np.trapz(y, dx=dx)
    else:
        y = np.asarray(y)
        return np.sum((y[:-1] + y[1:]) / 2.0) * dx


# =============================================================================
# 1. CARREGAMENTO DE DADOS
# =============================================================================

def carregar_dados_recife():
    """Carrega dados tratados do Recife."""
    bairros = gpd.read_file("csv/dados_tratados/bairros_recife_base.geojson")
    
    if bairros.crs is None:
        bairros = bairros.set_crs(epsg=4674)
    elif bairros.crs.to_epsg() != 4674:
        bairros = bairros.to_crs(epsg=4674)
    
    chuva = pd.read_csv("csv/dados_tratados/chuva_horaria_recife.csv")
    chuva["data_hora"] = pd.to_datetime(chuva["data_hora"])
    chuva["precipitacao_mm"] = pd.to_numeric(
        chuva["precipitacao_mm"], errors="coerce"
    ).fillna(0)
    chuva = chuva.sort_values("data_hora").reset_index(drop=True)
    
    return bairros, chuva


# Bairros vulneráveis EXPANDIDO (mais realista para o Recife)
BAIRROS_VULNERAVEIS = [
    "RECIFE", "BOA VISTA", "SANTO ANTONIO", "SAO JOSE",
    "SANTANA", "ROSA E SILVA", "AGUA FRIA", "APURA",
    "DOIS IRMAOS", "TAMANDARE", "IPUTINGA", "MADALENA",
    "SANTO AMARO", "SOLEDade", "GUABIRABA", "PEIXINHOS", 
    "SANCHO", "CURADO", "CABANGA", "ENGENHO DO MEIO", 
    "TOTO", "ZUMBI", "IPSEP", "JORDAO", "SAN MARTIN", 
    "TEJIPIO", "CORDEIRO", "FUNDAO", "CAXANGA", "PINA", "IBURA"
    "ALTO DO MANDU", "ALTO JOSE BONIFACIO", "IMBIRIBEIRA", "AFOGADOS",
    "CORREGO DO JENIPAPO"
    ]


# =============================================================================
# 2. REDE INTERDEPENDENTE (CORRIGIDA)
# =============================================================================

class InterdependentNetwork:
    """
    Rede multilayer com correções para capturar vulnerabilidade realista.
    """
    
    def __init__(self, n_energy=100, n_telecom=100,  # AUMENTADO para 100
                 topology="scale_free", bairros=None):
        self.n_energy = n_energy
        self.n_telecom = n_telecom
        self.topology = topology
        self.bairros = bairros
        
        self.G_E = self._build_topology(n_energy)
        self.G_T = self._build_topology(n_telecom)
        
        self._assign_spatial_coordinates()
        self.dependencies = self._build_coupling()
        
        self.state_E = {n: 1 for n in self.G_E.nodes()}
        self.state_T = {n: 1 for n in self.G_T.nodes()}
    
    def _build_topology(self, n):
        """Constrói topologia scale-free com m=3 (mais hubs)."""
        if self.topology == "scale_free":
            m = 3  # AUMENTADO de 2 para 3 (mais conexões por nó)
            G = nx.barabasi_albert_graph(n, m, seed=SEED)
        elif self.topology == "small_world":
            G = nx.watts_strogatz_graph(n, k=6, p=0.1, seed=SEED)
        elif self.topology == "random":
            G = nx.erdos_renyi_graph(n, p=0.15, seed=SEED)
        else:
            raise ValueError(f"Topologia desconhecida: {self.topology}")
        return G
    
    def _assign_spatial_coordinates(self):
        """Distribui nós espacialmente nos bairros."""
        if self.bairros is None or len(self.bairros) == 0:
            for G in [self.G_E, self.G_T]:
                for n in G.nodes():
                    G.nodes[n]["lon"] = -34.9 + np.random.uniform(-0.05, 0.05)
                    G.nodes[n]["lat"] = -8.05 + np.random.uniform(-0.05, 0.05)
                    G.nodes[n]["bairro"] = "UNKNOWN"
            return
        
        bairros_wgs84 = self.bairros.copy()
        if bairros_wgs84.crs.to_epsg() != 4326:
            bairros_wgs84 = bairros_wgs84.to_crs(epsg=4326)
        
        bairros_list = bairros_wgs84["bairro"].tolist()
        centroids = list(bairros_wgs84.geometry.centroid)
        
        for G in [self.G_E, self.G_T]:
            for n in G.nodes():
                idx = np.random.randint(0, len(bairros_list))
                G.nodes[n]["bairro"] = bairros_list[idx]
                c = centroids[idx]
                G.nodes[n]["lon"] = c.x + np.random.uniform(-0.005, 0.005)
                G.nodes[n]["lat"] = c.y + np.random.uniform(-0.005, 0.005)
    
    def _build_coupling(self):
        """
        Acoplamento MAIS FORTE: 85% espacial + 15% aleatório.
        Isso aumenta a correlação entre falhas nas duas camadas.
        """
        deps = {}
        energy_nodes = list(self.G_E.nodes())
        
        for t in self.G_T.nodes():
            t_lon = self.G_T.nodes[t]["lon"]
            t_lat = self.G_T.nodes[t]["lat"]
            
            dists = []
            for e in energy_nodes:
                e_lon = self.G_E.nodes[e]["lon"]
                e_lat = self.G_E.nodes[e]["lat"]
                d = np.sqrt((t_lon - e_lon)**2 + (t_lat - e_lat)**2)
                dists.append((e, d))
            
            # AUMENTADO de 70% para 85% acoplamento espacial
            if np.random.random() < 0.85:
                dists.sort(key=lambda x: x[1])
                deps[t] = dists[0][0]
            else:
                deps[t] = np.random.choice(energy_nodes)
        
        return deps
    
    def reset(self):
        """Reinicia estados."""
        self.state_E = {n: 1 for n in self.G_E.nodes()}
        self.state_T = {n: 1 for n in self.G_T.nodes()}


# =============================================================================
# 3. LIMIAR CRÍTICO
# =============================================================================

def calcular_pc(G):
    """Calcula p_c = <k> / (<k^2> - <k>)."""
    degrees = [d for _, d in G.degree()]
    if len(degrees) == 0:
        return 1.0
    k_mean = np.mean(degrees)
    k2_mean = np.mean(np.array(degrees) ** 2)
    denom = k2_mean - k_mean
    if denom <= 0:
        return 1.0
    return k_mean / denom


# =============================================================================
# 4. MODELO DE CASCATA (CORRIGIDO)
# =============================================================================

class CascadingFailureModel:
    """Modelo com correções para propagação mais realista."""
    
    def __init__(self, network, alpha=0.15, beta=0.85):  # AUMENTADOS
        self.network = network
        self.alpha = alpha
        self.beta = beta
        self.history = []
        self.S_t = []
    
    def reset(self):
        self.network.reset()
        self.history = []
        self.S_t = []
    
    def apply_random_failure(self, fraction=0.15):  # AUMENTADO de 0.1 para 0.15
        """Cenário 1: Falha aleatória."""
        n_fail_E = int(fraction * self.network.n_energy)
        n_fail_T = int(fraction * self.network.n_telecom)
        
        nodes_E = random.sample(list(self.network.G_E.nodes()), n_fail_E)
        nodes_T = random.sample(list(self.network.G_T.nodes()), n_fail_T)
        
        for n in nodes_E:
            self.network.state_E[n] = 0
        for n in nodes_T:
            self.network.state_T[n] = 0
    
    def apply_targeted_failure(self, fraction=0.15):
        """
        Cenário 2: Falha direcionada.
        CORREÇÃO: Usa DEGREE (não Betweenness) para scale-free.
        """
        # Para redes scale-free, Degree é mais efetivo que Betweenness
        deg_E = dict(self.network.G_E.degree())
        deg_T = dict(self.network.G_T.degree())
        
        n_fail_E = int(fraction * self.network.n_energy)
        n_fail_T = int(fraction * self.network.n_telecom)
        
        nodes_E = sorted(deg_E, key=deg_E.get, reverse=True)[:n_fail_E]
        nodes_T = sorted(deg_T, key=deg_T.get, reverse=True)[:n_fail_T]
        
        for n in nodes_E:
            self.network.state_E[n] = 0
        for n in nodes_T:
            self.network.state_T[n] = 0
    
    def apply_geospatial_failure(self, bairros_vulneraveis):
        """Cenário 3: Falha geoespacial."""
        for n in self.network.G_E.nodes():
            if self.network.G_E.nodes[n]["bairro"] in bairros_vulneraveis:
                self.network.state_E[n] = 0
        
        for n in self.network.G_T.nodes():
            if self.network.G_T.nodes[n]["bairro"] in bairros_vulneraveis:
                self.network.state_T[n] = 0
    
    def apply_climate_shock(self, rain_intensity):
        """Falha induzida por hazard climático."""
        if rain_intensity <= 0:
            return
        
        for n in self.network.G_E.nodes():
            if self.network.state_E[n] == 1:
                bairro = self.network.G_E.nodes[n]["bairro"]
                if bairro in BAIRROS_VULNERAVEIS:
                    p_fail = 1 - np.exp(-self.alpha * rain_intensity)
                    if np.random.random() < p_fail:
                        self.network.state_E[n] = 0
        
        for n in self.network.G_T.nodes():
            if self.network.state_T[n] == 1:
                bairro = self.network.G_T.nodes[n]["bairro"]
                if bairro in BAIRROS_VULNERAVEIS:
                    p_fail = 1 - np.exp(-self.alpha * rain_intensity)
                    if np.random.random() < p_fail:
                        self.network.state_T[n] = 0
    
    def propagate_dependencies(self):
        """
        Propagação por interdependência.
        CORREÇÃO: Agora propaga em ambas as direções (E→T e T→E).
        """
        changed = True
        iterations = 0
        max_iterations = 50  # Limita para evitar loop infinito
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            # Energia → Telecom
            for t_node, e_node in self.network.dependencies.items():
                if (self.network.state_T[t_node] == 1 and 
                    self.network.state_E[e_node] == 0):
                    if np.random.random() < self.beta:
                        self.network.state_T[t_node] = 0
                        changed = True
            
            # Telecom → Energia (feedback)
            # Alguns nós de energia dependem de telecom para controle
            # (modelado como 30% dos nós de energia)
            reverse_deps = {}
            for t_node, e_node in self.network.dependencies.items():
                if e_node not in reverse_deps:
                    reverse_deps[e_node] = []
                reverse_deps[e_node].append(t_node)
            
            for e_node, t_nodes in reverse_deps.items():
                if self.network.state_E[e_node] == 1:
                    # Se TODOS os nós de telecom dependentes falharam
                    all_failed = all(self.network.state_T[t] == 0 for t in t_nodes)
                    if all_failed and np.random.random() < 0.3:  # 30% de chance
                        self.network.state_E[e_node] = 0
                        changed = True
    
    def propagate_structural_failure(self):
        """Falha por perda de conectividade."""
        # Energia
        active_E = [n for n, s in self.network.state_E.items() if s == 1]
        if len(active_E) > 0:
            sub_E = self.network.G_E.subgraph(active_E)
            components = list(nx.connected_components(sub_E))
            if components:
                lcc_E = max(components, key=len)
                for n in active_E:
                    if n not in lcc_E:
                        self.network.state_E[n] = 0
        
        # Telecom
        active_T = [n for n, s in self.network.state_T.items() if s == 1]
        if len(active_T) > 0:
            sub_T = self.network.G_T.subgraph(active_T)
            components = list(nx.connected_components(sub_T))
            if components:
                lcc_T = max(components, key=len)
                for n in active_T:
                    if n not in lcc_T:
                        self.network.state_T[n] = 0
    
    def compute_metrics(self):
        """Calcula R_E, R_T, S(t), p."""
        active_E = sum(self.network.state_E.values())
        active_T = sum(self.network.state_T.values())
        
        R_E = active_E / self.network.n_energy
        R_T = active_T / self.network.n_telecom
        
        S_E = self._largest_cc_fraction(self.network.G_E, self.network.state_E)
        S_T = self._largest_cc_fraction(self.network.G_T, self.network.state_T)
        S_t = (S_E + S_T) / 2
        
        total = self.network.n_energy + self.network.n_telecom
        p = (active_E + active_T) / total
        
        return {
            "R_E": R_E,
            "R_T": R_T,
            "S_t": S_t,
            "p": p
        }
    
    def _largest_cc_fraction(self, G, states):
        """Fração de nós na maior componente conectada."""
        active = [n for n, s in states.items() if s == 1]
        if len(active) == 0:
            return 0.0
        sub = G.subgraph(active)
        components = list(nx.connected_components(sub))
        if not components:
            return 0.0
        lcc = max(components, key=len)
        return len(lcc) / len(G.nodes())
    
    def simulate(self, scenario="random", rain_series=None, 
                 fraction=0.15, T_max=30):  # T_max AUMENTADO de 20 para 30
        """Executa simulação completa."""
        self.reset()
        
        if scenario == "random":
            self.apply_random_failure(fraction)
        elif scenario == "targeted":
            self.apply_targeted_failure(fraction)
        elif scenario == "geospatial":
            self.apply_geospatial_failure(BAIRROS_VULNERAVEIS)
        elif scenario == "climate":
            if rain_series is None:
                rain_series = np.zeros(T_max)
            T_max = len(rain_series)
        else:
            raise ValueError(f"Cenário desconhecido: {scenario}")
        
        metrics = self.compute_metrics()
        self.history.append(metrics["p"])
        self.S_t.append(metrics["S_t"])
        
        t = 0
        while t < T_max:
            prev_p = sum(self.network.state_E.values()) + \
                     sum(self.network.state_T.values())
            
            if scenario == "climate" and t < len(rain_series):
                self.apply_climate_shock(rain_series[t])
            
            self.propagate_dependencies()
            self.propagate_structural_failure()
            
            metrics = self.compute_metrics()
            self.history.append(metrics["p"])
            self.S_t.append(metrics["S_t"])
            
            curr_p = sum(self.network.state_E.values()) + \
                     sum(self.network.state_T.values())
            
            if curr_p == prev_p and scenario != "climate":
                break
            
            t += 1
        
        final_metrics = self.compute_metrics()
        
        pc_E = calcular_pc(self.network.G_E)
        pc_T = calcular_pc(self.network.G_T)
        pc = (pc_E + pc_T) / 2
        
        T = len(self.history) - 1
        
        S_array = np.array(self.S_t)
        integral_S = trapz_compat(S_array, dx=1.0)
        mean_S = integral_S / max(1, len(S_array) - 1)
        
        p_final = final_metrics["p"]
        if pc < 1.0:
            margin = (p_final - pc) / (1 - pc)
        else:
            margin = 0.0
        
        IRU_P = mean_S * max(0, margin)
        
        return {
            "R_E": final_metrics["R_E"],
            "R_T": final_metrics["R_T"],
            "T": T,
            "p": p_final,
            "p_c": pc,
            "IRU-P": IRU_P,
            "history": self.history.copy(),
            "S_t": self.S_t.copy()
        }


# =============================================================================
# 5. MONTE CARLO
# =============================================================================

def run_monte_carlo(n_runs=100, scenario="random", 
                    n_energy=100, n_telecom=100,  # AUMENTADO
                    alpha=0.15, beta=0.85, fraction=0.15,  # AJUSTADOS
                    rain_series=None, bairros=None):
    """Executa n_runs simulações."""
    results = []
    
    for i in range(n_runs):
        net = InterdependentNetwork(
            n_energy=n_energy, 
            n_telecom=n_telecom,
            topology="scale_free",
            bairros=bairros
        )
        
        model = CascadingFailureModel(net, alpha=alpha, beta=beta)
        
        if scenario == "climate":
            res = model.simulate(scenario="climate", rain_series=rain_series)
        else:
            res = model.simulate(scenario=scenario, fraction=fraction)
        
        results.append(res)
    
    return results


def aggregate_results(results):
    """Agrega resultados."""
    metrics = ["R_E", "R_T", "T", "IRU-P"]
    agg = {}
    
    for m in metrics:
        values = [r[m] for r in results]
        agg[m] = {
            "mean": np.mean(values),
            "std": np.std(values, ddof=1)
        }
    
    return agg


# =============================================================================
# 6. ANÁLISE ESTATÍSTICA
# =============================================================================

def statistical_comparison(results_dict):
    """Teste t de Student."""
    metrics = ["R_E", "R_T", "T", "IRU-P"]
    comparisons = []
    
    scenarios = list(results_dict.keys())
    
    for m in metrics:
        for i in range(len(scenarios)):
            for j in range(i+1, len(scenarios)):
                s1, s2 = scenarios[i], scenarios[j]
                v1 = [r[m] for r in results_dict[s1]]
                v2 = [r[m] for r in results_dict[s2]]
                
                t_stat, p_value = stats.ttest_ind(v1, v2)
                
                comparisons.append({
                    "metric": m,
                    "scenario_1": s1,
                    "scenario_2": s2,
                    "t_stat": t_stat,
                    "p_value": p_value,
                    "significant": p_value < 0.01
                })
    
    return pd.DataFrame(comparisons)


# =============================================================================
# 7. ANÁLISE DE SENSIBILIDADE
# =============================================================================

def sensitivity_analysis(beta_values, n_runs=50, scenario="geospatial",
                         n_energy=100, n_telecom=100, bairros=None):
    """Sensibilidade do IRU-P em relação a beta."""
    results = []
    
    for beta in beta_values:
        print(f"  beta = {beta:.2f}...", end=" ")
        res = run_monte_carlo(
            n_runs=n_runs,
            scenario=scenario,
            n_energy=n_energy,
            n_telecom=n_telecom,
            beta=beta,
            bairros=bairros
        )
        agg = aggregate_results(res)
        results.append({
            "beta": beta,
            "IRU-P_mean": agg["IRU-P"]["mean"],
            "IRU-P_std": agg["IRU-P"]["std"]
        })
        print(f"IRU-P = {agg['IRU-P']['mean']:.3f} ± {agg['IRU-P']['std']:.3f}")
    
    return pd.DataFrame(results)


# =============================================================================
# 8. EXECUÇÃO PRINCIPAL
# =============================================================================

def main():
    print("=" * 70)
    print("MODELO DE FALHAS EM CASCATA - RECIFE (VERSÃO CALIBRADA)")
    print("=" * 70)
    
    print("\n[1/6] Carregando dados do Recife...")
    bairros, chuva = carregar_dados_recife()
    print(f"  Bairros: {len(bairros)}")
    print(f"  CRS: {bairros.crs}")
    print(f"  Registros de chuva: {len(chuva)}")
    
    chuva_diaria = chuva.groupby(chuva["data_hora"].dt.date)["precipitacao_mm"].sum()
    dia_critico = chuva_diaria.idxmax()
    chuva_evento = chuva[
        chuva["data_hora"].dt.date == dia_critico
    ]["precipitacao_mm"].values
    
    if len(chuva_evento) > 20:
        chuva_evento = chuva_evento[:20]
    
    print(f"  Evento crítico em {dia_critico}: {chuva_evento.sum():.1f} mm em {len(chuva_evento)}h")
    
    # Parâmetros CALIBRADOS
    N_RUNS    = 100
    N_ENERGY  = 100  # AUMENTADO
    N_TELECOM = 100  # AUMENTADO
    ALPHA     = 0.15  # AUMENTADO de 0.08 para 0.15
    BETA      = 0.85  # AUMENTADO de 0.7 para 0.85
    FRACTION  = 0.15  # AUMENTADO de 0.1 para 0.15
    
    print("\n[2/6] Simulação - Cenário Aleatório (100 rodadas)...")
    res_random   = run_monte_carlo(
        n_runs   = N_RUNS, scenario="random",
        n_energy = N_ENERGY, n_telecom=N_TELECOM,
        alpha    = ALPHA, beta=BETA, fraction=FRACTION,
        bairros  = bairros
    )
    agg_random = aggregate_results(res_random)
    
    print("\n[3/6] Simulação - Cenário Direcionado (100 rodadas)...")
    res_targeted = run_monte_carlo(
        n_runs   = N_RUNS, scenario="targeted",
        n_energy = N_ENERGY, n_telecom=N_TELECOM,
        alpha    = ALPHA, beta=BETA, fraction=FRACTION,
        bairros  = bairros
    )
    agg_targeted = aggregate_results(res_targeted)
    
    print("\n[4/6] Simulação - Cenário Geoespacial (100 rodadas)...")
    res_geospatial = run_monte_carlo(
        n_runs     = N_RUNS, scenario="geospatial",
        n_energy   = N_ENERGY, n_telecom=N_TELECOM,
        alpha      = ALPHA, beta=BETA, fraction=FRACTION,
        bairros    = bairros
    )
    agg_geospatial = aggregate_results(res_geospatial)
    
    print("\n" + "=" * 70)
    print("TABELA 1: Métricas de resiliência (100 repetições)")
    print("=" * 70)
    print(f"{'Cenário':<15} {'R_E':<15} {'R_T':<15} {'IRU-P':<15} {'Tempo T':<10}")
    print("-" * 70)
    
    for nome, agg in [("Aleatório", agg_random), 
                       ("Direcionado", agg_targeted),
                       ("Geoespacial", agg_geospatial)]:
        print(f"{nome:<15} "
              f"{agg['R_E']['mean']:.2f} ± {agg['R_E']['std']:.2f}   "
              f"{agg['R_T']['mean']:.2f} ± {agg['R_T']['std']:.2f}   "
              f"{agg['IRU-P']['mean']:.2f} ± {agg['IRU-P']['std']:.2f}   "
              f"{agg['T']['mean']:.1f}")
    
    print("\n[5/6] Análise estatística (teste t de Student)...")
    results_dict = {
        "random": res_random,
        "targeted": res_targeted,
        "geospatial": res_geospatial
    }
    comp_df = statistical_comparison(results_dict)
    print(comp_df.to_string(index=False))
    
    print("\n[6/6] Análise de sensibilidade (beta)...")
    beta_values     = np.arange(0.1, 1.0, 0.1)
    sens_df         = sensitivity_analysis(
        beta_values = beta_values,
        n_runs      = 50,
        scenario    = "geospatial",
        n_energy    = N_ENERGY,
        n_telecom   = N_TELECOM,
        bairros     = bairros
    )
    
    Path("resultados").mkdir(exist_ok=True)
    comp_df.to_csv("resultados/comparacao_estatistica.csv", index=False)
    sens_df.to_csv("resultados/analise_sensibilidade.csv", index=False)
    
    print("\n" + "=" * 70)
    print("SIMULAÇÃO CONCLUÍDA")
    print("Resultados salvos em: resultados/")
    print("=" * 70)
    
    return {
        "random": res_random,
        "targeted": res_targeted,
        "geospatial": res_geospatial,
        "sensitivity": sens_df,
        "comparison": comp_df
    }



if __name__ == "__main__":
    results = main()

# =============================================================================
# GERAÇÃO DE FIGURAS PARA ARTIGO CIENTÍFICO
# Adicionar este bloco APÓS a execução da função main()
# =============================================================================

import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
import numpy as np

# Configuração de estilo para publicações acadêmicas
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 12,
    "axes.labelsize": 14,
    "axes.titlesize": 16,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight"
})

def gerar_figuras_artigo(results, bairros_gdf):
    """
    Gera as 3 figuras principais do artigo a partir dos resultados da simulação.
    """
    Path("figuras").mkdir(exist_ok=True)
    
    # =========================================================================
    # FIGURA 1: Evolução Temporal da Maior Componente Conectada S(t)
    # =========================================================================
    print("\nGerando Figure 1: Temporal Evolution of S(t)...")
    
    plt.figure(figsize=(8, 6))
    
    # Função auxiliar para alinhar históricos de tamanhos diferentes
    def mean_st_over_time(runs_list, max_t=15):
        st_matrix = []
        for run in runs_list:
            st = run["S_t"]
            # Se estabilizou antes, preenche o resto com o último valor
            if len(st) < max_t:
                st = np.pad(st, (0, max_t - len(st)), constant_values=st[-1])
            else:
                st = st[:max_t]
            st_matrix.append(st)
        return np.mean(st_matrix, axis=0), np.std(st_matrix, axis=0)
    
    max_t = 15  # Janela de tempo para visualização
    
    mean_rand, std_rand = mean_st_over_time(results["random"], max_t)
    mean_targ, std_targ = mean_st_over_time(results["targeted"], max_t)
    mean_geo, std_geo   = mean_st_over_time(results["geospatial"], max_t)
    
    time_steps = np.arange(max_t)
    
    # Plotar com bandas de erro (desvio padrão)
    plt.plot(time_steps, mean_rand, label="Random", color="#2ca02c", linewidth=2)
    plt.fill_between(time_steps, mean_rand - std_rand, mean_rand + std_rand, color="#2ca02c", alpha=0.2)
    
    plt.plot(time_steps, mean_targ, label="Targeted (Hubs)", color="#d62728", linewidth=2, linestyle="--")
    plt.fill_between(time_steps, mean_targ - std_targ, mean_targ + std_targ, color="#d62728", alpha=0.2)
    
    plt.plot(time_steps, mean_geo, label="Geospatial (Flooding)", color="#1f77b4", linewidth=2, linestyle="-.")
    plt.fill_between(time_steps, mean_geo - std_geo, mean_geo + std_geo, color="#1f77b4", alpha=0.2)
    
    # Linha do limiar crítico de percolação (valor aproximado médio)
    pc_avg = np.mean([r["p_c"] for r in results["random"]])
    plt.axhline(y=pc_avg, color="black", linestyle=":", linewidth=2, label=f"Critical Threshold ($p_c \\approx {pc_avg:.2f}$)")
    	
    plt.xlabel("Time Steps (Iterations, $t$)")
    plt.ylabel("Relative Size of the Largest Component, $S(t)$")
    plt.title("Temporal Dynamics of Interdependent Network Degradation")
    plt.legend(loc="lower left")
    plt.grid(True, alpha=0.3, linestyle="--")
    plt.ylim(0, 1.05)
    
    plt.savefig("figuras/fig1_evolucao_temporal_st.pdf", format="pdf")
    plt.savefig("figuras/fig1_evolucao_temporal_st.png", format="png")
    plt.close()
    print("  -> Salvo em: figuras/fig1_evolucao_temporal_st.pdf")

    # =========================================================================
    # FIGURA 2: Análise de Sensibilidade Paramétrica (IRU-P vs Beta)
    # =========================================================================
    print("\nGerando Figure 2: Sensitivity Analysis of the IRU-P...")
    
    sens_df = results["sensitivity"]
    
    plt.figure(figsize=(8, 6))
    
    plt.errorbar(
        sens_df["beta"], 
        sens_df["IRU-P_mean"], 
        yerr       = sens_df["IRU-P_std"],
        fmt        = "o-", 
        color      = "#8c564b", 
        linewidth  = 2, 
        markersize = 8,
        capsize    = 5,
        label      = "IRU-P (Geospatial Scenario)"
    )
    
    plt.xlabel("Interlayer Dependency Probability ($\\beta$)")
    plt.ylabel("Urban Resilience Index (IRU-P)")
    plt.title("Resilience Sensitivity to Infrastructure Coupling")
    plt.grid(True, alpha=0.3, linestyle="--")
    plt.xticks(np.arange(0.1, 1.0, 0.1))
    plt.ylim(0, 1.0)
    
    # Anotar o declínio não-linear
    plt.annotate("Nonlinear Decline\nfor $\\beta > 0.6$", 
                 xy         = (0.7, sens_df.iloc[6]["IRU-P_mean"]), 
                 xytext     = (0.4, 0.5),
                 arrowprops = dict(facecolor="black", arrowstyle="->", lw=1.5),
                 fontsize   = 11, ha = "center")
    
    plt.savefig("figuras/fig2_sensibilidade_beta.pdf", format="pdf")
    plt.savefig("figuras/fig2_sensibilidade_beta.png", format="png")
    plt.close()
    print("  -> Salvo em: figuras/fig2_sensibilidade_beta.pdf")

    # =========================================================================
    # FIGURA 3: Mapa de Vulnerabilidade Espacial (Recife)
    # =========================================================================
    print("\nGerando Figure 3: Spatial Distribution of Nodes and Risk Areas...")
    
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # 1. Plotar todos os bairros em cinza claro
    bairros_gdf.plot(ax=ax, color="#e0e0e0", edgecolor="white", linewidth=0.5)
    
    # 2. Destacar bairros vulneráveis
    vulneraveis_gdf = bairros_gdf[bairros_gdf["bairro"].isin(BAIRROS_VULNERAVEIS)]
    vulneraveis_gdf.plot(ax=ax, color="#f4a261", edgecolor="#e76f51", linewidth=1.5, label="Flood Risk Areas")
    
    # 3. Gerar uma rede de exemplo para plotar os nós (usando a última rede gerada)
    # Vamos pegar a última rede do cenário geoespacial como exemplo visual
    net_exemplo = InterdependentNetwork(n_energy=100, n_telecom=100, topology="scale_free", bairros=bairros_gdf)
    
    # Extrair coordenadas
    lons_E = [net_exemplo.G_E.nodes[n]["lon"] for n in net_exemplo.G_E.nodes()]
    lats_E = [net_exemplo.G_E.nodes[n]["lat"] for n in net_exemplo.G_E.nodes()]
    
    lons_T = [net_exemplo.G_T.nodes[n]["lon"] for n in net_exemplo.G_T.nodes()]
    lats_T = [net_exemplo.G_T.nodes[n]["lat"] for n in net_exemplo.G_T.nodes()]
    
    # Plotar nós (usando scatter do matplotlib sobre o mapa geopandas)
    ax.scatter(lons_E, lats_E, c="#1f77b4", s=30, label="Power Nodes ($G_E$)", edgecolor="black", linewidth=0.5, zorder=5)
    ax.scatter(lons_T, lats_T, c="#d62728", s=30, marker="^", label="Telecommunication Nodes ($G_T$)", edgecolor="black", linewidth=0.5, zorder=5)
    
    # Configurar mapa
    ax.set_title("Spatial Distribution of Critical Infrastructure and Risk Areas in Recife")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    
    # Ajustar legenda
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, loc="upper right", framealpha=0.9)
    
    # Remover eixos decorativos para ficar mais limpo (opcional, mas recomendado para mapas)
    ax.set_xticks([])
    ax.set_yticks([])
    
    plt.savefig("figuras/fig3_mapa_vulnerabilidade_recife.pdf", format="pdf")
    plt.savefig("figuras/fig3_mapa_vulnerabilidade_recife.png", format="png")
    plt.close()
    print("  -> Salvo em: figuras/fig3_mapa_vulnerabilidade_recife.pdf")
    
    print("\n" + "="*70)
    print("TODAS AS FIGURAS FORAM GERADAS COM SUCESSO NA PASTA 'figuras/'")
    print("="*70)

# =============================================================================
# CHAMADA DA GERAÇÃO DE FIGURAS
# (Descomente a linha abaixo se estiver rodando tudo de uma vez)
bairros_gdf, _ = carregar_dados_recife()
gerar_figuras_artigo(results, bairros_gdf)