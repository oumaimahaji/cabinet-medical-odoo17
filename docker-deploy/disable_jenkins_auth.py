import re

config_path = "/var/lib/jenkins/config.xml"
with open(config_path, "r", encoding="utf-8") as f:
    content = f.read()

# Remplacer toute variante de useSecurity par false
content = re.sub(r"<useSecurity>.*?</useSecurity>", "<useSecurity>false</useSecurity>", content)
content = re.sub(r"<useSecurity\.[^>]*>.*?</useSecurity>", "<useSecurity>false</useSecurity>", content)

with open(config_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Jenkins security disabled successfully!")
