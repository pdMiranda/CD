import torch
import torch.nn as nn
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

# --- Novo Modelo: Rede Neural Multi-Camadas ---
class ComplexNeuralNetwork(nn.Module):
    def __init__(self, input_dim, hidden_dim1, hidden_dim2, output_dim):
        super(ComplexNeuralNetwork, self).__init__()
        self.layer1 = nn.Linear(input_dim, hidden_dim1)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(0.2) # Adicionando dropout
        self.layer2 = nn.Linear(hidden_dim1, hidden_dim2)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(0.2)
        self.output_layer = nn.Linear(hidden_dim2, output_dim)

    def forward(self, x):
        x = self.dropout1(self.relu1(self.layer1(x)))
        x = self.dropout2(self.relu2(self.layer2(x)))
        return torch.sigmoid(self.output_layer(x)) # Para classificação binária

# --- Função de Geração de Dados (Aumentando num_samples) ---
def generate_dummy_data(num_samples=10000, n_features=20): # Aumentei num_samples e n_features
    # Aumentando num_samples para 10000 e n_features para 20 (ou mais) para dificultar
    X, y = make_classification(n_samples=num_samples, n_features=n_features,
                               n_informative=10, n_redundant=5, # Mais features informativas e redundantes
                               n_classes=2, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    X_train = torch.tensor(X_train, dtype=torch.float32)
    y_train = torch.tensor(y_train, dtype=torch.float32).view(-1, 1)
    X_test = torch.tensor(X_test, dtype=torch.float32)
    y_test = torch.tensor(y_test, dtype=torch.float32).view(-1, 1)

    return X_train, y_train, X_test, y_test

# --- Função de Avaliação Permanece a Mesma ---
def evaluate_model(model, X_test, y_test):
    model.eval()
    with torch.no_grad():
        outputs = model(X_test)
        predictions = (outputs >= 0.5).float()
        accuracy = accuracy_score(y_test.numpy(), predictions.numpy())
    return accuracy