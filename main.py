import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import random as rand
import pandas as pd

# dados reais horário de preciptação do INMET
df_chuva = pd.read_csv("csv/dados_tratados/chuva_horaria_recife.csv")

# Converter data/hora
df_chuva["data_hora"] = pd.to_datetime(
    df_chuva["data_hora"]
)

# Garantir que precipitação seja numérica
df_chuva["precipitacao_mm"] = pd.to_numeric(
    df_chuva["precipitacao_mm"],
    errors="coerce"
)

# Ordenar pela data/hora
df_chuva = df_chuva.sort_values("data_hora")

# Remover valores ausentes
df_chuva = df_chuva.dropna(
    subset=["precipitacao_mm"]
)

# Série de precipitação observada
rain_series = df_chuva["precipitacao_mm"].to_numpy()



class CascadingFailureModel:
    # n_energy        - nr de nós da rede de energia (ex.: 30 substação)
    # n_telecom       - nr de nós da rede telecom
    # alpha           - taxa de falha ou probabilidade ou sensibilidade
    # beta            - representa a dependência, propagação ou influência entre os sistemas
    # dependency_type - define o tipo de dependência entre os componentes do sistemas
    def __init__(self, n_energy=30, n_telecom=30, 
                 alpha=0.05, beta=0.7, 
                 dependency_type="partial"):
        
        self.n_energy        = n_energy
        self.n_telecom       = n_telecom
        self.alpha           = alpha
        self.beta            = beta
        self.dependency_type = dependency_type

        # duas possibilidade, escolher uma delas
        # criação dos nós com 10% de probabilidade de existir
        '''
        self.G_energy  = nx.erdos_renyi_graph(n_energy, 0.1)
        self.G_telecom = nx.erdos_renyi_graph(n_telecom, 0.1)
        '''

        self.G_energy  = nx.path_graph(n_energy)
        self.G_telecom = nx.path_graph(n_telecom)

        
        self.energy_states  = {i:1 for i in self.G_energy.nodes()}
        self.telecom_states = {i:1 for i in self.G_telecom.nodes()}

# Dependência: cada telecom depende de um nó elétrico aleatório
        '''
        self.dependencies = {t: rand.choice(list(self.G_energy.nodes()))
                             for t in self.G_telecom.nodes()}
        '''
        # a dependência aqui é determinístico
        self.dependencies = { t: t for t in self.G_telecom.nodes() }


        # Gero chuva artificial (aleatória)
        # Vulnerabilidade estrutural aleatória
        # theta = 0.5 : componente relativamente resistente
        # theta = 1.0 : vulnerabilidade média
        # theta = 1.5 : componente mais vulnerável
        self.vulnerability_energy = {i: rand.uniform(0.5,1.5)
                                     for i in self.G_energy.nodes()}
        self.vulnerability_telecom = {i: rand.uniform(0.5,1.5)
                                      for i in self.G_telecom.nodes()}

        # vulnerabilidade 1, isto é, todos são vulneráveis
        self.vulnerability_energy = { i: 1.0 for i in self.G_energy.nodes() }

        self.vulnerability_telecom = { i: 1.0 for i in self.G_telecom.nodes() }




        
        self.history = []

    def climate_failure_probability(self, node, layer, rain_intensity):
        if layer == "energy":
            theta = self.vulnerability_energy[node]
        else:
            theta = self.vulnerability_telecom[node]

        # cálculo da probabilidade de falha climática
        # alpha          - sensibilidade global ao envento
        # theta          - vulnerabilidade específica do nó
        # rain_intensity - intensidade da chuva
        return 1 - np.exp(-self.alpha * theta * rain_intensity)
    
    def apply_climate_shock(self, rain_intensity):
        for node in self.G_energy.nodes():
            if self.energy_states[node] == 1:
                if rand.random() < self.climate_failure_probability(node,"energy",rain_intensity):
                    self.energy_states[node] = 0
                    
        for node in self.G_telecom.nodes():
            if self.telecom_states[node] == 1:
                if rand.random() < self.climate_failure_probability(node,"telecom",rain_intensity):
                    self.telecom_states[node] = 0
                    
    def apply_dependency(self):
        for t_node, e_node in self.dependencies.items():
            if self.telecom_states[t_node] == 1:
                if self.dependency_type == "total":
                    if self.energy_states[e_node] == 0:
                        self.telecom_states[t_node] = 0
                else:
                    if self.energy_states[e_node] == 0:
                        if rand.random() < self.beta:
                            self.telecom_states[t_node] = 0
                            
    def apply_structural_failure(self):
        # Energia
        active_energy = [n for n,s in self.energy_states.items() if s==1]
        G_sub = self.G_energy.subgraph(active_energy)
        if len(G_sub) > 0:
            largest_cc = max(nx.connected_components(G_sub), key=len)
            for node in active_energy:
                if node not in largest_cc:
                    self.energy_states[node] = 0
        
        # Telecom
        active_telecom = [n for n,s in self.telecom_states.items() if s==1]
        G_sub = self.G_telecom.subgraph(active_telecom)
        if len(G_sub) > 0:
            largest_cc = max(nx.connected_components(G_sub), key=len)
            for node in active_telecom:
                if node not in largest_cc:
                    self.telecom_states[node] = 0
                    
    def resilience_metric(self):
        total_nodes  = self.n_energy + self.n_telecom
        active_nodes = sum(self.energy_states.values()) + sum(self.telecom_states.values())
        return active_nodes / total_nodes

    
    '''
    def simulate(self, T=10, rain_series=None):
    '''
    def simulate(self, rain_series):    

        # comentado para usar os dados reais. 
        '''
        if rain_series is None:
            rain_series = np.random.uniform(0,50,T)
        
        for t in range(T):
            self.apply_climate_shock(rain_series[t])
            self.apply_dependency()
            self.apply_structural_failure()
            self.history.append(self.resilience_metric())
        
        return self.history
        '''
        T = len(rain_series)
        '''
        for rain in rain_series:

                self.apply_climate_shock(rain)
                self.apply_dependency()
                self.apply_structural_failure()

                self.history.append(
                    self.resilience_metric()
                )
        '''
        for t in range(T):

            # Chuva
            self.apply_climate_shock(rain_series[t])

            energy_before  = sum(self.energy_states.values())
            telecom_before = sum(self.telecom_states.values())

            # Dependência
            self.apply_dependency()

            energy_after_dep = sum(self.energy_states.values())
            telecom_after_dep = sum(self.telecom_states.values())

            # Falha estrutural
            self.apply_structural_failure()

            energy_final  = sum(self.energy_states.values())
            telecom_final = sum(self.telecom_states.values())

            resilience = self.resilience_metric()

            self.history.append(resilience)

            # Mostrar somente quando existe chuva
            if rain_series[t] > 0:

                print(
                    f"{t}: "
                    f"chuva={rain_series[t]:.2f} mm | "
                    f"energia={energy_final}/{self.n_energy} | "
                    f"telecom={telecom_final}/{self.n_telecom} | "
                    f"resiliência={resilience:.4f}"
                )

        return self.history


model = CascadingFailureModel(
    n_energy        = 40,
    n_telecom       = 40,
    alpha           = 0.08, # quanto > alpha, > a probabilidade de falha provocada pela chuva
    beta            = 0.6,  # se o componente elétrico do qual um componente de telecom depende falhar, 
                            # existe 60% de probabilidade do componente de telecom falhar também.
    dependency_type = "partial"  # ou "total"
)

# comentado para usar dados reais de precipitação do INMET
'''
resilience = model.simulate(T=20)
'''
resilience = model.simulate(rain_series)

print("Histórico de Resiliência:", resilience)
print("Robustez Média:", np.mean(resilience))
