# 🌧️ RainTrack – Monitoramento Meteorológico em Tempo Real

Esse é o **Trabalho de Conclusão de Curso (TCC)** desenvolvido com o objetivo de construir um sistema completo de monitoramento climático capaz de coletar, processar e exibir dados ambientais em tempo real.

O sistema utiliza:  
✔ Microcontrolador ESP32  
✔ Protocolo MQTT  
✔ Backend em Python com Flask  
✔ Banco de dados MySQL  
✔ Dashboard interativo para visualização dos dados  

---

## 📋 Índice

- 📌 Sobre o Projeto  
- 🛠 Tecnologias Utilizadas  
- 🚀 Como Funciona  
- ⚙️ Instalação & Configuração  
- ▶️ Como Executar  

---

## 📌 Sobre o Projeto

O RainTrack é um sistema que monitora condições meteorológicas em tempo real, coletando dados como:
- Temperatura  
- Umidade  
- Precipitação  

Esses dados são enviados por um ESP32 ao backend via MQTT, armazenados em um banco de dados e exibidos em um dashboard web intuitivo.

---

## 🛠 Tecnologias Utilizadas

Este projeto foi construído utilizando:

- Python (Flask)  
- MQTT (Eclipse Mosquitto)  
- MySQL  
- ESP32  
- HTML, CSS, JavaScript  
- Highcharts  
- Git & GitHub  

---

## 🚀 Como Funciona

1. O dispositivo **ESP32** lê dados de sensores ambientais  
2. Os dados são enviados via MQTT para o backend  
3. O backend Flask processa e salva no banco MySQL  
4. O usuário visualiza tudo no dashboard web  

---

## ⚙️ Instalação & Configuração

### 1) Pré-requisitos

Antes de começar, instale:

- Python 3.7+  
- MySQL ou MariaDB  
- Mosquitto MQTT Broker  
- Git  

---

### 2) Clone o Repositório
  ```bash
  git clone https://github.com/igorcsouzaa/RainTrack.git
  cd RainTrack
  ```

---

### 3) Configurar o Ambiente Python

Crie um ambiente virtual e instale as dependências:
```bash
python -m venv venv
venv\Scripts\activate # Windows
source venv/bin/activate # Mac / Linux
pip install -r requirements.txt
```

---

### 4) Configuração do Banco de Dados

1. Crie um banco MySQL (ex: `raintrack_db`)
2. Configure usuário e senha
3. Atualize os dados no arquivo de configuração (ex: `config.py`)

---

### 5) Configuração MQTT

1. Instale o broker Mosquitto  
2. Garanta que ele esteja rodando localmente  
3. Atualize as configurações de host e porta no backend  

---

## ▶️ Como Executar

### Backend Python
  ```bash
  flask run
  ```

Acesse no navegador:

http://localhost:5000
