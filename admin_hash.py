from argon2 import PasswordHasher

ph = PasswordHasher()

password = "admin@123"

hashed_password = ph.hash(password)

print("\nArgon2 Hashed Password:\n")
print(hashed_password)