import PyInstaller.__main__
import customtkinter
import os
import sys

# Obtener la ruta de customtkinter para incluir sus archivos de tema/imágenes
ctk_path = os.path.dirname(customtkinter.__file__)

# Definir los argumentos para PyInstaller
args = [
    'main.py',                            # Archivo principal
    '--name=ArduinoMonitor3D',            # Nombre del ejecutable
    '--onefile',                          # Crear un solo archivo .exe
    '--noconsole',                        # No mostrar la consola negra de fondo
    '--clean',                            # Limpiar caché antes de construir
    f'--add-data={ctk_path};customtkinter', # Incluir carpeta de customtkinter
    # Excluir módulos innecesarios para reducir tamaño (opcional)
    # '--exclude-module=scipy',
]

print("Iniciando compilación con PyInstaller...")
print(f"Incluyendo CustomTkinter desde: {ctk_path}")

# Ejecutar PyInstaller
PyInstaller.__main__.run(args)
