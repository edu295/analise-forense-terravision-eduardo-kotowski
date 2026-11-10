# TerraVision vs. Google Earth: como um mapa 3D decide o que mostrar na costa

**Aluno:** Eduardo Gabriel da Silva Kotowski · **Nº:** 3 · **Turma:** 3°D – DS
**Tema 3:** Regiões Litorâneas e Dinâmica Oceânica (Linha de Costa/Erosão)
**Disciplinas integradas:** Ciência de Dados & Computação Gráfica

---

## A ideia do trabalho

Quando a gente abre o Google Earth e dá zoom em uma praia, parece que o programa tem a Terra inteira em alta resolução guardada em algum lugar. Na verdade, ele não tem como carregar tudo ao mesmo tempo: a memória do computador não aguenta. O truque, que já aparecia no TerraVision lá nos anos 90, é carregar **só o detalhe que a câmera consegue enxergar naquele momento**. Isso se chama **Level of Detail (LoD)**.

Neste projeto eu escolhi a costa porque ela é um caso difícil: a linha entre terra e mar é cheia de curvas, então a diferença entre ver "um borrão" e ver "a praia de verdade" é muito clara. Fiz um programa em Python que simula uma câmera descendo de 5000 km até 5 km de altitude e mostra o que acontece com a imagem e com a memória.

---

## Etapa 1: o algoritmo (`script.py`)

### O que o código faz, passo a passo

1. **Cria uma costa fictícia.** Como não dá para baixar imagem de satélite real sem internet, o programa gera um terreno com relevo aleatório (várias camadas de ruído somadas). Valores acima de zero são terra, abaixo de zero são mar.
2. **Escolhe o nível de detalhe pela altitude.** A função `carregar_camada_satelite()` usa `if/elif/else`:

   | Altitude da câmera | Nível | Resolução carregada |
   |---|---|---|
   | ≥ 1000 km | LoD 0 – Global | 16×16 |
   | 200 a 999 km | LoD 1 – Regional | 48×48 |
   | 30 a 199 km | LoD 2 – Local | 160×160 |
   | < 30 km | LoD 3 – Detalhe | 512×512 |

3. **Valida a altitude.** Se alguém passar um valor negativo, zero, texto ou algo acima de 40 000 km, a função levanta um `ValueError` com uma mensagem clara, e o programa continua rodando em vez de travar.
4. **Desenha tudo e salva uma imagem** (`renderizacao_lod.png`) com os quatro níveis lado a lado e um gráfico do consumo de memória.

### Como rodar

```bash
pip install numpy matplotlib
python script.py
```

O terminal mostra os testes de validação e, no fim, a imagem é salva na mesma pasta.

---

## Resultado: a imagem que o código renderiza

![Renderização dos 4 níveis de LoD e consumo de memória](renderizacao_lod.png)

*Figura 1: saída do `script.py`. Em cima, a mesma costa vista em quatro altitudes; a linha branca é a linha de costa. Embaixo, a memória que cada camada usa (escala logarítmica).*

### O que dá para observar

- No **LoD 0** a costa vira uma escada de quadrados. Dá para saber onde é terra e onde é mar, mas nada além disso.
- No **LoD 1 e 2** as baías e a faixa de areia começam a aparecer.
- No **LoD 3** surgem até as ilhotas pequenas no canto inferior, que simplesmente não existiam nos níveis anteriores.
- O custo disso: o LoD 3 usa cerca de **1000 vezes mais memória** que o LoD 0 (1 MB contra 0,001 MB, para uma única camada). Se o programa carregasse o LoD 3 do planeta inteiro, ficaria inviável. Por isso o `if/elif/else` é tão importante.

---

## Etapa 2: Computação Gráfica e UX/UI

### 1. Costurando imagens de satélite no litoral (stitching e texturas)

Juntar fotos de satélite é mais difícil no mar do que em terra firme, por três motivos:

- **Reflexo do sol na água (*specular glare*).** Dependendo do ângulo do satélite, a água fica com manchas brilhantes. Duas fotos vizinhas, tiradas em horários diferentes, podem ter cores bem diferentes no mesmo mar, e a emenda aparece.
- **A água não fica parada.** Maré, ondas e espuma mudam a faixa de areia visível de uma foto para outra. É preciso suavizar a transição (*blending*) para a emenda não virar uma linha reta no meio da praia.
- **Gradiente de profundidade e sedimentos.** O azul-escuro do mar profundo vai virando turquesa perto da costa, e nas fozes de rios a água fica turva. Se a transição de cores for mal feita, aparecem faixas e artefatos de compressão.

### 2. Design da interface e Leis da Gestalt

Navegando pelo Google Earth no litoral, percebi duas leis da Gestalt em ação:

- **Figura-fundo:** o mar, grande e de cor uniforme, funciona como fundo. Por isso o contorno do continente, a malha urbana e a linha de praia se destacam como figura.
- **Continuidade:** a linha de costa é um traçado contínuo e o olhar segue ela naturalmente. Isso ajuda a "caminhar" pelo litoral procurando pontos de erosão.

O contraste forte entre mar e areia também guia o zoom. Conforme me aproximo, a textura das ondas e o relevo aparecem, e isso me avisa que o programa carregou um nível de detalhe maior. Ou seja, a própria imagem funciona como feedback para o usuário.

### 3. Evidência visual no Google Earth

![Pontal de Atafona no Google Earth](imagem_costa.png)

*Figura 2: captura de tela do Google Earth no Pontal de Atafona (São João da Barra, RJ). Dá para ver a foz do Rio Paraíba do Sul, a pluma de sedimentos na água, as ondas e o avanço da erosão sobre a área urbana.*

Atafona é um exemplo forte para o tema: o mar já levou várias ruas da cidade. Esse é o tipo de caso em que ver a costa com detalhe, em níveis de LoD mais altos, faz diferença real para estudar erosão.

---

## Conexão forense: TerraVision vs. Google Earth

No Episódio 4, durante a perícia do código no tribunal, o ponto central era que carregar dados geoespaciais em tempo real depende de **condicionais eficientes**. É exatamente o que o `carregar_camada_satelite()` faz: antes de gastar RAM/VRAM, ele decide qual resolução realmente precisa ser carregada. Sem isso, renderizar oceanos e costas do planeta inteiro estrangularia a memória. O Google Earth moderno usa a mesma lógica, só que com muito mais níveis e dados reais.

## Limitações

- O terreno é **sintético**, não são dados reais de satélite. Serve para demonstrar a lógica de LoD, não para medir erosão de verdade.
- Os limites de altitude (1000, 200 e 30 km) são valores que eu escolhi para a demonstração.
- O consumo de memória é uma estimativa simples (4 bytes por pixel, camada RGBA de 8 bits).

## Histórico de commits

- `feat: estrutura inicial do repositorio e README.md`
- `feat(script): criacao da funcao carregar_camada_satelite com estruturas condicionais`
- `docs(readme): insercao da analise de processamento de imagem e leis da Gestalt`
- `fix(script): tratamento de excecoes para validacao das altitudes`
- `docs(readme): inclusao do item 3 (evidencia visual) e historico de commits`
- `feat(script): renderizacao da imagem com matplotlib e grafico de memoria`
- `docs(readme): reescrita do README com resultados e limitacoes`
