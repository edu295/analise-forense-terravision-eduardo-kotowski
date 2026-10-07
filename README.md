# Análise Analítica Forense e Computação Gráfica - TerraVision vs. Google Earth

- **Aluno:** Eduardo Gabriel da Silva Kotowski
- **Número:** 3
- **Turma:** 3°D - DS
- **Tema Designado:** Regiões Litorâneas e Dinâmica Oceânica (Linha de Costa/Erosão)
- **Disciplinas Integradas:** Ciência de Dados & Computação Gráfica

---

##  Etapa 1: Algoritmo em Python
O código desenvolvido no arquivo `script.py` implementa a técnica de **Level of Detail (LoD)**, alternando a resolução dos dados geoespaciais conforme a aproximação da câmera virtual em regiões litorâneas.

---

## Etapa 2: Análise de Computação Gráfica & UX/UI

### 1. Processamento e Tratamento de Imagem (Stitching e Texturas)
Ao renderizar e realizar a "costura" (*stitching*) de imagens de satélite em regiões litorâneas e oceânicas, os algoritmos enfrentam os seguintes desafios técnicos:

- **Reflexo Especular da Água (*Specular Glare*):** A luz solar reflete na água de forma variável dependendo da posição do satélite. Isso causa manchas brilhantes e desalinhamento de cores ao costurar fotos vizinhas tiradas em horários diferentes.
- **Dinâmica de Marés e Ondas:** Como a água está em constante movimento, imagens capturadas em momentos distintos apresentam variações na faixa de areia visível, espumas de ondas e turbidez, exigindo algoritmos de suavização (*blending*).
- **Gradiente de Profundidade:** Transicionar suavemente as cores do oceano profundo (azul escuro) para a costa rasa (verde-água/turquesa) sem criar bordas bruscas ou artefatos de compressão na textura.

### 2. Design de Interface e Leis da Gestalt
Ao observar a navegação no Google Earth para o mapeamento litorâneo, identificamos as seguintes Leis da Gestalt:

- **Lei da Figura-Fundo (Figure-Ground):** A grande massa de água azul atua como o **fundo**, permitindo que o contorno da massa terrestre e a linha de praia emergam claramente como a **figura** principal em foco.
- **Lei da Continuidade (Continuity):** A linha de costa cria um traçado contínuo que o olho humano segue naturalmente. Isso facilita navegar ao longo do litoral procurando focos de erosão ou alterações no desenho da praia.

**Orientação da Atenção do Usuário:** O contraste visual forte entre o azul do mar e o tom de terra/areia guia o movimento do zoom de forma intuitiva. Ao aproximar, o relevo costeiro e as texturas das ondas indicam claramente o nível de detalhamento alcançado pelo software.

---

## 📸 Evidência Visual (Captura de Tela)
![Linha de Costa no Google Earth](imagem_costa.png)
*Figura 1: Captura de tela do Google Earth demonstrando a dinâmica de linha de costa e erosão litorânea.*
