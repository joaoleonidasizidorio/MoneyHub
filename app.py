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

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor, preencha todos os campos!', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login falhou. Verifique usuário e senha.', 'danger')
    
    return render_template('login.html')

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
        global_income = sum(t.amount for t in all_transactions if t.type == 'income')
        global_expenses = sum(t.amount for t in all_transactions if t.type == 'expense')
        global_balance = global_income - global_expenses
        
        # Transações apenas do mês selecionado
        monthly_transactions = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            extract('month', Transaction.date) == selected_month,
            extract('year', Transaction.date) == selected_year
        ).all()
        
        monthly_income = sum(t.amount for t in monthly_transactions if t.type == 'income')
        monthly_expenses = sum(t.amount for t in monthly_transactions if t.type == 'expense')
        
        # Transações recentes globais
        recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
            .order_by(Transaction.date.desc()).limit(5).all()
        
        return render_template('dashboard.html', 
                             transactions=recent_transactions,
                             total_income=monthly_income,
                             total_expenses=monthly_expenses,
                             balance=global_balance,
                             selected_month=selected_month,
                             selected_year=selected_year,
                             now=now)
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {str(e)}', 'danger')
        return render_template('dashboard.html', 
                             transactions=[],
                             total_income=0,
                             total_expenses=0,
                             balance=0,
                             now=datetime.now())

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
                author=current_user
            )
            
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
        filepath = os.path.join('/app/uploads', filename)
        file.save(filepath)
        
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                return jsonify({'error': 'Chave de API do Gemini não configurada. Adicione-a no arquivo .env'}), 500
                
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Upload the file to Gemini
            gemini_file = genai.upload_file(filepath)
            
            prompt = """
            Analise esta imagem de um cupom ou nota fiscal.
            Eu preciso que você extraia as seguintes informações e retorne EXATAMENTE um JSON válido:
            {
                "amount": <valor total flutuante usando ponto como decimal, ex: 150.50>,
                "description": "<nome do estabelecimento principal>",
                "date": "<data da compra no formato YYYY-MM-DD>"
            }
            Não retorne nada além do JSON. Se não encontrar uma informação, use null.
            """
            
            response = model.generate_content([gemini_file, prompt])
            
            # Limpar o texto para garantir que é um JSON puro
            json_text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(json_text)
            
            # Limpar o arquivo temporário
            os.remove(filepath)
            
            return jsonify(data)
            
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Erro na análise do cupom: {str(e)}'}), 500

# Inicialização do Banco de Dados
def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Banco de dados inicializado com sucesso!")

if __name__ == '__main__':
    init_db()
    print("🚀 Servidor iniciando...")
    print("📊 Acesse: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)