@echo off
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U odoo -d odoo -c "UPDATE ir_module_module SET state='to remove' WHERE name='muk_web_theme';"
echo Module muk_web_theme marked for removal
pause
