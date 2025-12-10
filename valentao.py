from mpi4py import MPI
import pygame
import math
import sys
import random 

# Configurações do MPI
# Pega o comunicador global (todos os processos)
comm = MPI.COMM_WORLD
# Pega o ID deste processo específico (0, 1, 2...)
rank = comm.Get_rank()
# Pega o total de processos rodando
size = comm.Get_size()

# Tags
# Define os códigos de mensagem para saber o que fazer quando receber algo
TAG_KILL = 1      
TAG_STATUS = 2     
TAG_STEP = 3      
TAG_ELECTION = 4  
TAG_OK = 5        
TAG_COORD = 6     
TAG_PING = 7       
TAG_PONG = 8       
TAG_STATE_UI = 10
TAG_REVIVE = 11    # Nova tag pra reviver processo morto

# Cores
# Define as cores RGB pra usar no desenho
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 50, 50)
GREEN = (50, 200, 50)
BLUE = (50, 50, 200)
REVIVE_CYAN = (0, 150, 150)
GRAY_ARROW = (200, 200, 200) 
GOLD = (255, 215, 0)

# Função auxiliar pra desenhar a setinha na tela
# Calcula o angulo entre dois pontos e desenha um triângulo na ponta da linha
def draw_arrow(screen, color, start, end, thickness=2):
    # Desenha a linha principal
    pygame.draw.line(screen, color, start, end, thickness)
    # Calcula a rotação da linha em radianos
    rotation = math.atan2(start[1] - end[1], start[0] - end[0])
    # Tamanho da ponta da seta
    arrow_len = 15
    # Angulo de abertura da ponta
    angle = math.pi / 6
    # Define o ponto final da linha como o bico da seta
    p1 = end
    # Calcula os outros dois pontos do triângulo da seta usando seno e cosseno
    p2 = (end[0] + arrow_len * math.cos(rotation + angle),
          end[1] + arrow_len * math.sin(rotation + angle))
    p3 = (end[0] + arrow_len * math.cos(rotation - angle),
          end[1] + arrow_len * math.sin(rotation - angle))
    # Desenha o triângulo preenchido
    pygame.draw.polygon(screen, color, [p1, p2, p3])

# ==========================================
# LÓGICA DO MESTRE (INTERFACE GRÁFICA)
# ==========================================
# Essa função roda só no processo 0.
# Ela desenha a tela, os botões e gerencia o clique do mouse.
# Não participa da eleição, só desenha o que os outros mandam.
def run_maestro():
    print("[Maestro] Interface Iniciada.")
    # Inicia o pygame
    pygame.init()
    # Cria um relógio pra controlar o FPS
    clock = pygame.time.Clock()
    
    # Define tamanho da tela e da barra lateral
    WIDTH, HEIGHT = 900, 700 
    SIDEBAR_WIDTH = 250 
    CANVAS_WIDTH = WIDTH - SIDEBAR_WIDTH
    
    # Cria a janela
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Algoritmo do Valentão - MPI")
    
    # Carrega as fontes pra escrever texto
    font_node = pygame.font.SysFont('Arial', 20, bold=True)
    font_state = pygame.font.SysFont('Arial', 14, bold=True)
    font_ui = pygame.font.SysFont('Arial', 16)
    font_legend = pygame.font.SysFont('Arial', 14, bold=True)
    font_title = pygame.font.SysFont('Arial', 22, bold=True)

    # Dicionário pra guardar se cada processo tá vivo ou morto
    process_states = {i: True for i in range(1, size)}
    # Dicionário pro texto que aparece em cima da bolinha
    process_labels = {i: "Iniciando..." for i in range(1, size)}
    # Lista pra guardar as setas que tem que desenhar nesse frame
    active_arrows = []
    
    # Configura cores e variáveis de layout
    GRAY_PANEL = (50, 50, 60)
    BTN_KILL_COLOR = (200, 80, 80)
    BTN_DISABLED = (100, 100, 100)
    COLOR_ELECTION = (255, 140, 0)   
    COLOR_OK = (0, 191, 255)         
    COLOR_COORD = (255, 215, 0)      

    # Calcula onde cada bolinha vai ficar no circulo
    radius = 180
    center = (CANVAS_WIDTH // 2, HEIGHT // 2)
    node_positions = {}
    num_workers = size - 1
    for i in range(num_workers):
        # Matemática de circulo pra distribuir os pontos
        angle = (2 * math.pi * i / num_workers) - (math.pi / 2)
        x = center[0] + int(radius * math.cos(angle))
        y = center[1] + int(radius * math.sin(angle))
        node_positions[i + 1] = (x, y)

    # Cria o retângulo do botão de próximo passo
    btn_step_rect = pygame.Rect(WIDTH - SIDEBAR_WIDTH + 15, HEIGHT - 80, 220, 50)
    # Cria a lista de botões de matar/reviver na lateral
    kill_buttons = []
    start_y = 100
    for i in range(1, size):
        rect = pygame.Rect(WIDTH - SIDEBAR_WIDTH + 25, start_y + (i-1)*50, 200, 40)
        kill_buttons.append({'rank': i, 'rect': rect})

    running = True
    comm.Barrier()
    # Loop principal da interface
    while running:
        # Verifica se tem mensagem chegando sem travar a tela
        while comm.Iprobe(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG):
            status = MPI.Status()
            # Espia a mensagem pra saber quem mandou e qual a tag
            comm.Probe(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status)
            tag = status.Get_tag()
            source = status.Get_source()

            # Se for aviso de status (morreu, reviveu, desenha seta)
            if tag == TAG_STATUS:
                msg = comm.recv(source=source, tag=TAG_STATUS)
                if msg == "DIED":
                    # Marca como morto no visual
                    process_states[source] = False
                    process_labels[source] = "MORTO"
                elif msg == "REVIVED": 
                    # Marca como vivo no visual
                    process_states[source] = True
                    process_labels[source] = "Revivendo..."
                # Se for pedido pra desenhar seta
                elif isinstance(msg, tuple) and msg[0] == "DRAW":
                    _, target, m_type = msg
                    # Pega posições de origem e destino
                    start_pos = node_positions[source]
                    end_pos = node_positions[target]
                    # Calcula vetor pra encurtar a linha e não entrar na bolinha
                    dx = end_pos[0] - start_pos[0]
                    dy = end_pos[1] - start_pos[1]
                    dist = math.hypot(dx, dy)
                    offset = 35 # Distancia pra parar antes do centro
                    if dist > 0:
                        new_end = (end_pos[0] - (dx/dist)*offset, end_pos[1] - (dy/dist)*offset)
                        new_start = (start_pos[0] + (dx/dist)*offset, start_pos[1] + (dy/dist)*offset)
                    else:
                        new_end, new_start = end_pos, start_pos

                    # Guarda a seta pra desenhar depois
                    active_arrows.append({'start': new_start, 'end': new_end, 'type': m_type})

            # Se for atualização de texto de estado (Lider, Eleição...)
            elif tag == TAG_STATE_UI:
                msg = comm.recv(source=source, tag=TAG_STATE_UI)
                process_labels[source] = msg
            # Se for qualquer outra coisa, só consome pra limpar o buffer
            else:
                comm.recv(source=source, tag=tag)

        # Preenche fundo branco
        screen.fill(WHITE)
        # Desenha a barra lateral cinza
        pygame.draw.rect(screen, GRAY_PANEL, (CANVAS_WIDTH, 0, SIDEBAR_WIDTH, HEIGHT))
        # Escreve titulo na barra
        title_surf = font_title.render("Painel de Controle", True, WHITE)
        screen.blit(title_surf, (CANVAS_WIDTH + 20, 30))

        # Desenha os botões de matar/reviver
        for btn in kill_buttons:
            p_rank = btn['rank']
            is_alive = process_states[p_rank]
            
            # Troca cor e texto se ta vivo ou morto
            if is_alive:
                color = BTN_KILL_COLOR
                txt_str = f"Matar {p_rank}"
            else:
                color = REVIVE_CYAN
                txt_str = f"Reviver {p_rank}"

            # Desenha o retangulo e o texto do botão
            pygame.draw.rect(screen, color, btn['rect'], border_radius=8)
            text = font_ui.render(txt_str, True, WHITE)
            text_rect = text.get_rect(center=btn['rect'].center)
            screen.blit(text, text_rect)

        # Desenha botão de proximo passo
        pygame.draw.rect(screen, BLUE, btn_step_rect, border_radius=8)
        step_text = font_node.render("PRÓXIMO PASSO >", True, WHITE)
        text_rect = step_text.get_rect(center=btn_step_rect.center)
        screen.blit(step_text, text_rect)

        # Desenha a legenda de cores
        legend_x = 20
        legend_y = HEIGHT - 110
        # Fundo da legenda
        pygame.draw.rect(screen, (245, 245, 245), (legend_x - 10, legend_y - 10, 180, 100), border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), (legend_x - 10, legend_y - 10, 180, 100), 1, border_radius=5)
        # Itens da legenda
        items = [("Eleição", COLOR_ELECTION), ("Resposta OK", COLOR_OK), ("Novo Líder", COLOR_COORD), ("Ping Check", GRAY_ARROW)]
        for i, (text, color) in enumerate(items):
            ly = legend_y + i * 22
            pygame.draw.rect(screen, color, (legend_x, ly, 15, 15))
            txt_surf = font_legend.render(text, True, (50, 50, 50))
            screen.blit(txt_surf, (legend_x + 25, ly))

        # Desenha as linhas pretas conectando o anel
        point_list = list(node_positions.values())
        if len(point_list) > 1:
            pygame.draw.lines(screen, BLACK, True, point_list, 2)

        # Desenha as setas ativas
        for arrow in active_arrows:
            color = COLOR_ELECTION
            if arrow['type'] == "OK": color = COLOR_OK
            if arrow['type'] == "COORD": color = COLOR_COORD
            if arrow['type'] == "PING" or arrow['type'] == "PONG": color = GRAY_ARROW
            draw_arrow(screen, color, arrow['start'], arrow['end'], thickness=2 if color == GRAY_ARROW else 4)

        # Desenha as bolinhas dos processos
        for p_rank, pos in node_positions.items():
            color = GREEN if process_states[p_rank] else RED
            # Circulo colorido e borda preta
            pygame.draw.circle(screen, color, pos, 30)
            pygame.draw.circle(screen, BLACK, pos, 30, 2)
            # Numero do ID dentro da bolinha
            text = font_node.render(str(p_rank), True, BLACK if process_states[p_rank] else WHITE)
            text_rect = text.get_rect(center=pos)
            screen.blit(text, text_rect)
            
            # Texto de estado em cima da bolinha
            label = process_labels.get(p_rank, "")
            text_color = (50, 50, 150)
            if label == "LÍDER": text_color = (180, 140, 0) # Dourado se for lider
            elif label == "MORTO": text_color = RED

            # Renderiza o texto e poe fundo branco semi-transparente
            lbl_surf = font_state.render(label, True, text_color)
            lbl_rect = lbl_surf.get_rect(center=(pos[0], pos[1]-45))
            bg_rect = lbl_rect.inflate(14, 6)
            pygame.draw.rect(screen, (255, 255, 255, 230), bg_rect, border_radius=5)
            pygame.draw.rect(screen, (200, 200, 200), bg_rect, 1, border_radius=5)
            screen.blit(lbl_surf, lbl_rect)

        # Processa eventos do Pygame (cliques e fechar janela)
        for event in pygame.event.get():
            # Se clicar no X, fecha tudo
            if event.type == pygame.QUIT:
                running = False
                # Manda todos os processos saírem
                for i in range(1, size): comm.send("EXIT", dest=i, tag=TAG_KILL)
            
            # Se clicou com mouse
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                # Se clicou no botão Step
                if btn_step_rect.collidepoint(mx, my):
                    active_arrows.clear() # Limpa setas antigas
                    # Manda sinal de passo pra todo mundo que ta vivo
                    for i in range(1, size):
                        if process_states[i]: comm.send("STEP", dest=i, tag=TAG_STEP)
                
                # Se clicou num botão lateral
                for btn in kill_buttons:
                    if btn['rect'].collidepoint(mx, my):
                        p_rank = btn['rank']
                        # Se ta vivo manda morrer, se ta morto manda reviver
                        if process_states[p_rank]: 
                            comm.send("DIE", dest=p_rank, tag=TAG_KILL)
                        else:
                            comm.send("REVIVE", dest=p_rank, tag=TAG_REVIVE)
        
        # Atualiza a tela
        pygame.display.flip()
        # Segura em 60 FPS
        clock.tick(60)
    pygame.quit()

# ==========================================
# LÓGICA DO TRABALHADOR
# ==========================================
# Essa função roda nos processos 1 a N.
# É aqui que a mágica do algoritmo acontece.
def run_worker():
    alive = True
    # Assume que o maior ID é o lider no começo
    current_leader = size - 1 
    
    # Constantes pra máquina de estado
    STATE_NORMAL = 0
    STATE_ELECTION = 1    
    STATE_WAITING = 2     
    
    # Estado inicial
    my_state = STATE_NORMAL
    patience_timer = 0
    # Fila de ações pra executar (envia msg, inicia eleição...)
    action_queue = []
    # Caixa de entrada pra guardar mensagens que chegam fora de hora
    mailbox = []

    # Configuração do Vigia (Processo 1)
    check_counter = 1
    waiting_pong = False
    ping_wait_timer = 0 
    heartbeat_cooldown = 0 

    # Funçãozinha pra facilitar mandar texto pra interface
    def update_status_gui(text):
        comm.send(text, dest=0, tag=TAG_STATE_UI)

    # Já avisa a interface quem sou eu no começo
    if rank == current_leader: update_status_gui("LÍDER")
    else: update_status_gui("Normal")
    comm.Barrier()
    # Loop principal do processo
    while True:
        status = MPI.Status()
        # TRAVA AQUI: Espera chegar qualquer mensagem pra continuar
        msg = comm.recv(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status)
        tag = status.Get_tag()
        source = status.Get_source()

        # 1. ORDEM DE MORTE
        # Se mandaram morrer, desliga a flag e avisa interface
        if tag == TAG_KILL:
            if msg == "EXIT": break # Fecha o programa
            if msg == "DIE":
                alive = False
                comm.send("DIED", dest=0, tag=TAG_STATUS)
        
        # 2. ORDEM DE REVIVER
        # Única coisa que processa se estiver morto
        if tag == TAG_REVIVE:
            alive = True
            # Reseta tudo pra estado inicial
            my_state = STATE_NORMAL
            action_queue = []
            mailbox = []
            waiting_pong = False
            
            # Truque: não sei quem é lider, então vou forçar eleição
            current_leader = -1 
            
            # Avisa que voltou
            comm.send("REVIVED", dest=0, tag=TAG_STATUS)
            # Agenda eleição na hora
            action_queue.append(("START_ELECTION", None))

        # Se ta morto, ignora o resto e volta pro topo esperar msg
        if not alive: continue

        # Guarda mensagens de jogo na caixa de correio pra ler depois
        if tag in [TAG_ELECTION, TAG_OK, TAG_PING, TAG_PONG, TAG_COORD]:
            mailbox.append((tag, source))
            # Se tem agito na rede, para de fiscalizar o lider por um tempo
            if tag in [TAG_ELECTION, TAG_OK, TAG_COORD]:
                heartbeat_cooldown = 10 
                waiting_pong = False

        # Se chegou a ordem de dar um passo
        if tag == TAG_STEP:
            received_pong = False
            
            oks_to_send = []
            trigger_election = False
            
            # --- FASE A: LER CAIXA DE CORREIO ---
            # Processa tudo que chegou desde o ultimo passo
            while mailbox:
                m_tag, m_source = mailbox.pop(0)
                
                # Se alguém virou lider
                if m_tag == TAG_COORD:
                    current_leader = m_source
                    my_state = STATE_NORMAL
                    patience_timer = 0
                    waiting_pong = False
                    action_queue.clear() # Limpa pendencias, paz reinou
                    
                    if rank == current_leader: update_status_gui("LÍDER")
                    else: update_status_gui("Normal")
                    heartbeat_cooldown = 1 # Da um tempinho pro novo lider respirar
                
                # Se recebi OK (alguem maior ta vivo)
                elif m_tag == TAG_OK:
                    if my_state == STATE_ELECTION:
                        my_state = STATE_WAITING # Paro de tentar ser lider
                        patience_timer = 0
                        update_status_gui("Aguardando...")
                
                # Se alguém pediu eleição
                elif m_tag == TAG_ELECTION:
                    # Guarda pra responder OK depois tudo junto
                    oks_to_send.append(m_source)
                    # Se eu to de boa e não sou lider, entro na briga tbm
                    if (my_state == STATE_NORMAL or my_state == STATE_WAITING):
                         if rank != current_leader:
                             trigger_election = True
                
                # Se recebi Ping (só acontece se eu for lider e tiver vivo)
                elif m_tag == TAG_PING:
                    if alive: action_queue.append( ("SEND_PONG", m_source) )
                
                # Se recebi Pong (resposta do lider)
                elif m_tag == TAG_PONG:
                    received_pong = True

            # --- PREPARAR AÇÕES ---
            # Se tenho OKs pra mandar, agendo envio em lote
            if oks_to_send:
                action_queue.append( ("SEND_OK_BATCH", oks_to_send) )
            
            # Se preciso iniciar eleição, agendo (sem duplicar)
            if trigger_election:
                 already_planned = False
                 for a in action_queue: 
                     if a[0] == "START_ELECTION": already_planned = True
                 if not already_planned:
                     action_queue.append( ("START_ELECTION", None) )

            # --- FASE B: EXECUTAR AÇÃO ---
            # Executa UMA ação da fila por vez pro visual ficar passo-a-passo
            if action_queue:
                action_tuple = action_queue.pop(0)
                action_type = action_tuple[0]
                
                # Manda OK pra todo mundo da lista
                if action_type == "SEND_OK_BATCH":
                    targets = action_tuple[1]
                    for t in targets:
                        comm.send(("DRAW", t, "OK"), dest=0, tag=TAG_STATUS)
                        comm.send("OK", dest=t, tag=TAG_OK)
                
                # Manda Pong de volta
                elif action_type == "SEND_PONG":
                    target = action_tuple[1]
                    comm.send(("DRAW", target, "PONG"), dest=0, tag=TAG_STATUS)
                    comm.send("PONG", dest=target, tag=TAG_PONG)

                # Começa minha eleição
                elif action_type == "START_ELECTION":
                    if my_state != STATE_ELECTION:
                        my_state = STATE_ELECTION
                        patience_timer = 3 # Espero 1 rodada
                        update_status_gui("Eleição") 
                        
                        # Manda eleição pra todo mundo maior que eu
                        sent_to_anyone = False
                        for t in range(rank + 1, size):
                            comm.send(("DRAW", t, "ELECTION"), dest=0, tag=TAG_STATUS)
                            comm.isend("ELECTION", dest=t, tag=TAG_ELECTION)
                            sent_to_anyone = True
                        
                        # Se não tem ninguem maior, ganho na hora
                        if not sent_to_anyone: patience_timer = 0 
            
            # --- FASE C: LÓGICA DE ESTADO ---
            else:
                # 1. Lógica de Timeout da Eleição
                if my_state == STATE_ELECTION:
                    if patience_timer > 0:
                        patience_timer -= 1 # Espera...
                    else:
                        # Ganhei! Sou o novo Lider
                        current_leader = rank
                        update_status_gui("LÍDER")
                        # Aviso todo mundo
                        for t in range(1, size):
                            if t != rank:
                                comm.send(("DRAW", t, "COORD"), dest=0, tag=TAG_STATUS)
                                comm.send("COORD", dest=t, tag=TAG_COORD)
                        my_state = STATE_NORMAL

                # 2. Heartbeat (Só o Processo 1 faz isso)
                if rank == 1 and my_state == STATE_NORMAL and current_leader != rank and current_leader != -1:
                    # Se tiver em cooldown, espera
                    if heartbeat_cooldown > 0:
                        heartbeat_cooldown -= 1
                    else:
                        # Se estava esperando resposta...
                        if waiting_pong:
                            if received_pong:
                                # Recebeu! Tudo certo.
                                waiting_pong = False
                                update_status_gui("Normal")
                                check_counter = 1
                            else:
                                # Não recebeu. Espera mais um pouco pela latencia?
                                if ping_wait_timer > 0:
                                    ping_wait_timer -= 1
                                else:
                                    # Desistiu. Lider morreu. Inicia eleição.
                                    waiting_pong = False
                                    action_queue.append(("START_ELECTION", None))
                        else:
                            # Hora de checar?
                            if check_counter > 0:
                                check_counter -= 1
                            else:
                                # Manda o Ping
                                update_status_gui("Checando...")
                                comm.send(("DRAW", current_leader, "PING"), dest=0, tag=TAG_STATUS)
                                comm.isend("PING", dest=current_leader, tag=TAG_PING)
                                waiting_pong = True
                                ping_wait_timer = 1

# Ponto de entrada do script
if __name__ == "__main__":
    if size < 2:
        print("Erro: Precisa de 2 processos")
        sys.exit(1)
    if rank == 0: run_maestro() # Processo 0 vira tela
    else: run_worker() # Outros viram workers