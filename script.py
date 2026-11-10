"""
Analise Forense TerraVision - Level of Detail (LoD) em regioes litoraneas
Aluno: Eduardo Gabriel da Silva Kotowski

O que o script faz:
1. Gera um terreno costeiro sintetico (terra, mar e linha de costa).
2. Simula a camera descendo de 5000 km ate 5 km de altitude.
3. Para cada altitude, carregar_camada_satelite() decide, com if/elif/else,
   qual nivel de detalhe (LoD) carregar.
4. Renderiza tudo em uma imagem (renderizacao_lod.png) e mostra quanta
   memoria cada LoD consome.

Uso:
    pip install numpy matplotlib
    python script.py
"""

import numpy as np
import matplotlib

matplotlib.use("Agg")  # permite salvar a imagem sem abrir janela
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

TAMANHO_BASE = 512        # resolucao maxima do terreno (512 x 512)
NIVEL_DO_MAR = 0.0
ARQUIVO_SAIDA = "renderizacao_lod.png"

# Tabela de LoD: nome, resolucao (pixels por lado)
LOD = {
    0: ("LoD 0 - Global", 16),
    1: ("LoD 1 - Regional", 48),
    2: ("LoD 2 - Local", 160),
    3: ("LoD 3 - Detalhe", 512),
}


# ----------------------------------------------------------------------
# 1. Terreno costeiro sintetico
# ----------------------------------------------------------------------
def _ruido_octava(rng, n, celulas):
    """Ruido suave: grade aleatoria pequena ampliada com interpolacao bilinear."""
    grade = rng.random((celulas + 1, celulas + 1))
    x = np.linspace(0, celulas, n)
    i = np.clip(x.astype(int), 0, celulas - 1)
    f = x - i
    # interpola nas linhas e depois nas colunas
    linhas = grade[i, :] * (1 - f)[:, None] + grade[i + 1, :] * f[:, None]
    return linhas[:, i] * (1 - f)[None, :] + linhas[:, i + 1] * f[None, :]


def gerar_terreno(n=TAMANHO_BASE, semente=7):
    """Gera um mapa de altitudes: valores > 0 sao terra, < 0 sao mar."""
    rng = np.random.default_rng(semente)
    terreno = np.zeros((n, n))
    amplitude = 1.0
    for celulas in (3, 6, 12, 24, 48, 96):   # cada oitava adiciona mais detalhe
        terreno += amplitude * _ruido_octava(rng, n, celulas)
        amplitude *= 0.5
    terreno = (terreno - terreno.mean()) / terreno.std()

    # inclinacao: terra a esquerda, oceano a direita (forma uma linha de costa)
    inclinacao = np.linspace(1.4, -1.4, n)[None, :]
    return terreno * 0.6 + inclinacao


# ----------------------------------------------------------------------
# 2. Logica de LoD (estruturas condicionais)
# ----------------------------------------------------------------------
def carregar_camada_satelite(altitude_km, terreno):
    """
    Escolhe o nivel de detalhe conforme a altitude da camera e devolve
    (nivel, nome, camada_reduzida).

    Levanta ValueError se a altitude for invalida.
    """
    if not isinstance(altitude_km, (int, float)) or isinstance(altitude_km, bool):
        raise ValueError(f"Altitude deve ser numerica, recebido: {altitude_km!r}")
    if altitude_km <= 0:
        raise ValueError(f"Altitude deve ser positiva, recebido: {altitude_km}")
    if altitude_km > 40000:
        raise ValueError(f"Altitude acima da orbita suportada: {altitude_km} km")

    # quanto mais alto, menos detalhe e carregado
    if altitude_km >= 1000:
        nivel = 0
    elif altitude_km >= 200:
        nivel = 1
    elif altitude_km >= 30:
        nivel = 2
    else:
        nivel = 3

    nome, resolucao = LOD[nivel]
    camada = reduzir_resolucao(terreno, resolucao)
    return nivel, nome, camada


def reduzir_resolucao(terreno, resolucao):
    """Reduz o terreno para resolucao x resolucao pela media de cada bloco."""
    n = terreno.shape[0]
    bloco = n // resolucao
    recorte = terreno[: resolucao * bloco, : resolucao * bloco]
    return recorte.reshape(resolucao, bloco, resolucao, bloco).mean(axis=(1, 3))


def memoria_mb(resolucao):
    """Memoria aproximada de uma camada RGBA de 8 bits (4 bytes por pixel)."""
    return resolucao * resolucao * 4 / (1024 * 1024)


# ----------------------------------------------------------------------
# 3. Renderizacao
# ----------------------------------------------------------------------
def criar_paleta():
    """Azul escuro (fundo do mar) -> turquesa (raso) -> areia -> verde (terra)."""
    cores = [
        (0.00, "#06223d"),
        (0.38, "#1a6a8f"),
        (0.49, "#5fc7c0"),
        (0.50, "#e8d9a0"),
        (0.56, "#6b9a4f"),
        (1.00, "#2f5a2a"),
    ]
    return LinearSegmentedColormap.from_list("costa", cores)


def renderizar(terreno, altitudes, arquivo=ARQUIVO_SAIDA):
    paleta = criar_paleta()
    limite = np.abs(terreno).max()
    kwargs_mapa = dict(cmap=paleta, vmin=-limite, vmax=limite, interpolation="nearest")

    fig = plt.figure(figsize=(14, 8.5), facecolor="white")
    grade = fig.add_gridspec(2, 4, height_ratios=[1.5, 1], hspace=0.35, wspace=0.12)

    consumo = []
    for coluna, altitude in enumerate(altitudes):
        try:
            nivel, nome, camada = carregar_camada_satelite(altitude, terreno)
        except ValueError as erro:
            print(f"[erro] {erro}")
            continue

        resolucao = camada.shape[0]
        consumo.append((altitude, nivel, memoria_mb(resolucao)))

        ax = fig.add_subplot(grade[0, coluna])
        ax.imshow(camada, **kwargs_mapa)
        # linha de costa: contorno onde a altitude cruza o nivel do mar
        ax.contour(camada, levels=[NIVEL_DO_MAR], colors="white", linewidths=1.2)
        ax.set_title(f"{nome}\n{altitude:g} km  |  {resolucao}x{resolucao} px", fontsize=11)
        ax.set_xticks([])
        ax.set_yticks([])

    # grafico inferior: memoria usada por LoD
    ax2 = fig.add_subplot(grade[1, :])
    if consumo:
        rotulos = [f"{a:g} km\n(LoD {n})" for a, n, _ in consumo]
        valores = [m for _, _, m in consumo]
        barras = ax2.bar(rotulos, valores, color="#1a6a8f")
        for barra, valor in zip(barras, valores):
            ax2.text(barra.get_x() + barra.get_width() / 2, valor,
                     f"{valor:.3f} MB", ha="center", va="bottom", fontsize=10)
        ax2.set_yscale("log")
        ax2.set_ylabel("Memoria da camada (MB, escala log)")
        ax2.set_title("Custo de memoria: quanto mais perto, mais detalhe e mais RAM/VRAM",
                      fontsize=11)
        ax2.spines[["top", "right"]].set_visible(False)

    fig.suptitle("TerraVision - Level of Detail em uma linha de costa sintetica",
                 fontsize=15, fontweight="bold")
    fig.savefig(arquivo, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Imagem salva em: {arquivo}")


# ----------------------------------------------------------------------
# 4. Execucao
# ----------------------------------------------------------------------
if __name__ == "__main__":
    terreno = gerar_terreno()

    # demonstracao da validacao: altitudes invalidas sao tratadas sem quebrar
    for teste in (-5, 0, "alto", 99999):
        try:
            carregar_camada_satelite(teste, terreno)
        except ValueError as erro:
            print(f"[validacao ok] {erro}")

    # sobrevoo: a camera desce de 5000 km ate 5 km
    renderizar(terreno, altitudes=[5000, 500, 100, 5])
