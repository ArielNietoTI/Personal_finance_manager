class Config:
    # Conexión MySQL (XAMPP)
    MYSQL_HOST = 'localhost' # Direccion de la base de datos
    MYSQL_USER = 'root' # Asignamos un usuario (utilizamos el usuario por defecto en XAMPP)
    MYSQL_PASSWORD = '' # Asignamos una contraseña (en este caso no tiene ya que es lo defecto impuesto por XAMPP)
    MYSQL_DB = 'finance_db' # Asignamos el nombre de la base de datos
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}' # Utilizamos la conexion SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Desactivamos las modificaciones de SQLAlchemy para mejorar el rendimiento del projecto