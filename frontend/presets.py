"""Preset model snippets for user convenience."""

PRESETS = {
    "None": "",
    "SimpleMLP": """import torch.nn as nn\n\nclass SimpleMLP(nn.Module):\n    def __init__(self):\n        super().__init__()\n        self.fc1 = nn.Linear(784, 256)\n        self.relu = nn.ReLU()\n        self.fc2 = nn.Linear(256, 10)\n\n    def forward(self, x):\n        return self.fc2(self.relu(self.fc1(x)))\n""",
    "TinyCNN": """import torch.nn as nn\n\nclass TinyCNN(nn.Module):\n    def __init__(self):\n        super().__init__()\n        self.conv1 = nn.Conv2d(3, 16, 3, padding=1)\n        self.relu = nn.ReLU()\n        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)\n        self.pool = nn.AdaptiveAvgPool2d((1,1))\n        self.fc = nn.Linear(32, 10)\n\n    def forward(self, x):\n        return self.fc(self.pool(self.conv2(self.relu(self.conv1(x)))).view(x.size(0), -1))\n""",
    "SimpleRNN": """import torch.nn as nn\n\nclass SimpleRNN(nn.Module):\n    def __init__(self, input_size, hidden_size, output_size):\n        super().__init__()\n        self.rnn = nn.RNN(input_size, hidden_size, batch_first=True)\n        self.fc = nn.Linear(hidden_size, output_size)\n\n    def forward(self, x):\n        out, _ = self.rnn(x)\n        return self.fc(out[:, -1, :])\n""",
    "Transformer": """import torch.nn as nn\n\nclass TransformerModel(nn.Module):\n    def __init__(self, input_dim, num_heads, num_layers, hidden_dim, output_dim):\n        super().__init__()\n        self.encoder_layer = nn.TransformerEncoderLayer(d_model=input_dim, nhead=num_heads, dim_feedforward=hidden_dim)\n        self.transformer_encoder = nn.TransformerEncoder(self.encoder_layer, num_layers=num_layers)\n        self.fc = nn.Linear(input_dim, output_dim)\n\n    def forward(self, x):\n        x = self.transformer_encoder(x)\n        return self.fc(x.mean(dim=1))\n""",
}

__all__ = ["PRESETS"]
