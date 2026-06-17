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

