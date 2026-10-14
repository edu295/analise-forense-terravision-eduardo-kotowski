# Análise Analítica Forense e Computação Gráfica - TerraVision vs. Google Earth

- **Aluno:** Eduardo Gabriel da Silva Kotowski
- **Número:** 3
- **Turma:** 3°D - DS
- **Tema Designado:** 3. Regiões Litorâneas e Dinâmica Oceânica (Linha de Costa/Erosão)
- **Disciplinas Integradas:** Ciência de Dados & Computação Gráfica

---

## 💻 Etapa 1: Algoritmo em Python (`script.py`)
O código desenvolvido no ficheiro `script.py` implementa a técnica de **Level of Detail (LoD)**, alterando adaptativamente a resolução dos dados geoespaciais conforme a aproximação da câmara virtual em regiões litorâneas e zonas costeiras.

---

## 🎨 Etapa 2: Análise de Computação Gráfica & UX/UI

### 1. Processamento e Tratamento de Imagem (Stitching e Texturas)
Ao renderizar e realizar a "costura" (*stitching*) de imagens de satélite em regiões litorâneas e oceânicas, os algoritmos enfrentam os seguintes desafios técnicos:

- **Reflexo Especular da Água (*Specular Glare*):** A luz solar reflete na água de forma variável dependendo da posição do satélite. Isso causa manchas brilhantes e desalinhamento de cores ao costurar fotos vizinhas tiradas em horários diferentes.
- **Dinâmica de Marés e Ondas:** Como a água está em constante movimento, imagens capturadas em momentos distintos apresentam variações na faixa de areia visível, espumas de ondas e turbidez, exigindo algoritmos de suavização (*blending*).
- **Gradiente de Profundidade e Sedimentos:** Transicionar suavemente as cores do oceano profundo (azul escuro) para a costa rasa e fozes de rios (verde-água/turquesa e águas turvas com sedimentos) sem criar bordas bruscas ou artefatos de compressão na textura.

### 2. Design de Interface e Leis da Gestalt
Ao observar a navegação no Google Earth para o mapeamento litorâneo, identificamos as seguintes Leis da Gestalt:

- **Lei da Figura-Fundo (Figure-Ground):** A grande massa de água azul/turva atua como o **fundo**, permitindo que o contorno da massa terrestre, a malha urbana e a linha de praia emergam claramente como a **figura** principal em foco.
- **Lei da Continuidade (Continuity):** A linha de costa cria um traçado contínuo que o olho humano segue naturally. Isso facilita navegar ao longo do litoral procurando focos de erosão ou alterações no desenho da praia.

**Orientação da Atenção do Utilizador:** O contraste visual forte entre a cor do mar/rio e o tom de terra/areia guia o movimento do zoom de forma intuitiva. Ao aproximar, o relevo costeiro e as texturas das ondas indicam claramente o nível de detalhamento atingido pelo software.

### 3. Imagens / Evidências Visuais

![Pontal de Atafona no Google Earth](imagem_costa.jpg)

*Figura 1: Captura de ecrã do Google Earth focada no Pontal de Atafona (São João da Barra / RJ), demonstrando a foz do Rio Paraíba do Sul, a turbidez e plumas de sedimentos na água, a dinâmica de ondas e o impacto direto da erosão costeira na malha urbana.*

---

## ⚖️ Conexão Forense (TerraVision vs. Google Earth)
Assim como discutido no Episódio 4 durante a perícia de código do tribunal, a lógica de carregar dados geoespaciais em tempo real depende diretamente de estruturas condicionais eficientes (`if/else`) para evitar o estrangulamento da memória RAM/VRAM ao renderizar grandes superfícies como os oceanos e costas do planeta.

---

## 📜 Histórico de Commits (Git)
- `feat: estrutura inicial do repositorio e README.md`
- `feat(script): criacao da funcao carregar_camada_satelite com estruturas condicionais`
- `docs(readme): insercao da analise de processamento de imagem e leis da Gestalt`
- `fix(script): tratamento de excecoes para validacao das altitudes`
- `docs(readme): inclusao do item 3 (evidencia visual) e historico de commits`
