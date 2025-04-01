from flask import Flask, render_template, request, redirect, url_for, flash #Importa las clases y funciones necesarias de Flask para crear la aplicación web, manejar plantillas, solicitudes HTTP, redirecciones y mensajes flash.

from flask_sqlalchemy import SQLAlchemy #Importa SQLAlchemy para el manejo de bases de datos ORM (Mapeo Objeto-Relacional).

from datetime import datetime #Importa datetime para trabajar con fechas y horas.

from collections import deque, defaultdict #Importa deque (cola doblemente terminada) y defaultdict (diccionario con valores por defecto) para estructuras de datos adicionales.

app = Flask(__name__)
app.secret_key = 'clave_secreta_123' #Establece una clave secreta para la aplicación (necesaria para mensajes flash y sesiones).

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/finance_db' #Configura la URI de conexión a la base de datos MySQL.

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #Desactiva el seguimiento de modificaciones de SQLAlchemy para mejorar el rendimiento.
db = SQLAlchemy(app) #Crea una instancia de SQLAlchemy vinculada a la aplicación Flask.

# Modelos
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Creamos la clave primaria
    name = db.Column(db.String(50), nullable=False) # Nombres de las categorias
    type = db.Column(db.String(10), nullable=False)  # income/expense

class Transaction(db.Model): # Definimos una clase
    id = db.Column(db.Integer, primary_key=True) # Creamos la llave primaria
    description = db.Column(db.String(100), nullable=False) # Creamos la variable descripcion, ademas de definir que sera un string con un maximo de 100 caracteres y no podra estar vacio
    amount = db.Column(db.Float, nullable=False) # Creamos la variable amount que sera tipo float y no puede estar vacia
    type = db.Column(db.String(10), nullable=False) # Creamos la variable type, asignamos que sera string con un maximo de 10 caracteres y no podra estar vacia
    date = db.Column(db.DateTime, default=datetime.utcnow) # Creamos la variable date, esta sera tipo DateTime y en caso de no asignarse tomara una por defecto
    category_id = db.Column(db.Integer, db.ForeignKey('category.id')) #Jalamos la category_id pues es una foreign_key
    category = db.relationship('Category', backref='transactions') # Creamos la relacion category_transactions esto para permitirnos acceder a las transacciones

# Estructuras de datos adicionales
recent_transactions = deque(maxlen=10)  # Cola para las últimas 10 transacciones
category_stats = defaultdict(lambda: {'count': 0, 'total': 0.0})  # Estadísticas por categoría

# Crear tablas y datos iniciales
with app.app_context():
    db.create_all() # Creamos las tablas
    if not Category.query.first():
        default_cats = [
            Category(name='Salario', type='income'),
            Category(name='Ventas', type='income'),
            Category(name='Comida', type='expense'),
            Category(name='Transporte', type='expense'),
            Category(name='Entretenimiento', type='expense')
        ]
        db.session.add_all(default_cats)
        db.session.commit()

@app.route('/')
def index():
    transactions_query = db.session.query(
        Transaction,
        Category.name.label('category_name')
    ).join(Category).order_by(Transaction.date.desc()).all()
    
    # Convertir a lista para manipulación
    transactions_list = list(transactions_query)
    
    # Actualizar estructuras de datos
    recent_transactions.clear()
    recent_transactions.extend(transactions_list[:10])
    
    category_stats.clear()
    for trans in transactions_list:
        category_stats[trans.category_name]['count'] += 1
        category_stats[trans.category_name]['total'] += trans.Transaction.amount
    
    # Calcular balance usando lista
    balance = sum(t.Transaction.amount if t.Transaction.type == 'income' else -t.Transaction.amount 
                for t in transactions_list)
    
    # Preparar datos para template usando diccionario
    template_data = {
        'transactions': transactions_list,
        'balance': balance,
        'recent_transactions': list(recent_transactions),
        'category_stats': dict(category_stats)
    }
    
    return render_template('index.html', **template_data)

@app.route('/add', methods=['POST'])
def add_transaction():
    form_data = {
        'description': request.form['description'],
        'amount': float(request.form['amount']),
        'type': request.form['type'],
        'category_id': int(request.form['category']),
        'date': datetime.strptime(request.form['date'], '%Y-%m-%d')
    }
    
    try:
        new_trans = Transaction(**form_data)
        db.session.add(new_trans)
        db.session.commit()
        
        # Actualizar estructura de datos con la nueva transacción
        category = Category.query.get(form_data['category_id'])
        if category:
            recent_transactions.appendleft((new_trans, category.name))
            category_stats[category.name]['count'] += 1
            category_stats[category.name]['total'] += new_trans.amount
        
        flash('✅ Transacción agregada!', 'success')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_transaction(id):
    try:
        trans = Transaction.query.get_or_404(id)
        category_name = trans.category.name if trans.category else None
        
        db.session.delete(trans)
        db.session.commit()
        
        # Actualizar estructuras de datos
        if category_name:
            category_stats[category_name]['count'] -= 1
            category_stats[category_name]['total'] -= trans.amount
        
        # Eliminar de recent_transactions si está allí
        for item in list(recent_transactions):
            if item[0].id == id:
                recent_transactions.remove(item)
                break
        
        flash('🗑️ Transacción eliminada!', 'info')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)