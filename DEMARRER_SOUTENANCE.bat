@echo off
chcp 65001 >nul
title Lancement Écosystème DevOps & Médical - Soutenance PFE

echo ===============================================================================
echo 🚀 DÉMARRAGE AUTOMATIQUE DE L'ÉCOSYSTÈME DEVOPS & MÉDICAL (SOUTENANCE PFE)
echo ===============================================================================
echo.

echo [1/3] 💻 Démarrage de la machine virtuelle Ubuntu...
cd /d C:\vagrant\Ubuntu
vagrant up

echo.
echo [2/3] 🐳 Démarrage de tous les conteneurs Docker (Jenkins, Sonar, Nexus, Grafana, Odoo)...
vagrant ssh -c "docker start sonar nexus jenkins-ci prometheus grafana cabinet_db cabinet-deploy-odoo-1 2>/dev/null || true"

echo.
echo [3/3] 🌐 Ouverture du Portail de Soutenance Live...
start "" "c:\odoo - Copie\SOUTENANCE_DEVOPS.html"

echo.
echo ===============================================================================
echo ✅ TOUS LES SERVICES SONT PRÊTS ! BONNE SOUTENANCE ! 🎓
echo ===============================================================================
pause
