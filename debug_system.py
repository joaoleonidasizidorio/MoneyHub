import os
import sys

print("=== DEBUG DO SISTEMA FINANCEIRO ===")

# Verificar se o arquivo do banco existe
db_path = 'finance.db'
if os.path.exists(db_path):
    print(f"✅ Banco de dados encontrado: {db_path}")
    print(f"📊 Tamanho: {os.path.getsize(db_path)} bytes")
else:
    print(f"❌ Banco de dados NÃO encontrado: {db_path}")

# Verificar dependências
try:
    from flask import Flask
    print("✅ Flask instalado")
except ImportError as e:
    print(f"❌ Flask não instalado: {e}")

try:
    from flask_sqlalchemy import SQLAlchemy
    print("✅ Flask-SQLAlchemy instalado")
except ImportError as e:
    print(f"❌ Flask-SQLAlchemy não instalado: {e}")

try:
    from flask_bcrypt import Bcrypt
    print("✅ Flask-Bcrypt instalado")
except ImportError as e:
    print(f"❌ Flask-Bcrypt não instalado: {e}")

try:
    from flask_login import LoginManager
    print("✅ Flask-Login instalado")
except ImportError as e:
    print(f"❌ Flask-Login não instalado: {e}")

# Verificar estrutura de pastas
templates_path = 'templates'
if os.path.exists(templates_path) and os.path.isdir(templates_path):
    print(f"✅ Pasta templates encontrada")
    templates = os.listdir(templates_path)
    print(f"📁 Templates: {templates}")
else:
    print(f"❌ Pasta templates NÃO encontrada")

print("\n=== INSTRUÇÕES ===")
print("1. Se houver ❌ acima, instale as dependências com: pip install flask flask-sqlalchemy flask-bcrypt flask-login")
print("2. Se o banco não existe, ele será criado automaticamente ao executar o app.py")
print("3. Execute: python app.py")