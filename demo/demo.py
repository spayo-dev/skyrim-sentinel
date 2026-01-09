import hashlib

# Data to be hashed (must be bytes)
data = b"This is a test string to test sha256 hashing."

# Create a SHA256 hash object
sha256_hash = hashlib.sha256()

# Update the hash object with the data
sha256_hash.update(data)

# Get the hexadecimal representation of the hash
hex_digest = sha256_hash.hexdigest()

print(f"SHA256 hash of '{data.decode()}': {hex_digest}")

# You can also do this in a more condensed way:
md5_digest = hashlib.md5(b"Another string to hash").hexdigest()
print(f"MD5 hash of 'Another string to hash': {md5_digest}")
