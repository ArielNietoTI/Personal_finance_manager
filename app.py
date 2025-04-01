from flask import Flask, render_template, request, redirect, url_for, flash  
# Importa las clases y funciones necesarias de Flask para crear la aplicacion web, manejar plantillas, solicitudes HTTP, redirecciones y mensajes flash.

from flask_sqlalchemy import SQLAlchemy  
# Importa SQLAlchemy para el manejo de bases de datos ORM (Mapeo Objeto-Relacional).

from datetime import datetime  
# Importa datetime para trabajar con fechas y horas.

from collections import deque, defaultdict  
# Importa deque (cola doblemente terminada) y defaultdict (diccionario con valores por defecto) para estructuras de datos adicionales.

app = Flask(__name__)  
app.secret_key = 'clave_secreta_123'  
# Establece una clave secreta para la aplicacion (necesaria para mensajes flash y sesiones).

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/finance_db'  
# Configura la URI de conexion a la base de datos MySQL.

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  
# Desactiva el seguimiento de modificaciones de SQLAlchemy para mejorar el rendimiento.

db = SQLAlchemy(app)  
# Crea una instancia de SQLAlchemy vinculada a la aplicacion Flask.

# Modelos
class Category(db.Model):  
    id = db.Column(db.Integer, primary_key=True)  # Creamos la clave primaria
    name = db.Column(db.String(50), nullable=False)  # Nombres de las categorias
    type = db.Column(db.String(10), nullable=False)  # income/expense

class Transaction(db.Model):  
    id = db.Column(db.Integer, primary_key=True)  # Creamos la clave primaria
    description = db.Column(db.String(100), nullable=False)  # Variable descripcion, sera un string de maximo 100 caracteres y no podra estar vacia
    amount = db.Column(db.Float, nullable=False)  # Variable amount, sera tipo float y no puede estar vacia
    type = db.Column(db.String(10), nullable=False)  # Variable type, sera string con maximo 10 caracteres y no podra estar vacia
    date = db.Column(db.DateTime, default=datetime.utcnow)  # Variable date, sera tipo DateTime y en caso de no asignarse tomara una por defecto
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))  # category_id como clave foranea
    category = db.relationship('Category', backref='transactions')  
    # Relacion entre transacciones y categorias para poder acceder a los datos facilmente

# Estructuras de datos adicionales
recent_transactions = deque(maxlen=10)  # Cola que almacena las ultimas 10 transacciones

category_stats = defaultdict(lambda: {'count': 0, 'total': 0.0})  # Diccionario con valores por defecto para almacenar estadisticas por categoria

# Creamos las tablas y los datos iniciales
with app.app_context():  
    db.create_all()  # Creamos las tablas
    
    if not Category.query.first():  
        # Si no hay categorias en la base de datos, insertamos algunas por defecto
        default_cats = [
            Category(name='Salario', type='income'),
            Category(name='Ventas', type='income'),
            Category(name='Comida', type='expense'),
            Category(name='Transporte', type='expense'),
            Category(name='Entretenimiento', type='expense')
        ]
        db.session.add_all(default_cats)  # Agregamos las categorias
        db.session.commit()  # Guardamos los cambios

@app.route('/')  
def index():  
    # Consultamos todas las transacciones junto con sus categorias y las ordenamos por fecha descendente
    transactions_query = db.session.query(
        Transaction,
        Category.name.label('category_name')
    ).join(Category).order_by(Transaction.date.desc()).all()
    
    transactions_list = list(transactions_query)  # Convertimos la consulta en una lista

    recent_transactions.clear()  # Limpiamos la cola antes de actualizarla
    recent_transactions.extend(transactions_list[:10])  # Agregamos las 10 transacciones mas recientes

    category_stats.clear()  # Reiniciamos el diccionario de estadisticas
    for trans in transactions_list:  
        # Recorremos la lista de transacciones y actualizamos los valores del diccionario
        category_stats[trans.category_name]['count'] += 1
        category_stats[trans.category_name]['total'] += trans.Transaction.amount

    balance = sum(
        t.Transaction.amount if t.Transaction.type == 'income' else -t.Transaction.amount
        for t in transactions_list
    )  
    # Calculamos el balance total sumando ingresos y restando gastos

    return render_template('index.html', 
                           transactions=transactions_list, 
                           balance=balance, 
                           recent_transactions=list(recent_transactions), 
                           category_stats=dict(category_stats))  
    # Pasamos los datos a la plantilla para mostrarlos en la interfaz

@app.route('/add', methods=['POST'])  
def add_transaction():  
    # Capturamos los datos del formulario y convertimos los valores
    form_data = {
        'description': request.form['description'],
        'amount': float(request.form['amount']),
        'type': request.form['type'],
        'category_id': int(request.form['category']),
        'date': datetime.strptime(request.form['date'], '%Y-%m-%d')
    }
    
    try:
        new_trans = Transaction(**form_data)  # Creamos una nueva transaccion
        db.session.add(new_trans)  # La agregamos a la base de datos
        db.session.commit()  # Guardamos
        
        # Actualizamos la estructura de datos con la nueva transaccion
        category = Category.query.get(form_data['category_id'])
        if category:
            recent_transactions.appendleft((new_trans, category.name))  # Agregamos a la cola de transacciones recientes
            category_stats[category.name]['count'] += 1  # Aumentamos el conteo en la categoria
            category_stats[category.name]['total'] += new_trans.amount  # Aumentamos el total de la categoria
        
        flash('✅ Transaccion agregada!', 'success')  # Mostramos mensajito de exito
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')  # Mostramos mensajito de error
    return redirect(url_for('index'))  # Redirigimos al inicio

@app.route('/delete/<int:id>')  
def delete_transaction(id):  
    try:
        trans = Transaction.query.get_or_404(id)  # Obtenemos la transaccion o lanzamos error si no existe
        category_name = trans.category.name if trans.category else None  # Obtenemos el nombre de la categoria
        
        db.session.delete(trans)  # Eliminamos la transaccion
        db.session.commit()  # Guardamos
        
        # Actualizamos las estructuras de datos
        if category_name:
            category_stats[category_name]['count'] -= 1  # Reducimos conteo en la categoria
            category_stats[category_name]['total'] -= trans.amount  # Reducimos total en la categoria
        
        # Eliminamos de recent_transactions si esta alli
        for item in list(recent_transactions):
            if item[0].id == id:
                recent_transactions.remove(item)  # Eliminamos la transaccion de la cola
                break
        
        flash('🗑️ Transaccion eliminada!', 'info')  # Mostramos mensaje de exito
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')  # Mostramos mensaje de error
    return redirect(url_for('index'))  # Redirigimos al inicio

if __name__ == '__main__':  
    app.run(debug=True)  # Ejecutamos la aplicacion
