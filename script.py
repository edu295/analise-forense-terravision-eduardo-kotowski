"""
Analise Forense TerraVision - Level of Detail (LoD) em regioes litoraneas
Aluno: Eduardo Gabriel da Silva Kotowski

O que o script faz:
1. Carrega a imagem real do Google Earth (imagem_costa.png, Pontal de Atafona).
   Se o arquivo nao for encontrado, usa uma costa sintetica no lugar.
2. carregar_camada_satelite() decide, com if/elif/else, qual nivel de detalhe
   (LoD) carregar conforme a altitude da camera.
3. Abre uma janela INTERATIVA: voce da zoom com o mouse (a altitude da camera
   desce e o LoD muda sozinho), arrasta a imagem e ve as ondas da agua se
   moverem em tempo real.
4. Tambem salva um painel estatico (renderizacao_lod.png) com os 4 niveis de
   LoD e o consumo de memoria de cada um.

Controles na janela:
    Scroll do mouse ....... zoom (aproxima/afasta a camera)
    Arrastar (botao esq.) . mover a imagem          (ou setas do teclado)
    + / - ................. zoom pelo teclado
    Espaco ................ pausar / retomar as ondas
    M ..................... mostrar a mascara da agua (onde as ondas agem)
    [  e  ] ............... ajustar a deteccao de agua
    R ..................... reiniciar a visao
    S ..................... salvar captura (captura_lod.png)
    Q ..................... sair

Uso:
    pip install numpy matplotlib
    python script.py
(imagem_costa.png deve estar na mesma pasta do script)
"""

import time
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.animation import FuncAnimation
from matplotlib.colors import LinearSegmentedColormap

PASTA = Path(__file__).resolve().parent
ARQUIVO_IMAGEM = PASTA / "imagem_costa.png"
ARQUIVO_PAINEL = PASTA / "renderizacao_lod.png"
ARQUIVO_CAPTURA = PASTA / "captura_lod.png"

ALTITUDE_MAX_KM = 5000.0   # camera la no alto (visao global)
ALTITUDE_MIN_KM = 5.0      # camera bem perto da costa
LARGURA_TELA = 640         # resolucao da janela interativa (quanto menor, mais fluido)

# Tabela de LoD: nome e tamanho do bloco de reducao (quanto maior, menos detalhe)
LOD = {
    0: ("LoD 0 - Global", 64),
    1: ("LoD 1 - Regional", 16),
    2: ("LoD 2 - Local", 4),
    3: ("LoD 3 - Detalhe", 1),
}


# ----------------------------------------------------------------------
# 1. Carregar a imagem (real ou sintetica)
# ----------------------------------------------------------------------
def carregar_imagem(caminho=ARQUIVO_IMAGEM):
    """Le a imagem do Google Earth como matriz RGB (valores de 0 a 1)."""
    if caminho.exists():
        img = mpimg.imread(caminho)
        if img.dtype != np.float32 and img.dtype != np.float64:
            img = img.astype(np.float32) / 255.0
        if img.ndim == 2:                       # imagem em tons de cinza
            img = np.stack([img] * 3, axis=-1)
        print(f"Imagem carregada: {caminho.name} ({img.shape[1]}x{img.shape[0]} px)")
        return img[..., :3].astype(np.float32), True   # descarta canal alfa

    print(f"[aviso] {caminho.name} nao encontrado; usando costa sintetica.")
    return gerar_costa_sintetica(), False


def _ruido_octava(rng, n, celulas):
    grade = rng.random((celulas + 1, celulas + 1))
    x = np.linspace(0, celulas, n)
    i = np.clip(x.astype(int), 0, celulas - 1)
    f = x - i
    linhas = grade[i, :] * (1 - f)[:, None] + grade[i + 1, :] * f[:, None]
    return linhas[:, i] * (1 - f)[None, :] + linhas[:, i + 1] * f[None, :]


def gerar_costa_sintetica(n=512, semente=7):
    """Plano B: gera uma costa ficticia e a converte em imagem RGB."""
    rng = np.random.default_rng(semente)
    terreno = np.zeros((n, n))
    amplitude = 1.0
    for celulas in (3, 6, 12, 24, 48, 96):
        terreno += amplitude * _ruido_octava(rng, n, celulas)
        amplitude *= 0.5
    terreno = (terreno - terreno.mean()) / terreno.std()
    terreno = terreno * 0.6 + np.linspace(1.4, -1.4, n)[None, :]

    paleta = LinearSegmentedColormap.from_list("costa", [
        (0.00, "#06223d"), (0.38, "#1a6a8f"), (0.49, "#5fc7c0"),
        (0.50, "#e8d9a0"), (0.56, "#6b9a4f"), (1.00, "#2f5a2a"),
    ])
    limite = np.abs(terreno).max()
    return paleta((terreno + limite) / (2 * limite))[..., :3].astype(np.float32)


# ----------------------------------------------------------------------
# 2. Logica de LoD (estruturas condicionais)
# ----------------------------------------------------------------------
def nivel_para_altitude(altitude_km):
    """
    Escolhe o nivel de detalhe (0 a 3) conforme a altitude da camera.
    Levanta ValueError se a altitude for invalida.
    """
    if not isinstance(altitude_km, (int, float, np.floating)) or isinstance(altitude_km, bool):
        raise ValueError(f"Altitude deve ser numerica, recebido: {altitude_km!r}")
    if altitude_km <= 0:
        raise ValueError(f"Altitude deve ser positiva, recebido: {altitude_km}")
    if altitude_km > 40000:
        raise ValueError(f"Altitude acima da orbita suportada: {altitude_km} km")

    # quanto mais alto, menos detalhe e carregado
    if altitude_km >= 1000:
        return 0
    elif altitude_km >= 200:
        return 1
    elif altitude_km >= 30:
        return 2
    else:
        return 3


def carregar_camada_satelite(altitude_km, imagem):
    """Devolve (nivel, nome, camada_reduzida) para a altitude informada."""
    nivel = nivel_para_altitude(altitude_km)
    nome, bloco = LOD[nivel]
    return nivel, nome, reduzir_resolucao(imagem, bloco)


def reduzir_resolucao(imagem, bloco):
    """Reduz a imagem tirando a media de cada bloco bloco x bloco de pixels."""
    if bloco == 1:
        return imagem
    h, w, c = imagem.shape
    h2, w2 = h // bloco, w // bloco
    recorte = imagem[: h2 * bloco, : w2 * bloco]
    return recorte.reshape(h2, bloco, w2, bloco, c).mean(axis=(1, 3))


def memoria_kb(camada):
    """Memoria aproximada da camada em RGBA de 8 bits (4 bytes por pixel)."""
    h, w = camada.shape[:2]
    return h * w * 4 / 1024


# ----------------------------------------------------------------------
# 3. Deteccao de agua (onde as ondas vao atuar)
# ----------------------------------------------------------------------
def _suavizar(a, k=7):
    """Media movel k x k (usada para limpar ruido da mascara)."""
    r = k // 2
    p = np.pad(a.astype(np.float64), r, mode="edge")
    c = np.pad(np.cumsum(np.cumsum(p, axis=0), axis=1), ((1, 0), (1, 0)))
    h, w = a.shape
    soma = c[k:k + h, k:k + w] - c[0:h, k:k + w] - c[k:k + h, 0:w] + c[0:h, 0:w]
    return soma / (k * k)


def detectar_agua(imagem, limiar=0.03):
    """
    Marca como agua os pixels em que o azul domina o vermelho (mar, rio) e que
    nao sao vegetacao. Devolve uma mascara de 0 a 1 do tamanho da imagem.
    """
    r, g, b = imagem[..., 0], imagem[..., 1], imagem[..., 2]
    agua = ((b - r) > limiar) & ((g - b) < 0.04)
    return (_suavizar(agua.astype(np.float32), 7) > 0.5).astype(np.float32)


# ----------------------------------------------------------------------
# 4. Visualizador interativo (zoom, arrastar e ondas)
# ----------------------------------------------------------------------
class Visualizador:
    def __init__(self, imagem, real):
        self.img = imagem
        self.real = real
        self.H, self.W = imagem.shape[:2]

        self.out_w = LARGURA_TELA
        self.out_h = max(2, round(LARGURA_TELA * self.H / self.W))
        self.zmax = max(6.0, self.W / (self.out_w * 0.35))   # zoom maximo
        self.px, self.py = np.meshgrid(
            np.arange(self.out_w, dtype=np.float32) + 0.5,
            np.arange(self.out_h, dtype=np.float32) + 0.5,
        )

        # piramide de LoD: a imagem ja reduzida em cada nivel (calculada uma vez)
        self.pir_img = {n: reduzir_resolucao(imagem, b) for n, (_, b) in LOD.items()}
        self.limiar = 0.03
        self._recalcular_mascara()

        self.ondas = True
        self.mostrar_mascara = False
        self.tempo = 0.0
        self._ultimo = time.perf_counter()
        self.arrasto = None
        self.sujo = True
        self.ultimo_quadro = None
        self.reiniciar()

    # --- estado da camera ---------------------------------------------
    def reiniciar(self):
        self.zoom = 1.0
        self.cx, self.cy = self.W / 2, self.H / 2
        self.sujo = True

    @property
    def altitude(self):
        """Zoom 1 = 5000 km; zoom maximo = 5 km (interpolacao logaritmica)."""
        t = np.log(self.zoom) / np.log(self.zmax)
        return ALTITUDE_MAX_KM * (ALTITUDE_MIN_KM / ALTITUDE_MAX_KM) ** t

    def _limitar(self):
        vw, vh = self.W / self.zoom, self.H / self.zoom
        self.cx = float(np.clip(self.cx, vw / 2, self.W - vw / 2))
        self.cy = float(np.clip(self.cy, vh / 2, self.H - vh / 2))
        self.sujo = True

    def zoom_em(self, ax_x, ax_y, fator):
        """Da zoom mantendo o ponto sob o cursor parado."""
        vw, vh = self.W / self.zoom, self.H / self.zoom
        sx = self.cx - vw / 2 + ax_x / self.out_w * vw
        sy = self.cy - vh / 2 + ax_y / self.out_h * vh
        self.zoom = float(np.clip(self.zoom * fator, 1.0, self.zmax))
        vw, vh = self.W / self.zoom, self.H / self.zoom
        self.cx = sx - ax_x / self.out_w * vw + vw / 2
        self.cy = sy - ax_y / self.out_h * vh + vh / 2
        self._limitar()

    def _recalcular_mascara(self):
        mascara = detectar_agua(self.img, self.limiar)
        self.pir_msk = {
            n: reduzir_resolucao(mascara[..., None], b)[..., 0] for n, (_, b) in LOD.items()
        }
        self.sujo = True

    # --- desenho de um quadro -----------------------------------------
    def renderizar_quadro(self):
        nivel = nivel_para_altitude(self.altitude)
        bloco = LOD[nivel][1]
        camada, mascara = self.pir_img[nivel], self.pir_msk[nivel]
        h, w = camada.shape[:2]

        vw, vh = self.W / self.zoom, self.H / self.zoom
        x0, y0 = self.cx - vw / 2, self.cy - vh / 2
        escx, escy = vw / self.out_w, vh / self.out_h
        px, py, t = self.px, self.py, self.tempo

        def indices(sx, sy):
            xi = np.clip((sx / bloco).astype(np.int32), 0, w - 1)
            yi = np.clip((sy / bloco).astype(np.int32), 0, h - 1)
            return yi, xi

        yi, xi = indices(x0 + px * escx, y0 + py * escy)
        agua = mascara[yi, xi]

        if self.ondas:
            # deslocamento das ondas (em pixels da tela), so onde ha agua
            dx = 3.0 * np.sin(py * 0.045 + t * 2.2 + 0.8 * np.sin(px * 0.021 + t * 0.9))
            dy = 1.8 * np.cos(px * 0.052 - t * 1.8)
            yi, xi = indices(x0 + (px + dx * agua) * escx, y0 + (py + dy * agua) * escy)

        rgb = camada[yi, xi]

        if self.ondas:
            # brilho do sol na superficie da agua (reflexo especular)
            brilho = np.sin(px * 0.09 + py * 0.05 + t * 3.1) * np.sin(py * 0.13 - t * 2.4)
            fator = (1 + 0.10 * brilho * agua)[..., None]
            glint = (0.25 * np.clip(brilho - 0.8, 0, 1) * agua)[..., None]
            rgb = rgb * fator + glint

        if self.mostrar_mascara:
            rgb = rgb * 0.4 + agua[..., None] * np.array([0.0, 0.6, 1.0]) * 0.6

        return np.clip(rgb, 0, 1), nivel, camada

    # --- eventos -------------------------------------------------------
    def ao_rolar(self, ev):
        if ev.inaxes is self.ax and ev.xdata is not None:
            self.zoom_em(ev.xdata, ev.ydata, 1.25 if ev.button == "up" else 1 / 1.25)

    def ao_apertar(self, ev):
        if ev.inaxes is self.ax and ev.button == 1:
            self.arrasto = (ev.x, ev.y)

    def ao_soltar(self, ev):
        self.arrasto = None

    def ao_mover(self, ev):
        if self.arrasto is None or ev.x is None:
            return
        dxp, dyp = ev.x - self.arrasto[0], ev.y - self.arrasto[1]
        self.arrasto = (ev.x, ev.y)
        vw, vh = self.W / self.zoom, self.H / self.zoom
        self.cx -= dxp * vw / self.ax.bbox.width
        self.cy += dyp * vh / self.ax.bbox.height
        self._limitar()

    def ao_tecla(self, ev):
        k = ev.key
        vw, vh = self.W / self.zoom, self.H / self.zoom
        if k in ("+", "="):
            self.zoom_em(self.out_w / 2, self.out_h / 2, 1.25)
        elif k in ("-", "_"):
            self.zoom_em(self.out_w / 2, self.out_h / 2, 1 / 1.25)
        elif k == "left":
            self.cx -= vw * 0.12; self._limitar()
        elif k == "right":
            self.cx += vw * 0.12; self._limitar()
        elif k == "up":
            self.cy -= vh * 0.12; self._limitar()
        elif k == "down":
            self.cy += vh * 0.12; self._limitar()
        elif k == " ":
            self.ondas = not self.ondas; self.sujo = True
        elif k == "m":
            self.mostrar_mascara = not self.mostrar_mascara; self.sujo = True
        elif k == "[":
            self.limiar -= 0.01; self._recalcular_mascara()
        elif k == "]":
            self.limiar += 0.01; self._recalcular_mascara()
        elif k == "r":
            self.reiniciar()
        elif k == "s" and self.ultimo_quadro is not None:
            mpimg.imsave(ARQUIVO_CAPTURA, self.ultimo_quadro)
            print(f"Captura salva em: {ARQUIVO_CAPTURA}")

    # --- animacao ------------------------------------------------------
    def atualizar(self, _quadro):
        agora = time.perf_counter()
        dt, self._ultimo = agora - self._ultimo, agora
        if self.ondas:
            self.tempo += dt
        elif not self.sujo:
            return []

        rgb, nivel, camada = self.renderizar_quadro()
        self.sujo = False
        self.ultimo_quadro = rgb
        self.im.set_data(rgb)

        h, w = camada.shape[:2]
        self.hud.set_text(
            f"Altitude: {self.altitude:,.0f} km   |   {LOD[nivel][0]}   |   "
            f"camada {w}x{h} px ({memoria_kb(camada):,.1f} KB)\n"
            f"Zoom {self.zoom:.1f}x   |   ondas: {'ligadas' if self.ondas else 'pausadas'}   |   "
            f"limiar da agua: {self.limiar:.2f}"
        )
        return []

    def abrir(self, mostrar=True):
        plt.rcParams["toolbar"] = "None"
        for chave in list(plt.rcParams.keys()):       # libera as teclas para o nosso uso
            if chave.startswith("keymap.") and chave != "keymap.quit":
                plt.rcParams[chave] = []

        largura_pol = 12
        altura_pol = min(8.0, largura_pol * self.H / self.W)
        self.fig = plt.figure(figsize=(largura_pol, altura_pol), facecolor="black")
        self.fig.canvas.manager.set_window_title("TerraVision - LoD interativo")
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.axis("off")
        self.im = self.ax.imshow(
            np.zeros((self.out_h, self.out_w, 3)), extent=(0, self.out_w, self.out_h, 0),
            interpolation="nearest", aspect="auto",
        )
        self.hud = self.ax.text(
            8, 8, "", color="white", fontsize=10, va="top", family="monospace",
            bbox=dict(facecolor="black", alpha=0.6, edgecolor="none", pad=5),
        )
        self.ax.text(
            self.out_w - 8, self.out_h - 8,
            "Scroll: zoom | Arrastar: mover | Espaco: pausar ondas | M: mascara da agua | "
            "[ ]: ajustar agua | R: reiniciar | S: salvar | Q: sair",
            color="white", fontsize=8, va="bottom", ha="right",
            bbox=dict(facecolor="black", alpha=0.6, edgecolor="none", pad=4),
        )

        c = self.fig.canvas
        c.mpl_connect("scroll_event", self.ao_rolar)
        c.mpl_connect("button_press_event", self.ao_apertar)
        c.mpl_connect("button_release_event", self.ao_soltar)
        c.mpl_connect("motion_notify_event", self.ao_mover)
        c.mpl_connect("key_press_event", self.ao_tecla)

        self.anim = FuncAnimation(self.fig, self.atualizar, interval=33,
                                  cache_frame_data=False)
        if mostrar:
            plt.show()


# ----------------------------------------------------------------------
# 5. Painel estatico (4 niveis de LoD + memoria) salvo em PNG
# ----------------------------------------------------------------------
def salvar_painel(imagem, real, altitudes):
    fig = plt.figure(figsize=(15, 9), facecolor="white")
    grade = fig.add_gridspec(2, 4, height_ratios=[1.6, 1], hspace=0.3, wspace=0.08)

    consumo = []
    for coluna, altitude in enumerate(altitudes):
        try:
            nivel, nome, camada = carregar_camada_satelite(altitude, imagem)
        except ValueError as erro:
            print(f"[erro] {erro}")
            continue
        h, w = camada.shape[:2]
        consumo.append((altitude, nivel, memoria_kb(camada)))

        ax = fig.add_subplot(grade[0, coluna])
        ax.imshow(camada, interpolation="nearest")
        ax.set_title(f"{nome}\n{altitude:g} km  |  {w}x{h} px", fontsize=11)
        ax.set_xticks([])
        ax.set_yticks([])

    ax2 = fig.add_subplot(grade[1, :])
    if consumo:
        rotulos = [f"{a:g} km\n(LoD {n})" for a, n, _ in consumo]
        valores = [m for _, _, m in consumo]
        barras = ax2.bar(rotulos, valores, color="#1a6a8f")
        for barra, valor in zip(barras, valores):
            ax2.text(barra.get_x() + barra.get_width() / 2, valor,
                     f"{valor:,.1f} KB", ha="center", va="bottom", fontsize=10)
        ax2.set_yscale("log")
        ax2.set_ylabel("Memoria da camada (KB, escala log)")
        ax2.set_title("Custo de memoria: quanto mais perto, mais detalhe e mais RAM/VRAM",
                      fontsize=11)
        ax2.spines[["top", "right"]].set_visible(False)

    origem = "Pontal de Atafona (Google Earth)" if real else "costa sintetica"
    fig.suptitle(f"TerraVision - Level of Detail aplicado a: {origem}",
                 fontsize=15, fontweight="bold")
    fig.savefig(ARQUIVO_PAINEL, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Painel salvo em: {ARQUIVO_PAINEL}")


# ----------------------------------------------------------------------
# 6. Execucao
# ----------------------------------------------------------------------
if __name__ == "__main__":
    imagem, real = carregar_imagem()

    # demonstracao da validacao: altitudes invalidas sao tratadas sem quebrar
    for teste in (-5, 0, "alto", 99999):
        try:
            carregar_camada_satelite(teste, imagem)
        except ValueError as erro:
            print(f"[validacao ok] {erro}")

    salvar_painel(imagem, real, altitudes=[5000, 500, 100, 5])

    print("Abrindo janela interativa... (scroll = zoom, arrastar = mover)")
    Visualizador(imagem, real).abrir()
