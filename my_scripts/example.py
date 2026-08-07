print("Hello from the remote server!")

total = 0
for i in range(1, 1_000_001):
    total += i * i

print(f"Sum of squares up to 1,000,000: {total}")