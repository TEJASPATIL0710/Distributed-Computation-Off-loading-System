import torch
import torch.nn as nn

model = nn.Sequential(
    nn.Linear(20, 64),
    nn.ReLU(),
    nn.Linear(64, 32),
    nn.ReLU(),
    nn.Linear(32, 3),
)
model.eval()

dummy_input = torch.rand(1, 20)
with torch.no_grad():
    output = model(dummy_input)

print(f"Input shape: {dummy_input.shape}")
print(f"Output: {output.tolist()}")
print(f"Predicted class: {output.argmax().item()}")