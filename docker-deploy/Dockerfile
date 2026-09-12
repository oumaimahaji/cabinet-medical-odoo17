FROM odoo:17.0

USER root

# Installation des packages Python requis par cabinet_medical
RUN pip3 install --no-cache-dir \
    passlib \
    openpyxl \
    scikit-learn \
    joblib \
    pandas \
    numpy

USER odoo
