import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import random as rand

class CascadingFailureModel:
    def __init__(self, n_energy=30, n_telecom=30, 
                 alpha=0.05, beta=0.7, 
                 dependency_type="partial"):
        
        self.n_energy        = n_energy
        self.n_telecom       = n_telecom
        self.alpha           = alpha
        self.beta            = beta
        self.dependency_type = dependency_type
        
        self.G_energy  = nx.erdos_renyi_graph(n_energy, 0.1)
        self.G_telecom = nx.erdos_renyi_graph(n_telecom, 0.1)
        
        self.energy_states  = {i:1 for i in self.G_energy.nodes()}
        self.telecom_states = {i:1 for i in self.G_telecom.nodes()}

# Dependência: cada telecom depende de um nó elétrico aleatório
        self.dependencies = {t: rand.choice(list(self.G_energy.nodes()))
                             for t in self.G_telecom.nodes()}
        
        # Vulnerabilidade estrutural aleatória
        self.vulnerability_energy = {i: rand.uniform(0.5,1.5)
                                     for i in self.G_energy.nodes()}
        self.vulnerability_telecom = {i: rand.uniform(0.5,1.5)
                                      for i in self.G_telecom.nodes()}
        
        self.history = []

    def climate_failure_probability(self, node, layer, rain_intensity):
        if layer == "energy":
            theta = self.vulnerability_energy[node]
        else:
            theta = self.vulnerability_telecom[node]
        
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
    
    def simulate(self, T=10, rain_series=None):
        if rain_series is None:
            rain_series = np.random.uniform(0,50,T)
        
        for t in range(T):
            self.apply_climate_shock(rain_series[t])
            self.apply_dependency()
            self.apply_structural_failure()
            self.history.append(self.resilience_metric())
        
        return self.history

model = CascadingFailureModel(
    n_energy=40,
    n_telecom=40,
    alpha=0.08,
    beta=0.6,
    dependency_type="partial"  # ou "total"
)

resilience = model.simulate(T=20)

print("Histórico de Resiliência:", resilience)
print("Robustez Média:", np.mean(resilience))
