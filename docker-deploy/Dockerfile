FROM odoo:17.0

USER root

# Installation des packages Python requis par cabinet_medical
RUN pip3 install --no-cache-dir \
    passlib \
    openpyxl \
    scikit-learn \
    joblib \
    pandas \
    numpy \
    torch \
    sentence-transformers \
    "pillow==10.4.0" \
    --extra-index-url https://download.pytorch.org/whl/cpu

USER odoo
