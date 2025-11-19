# Trabalho de referência: A study of polarization compensation for quantum networks
# link: https://arxiv.org/pdf/2208.13584

import time
import numpy as np
from qmi.core.context import QMI_Context
from qmi.instruments.thorlabs.mpc320 import Thorlabs_Mpc320
import serial.tools.list_ports

# --- CONFIGURAÇÕES DO HARDWARE ---
COM_PORT = None
PADDLES = [1, 2, 3]

# --- CONFIGURAÇÕES DO ALGORITMO ---
TARGET_VIS_HV = 0.95       # 95% para base HV
TARGET_VIS_DA = 0.98       # 98% para base DA
TARGET_VIS_GLOBAL = 0.95   # Média das duas
MAX_GLOBAL_RETRIES = 10    # 
MAX_BASE_RETRIES = 4       # 
INITIAL_TEST_ANGLE = 10    # Graus para testar impacto
THRESHOLD_REDUCTION_STEP = 0.002  # Redução de 0.2% se falhar

# -- IDENTIFICADORES DE DISPOSITIVOS USB ---
MPC320_VID = 1027
MPC320_PID = 64240

class PolarizationCompensator:
    def __init__(self, mpc_instrument):
        self.mpc = mpc_instrument

    # =================================================================
    #  TODO: INTEGRAÇÃO COM DETECTORES
    # =================================================================
    
    def switch_basis(self, basis: str):
        """
        STUB: Código para trocar a base ótica (Shutters/Rotadores).
        No artigo, isso controla os shutters S1-S4.
        """
        print(f"  [HARDWARE] Trocando sistema ótico para base: {basis}")
        # TODO: código real para controlar os shutters
        time.sleep(0.2)

    def measure_visibility(self, basis: str) -> float:
        """
        STUB: Código para ler o detector de fótons e calcular Visibilidade.
        Deve retornar um float entre 0.0 e 1.0.
        """
        # TODO: código real para ler os detectores e calcular visibilidade
        simulated_vis = np.random.uniform(0.7, 1.0)  # Simula uma visibilidade aleatória
        return simulated_vis

    #CONTROLE DO MPC320 

    def get_angle(self, paddle_idx):
        """Lê a posição atual de um paddle."""
        return self.mpc.get_status_update(paddle_idx).position

    def move_paddle(self, paddle_idx, angle):
        """Move para angulo absoluto com espera."""
        # Garante limites de 0 a 170 (ou 360 dependendo do modelo, ajuste se necessário)
        if angle > 170 or angle < 0:
            raise ValueError(f"Ângulo {angle} fora dos limites (0-170)")
        
        self.mpc.move_absolute(paddle_idx, angle)
        time.sleep(0.3) # Tempo para o motor chegar
        

    def move_relative(self, paddle_idx, delta):
        curr = self.get_angle(paddle_idx)
        try:
            self.move_paddle(paddle_idx, curr + delta)
        except ValueError as e:
            print(f"  [AVISO] Movimento relativo fora dos limites: {e}")

    # LÓGICA DO ALGORITMO

    def get_paddle_impacts(self, basis):
        """
        Move cada paddle um pouco para ver qual afeta mais a visibilidade.
        Baseado em: "finds the paddle with the highest impact"
        """
        impacts = {}
        original_vis = self.measure_visibility(basis)
        
        for p in PADDLES:
            start_pos = self.get_angle(p)
            
            # Move um pouco
            self.move_relative(p, INITIAL_TEST_ANGLE)
            new_vis = self.measure_visibility(basis)
            
            # Calcula impacto (mudança absoluta na visibilidade)
            impacts[p] = abs(new_vis - original_vis)
            
            # Restaura posição
            self.move_paddle(p, start_pos)
            
        # Retorna lista ordenada: [(paddle_id, impacto), ...]
        return sorted(impacts.items(), key=lambda x: x[1], reverse=True)

    def scan_1d(self, paddle, basis):
        """Varredura simples de um único paddle."""
        print(f"    -> Otimizando Paddle {paddle} (1D)...")
        best_vis = -1
        best_ang = self.get_angle(paddle)
        
        # Varredura grosseira (ex: de 0 a 170 em passos de 20)
        # TODO: Para produção, um algoritmo de busca (Nelder-Mead ou Gradiente) seria mais rápido
        for ang in range(0, 170, 20):
            self.move_paddle(paddle, ang)
            vis = self.measure_visibility(basis)
            if vis > best_vis:
                best_vis = vis
                best_ang = ang
        
        # Move para o melhor encontrado
        self.move_paddle(paddle, best_ang)
        return best_vis

    def scan_2d(self, p1, p2, basis):
        """Varredura aninhada de dois paddles"""
        print(f"    -> Otimizando Paddles {p1} e {p2} (2D Loop)...")
        best_vis = -1
        best_pos = (self.get_angle(p1), self.get_angle(p2))

        # Varredura simplificada (Grade 5x5 ao redor do ponto atual para não demorar séculos)
        start_p1 = self.get_angle(p1)
        start_p2 = self.get_angle(p2)
        
        offsets = [-20, -10, 0, 10, 20]
        
        for off1 in offsets:
            if (start_p1 + off1 <= 170 and start_p1 + off1 >= 0):
                self.move_paddle(p1, start_p1 + off1)

                for off2 in offsets:
                    if (start_p2 + off2 <= 170 and start_p2 + off2 >= 0): 
                        self.move_paddle(p2, start_p2 + off2)

                        vis = self.measure_visibility(basis)
                        if vis > best_vis:
                            best_vis = vis
                            best_pos = (self.get_angle(p1), self.get_angle(p2))
        
        self.move_paddle(p1, best_pos[0])
        self.move_paddle(p2, best_pos[1])
        return best_vis

    def minimize_polarization_state(self, basis, threshold, max_tries):
        """
        Fluxo da direita da Figura 4.
        Tenta atingir o threshold para uma base específica.
        """
        self.switch_basis(basis)
        current_threshold = threshold

        for attempt in range(1, max_tries + 1):
            vis = self.measure_visibility(basis)
            print(f"  [Base {basis}] Tentativa {attempt}/{max_tries}. Vis Atual: {vis:.1%}, Alvo: {current_threshold:.1%}")

            if vis >= current_threshold:
                return True

            # 1. Identificar Paddles de maior impacto
            sorted_paddles = self.get_paddle_impacts(basis)
            best_p = sorted_paddles[0][0]
            second_p = sorted_paddles[1][0]

            # 2. Otimizar o melhor paddle (1D)
            vis = self.scan_1d(best_p, basis)
            if vis >= current_threshold:
                return True
            
            # 3. Se falhar, otimizar os dois melhores (2D)
            vis = self.scan_2d(best_p, second_p, basis)
            if vis >= current_threshold:
                return True
            
            # 4. Se falhar, reduzir threshold 
            current_threshold -= THRESHOLD_REDUCTION_STEP
            print(f"    ! Falha na tentativa. Reduzindo alvo para {current_threshold:.1%}")

        return False

    def run_full_algorithm(self):
        """
        Fluxo da esquerda da Figura 4.
        Alterna entre bases até que a média global seja satisfatória.
        """
        print("\n=== INICIANDO COMPENSAÇÃO DE POLARIZAÇÃO ===")
        
        # Reset Opcional (Home)
        for p in PADDLES: self.move_paddle(p, 0)

        for global_try in range(MAX_GLOBAL_RETRIES):
            print(f"\n>>> Ciclo Global {global_try + 1}")

            # Otimiza HV
            self.minimize_polarization_state('HV', TARGET_VIS_HV, MAX_BASE_RETRIES)
            
            # Troca e Otimiza DA
            self.minimize_polarization_state('DA', TARGET_VIS_DA, MAX_BASE_RETRIES)

            # Checagem Final Global [cite: 163]
            # Mede ambas rapidamente para calcular média
            self.switch_basis('HV')
            v_hv = self.measure_visibility('HV')
            self.switch_basis('DA')
            v_da = self.measure_visibility('DA')
            
            global_avg = (v_hv + v_da) / 2
            print(f"  >>> Status Global: HV={v_hv:.1%}, DA={v_da:.1%}, GLOBAL={global_avg:.1%}")

            if global_avg >= TARGET_VIS_GLOBAL:
                print("=== SUCESSO: Compensação Finalizada! ===")
                return True
        
        print("=== FALHA: Não foi possível atingir os critérios após 10 ciclos. ===")
        return False

# -- utils ------------------------------------------------
#TODO: mover para utils.py (refactor)
def autodetect_serial_port(vid, pid):
    """Tenta detectar automaticamente a porta COM do dispositivo conectado."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == vid and port.pid == pid:
            return f"serial:{port.device}"
    return None

def connect(device_vid, device_pid, device_name):
    port = autodetect_serial_port(device_vid, device_pid)
    if not port:
        raise ConnectionError(f"{device_name} não detectado. Verifique a conexão.")
    return port

# =================================================================
#  EXECUÇÃO PRINCIPAL
# =================================================================
def main():
    global COM_PORT # fora do escopo
    COM_PORT = connect(MPC320_VID, MPC320_PID, "MPC320")

    qmi_context = QMI_Context("polarization_control")
    qmi_context.start()
    
    mpc = None
    try:
        print(f"Conectando ao MPC320 em {COM_PORT}...")
        mpc = Thorlabs_Mpc320(context=qmi_context, name="mpc", transport=COM_PORT)
        mpc.open()
        mpc.enable_channels(PADDLES)
        # Configura velocidade alta para otimização rápida
        mpc.set_polarisation_parameters(velocity=90, home_pos=0, jog_step1=10, jog_step2=10, jog_step3=10)

        # Instancia e roda o compensador
        compensator = PolarizationCompensator(mpc)
        compensator.run_full_algorithm()

    except Exception as e:
        print(f"ERRO: {e}")
    finally:
        if mpc: 
            mpc.close()
        qmi_context.stop()
        print("Conexão encerrada.")

if __name__ == "__main__":
    main()