"""Preset model snippets for user convenience."""

PRESETS = {
    "None": "",
    "SimpleMLP": """import torch.nn as nn\n\nclass SimpleMLP(nn.Module):\n    def __init__(self):\n        super().__init__()\n        self.fc1 = nn.Linear(784, 256)\n        self.relu = nn.ReLU()\n        self.fc2 = nn.Linear(256, 10)\n\n    def forward(self, x):\n        return self.fc2(self.relu(self.fc1(x)))\n""",
    "TinyCNN": """import torch.nn as nn\n\nclass TinyCNN(nn.Module):\n    def __init__(self):\n        super().__init__()\n        self.conv1 = nn.Conv2d(3, 16, 3, padding=1)\n        self.relu = nn.ReLU()\n        self.conv2 = nn.Conv2d(16, 32, 3, padding=1)\n        self.pool = nn.AdaptiveAvgPool2d((1,1))\n        self.fc = nn.Linear(32, 10)\n\n    def forward(self, x):\n        return self.fc(self.pool(self.conv2(self.relu(self.conv1(x)))).view(x.size(0), -1))\n""",
}

__all__ = ["PRESETS"]
