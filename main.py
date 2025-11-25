import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
import time
import re
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import tkinter.messagebox as tkmb

from tkinter.colorchooser import askcolor

# Configuración de apariencia
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SerialReader:
    def __init__(self, port, baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = False
        self.thread = None
        self.data_callback = None

    def start(self, callback):
        self.data_callback = callback
        self.running = True
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            return True, None
        except Exception as e:
            print(f"Error al conectar: {e}")
            return False, str(e)

    def stop(self):
        self.running = False
        if self.serial_conn:
            self.serial_conn.close()

    def _read_loop(self):
        while self.running and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode('utf-8').strip()
                if line:
                    self._parse_data(line)
            except Exception as e:
                print(f"Error leyendo serial: {e}")
                break

    def _parse_data(self, line):
        # Formato esperado: "Pitch: 12.34 | Roll: -56.78 | Heading: 123.45 deg | Dir: NORTE"
        # Nota: El regex original solo buscaba Pitch y Roll. Lo actualizamos para incluir Heading opcionalmente
        # para mantener compatibilidad si el formato cambia, pero el usuario dijo que usemos el nuevo formato.

        # Intentamos coincidir con el formato completo
        match = re.search(r"Pitch:\s*([-\d\.]+)\s*\|\s*Roll:\s*([-\d\.]+)(?:\s*\|\s*Heading:\s*([-\d\.]+))?", line)
        if match:
            try:
                pitch = float(match.group(1))
                roll = float(match.group(2))
                heading = 0.0
                if match.group(3):
                    heading = float(match.group(3))

                if self.data_callback:
                    self.data_callback(pitch, roll, heading)
            except ValueError:
                pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Monitor Arduino 3D - MPU6050 + Compass")
        self.geometry("1200x700")

        # Variables de estado
        self.current_pitch = 0.0
        self.current_roll = 0.0
        self.current_heading = 0.0

        self.face_color = '#A600FF'
        self.edge_color = '#67009E'

        self.serial_reader = None
        self.is_connected = False


        # Definición del objeto 3D (Un barco pequeño)
        self.vertices = np.array([
            [-2.0, -1.0,  0.5], # 0: Popa Arriba Izq
            [-2.0,  1.0,  0.5], # 1: Popa Arriba Der
            [-1.5, -0.5, -0.5], # 2: Popa Abajo Izq
            [-1.5,  0.5, -0.5], # 3: Popa Abajo Der
            [ 1.0, -1.0,  0.5], # 4: Centro Arriba Izq
            [ 1.0,  1.0,  0.5], # 5: Centro Arriba Der
            [ 1.0, -0.5, -0.5], # 6: Centro Abajo Izq
            [ 1.0,  0.5, -0.5], # 7: Centro Abajo Der
            [ 2.5,  0.0,  0.5], # 8: Proa Punta Arriba
            [ 2.0,  0.0, -0.5], # 9: Proa Punta Abajo
        ])

        # Definición de las caras (índices de vértices)
        self.faces = [
            [0, 1, 3, 2],       # Trasera
            [2, 3, 7, 9, 6],    # Fondo
            [0, 2, 6, 4],       # Costado Izquierdo
            [1, 5, 7, 3],       # Costado Derecho

            # Proa Izquierda (Dividida en triángulos para evitar deformación)
            [4, 6, 9],
            [4, 9, 8],

            # Proa Derecha (Dividida en triángulos para evitar deformación)
            [5, 8, 9],
            [5, 9, 7],

            [0, 4, 8, 5, 1]     # Cubierta
        ]

        self._init_ui()

    def _init_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Arduino 3D View", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        # Controles
        self.port_label = ctk.CTkLabel(self.sidebar_frame, text="Puerto COM:", anchor="w")
        self.port_label.grid(row=1, column=0, padx=20, pady=(10, 0))

        self.port_option_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=self._get_serial_ports())
        self.port_option_menu.grid(row=2, column=0, padx=20, pady=(0, 10))

        self.refresh_btn = ctk.CTkButton(self.sidebar_frame, text="Refrescar Puertos", command=self._refresh_ports)
        self.refresh_btn.grid(row=3, column=0, padx=20, pady=10)

        self.connect_btn = ctk.CTkButton(self.sidebar_frame, text="Conectar", fg_color="green", command=self._toggle_connection)
        self.connect_btn.grid(row=4, column=0, padx=20, pady=10)

        # Panel de Datos
        self.value_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#1a1a1a")
        self.value_frame.grid(row=5, column=0, padx=20, pady=20, sticky="nsew")

        self.pitch_label = ctk.CTkLabel(self.value_frame, text="Pitch\n0.0°", font=("Roboto Medium", 24))
        self.pitch_label.pack(pady=10)

        self.roll_label = ctk.CTkLabel(self.value_frame, text="Roll\n0.0°", font=("Roboto Medium", 24))
        self.roll_label.pack(pady=10)

        self.heading_label = ctk.CTkLabel(self.value_frame, text="Heading\n0.0°", font=("Roboto Medium", 24))
        self.heading_label.pack(pady=10)

        # Apariencia
        self.appearance_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.appearance_frame.grid(row=6, column=0, padx=20, pady=10, sticky="ew")

        self.color_btn_face = ctk.CTkButton(self.appearance_frame, text="Color Cuerpo", command=self._choose_face_color)
        self.color_btn_face.pack(pady=5, fill="x")

        self.color_btn_edge = ctk.CTkButton(self.appearance_frame, text="Color Bordes", command=self._choose_edge_color)
        self.color_btn_edge.pack(pady=5, fill="x")

        # --- Área 3D y Brújula ---
        self.graph_frame = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self.graph_frame.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")

        # Configurar Matplotlib
        self.fig = Figure(figsize=(10, 6), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')

        # Subplot 3D (Izquierda)
        self.ax = self.fig.add_subplot(121, projection='3d')
        self.ax.set_facecolor('#2b2b2b')

        # Subplot Brújula (Derecha)
        self.ax_compass = self.fig.add_subplot(122, projection='polar')
        self.ax_compass.set_facecolor('#2b2b2b')

        # Ajustes iniciales
        self._setup_3d_axes()
        self._setup_compass_axes()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Loop de actualización
        self.after(50, self._update_ui_loop)

        self.port_option_menu.set(self._get_serial_ports()[0])

    def _setup_3d_axes(self):
        self.ax.set_xlim([-3, 3])
        self.ax.set_ylim([-3, 3])
        self.ax.set_zlim([-3, 3])
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')

        # Ocultar rejillas y ejes para un look más limpio
        self.ax.grid(False)
        self.ax.set_axis_off()

        # Color de fondo del panel 3D
        self.ax.set_facecolor('#2b2b2b')

    def _setup_compass_axes(self):
        self.ax_compass.set_theta_zero_location('N')
        self.ax_compass.set_theta_direction(-1) # Sentido horario
        self.ax_compass.set_rticks([]) # Sin marcas radiales
        self.ax_compass.set_facecolor('#2b2b2b')

        # Configurar color de las etiquetas y rejilla
        self.ax_compass.tick_params(axis='x', colors='white')
        self.ax_compass.grid(color='#555555')
        self.ax_compass.spines['polar'].set_visible(False)

    def _get_serial_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        return ports if ports else ["No ports found"]

    def _refresh_ports(self):
        self.port_option_menu.configure(values=self._get_serial_ports())
        self.port_option_menu.set(self._get_serial_ports()[0])

    def _toggle_connection(self):
        if not self.is_connected:
            port = self.port_option_menu.get()
            if port == "No ports found":
                return

            self.serial_reader = SerialReader(port)
            success, error_msg = self.serial_reader.start(self._on_new_data)

            if success:
                self.is_connected = True
                self.connect_btn.configure(text="Desconectar", fg_color="red")
                self.port_option_menu.configure(state="disabled")
            else:
                tkmb.showerror("Error de Conexión", f"No se pudo conectar al puerto {port}.\n\nDetalles: {error_msg}")
        else:
            if self.serial_reader:
                self.serial_reader.stop()
            self.is_connected = False
            self.connect_btn.configure(text="Conectar", fg_color="green")
            self.port_option_menu.configure(state="normal")

    def _on_new_data(self, pitch, roll, heading=0.0):
        self.current_pitch = pitch
        self.current_roll = roll
        self.current_heading = heading

    def _rotate_vertices(self, vertices, pitch_deg, roll_deg):
        # Convertir a radianes
        # Nota: Dependiendo de cómo esté montado el sensor, los ejes pueden variar.
        # Asumimos Pitch -> Rotación en Y, Roll -> Rotación en X
        pitch = np.radians(pitch_deg)
        roll = np.radians(roll_deg)

        # Matriz de rotación en X (Roll)
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(roll), -np.sin(roll)],
            [0, np.sin(roll), np.cos(roll)]
        ])

        # Matriz de rotación en Y (Pitch)
        Ry = np.array([
            [np.cos(pitch), 0, np.sin(pitch)],
            [0, 1, 0],
            [-np.sin(pitch), 0, np.cos(pitch)]
        ])

        # Rotación combinada R = Ry * Rx
        R = np.dot(Ry, Rx)

        # Aplicar rotación a cada vértice
        # Transponemos vertices para multiplicar (3xN), luego transponemos de vuelta
        return np.dot(vertices, R.T)

    def _update_ui_loop(self):
        if self.is_connected:
            # Actualizar etiquetas
            self.pitch_label.configure(text=f"Pitch\n{self.current_pitch:.1f}°")
            self.roll_label.configure(text=f"Roll\n{self.current_roll:.1f}°")
            self.heading_label.configure(text=f"Heading\n{self.current_heading:.1f}°")

            # --- Actualizar 3D ---
            # Calcular nuevos vértices
            rotated_vertices = self._rotate_vertices(self.vertices, self.current_pitch, self.current_roll)

            # Limpiar y redibujar 3D
            self.ax.clear()
            self._setup_3d_axes()

            # Crear colección de polígonos
            poly3d = [[rotated_vertices[vert_id] for vert_id in face] for face in self.faces]

            # Estilo del cubo
            collection = Poly3DCollection(poly3d, linewidths=1, edgecolors=self.edge_color, alpha=0.8)
            collection.set_facecolor(self.face_color)

            self.ax.add_collection3d(collection)

            # --- Actualizar Brújula ---
            self.ax_compass.clear()
            self._setup_compass_axes()

            # Dibujar aguja (flecha)
            # Convertir heading a radianes
            heading_rad = np.radians(self.current_heading)

            # Determinar color de la flecha (Verde si es Norte, Rojo si no)
            arrow_color = 'red'
            if self.current_heading >= 337.5 or self.current_heading < 22.5:
                arrow_color = 'green'

            # Dibujar flecha apuntando al heading
            self.ax_compass.arrow(heading_rad, 0, 0, 0.9, alpha=0.9, width=0.05,
                                 edgecolor='white', facecolor=arrow_color, lw=2, zorder=5)

            # Dibujar línea de referencia Norte
            # self.ax_compass.plot([0, 0], [0, 1], color='gray', linestyle='--', alpha=0.5)

            self.canvas.draw()

        self.after(50, self._update_ui_loop) # 20 FPS

    def _choose_face_color(self):
        color = askcolor(color=self.face_color, title="Seleccionar Color del Cuerpo")[1]
        if color:
            self.face_color = color

    def _choose_edge_color(self):
        color = askcolor(color=self.edge_color, title="Seleccionar Color de Bordes")[1]
        if color:
            self.edge_color = color

if __name__ == "__main__":
    app = App()
    app.mainloop()
