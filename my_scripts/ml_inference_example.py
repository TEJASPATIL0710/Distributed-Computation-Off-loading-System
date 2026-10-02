"""Small deterministic CPU inference example for the ML offload worker.

Submit this file with ``task_type=ml``.  It intentionally creates the model
inside the sandbox, so no model files or network access are required.
"""

import torch
from torch import nn

torch.manual_seed(7)

model = nn.Sequential(
    nn.Linear(4, 8),
    nn.ReLU(),
    nn.Linear(8, 3),
)
model.eval()

features = torch.tensor([[0.25, -0.5, 0.75, 1.0]], dtype=torch.float32)
with torch.inference_mode():
    logits = model(features)
    probabilities = torch.softmax(logits, dim=1)
    predicted_class = int(probabilities.argmax(dim=1).item())

print(f"Input shape: {tuple(features.shape)}")
print(f"Probabilities: {probabilities.squeeze(0).tolist()}")
print(f"Predicted class: {predicted_class}")
