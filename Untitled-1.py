# Импортируйте PyTorch.
import torch
# Импортируйте модуль nn.
from torch import nn


class BasicBlock(nn.Module):
    def __init__(self, inp, out):
        super().__init__()
        self.layers = nn.ModuleList()
        self.layers.add_module('layer1', nn.Linear(inp, 10))
        self.layers.add_module('act1', nn.ReLU())
        self.layers.add_module('layer2', nn.Linear(10, inp))
        self.layers.add_module('act2', nn.ReLU())
    
    def forward(self, x):
        y = self.layers[0](x)
        y = self.layers[1](y)
        y = self.layers[2](y)
        y = self.layers[3](x + y)
        return y
    
class MyModel(nn.Module):
    def __init__(self, inp, out):
        super().__init__()
        self.layers = nn.ModuleList()
        for i in range(0, 10):
            self.layers.add_module(f'layer{i}', BasicBlock(inp, i))
        self.layers.add_module('linear',nn.Linear(inp, out))
        print(self.layers)

    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return x
        
model = MyModel(5, 15)




