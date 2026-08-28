FROM odoo:17.0

USER root

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installation des packages Python requis par cabinet_medical
RUN pip3 install --no-cache-dir \
    passlib \
    openpyxl \
    scikit-learn \
    joblib \
    pandas \
    numpy

USER odoo
