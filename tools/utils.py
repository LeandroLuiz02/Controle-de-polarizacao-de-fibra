import serial.tools.list_ports
import time

def autodetect_serial_port(vid, pid):
    """Tenta detectar automaticamente a porta COM do dispositivo conectado."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == vid and port.pid == pid:
            return f"serial:{port.device}"
    return None

def get_port(device_vid, device_pid, device_name):
    port = autodetect_serial_port(device_vid, device_pid)
    if not port:
        raise ConnectionError(f"{device_name} não detectado. Verifique a conexão.")
    return port

def read_serial(stop_event, serial_object):
    """Lê continuamente da porta serial até que o evento de parada seja definido."""
    try:
        while not stop_event.is_set():
            if serial_object.in_waiting > 0:
                line = serial_object.readline().decode('utf-8').rstrip()
                print(f"Linha recebida: {line}")
            time.sleep(0.1)  # Pequena pausa para evitar uso excessivo da CPU
    except Exception as e:
        print(f"Erro na leitura serial: {e}")