import numpy as np

a = np.linspace(1, 10, 10)
b = np.linspace(10, 100, 10)
print(np.ndim(b))
b = np.reshape(b, (len(b), -1))
print(np.ndim(b))
print(b)
