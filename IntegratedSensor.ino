#include <Wire.h>

// --- Configuración MPU6050 ---
const int MPU_ADDR = 0x68;
int16_t accelX, accelY, accelZ;

// --- Configuración QMC5883L ---
#define QMC5883L_ADDR 0x0D

void setup() {
  Serial.begin(9600);
  Wire.begin();

  // Inicializar MPU6050
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // Registro PWR_MGMT_1
  Wire.write(0);    // Despierta el MPU6050
  Wire.endTransmission(true);

  // Inicializar QMC5883L
  Wire.beginTransmission(QMC5883L_ADDR);
  Wire.write(0x0B); // Periodo Set/Reset
  Wire.write(0x01);
  Wire.endTransmission();

  Wire.beginTransmission(QMC5883L_ADDR);
  Wire.write(0x09); // Control 1
  Wire.write(0x1D); // OSR=512, RNG=8G, ODR=200Hz, Mode=Continuous
  Wire.endTransmission();

  Serial.println("Sensores Inicializados: MPU6050 + QMC5883L");

  // Configurar pin del relé
  pinMode(4, OUTPUT);
  digitalWrite(4, LOW); // Apagado por defecto
}

void loop() {
  // --- Leer MPU6050 ---
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); // Registro ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6, true);

  if (Wire.available() >= 6) {
    accelX = (Wire.read() << 8 | Wire.read());
    accelY = (Wire.read() << 8 | Wire.read());
    accelZ = (Wire.read() << 8 | Wire.read());
  }

  // Convertir a g y calcular ángulos
  float Ax = accelX / 16384.0;
  float Ay = accelY / 16384.0;
  float Az = accelZ / 16384.0;

  float pitch = atan2(-Ax, sqrt(Ay * Ay + Az * Az)) * 180.0 / PI;
  float roll = atan2(Ay, Az) * 180.0 / PI;

  // --- Leer QMC5883L ---
  int16_t magX = 0, magY = 0, magZ = 0; // Usar int16_t para asegurar signo correcto

  Wire.beginTransmission(QMC5883L_ADDR);
  Wire.write(0x00); // Inicio de datos
  Wire.endTransmission();

  Wire.requestFrom(QMC5883L_ADDR, 6);
  if (Wire.available() >= 6) {
    magX = Wire.read();
    magX |= Wire.read() << 8;

    magY = Wire.read();
    magY |= Wire.read() << 8;

    magZ = Wire.read();
    magZ |= Wire.read() << 8;
  }

  // --- Calcular Dirección (Brújula) ---
  // Calcular el ángulo en radianes
  float heading = atan2(magY, magX);

  // Ajustar declinación magnética (Opcional: ajusta este valor para tu ubicación)
  // Por ejemplo, para Ciudad de México es aprox +5 grados (0.087 rad)
  // float declinationAngle = 0.0;
  // heading += declinationAngle;

  // Corregir si el signo está invertido
  if(heading < 0)
    heading += 2 * PI;

  // Corregir si se pasa de 2PI
  if(heading > 2 * PI)
    heading -= 2 * PI;

  // Convertir a grados
  float headingDegrees = heading * 180/PI;

  // Determinar dirección cardinal
  String direction = "";
  if (headingDegrees >= 337.5 || headingDegrees < 22.5) direction = "NORTE";
  else if (headingDegrees >= 22.5 && headingDegrees < 67.5) direction = "NORESTE";
  else if (headingDegrees >= 67.5 && headingDegrees < 112.5) direction = "ESTE";
  else if (headingDegrees >= 112.5 && headingDegrees < 157.5) direction = "SURESTE";
  else if (headingDegrees >= 157.5 && headingDegrees < 202.5) direction = "SUR";
  else if (headingDegrees >= 202.5 && headingDegrees < 247.5) direction = "SUROESTE";
  else if (headingDegrees >= 247.5 && headingDegrees < 292.5) direction = "OESTE";
  else if (headingDegrees >= 292.5 && headingDegrees < 337.5) direction = "NOROESTE";

  // --- Control de Relé ---
  // Si NO es NORTE, encender relé (Pin 4 HIGH)
  // Si es NORTE, apagar relé (Pin 4 LOW)
  if (direction == "NORTE") {
    digitalWrite(4, HIGH);
  } else {
    digitalWrite(4, LOW);
  }

  // --- Imprimir Datos Combinados ---
  Serial.print("Pitch: ");
  Serial.print(pitch);
  Serial.print(" | Roll: ");
  Serial.print(roll);

  // Datos de la brújula
  Serial.print(" | Heading: ");
  Serial.print(headingDegrees);
  Serial.print(" deg | Dir: ");
  Serial.println(direction);

  delay(100);
}
