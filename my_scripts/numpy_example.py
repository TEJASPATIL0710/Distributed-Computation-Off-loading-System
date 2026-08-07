import numpy as np

a = np.random.rand(400, 400)
b = np.random.rand(400, 400)
result = a @ b

print(f"Matrix shape: {result.shape}")
print(f"Sum: {result.sum():.2f}")
print(f"Mean: {result.mean():.4f}")