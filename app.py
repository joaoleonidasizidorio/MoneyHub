from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import google.generativeai as genai
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_super_secreta_aqui_mude_em_producao_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Modelos do Banco de Dados
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    avatar = db.Column(db.String(255), nullable=True)
    transactions = db.relationship('Transaction', backref='author', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), nullable=False)  # 'income' ou 'expense'
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=False)
    is_paid = db.Column(db.Boolean, default=True, nullable=False)
    receipt_image = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Rotas de Autenticação
@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if not username or not email or not password:
                flash('Todos os campos são obrigatórios!', 'danger')
                return render_template('register.html')

            if password != confirm_password:
                flash('Senhas não coincidem!', 'danger')
                return render_template('register.html')

            # Verificar se usuário já existe
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Nome de usuário já existe!', 'danger')
                return render_template('register.html')

            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash('Email já cadastrado!', 'danger')
                return render_template('register.html')

            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(username=username, email=email, password=hashed_password)
            
            db.session.add(user)
            db.session.commit()
            flash('Conta criada com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar conta: {str(e)}', 'danger')
            return render_template('register.html')

    return render_template('register.html')

QUOTES = [
    "Regra nº 1: Nunca perca dinheiro. Regra nº 2: Nunca esqueça a Regra nº 1. — Warren Buffett",
    "O dinheiro é um mestre terrível, mas um excelente servo. — P.T. Barnum",
    "Não economize o que sobra após os gastos, mas gaste o que sobra após as economias. — Warren Buffett",
    "Riqueza não é o que você ganha, mas o que você guarda. — Robert Kiyosaki",
    "Um orçamento diz para onde seu dinheiro deve ir, em vez de você se perguntar para onde ele foi. — Dave Ramsey",
    "A paz financeira não é a aquisição de coisas. É aprender a viver com menos do que você ganha. — Dave Ramsey"
]

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor, preencha todos os campos!', 'danger')
            import random
            quote = random.choice(QUOTES)
            return render_template('login.html', quote=quote)
        
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login falhou. Verifique usuário e senha.', 'danger')
    
    import random
    quote = random.choice(QUOTES)
    return render_template('login.html', quote=quote)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Rotas Principais
@app.route("/dashboard")
@login_required
def dashboard():
    try:
        from sqlalchemy import extract
        from datetime import datetime
        
        # Obter o mês e ano atual, ou via parâmetro GET
        now = datetime.now()
        selected_month = request.args.get('month', now.month, type=int)
        selected_year = request.args.get('year', now.year, type=int)
        
        # Todas as transações para calcular o Saldo Global
        all_transactions = Transaction.query.filter_by(user_id=current_user.id).all()
        global_income = sum(t.amount for t in all_transactions if t.type == 'income' and t.is_paid)
        global_expenses = sum(t.amount for t in all_transactions if t.type == 'expense' and t.is_paid)
        global_balance = global_income - global_expenses
        
        # Transações apenas do mês selecionado
        monthly_transactions = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            extract('month', Transaction.date) == selected_month,
            extract('year', Transaction.date) == selected_year
        ).all()
        
        monthly_income = sum(t.amount for t in monthly_transactions if t.type == 'income' and t.is_paid)
        monthly_expenses = sum(t.amount for t in monthly_transactions if t.type == 'expense' and t.is_paid)
        
        # Transações recentes do mês
        recent_transactions = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            extract('month', Transaction.date) == selected_month,
            extract('year', Transaction.date) == selected_year
        ).order_by(Transaction.date.desc()).limit(5).all()
        
        # Gráfico de Pizza: Gastos por Categoria
        category_expenses = {}
        for t in monthly_transactions:
            if t.type == 'expense' and t.is_paid:
                category_expenses[t.category] = category_expenses.get(t.category, 0) + t.amount
                
        # Gráfico de Barras: Últimos 6 meses
        import calendar
        import json
        
        # Mapeamento simples de meses para PT-BR
        meses_ptbr = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun', 
                      7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
                      
        six_months_data = []
        for i in range(5, -1, -1):
            m = selected_month - i
            y = selected_year
            while m <= 0:
                m += 12
                y -= 1
            
            month_trans = Transaction.query.filter(
                Transaction.user_id == current_user.id,
                extract('month', Transaction.date) == m,
                extract('year', Transaction.date) == y
            ).all()
            
            inc = sum(t.amount for t in month_trans if t.type == 'income' and t.is_paid)
            exp = sum(t.amount for t in month_trans if t.type == 'expense' and t.is_paid)
            
            six_months_data.append({
                'month': f"{meses_ptbr[m]}/{str(y)[2:]}",
                'income': inc,
                'expense': exp
            })
            
        # Progressão de Limites (Orçamentos)
        user_budgets = Budget.query.filter_by(user_id=current_user.id).all()
        budget_progress = []
        for b in user_budgets:
            spent = category_expenses.get(b.category, 0)
            percentage = min((spent / b.amount) * 100, 100) if b.amount > 0 else 100
            budget_progress.append({
                'id': b.id,
                'category': b.category,
                'amount': b.amount,
                'spent': spent,
                'percentage': percentage
            })
            
        return render_template('dashboard.html', 
                             transactions=recent_transactions,
                             total_income=monthly_income,
                             total_expenses=monthly_expenses,
                             balance=global_balance,
                             selected_month=selected_month,
                             selected_year=selected_year,
                             now=now,
                             category_expenses=json.dumps(category_expenses),
                             six_months_data=json.dumps(six_months_data),
                             budget_progress=budget_progress)
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'danger')
        return render_template('dashboard.html', 
                             transactions=[],
                             total_income=0,
                             total_expenses=0,
                             balance=0,
                             selected_month=datetime.now().month,
                             selected_year=datetime.now().year,
                             now=datetime.now(),
                             category_expenses="{}",
                             six_months_data="[]",
                             budget_progress=[])

@app.route("/report/<int:month>/<int:year>")
@login_required
def report(month, year):
    from sqlalchemy import extract
    from datetime import datetime
    
    monthly_transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year
    ).order_by(Transaction.date).all()
    
    monthly_income = sum(t.amount for t in monthly_transactions if t.type == 'income' and t.is_paid)
    monthly_expenses = sum(t.amount for t in monthly_transactions if t.type == 'expense' and t.is_paid)
    
    category_expenses = {}
    for t in monthly_transactions:
        if t.type == 'expense' and t.is_paid:
            category_expenses[t.category] = category_expenses.get(t.category, 0) + t.amount

    user_budgets = Budget.query.filter_by(user_id=current_user.id).all()
    budget_progress = []
    for b in user_budgets:
        spent = category_expenses.get(b.category, 0)
        percentage = min((spent / b.amount) * 100, 100) if b.amount > 0 else 100
        budget_progress.append({
            'category': b.category,
            'amount': b.amount,
            'spent': spent,
            'percentage': percentage
        })
        
    return render_template('report.html', 
                         transactions=monthly_transactions,
                         total_income=monthly_income,
                         total_expenses=monthly_expenses,
                         month=month,
                         year=year,
                         now=datetime.now(),
                         budget_progress=budget_progress)

@app.route("/transactions")
@login_required
def transactions():
    try:
        page = request.args.get('page', 1, type=int)
        transaction_type = request.args.get('type', 'all')
        category = request.args.get('category', 'all')
        
        query = Transaction.query.filter_by(user_id=current_user.id)
        
        if transaction_type != 'all':
            query = query.filter_by(type=transaction_type)
        
        if category != 'all':
            query = query.filter_by(category=category)
        
        transactions = query.order_by(Transaction.date.desc()).paginate(page=page, per_page=10, error_out=False)
        
        # Obter categorias únicas do usuário
        user_categories = db.session.query(Transaction.category)\
            .filter_by(user_id=current_user.id)\
            .distinct().all()
        categories = [cat[0] for cat in user_categories]
        
        return render_template('transactions.html', 
                             transactions=transactions,
                             categories=categories,
                             current_type=transaction_type,
                             current_category=category)
    except Exception as e:
        flash(f'Erro ao carregar transações: {str(e)}', 'danger')
        return render_template('transactions.html', 
                             transactions=[],
                             categories=[],
                             current_type='all',
                             current_category='all')

@app.route("/add_transaction", methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        try:
            type = request.form.get('type')
            amount = float(request.form.get('amount'))
            description = request.form.get('description')
            category = request.form.get('category')
            date_str = request.form.get('date')
            
            if date_str:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                date = datetime.utcnow()
            
            transaction = Transaction(
                type=type,
                amount=amount,
                description=description,
                category=category,
                date=date,
                is_paid=request.form.get('is_paid') == 'on',
                author=current_user
            )
            
            receipt_image_path = request.form.get('receipt_image_path')
            
            if receipt_image_path:
                transaction.receipt_image = receipt_image_path
            elif 'receipt_image' in request.files:
                file = request.files['receipt_image']
                if file and file.filename != '':
                    filename = secure_filename(f"receipt_{current_user.id}_{datetime.now().timestamp()}_{file.filename}")
                    upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'receipts')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, filename)
                    file.save(filepath)
                    transaction.receipt_image = f"uploads/receipts/{filename}"
            
            db.session.add(transaction)
            db.session.commit()
            flash('Transação adicionada com sucesso!', 'success')
            return redirect(url_for('transactions'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar transação: {str(e)}', 'danger')
    
    # Obter categorias únicas do usuário para o dropdown
    user_categories = db.session.query(Transaction.category)\
        .filter_by(user_id=current_user.id)\
        .distinct().all()
    categories = [cat[0] for cat in user_categories]
    
    return render_template('add_transaction.html', categories=categories)

@app.route("/edit_transaction/<int:transaction_id>", methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    if transaction.author != current_user:
        flash('Você não tem permissão para editar esta transação!', 'danger')
        return redirect(url_for('transactions'))
    
    if request.method == 'POST':
        try:
            transaction.type = request.form.get('type')
            transaction.amount = float(request.form.get('amount'))
            transaction.description = request.form.get('description')
            transaction.category = request.form.get('category')
            date_str = request.form.get('date')
            
            if date_str:
                transaction.date = datetime.strptime(date_str, '%Y-%m-%d')
            transaction.is_paid = request.form.get('is_paid') == 'on'
            
            if 'receipt_image' in request.files:
                file = request.files['receipt_image']
                if file and file.filename != '':
                    filename = secure_filename(f"receipt_{current_user.id}_{datetime.now().timestamp()}_{file.filename}")
                    upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'receipts')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, filename)
                    file.save(filepath)
                    transaction.receipt_image = f"uploads/receipts/{filename}"
            
            db.session.commit()
            flash('Transação atualizada com sucesso!', 'success')
            return redirect(url_for('transactions'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar transação: {str(e)}', 'danger')
    
    # Obter categorias únicas do usuário
    user_categories = db.session.query(Transaction.category)\
        .filter_by(user_id=current_user.id)\
        .distinct().all()
    categories = [cat[0] for cat in user_categories]
    
    return render_template('edit_transaction.html', 
                         transaction=transaction,
                         categories=categories)

@app.route("/delete_transaction/<int:transaction_id>", methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('transactions'))
    
    db.session.delete(transaction)
    db.session.commit()
    flash('Transação excluída com sucesso!', 'success')
    
    return redirect(url_for('transactions'))

@app.route("/toggle_payment/<int:transaction_id>", methods=['POST'])
@login_required
def toggle_payment(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(request.referrer or url_for('transactions'))
    
    transaction.is_paid = not transaction.is_paid
    db.session.commit()
    flash(f'Status atualizado com sucesso!', 'success')
    
    return redirect(request.referrer or url_for('transactions'))

@app.route("/budgets", methods=['GET', 'POST'])
@login_required
def budgets():
    if request.method == 'POST':
        try:
            category = request.form.get('category')
            amount = float(request.form.get('amount'))
            
            existing_budget = Budget.query.filter_by(user_id=current_user.id, category=category).first()
            if existing_budget:
                existing_budget.amount = amount
                flash(f'Limite de {category} atualizado!', 'success')
            else:
                new_budget = Budget(category=category, amount=amount, user_id=current_user.id)
                db.session.add(new_budget)
                flash(f'Limite para {category} criado com sucesso!', 'success')
                
            db.session.commit()
            return redirect(url_for('budgets'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar orçamento: {str(e)}', 'danger')
            
    user_budgets = Budget.query.filter_by(user_id=current_user.id).order_by(Budget.category).all()
    user_categories = db.session.query(Transaction.category).filter_by(user_id=current_user.id).distinct().all()
    categories = [cat[0] for cat in user_categories]
    
    return render_template('budgets.html', budgets=user_budgets, categories=categories)

@app.route("/delete_budget/<int:budget_id>", methods=['POST'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.user_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('budgets'))
        
    db.session.delete(budget)
    db.session.commit()
    flash('Orçamento removido!', 'success')
    return redirect(url_for('budgets'))

@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            # Pegar o usuário real do banco para garantir que as alterações sejam salvas
            user_obj = User.query.get(current_user.id)
            
            # Atualização de email
            new_email = request.form.get('email')
            if new_email and new_email != user_obj.email:
                existing_email = User.query.filter_by(email=new_email).first()
                if existing_email:
                    flash('Email já está em uso por outra conta.', 'danger')
                else:
                    user_obj.email = new_email
                    flash('Email atualizado com sucesso.', 'success')

            # Atualização de Senha
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if current_password and new_password:
                if bcrypt.check_password_hash(user_obj.password, current_password):
                    if new_password == confirm_password:
                        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                        user_obj.password = hashed_password
                        flash('Senha atualizada com sucesso!', 'success')
                    else:
                        flash('A nova senha e a confirmação não coincidem.', 'danger')
                else:
                    flash('Senha atual incorreta.', 'danger')
                    
            # Atualização de Avatar (Foto de Perfil)
            if 'avatar' in request.files:
                file = request.files['avatar']
                if file and file.filename != '':
                    filename = secure_filename(f"user_{user_obj.id}_avatar_{file.filename}")
                    # Caminho absoluto usando o root do Flask
                    upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'avatars')
                    os.makedirs(upload_folder, exist_ok=True)
                    filepath = os.path.join(upload_folder, filename)
                    file.save(filepath)
                    # Salvar caminho relativo no banco
                    user_obj.avatar = f"uploads/avatars/{filename}"
                    flash('Foto de perfil salva com sucesso!', 'success')

            db.session.add(user_obj)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar perfil: {str(e)}', 'danger')
            
        return redirect(url_for('profile'))

    return render_template('profile.html')

@app.route("/api/scan_receipt", methods=['POST'])
@login_required
def scan_receipt():
    if 'receipt' not in request.files:
        return jsonify({'error': 'Nenhuma imagem enviada'}), 400
    
    file = request.files['receipt']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'receipts')
        os.makedirs(upload_folder, exist_ok=True)
        final_filename = f"receipt_ocr_{current_user.id}_{datetime.now().timestamp()}_{filename}"
        filepath = os.path.join(upload_folder, final_filename)
        file.save(filepath)
        
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                return jsonify({'error': 'Chave de API do Gemini não configurada. Adicione-a no arquivo .env'}), 500
                
            import base64
            import urllib.request
            
            # Read and encode image
            with open(filepath, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
            prompt = """
            Você é um assistente financeiro altamente preciso. Analise esta imagem de um cupom fiscal, fatura ou nota fiscal.
            Extraia as seguintes informações e retorne EXATAMENTE neste esquema JSON (nenhum texto a mais):
            {
                "amount": <valor numérico flutuante usando ponto, ex: 150.50>,
                "description": "<nome do estabelecimento principal (curto)>",
                "date": "<data da compra no formato YYYY-MM-DD>",
                "category": "<sugira uma categoria curta: Alimentação, Transporte, Educação, Saúde, Lazer, Moradia, Serviços, Outros>"
            }
            Se não encontrar uma informação, retorne null no valor correspondente.
            """
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={api_key}"
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": encoded_string
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            
            data_encoded = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, headers={'Content-Type': 'application/json'})
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                
            # Extract JSON response
            response_text = result['candidates'][0]['content']['parts'][0]['text']
            data = json.loads(response_text)
            
            data['receipt_image_path'] = f"uploads/receipts/{final_filename}"
            
            return jsonify(data)
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            if os.path.exists(filepath):
                os.remove(filepath)
            print(f"HTTPError: {error_body}")
            return jsonify({'error': f"Erro da API do Gemini: {e.code}"}), 500
            
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            print(f"Exception: {str(e)}")
            return jsonify({'error': f"Erro na análise do cupom: {str(e)}"}), 500

# Inicialização do Banco de Dados
def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Banco de dados inicializado com sucesso!")

@app.route("/api/chat", methods=['POST'])
@login_required
def chat_ai():
    data = request.get_json()
    user_message = data.get('message', '')
    if not user_message:
        return jsonify({'error': 'Mensagem vazia'}), 400
        
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return jsonify({'error': 'Chave de API não configurada.'}), 500
            
        # Coletar dados do usuário
        from datetime import datetime, timedelta
        
        # Últimos 3 meses
        three_months_ago = datetime.now() - timedelta(days=90)
        recent_trans = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.date >= three_months_ago
        ).order_by(Transaction.date.desc()).limit(100).all()
        
        # Orçamentos
        budgets = Budget.query.filter_by(user_id=current_user.id).all()
        
        # Calcular gastos por categoria no mês atual
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        current_month_trans = [t for t in recent_trans if t.date.month == current_month and t.date.year == current_year and t.type == 'expense' and t.is_paid]
        spent_by_category = {}
        for t in current_month_trans:
            spent_by_category[t.category] = spent_by_category.get(t.category, 0) + t.amount
            
        budget_context = "ORÇAMENTOS E GASTOS DO MÊS ATUAL:\n"
        for b in budgets:
            spent = spent_by_category.get(b.category, 0)
            status = "ESTOUROU" if spent > b.amount else "DENTRO DO LIMITE"
            budget_context += f"- {b.category}: Limite R$ {b.amount:.2f} | Gasto R$ {spent:.2f} ({status})\n"
            
        trans_context = "ÚLTIMAS TRANSAÇÕES:\n"
        for t in recent_trans[:20]: # Limite reduzido para 20 para acelerar o processamento
            tipo = "Receita" if t.type == "income" else "Despesa"
            status = "Paga" if t.is_paid else "Pendente"
            trans_context += f"- {t.date.strftime('%Y-%m-%d')} | {tipo} | R$ {t.amount:.2f} | {t.category} | {t.description} | {status}\n"
            
        system_prompt = f"""Você é o Consultor Financeiro IA do aplicativo Moneyhub.
Sua personalidade tem duas fases:
1. No início, e para dúvidas normais ou pequenos erros do usuário, seja extremamente amigável, encorajador e use emojis.
2. Se você perceber que o usuário frequentemente estoura orçamentos, gasta mais do que ganha ou tenta justificar gastos ruins, mude o tom: seja frio, duro, sem emojis e dê uma "bronca" severa, agindo como um consultor rígido.

Use os dados financeiros REAIS do usuário abaixo para responder a pergunta. 
REGRA MÁXIMA: Seja EXTREMAMENTE conciso, direto e rápido na resposta. Responda no máximo em 2 ou 3 parágrafos curtos. Nunca gere textos longos.

DADOS DO USUÁRIO:
{budget_context}

{trans_context}"""

        import urllib.request
        import json
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={api_key}"
        
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [{
                "parts": [{"text": user_message}]
            }],
            "generationConfig": {
                "maxOutputTokens": 300,
                "temperature": 0.5
            }
        }
        
        data_encoded = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data_encoded, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            
        reply_text = result['candidates'][0]['content']['parts'][0]['text']
        return jsonify({'reply': reply_text})
        
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Chatbot HTTPError: {error_body}")
        import sys
        sys.stdout.flush()
        return jsonify({'error': f"Erro da API do Gemini: {error_body}"}), 500
        
    except Exception as e:
        print(f"Chatbot Exception: {str(e)}")
        import sys
        sys.stdout.flush()
        return jsonify({'error': str(e)}), 500

@app.route('/api/forecast', methods=['GET'])
@login_required
def forecast_ai():
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return jsonify({'error': 'Chave da API não configurada.'}), 500
            
        hoje = datetime.now()
        mes_atual = hoje.month
        ano_atual = hoje.year
        dia_atual = hoje.day
        import calendar
        ultimo_dia = calendar.monthrange(ano_atual, mes_atual)[1]
        
        budgets = Budget.query.filter_by(user_id=current_user.id).all()
        if not budgets:
            return jsonify({'forecast': 'Você ainda não definiu nenhum orçamento. Crie orçamentos para eu poder analisar o ritmo dos seus gastos!'})
            
        transacoes_mes = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            db.extract('month', Transaction.date) == mes_atual,
            db.extract('year', Transaction.date) == ano_atual,
            Transaction.type == 'expense'
        ).all()
        
        gastos_por_categoria = {}
        for t in transacoes_mes:
            gastos_por_categoria[t.category] = gastos_por_categoria.get(t.category, 0) + t.amount
            
        budget_context = ""
        for b in budgets:
            gasto = gastos_por_categoria.get(b.category, 0)
            budget_context += f"- {b.category}: Gasto R$ {gasto:.2f} de R$ {b.amount:.2f}\n"
            
        prompt = f"""
Você é o Assistente Financeiro IA do Moneyhub.
Hoje é dia {dia_atual} de um mês com {ultimo_dia} dias.
Analise os orçamentos e gastos do usuário abaixo para o mês atual.
Seu objetivo é gerar um "Alerta de Tendência" (Forecasting) muito curto e direto (apenas 1 parágrafo de até 3 linhas).
Se o usuário estiver gastando muito rápido (ex: gastou 80% do orçamento na metade do mês), preveja o dia aproximado que o dinheiro vai acabar e dê um conselho urgente (ex: "No ritmo atual, você vai estourar o orçamento de Lazer no dia 22...").
Se tudo estiver dentro do esperado ou não houver gastos, dê um pequeno incentivo.

ORÇAMENTOS E GASTOS:
{budget_context}
"""
        import urllib.request
        import json
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 200, "temperature": 0.5}
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
        
        reply_text = result['candidates'][0]['content']['parts'][0]['text']
        return jsonify({'forecast': reply_text.strip()})
        
    except Exception as e:
        print(f"Forecast Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/anomalies', methods=['GET'])
@login_required
def check_anomalies():
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return jsonify({'error': 'Chave da API não configurada.'}), 500
            
        # Buscar despesas dos últimos 4 meses
        quatro_meses_atras = datetime.now() - timedelta(days=120)
        despesas = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'expense',
            Transaction.date >= quatro_meses_atras
        ).order_by(Transaction.date.asc()).all()
        
        if not despesas:
            return jsonify({'anomaly': 'TUDO NORMAL'})
            
        # Agrupar por Mês/Ano para a IA entender a linha do tempo
        historico_agrupado = {}
        for d in despesas:
            chave_mes = d.date.strftime('%Y-%m')
            if chave_mes not in historico_agrupado:
                historico_agrupado[chave_mes] = []
            historico_agrupado[chave_mes].append(f"- {d.description} ({d.category}): R$ {d.amount:.2f}")
            
        contexto_transacoes = ""
        for mes, lista in historico_agrupado.items():
            contexto_transacoes += f"\\nMês {mes}:\\n" + "\\n".join(lista) + "\\n"
            
        mes_atual_str = datetime.now().strftime('%Y-%m')
            
        prompt = f"""
Você é um auditor financeiro IA rigoroso.
Analise o histórico de despesas dos últimos 4 meses do usuário abaixo. O mês atual é {mes_atual_str}.
Seu único objetivo é encontrar "Anomalias" nas contas recorrentes (ex: Luz, Água, Internet, Assinaturas, Mercado, etc).
Uma anomalia é um gasto no mês atual ({mes_atual_str}) que veio com um valor anormalmente alto (ex: 40% a mais ou mais) do que a média dos meses anteriores para a mesma conta.

REGRA 1: Se você encontrar UMA anomalia grave, retorne APENAS UMA MENSAGEM CURTA E DIRETA começando com "🚨 ". Exemplo: "🚨 Notamos um aumento anormal de 60% na sua conta de Energia este mês. Verifique a fatura!"
REGRA 2: Se tudo estiver normal, os aumentos forem pequenos, ou não houver dados suficientes, RETORNE EXATAMENTE AS PALAVRAS: "TUDO NORMAL" (sem aspas, sem pontos).

HISTÓRICO DE DESPESAS:
{contexto_transacoes}
"""
        import urllib.request
        import json
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 100, "temperature": 0.2}
        }
        
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
        
        reply_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
        return jsonify({'anomaly': reply_text})
        
    except Exception as e:
        print(f"Anomalies Exception: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    print("🚀 Servidor iniciando...")
    print("📊 Acesse: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)