import serial.tools.list_ports

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