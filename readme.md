# Simulação do Algoritmo do Valentão com MPI

Este projeto é uma implementação didática e visual do **Algoritmo de Eleição do Valentão** em sistemas distribuídos, utilizando **Python**, **MPI (Message Passing Interface)** para comunicação entre processos e **Pygame** para visualização gráfica do estado do sistema.

O objetivo é demonstrar como processos autônomos em uma rede podem coordenar a eleição de um líder e lidar com falhas de nós e latência de rede de forma assíncrona.

---

## 🛠️ Tecnologias Utilizadas

* **Python 3.x**
* **mpi4py:** Biblioteca para implementação do padrão MPI em Python.
* **Pygame:** Biblioteca para renderização da interface gráfica.
* **MS-MPI (Windows) / OpenMPI (Linux):** Implementação do protocolo MPI.

---

## 📋 Pré-requisitos

### 1. Instalar o MPI no Sistema
* **Windows:** Baixe e instale o [MS-MPI v10.0](https://www.microsoft.com/en-us/download/details.aspx?id=100593) (`msmpisetup.exe` e `msmpisdk.exe`).
* **Linux (Ubuntu/Debian):**
    sudo apt-get install mpich

### 2. Instalar Dependências Python
Execute no terminal:
    pip install mpi4py pygame

---

## 🚀 Como Rodar

Para iniciar a simulação, utilize o comando `mpiexec`. Recomenda-se entre 5 e 8 processos.

No terminal, dentro da pasta do projeto:
    mpiexec -n 8 python valentao.py

*Isso iniciará 8 processos: Rank 0 (Maestro/GUI) e Ranks 1-7 (Workers).*

---

## 🎮 Como Usar

A simulação é controlada passo-a-passo manualmente.

### 1. Botão "PRÓXIMO PASSO >"
* O sistema é **síncrono por passos**. Nada acontece até você clicar.
* Cada clique processa mensagens pendentes e executa **uma** ação por processo.
* Clique repetidamente para ver o fluxo das mensagens (setas).

### 2. Painel Lateral (Matar / Reviver)
* **Matar (Vermelho):** O processo falha ("MORTO") e para de responder.
* **Reviver (Azul):** O processo retorna. **Nota:** Ao reviver, ele inicia imediatamente uma eleição para se atualizar.

---

## 🎨 Legenda Visual

* 🟠 **Seta Laranja (ELEIÇÃO):** Processo desafiando nós maiores.
* 🔵 **Seta Azul (OK):** Resposta de um nó maior ("Eu assumo").
* 🟡 **Seta Amarela (COORD):** Novo Líder se anunciando.
* ⚪ **Seta Cinza (PING/PONG):** Vigia (Rank 1) checando o Líder.
* 🟢 **Bolinha Verde:** Vivo.
* 🔴 **Bolinha Vermelha:** Morto.

---

## 🧠 Estrutura do Código

* **Rank 0 (Maestro):** Monitor passivo. Recebe `TAG_STATUS` e desenha a tela. Envia `TAG_STEP` para avançar o tempo.
* **Rank > 0 (Workers):** Máquinas de estado independentes.
    * **Mailbox:** Buffer para mensagens recebidas entre passos.
    * **Action Queue:** Fila FIFO para execução sequencial de ações visuais.
    * **Heartbeat:** O Rank 1 atua como detector de falhas do Líder.
