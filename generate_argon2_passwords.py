from argon2 import PasswordHasher

ph = PasswordHasher()

print("Admin")
print(ph.hash("admin@123"))

print("\nStudent")
print(ph.hash("student@123"))

print("\nDriver")
print(ph.hash("driver@123"))

# ==========================================
# PARENT PASSWORD
# ==========================================

print("\nParent")
print(ph.hash("Parent@123"))

# UPDATE admins
# SET password='$argon2id$v=19$m=65536,t=3,p=4$OGz2H84OhGpo+pJllXGkJw$hkEhD+PSkHXoD9/aD9KYptLAD/rsoBRk5ts4ryrQl58'
# WHERE username='admin';

# UPDATE students
# SET password='$argon2id$v=19$m=65536,t=3,p=4$vOl93g8mHGilnfW9LsFrRg$3V76moOIKW1aA9a3oy34DCMUd2VqKmraoa/I8YzLP2U';

# UPDATE drivers
# SET password='$argon2id$v=19$m=65536,t=3,p=4$8qkutPZR/E1CF3w33pHTmw$0Ply0KnqCjAQZczq4kyZXCRjCfGa7rDkPVcWDLq9+y8';