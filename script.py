"""
Analise Forense TerraVision - Level of Detail (LoD) em regioes litoraneas
Aluno: Eduardo Gabriel da Silva Kotowski · Nº: 3 · Turma: 3°D - DS
Tema 3: Regioes Litoraneas e Dinamica Oceanica (Linha de Costa/Erosao)

O que o script faz:
1. Gera uma costa realista em memoria (1024x1024 RGB) com relevo 3D (hillshade),
   batimetria oceanica, faixa de arrebentacao/espuma, praia de areia granulada,
   falesias de erosao e vegetacao costeira, sem depender de imagens externas.
2. carregar_camada_satelite() e nivel_para_altitude() decidem, com if/elif/else,
   qual nivel de detalhe (LoD) carregar conforme a altitude da camera.
3. Abre uma janela INTERATIVA de alto FPS (Tkinter + ImageTk + ondas 2D uint8)
   com suporte a redimensionamento livre, botao maximizar e tela cheia (F11 / F).
4. Salva um painel estatico (renderizacao_lod.png) com os 4 niveis de LoD
   e o consumo de memoria de cada um.

Controles na janela:
    F11 ou F .............. alternar Tela Cheia / Janela
    Scroll do mouse ....... zoom (aproxima/afasta a camera)
    Arrastar (botao esq.) . mover a imagem          (ou setas do teclado)
    + / - ................. zoom pelo teclado
    Espaco ................ pausar / retomar as ondas
    M ..................... mostrar a mascara da agua (onde as ondas agem)
    [  e  ] ............... ajustar a deteccao de agua
    R ..................... reiniciar a visao
    S ..................... salvar captura (captura_lod.png)
    Q / Esc ............... sair da tela cheia ou fechar

Uso:
    pip install numpy matplotlib pillow
    python script.py
"""

import time
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.animation import FuncAnimation
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image

try:
    import tkinter as tk
    from PIL import ImageTk
    TK_DISPONIVEL = True
except ImportError:
    TK_DISPONIVEL = False

PASTA = Path(__file__).resolve().parent
ARQUIVO_PAINEL = PASTA / "renderizacao_lod.png"
ARQUIVO_CAPTURA = PASTA / "captura_lod.png"

ALTITUDE_MAX_KM = 5000.0   # camera la no alto (visao global)
ALTITUDE_MIN_KM = 5.0      # camera bem perto da costa
LARGURA_TELA = 560         # resolucao interna de renderizacao (mantem FPS alto)
INTERVALO_MS = 16          # alvo de ~60 FPS

# Tabela de LoD: nome e tamanho do bloco de reducao (quanto maior, menos detalhe)
LOD = {
    0: ("LoD 0 - Global", 64),
    1: ("LoD 1 - Regional", 16),
    2: ("LoD 2 - Local", 4),
    3: ("LoD 3 - Detalhe", 1),
}


# ----------------------------------------------------------------------
# 1. Geracao procedural de texturas costeiras realistas (sem imagem externa)
# ----------------------------------------------------------------------
def _ruido_octava(rng, n, celulas):
    grade = rng.random((celulas + 1, celulas + 1), dtype=np.float32)
    x = np.linspace(0, celulas, n, dtype=np.float32)
    i = np.clip(x.astype(np.int32), 0, celulas - 1)
    f = x - i
    # Interpolacao cubica suave (smoothstep) para eliminar marcas quadradas
    f = f * f * (3.0 - 2.0 * f)
    linhas = grade[i, :] * (1.0 - f)[:, None] + grade[i + 1, :] * f[:, None]
    return linhas[:, i] * (1.0 - f)[None, :] + linhas[:, i + 1] * f[None, :]


def _fbm(rng, n, oitavas, persistencia=0.5):
    """Ruido fractal multi-escala (fractional Brownian motion)."""
    acumulado = np.zeros((n, n), dtype=np.float32)
    amp = 1.0
    total_amp = 0.0
    for celulas in oitavas:
        acumulado += amp * _ruido_octava(rng, n, celulas)
        total_amp += amp
        amp *= persistencia
    return acumulado / total_amp


def gerar_costa(n=1024, semente=7):
    """
    Gera textura costeira realista (1024x1024 RGB) com:
    - Batimetria oceanica (aguas profundas, bancos de areia e zona de surf)
    - Relevo 3D com sombreamento solar direcional (hillshade)
    - Faixa de arrebentacao com espuma organica na linha d'agua
    - Areia molhada, dunas com granulacao mineral, falesias de erosao e mata
    """
    rng = np.random.default_rng(semente)

    macro = _fbm(rng, n, (3, 6, 12, 24), persistencia=0.50)
    medio = _fbm(rng, n, (32, 64, 128), persistencia=0.50)
    micro = _fbm(rng, n, (192, 384), persistencia=0.55)
    grao_fino = rng.normal(0.0, 1.0, (n, n)).astype(np.float32)

    relevo_macro = (macro - macro.mean()) / macro.std()
    y_norm, x_norm = np.mgrid[0:n, 0:n].astype(np.float32) / n
    enseada = 0.14 * np.sin(y_norm * 2.0 * np.pi * 1.2 + 0.4) + 0.06 * np.cos(y_norm * 4.2)

    elev_macro = relevo_macro * 0.48 + (1.10 - 2.25 * (x_norm + enseada))
    elev = elev_macro + (medio - 0.5) * 0.14 + (micro - 0.5) * 0.04

    # Calculo de relevo 3D (normais e iluminacao solar)
    gy, gx = np.gradient(elev * 1.4)
    luz = (-gx * 0.65 - gy * 0.45 + 0.55) / np.sqrt(gx * gx + gy * gy + 0.3025)
    sombra_terra = np.clip(0.68 + 0.52 * luz, 0.48, 1.28)
    sombra_agua = np.clip(0.90 + 0.18 * luz, 0.80, 1.12)

    gy_m, gx_m = np.gradient(elev_macro)
    declive_macro = np.hypot(gx_m, gy_m)

    paleta = LinearSegmentedColormap.from_list("costa_realista", [
        (0.000, "#051d36"),  # oceano profundo
        (0.280, "#0b426b"),  # talude oceanico
        (0.435, "#157594"),  # plataforma rasa
        (0.492, "#46bfb9"),  # zona de arrebentacao turquesa
        (0.500, "#bda77c"),  # areia molhada
        (0.522, "#ebd9a8"),  # faixa de areia seca / dunas
        (0.555, "#7ea34e"),  # vegetacao de restinga
        (0.660, "#386b29"),  # mata atlantica costeira
        (1.000, "#1c3d16"),  # floresta densa de encosta
    ])

    elev_norm = np.clip((elev + 1.5) / 3.0, 0.0, 1.0)
    rgb = paleta(elev_norm)[..., :3].astype(np.float32)

    mar = elev < 0.0
    terra = ~mar

    sombra = np.where(mar, sombra_agua, sombra_terra)[..., None]
    rgb *= sombra

    # Correntes submarinas suaves no oceano
    rgb[mar] += ((medio[mar] - 0.5) * 0.04)[:, None] * np.array([0.08, 0.42, 0.62], dtype=np.float32)

    # Espuma natural da rebentacao logo na linha da costa
    faixa_surf = np.exp(-((elev + 0.010) ** 2) / 0.00028)
    renda_espuma = np.clip((micro - 0.36) * 2.4 + grao_fino * 0.10, 0.0, 1.0)
    espuma = np.clip(faixa_surf * renda_espuma * 0.88, 0.0, 0.88)[..., None]
    rgb = rgb * (1.0 - espuma) + np.array([0.94, 0.97, 0.99], dtype=np.float32) * espuma

    # Granulacao mineral na faixa de areia e dunas
    areia = terra & (elev < 0.13)
    rgb[areia] += (grao_fino[areia] * 0.020 + (micro[areia] - 0.5) * 0.035)[:, None]

    # Falesias e encostas rochosas expostas pela erosao
    limiar_falesia = float(np.percentile(declive_macro[terra], 88))
    rocha = np.clip((declive_macro - limiar_falesia) * 240.0, 0.0, 0.85) * terra * (elev > 0.03)
    cor_rocha = np.array([0.52, 0.44, 0.37], dtype=np.float32) * sombra_terra[..., None]
    cor_rocha += ((micro - 0.5) * 0.06 + grao_fino * 0.02)[..., None]
    rgb = rgb * (1.0 - rocha[..., None]) + cor_rocha * rocha[..., None]

    # Textura organica de copas de arvores na area de mata
    mata = elev >= 0.13
    copas = (micro[mata] - 0.5) * 0.16 + (medio[mata] - 0.5) * 0.10 + grao_fino[mata] * 0.022
    rgb[mata] += copas[:, None] * np.array([0.32, 0.62, 0.22], dtype=np.float32)

    rgb = np.clip(rgb, 0.0, 1.0)
    print(f"Textura costeira realista gerada em memoria ({n}x{n} px)")
    return rgb


def redimensionar_para(imagem, altura, largura):
    """Redimensiona com interpolacao bilinear suave."""
    pil = Image.fromarray((np.clip(imagem, 0.0, 1.0) * 255.0).astype(np.uint8))
    pil = pil.resize((largura, altura), Image.Resampling.BILINEAR)
    return np.asarray(pil, dtype=np.float32) / 255.0


def recorte_central(imagem, proporcao):
    """Cria uma aproximacao suave de zoom a partir da matriz base."""
    h, w = imagem.shape[:2]
    nh, nw = max(2, int(h * proporcao)), max(2, int(w * proporcao))
    y0, x0 = (h - nh) // 2, (w - nw) // 2
    recorte = imagem[y0:y0 + nh, x0:x0 + nw]
    return redimensionar_para(recorte, h, w)


def preparar_camadas_altitude(mapa_base):
    """Prepara os enquadramentos para cada nivel de altitude."""
    return {
        0: mapa_base,
        1: recorte_central(mapa_base, 0.75),
        2: mapa_base,
        3: mapa_base,
    }


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

    if altitude_km >= 1000:
        return 0
    elif altitude_km >= 200:
        return 1
    elif altitude_km >= 30:
        return 2
    else:
        return 3


def carregar_camada_satelite(lista_altitudes):
    """
    Atividade: classifica uma lista/array de altitudes em METROS.
    A funcao exige pelo menos cinco valores e usa if/elif/else.
    """
    if not isinstance(lista_altitudes, (list, tuple, np.ndarray)):
        raise TypeError("Informe uma lista, tupla ou array NumPy de altitudes.")

    if len(lista_altitudes) < 5:
        raise ValueError("A atividade exige pelo menos cinco altitudes.")

    resultados = []
    for altitude in lista_altitudes:
        if isinstance(altitude, (bool, np.bool_)) or not isinstance(
            altitude, (int, float, np.integer, np.floating)
        ):
            raise ValueError(f"Altitude invalida: {altitude!r}. Use numeros em metros.")

        altitude = float(altitude)
        if not np.isfinite(altitude) or altitude < 0:
            raise ValueError(f"Altitude deve ser um numero finito e nao negativo: {altitude}")

        if altitude > 10000:
            nivel = "Baixa resolucao - mosaico global da Terra"
            detalhe = "Visao global: poucos detalhes para economizar memoria."
        elif altitude >= 1000:
            nivel = "Media resolucao - mosaico regional litoraneo"
            detalhe = "Visao regional: identifica a linha de costa e a dinamica oceanica."
        else:
            nivel = "Alta resolucao - detalhe da costa e erosao"
            detalhe = "Visao aproximada: destaca ondas, faixa de areia e areas de erosao."

        print(f"Altitude: {altitude:,.0f} m -> {nivel}")
        print(f"  {detalhe}")
        resultados.append((altitude, nivel))

    return resultados


def reduzir_resolucao(imagem, bloco):
    """Reduz a matriz tirando a media de cada bloco bloco x bloco de pixels."""
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
    nao sao vegetacao. Devolve uma mascara de 0 a 1 do tamanho da matriz.
    """
    r, g, b = imagem[..., 0], imagem[..., 1], imagem[..., 2]
    agua = ((b - r) > limiar) & ((g - b) < 0.06)
    return (_suavizar(agua.astype(np.float32), 7) > 0.5).astype(np.float32)


# ----------------------------------------------------------------------
# 4. Visualizador interativo (60 FPS + Tela Cheia / Redimensionavel)
# ----------------------------------------------------------------------
class Visualizador:
    def __init__(self, mapa, camadas=None):
        self.img = mapa
        self.camadas_base = camadas or preparar_camadas_altitude(mapa)
        self.H, self.W = mapa.shape[:2]

        self.out_w = LARGURA_TELA
        self.out_h = max(2, round(LARGURA_TELA * self.H / self.W))
        self.zmax = max(6.0, self.W / (self.out_w * 0.25))
        self.px, self.py = np.meshgrid(
            np.arange(self.out_w, dtype=np.float32) + 0.5,
            np.arange(self.out_h, dtype=np.float32) + 0.5,
        )

        # Tabelas trigonometricas pre-calculadas uma unica vez
        fase1 = 0.024 * self.px + 0.016 * self.py
        fase2 = -0.014 * self.px + 0.030 * self.py
        self.w1_sin = np.sin(fase1)
        self.w1_cos = np.cos(fase1)
        self.w2_sin = np.sin(fase2)
        self.w2_cos = np.cos(fase2)

        # Piramide de LoD ja em uint8
        self.pir_img = {n: reduzir_resolucao(self.camadas_base[n], b) for n, (_, b) in LOD.items()}
        self.pir_u8 = {
            n: (np.clip(cam, 0.0, 1.0) * 255.0).astype(np.uint8)
            for n, cam in self.pir_img.items()
        }
        self.pir_pil = {n: Image.fromarray(u8) for n, u8 in self.pir_u8.items()}

        self.limiar = 0.03
        self._recalcular_mascara()
        self.fps_atual = 0.0
        self._interp_atual = "nearest"

        # Cache da camera + buffer uint8 reutilizavel
        self._cache_chave = None
        self._cache_viewport = None
        self._quadro_buffer = np.zeros((self.out_h, self.out_w, 3), dtype=np.uint8)

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
        self._cache_chave = None
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
        self.pir_msk = {}
        self.pir_borda = {}
        for n, (_, bloco) in LOD.items():
            mascara = detectar_agua(self.camadas_base[n], self.limiar)
            self.pir_msk[n] = reduzir_resolucao(mascara[..., None], bloco)[..., 0]
            grad_y, grad_x = np.gradient(mascara)
            borda = np.hypot(grad_x, grad_y)
            self.pir_borda[n] = reduzir_resolucao(borda[..., None], bloco)[..., 0]
        self._cache_chave = None
        self.sujo = True

    def _obter_viewport_cache(self, nivel):
        """
        Recorta e interpola o fundo em uint8 apenas quando a camera se move.
        Nos quadros seguintes, as ondas rodam direto sobre esse cache.
        """
        chave = (nivel, round(self.cx, 2), round(self.cy, 2), round(self.zoom, 4), round(self.limiar, 3))
        if chave == self._cache_chave and self._cache_viewport is not None:
            return self._cache_viewport

        bloco = LOD[nivel][1]
        camada_u8 = self.pir_u8[nivel]
        mascara = self.pir_msk[nivel]
        borda = self.pir_borda[nivel]
        h, w = camada_u8.shape[:2]

        vw, vh = self.W / self.zoom, self.H / self.zoom
        x0, y0 = self.cx - vw / 2, self.cy - vh / 2
        escx, escy = vw / self.out_w, vh / self.out_h

        sx = x0 + self.px * escx
        sy = y0 + self.py * escy
        xi = np.clip((sx / bloco).astype(np.int32), 0, w - 1)
        yi = np.clip((sy / bloco).astype(np.int32), 0, h - 1)
        agua = mascara[yi, xi]
        borda_tela = borda[yi, xi]

        if nivel >= 2:
            frame_pil = self.pir_pil[nivel].transform(
                (self.out_w, self.out_h),
                Image.Transform.AFFINE,
                (escx / bloco, 0.0, x0 / bloco, 0.0, escy / bloco, y0 / bloco),
                resample=Image.Resampling.BILINEAR,
            )
            rgb_base_u8 = np.asarray(frame_pil, dtype=np.uint8)
        else:
            rgb_base_u8 = camada_u8[yi, xi]

        agua_mask3 = (agua > 0.25)[..., None]
        self._cache_chave = chave
        self._cache_viewport = (rgb_base_u8, agua, agua_mask3, borda_tela)
        return self._cache_viewport

    # --- desenho de um quadro (2D uint8 vetorizado, ~60 FPS) ----------
    def renderizar_quadro(self):
        nivel = nivel_para_altitude(self.altitude)
        camada = self.pir_img[nivel]
        rgb_base_u8, agua, agua_mask3, borda_tela = self._obter_viewport_cache(nivel)

        np.copyto(self._quadro_buffer, rgb_base_u8)

        if self.ondas:
            t = self.tempo
            s1, c1 = np.sin(t * 1.35), np.cos(t * 1.35)
            s2, c2 = np.sin(t * 0.95), np.cos(t * 0.95)

            onda1 = self.w1_sin * c1 - self.w1_cos * s1
            onda2 = self.w2_sin * c2 - self.w2_cos * s2

            # Ondulacao suave da superficie da agua em 2D quando aproximado
            if nivel >= 2:
                sx = int(round(1.5 * s1))
                sy = int(round(1.0 * c2))
                desloc = np.roll(rgb_base_u8, (sy, sx), axis=(0, 1))
                np.copyto(self._quadro_buffer, desloc, where=agua_mask3)

            # Soma saturada em uint8 (sem alocacoes de float32/int16)
            cristas = np.maximum(0.0, onda1 * 0.5 + onda2 * 0.25 - 0.50) * (34.0 * agua)
            espuma = np.maximum(0.0, onda1 * 0.6 + 0.35) * (95.0 * borda_tela)
            brilho = (cristas + espuma).astype(np.uint8)[..., None]
            np.minimum(self._quadro_buffer, 255 - brilho, out=self._quadro_buffer)
            self._quadro_buffer += brilho

        if self.mostrar_mascara:
            m = agua[..., None]
            tint = np.array([0.0, 165.0, 255.0], dtype=np.float32)
            self._quadro_buffer[:] = (
                self._quadro_buffer.astype(np.float32) * 0.45 + m * tint * 0.55
            ).astype(np.uint8)

        return self._quadro_buffer, nivel, camada

    def _processar_comando(self, k):
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

    def _texto_hud(self, nivel, camada):
        h, w = camada.shape[:2]
        return (
            f"Altitude: {self.altitude:,.0f} km  |  {LOD[nivel][0]}  |  "
            f"camada {w}x{h} px ({memoria_kb(camada):,.1f} KB)\n"
            f"Zoom {self.zoom:.1f}x  |  FPS: {self.fps_atual:.0f}  |  "
            f"ondas: {'ligadas' if self.ondas else 'pausadas'}  |  "
            f"limiar agua: {self.limiar:.2f}"
        )

    # --- janela Tkinter redimensionavel + Tela Cheia (F11 / F) ---------
    def _abrir_tk(self):
        root = tk.Tk()
        root.title("TerraVision - LoD interativo  (F11 ou F = Tela Cheia)")
        root.configure(bg="black")
        root.resizable(True, True)
        root.geometry("820x700")

        disp_w, disp_h = 820, 700
        foto_w, foto_h = self.out_w, self.out_h
        tela_cheia = False

        canvas = tk.Canvas(
            root, width=disp_w, height=disp_h, bg="black", highlightthickness=0
        )
        canvas.pack(fill="both", expand=True)

        pil_inicial = Image.fromarray(np.zeros((foto_h, foto_w, 3), dtype=np.uint8))
        foto_tk = ImageTk.PhotoImage(pil_inicial)
        img_id = canvas.create_image(0, 0, anchor="nw", image=foto_tk)

        hud_box = canvas.create_rectangle(10, 10, 560, 50, fill="#111111", outline="#333333")
        hud_id = canvas.create_text(
            18, 16, anchor="nw", text="", fill="white", font=("Consolas", 10)
        )
        rodape_box = canvas.create_rectangle(
            10, disp_h - 28, disp_w - 10, disp_h - 8, fill="#111111", outline="#333333"
        )
        rodape_id = canvas.create_text(
            disp_w // 2, disp_h - 18, anchor="center",
            text="F11 / F: Tela cheia | Scroll: zoom | Arrastar: mover | Espaco: ondas | M: mascara | [ ]: agua | R: reset | S: salvar | Q: sair",
            fill="white", font=("Consolas", 8),
        )

        def atualizar_layout_hud(w, h):
            canvas.coords(hud_box, 10, 10, min(w - 10, 620), 52)
            canvas.coords(rodape_box, 10, h - 28, max(20, w - 10), h - 8)
            canvas.coords(rodape_id, w // 2, h - 18)

        def on_configure(ev):
            nonlocal disp_w, disp_h
            if ev.widget is canvas and ev.width > 10 and ev.height > 10:
                if ev.width != disp_w or ev.height != disp_h:
                    disp_w, disp_h = ev.width, ev.height
                    atualizar_layout_hud(disp_w, disp_h)
                    self.sujo = True

        def alternar_tela_cheia():
            nonlocal tela_cheia
            tela_cheia = not tela_cheia
            root.attributes("-fullscreen", tela_cheia)
            self.sujo = True

        def on_scroll_win(ev):
            ax = ev.x * self.out_w / max(1, disp_w)
            ay = ev.y * self.out_h / max(1, disp_h)
            self.zoom_em(ax, ay, 1.25 if ev.delta > 0 else 1 / 1.25)

        def on_scroll_linux(ev, fator):
            ax = ev.x * self.out_w / max(1, disp_w)
            ay = ev.y * self.out_h / max(1, disp_h)
            self.zoom_em(ax, ay, fator)

        def on_press(ev):
            self.arrasto = (ev.x, ev.y)

        def on_drag(ev):
            if self.arrasto is None:
                return
            dxp, dyp = ev.x - self.arrasto[0], ev.y - self.arrasto[1]
            self.arrasto = (ev.x, ev.y)
            vw, vh = self.W / self.zoom, self.H / self.zoom
            self.cx -= dxp * vw / max(1, disp_w)
            self.cy -= dyp * vh / max(1, disp_h)
            self._limitar()

        mapa_teclas = {
            "plus": "+", "equal": "+", "KP_Add": "+",
            "minus": "-", "underscore": "-", "KP_Subtract": "-",
            "Left": "left", "Right": "right", "Up": "up", "Down": "down",
            "space": " ", "m": "m", "M": "m",
            "bracketleft": "[", "bracketright": "]",
            "r": "r", "R": "r", "s": "s", "S": "s",
        }

        def on_key(ev):
            nonlocal tela_cheia
            if ev.keysym in ("F11", "f", "F"):
                alternar_tela_cheia()
                return
            if ev.keysym == "Escape":
                if tela_cheia:
                    tela_cheia = False
                    root.attributes("-fullscreen", False)
                    self.sujo = True
                else:
                    root.destroy()
                return
            if ev.keysym in ("q", "Q"):
                root.destroy()
                return
            cmd = mapa_teclas.get(ev.keysym)
            if cmd is not None:
                self._processar_comando(cmd)

        canvas.bind("<Configure>", on_configure)
        canvas.bind("<MouseWheel>", on_scroll_win)
        canvas.bind("<Button-4>", lambda e: on_scroll_linux(e, 1.25))
        canvas.bind("<Button-5>", lambda e: on_scroll_linux(e, 1 / 1.25))
        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "arrasto", None))
        canvas.bind("<B1-Motion>", on_drag)
        root.bind("<KeyPress>", on_key)

        ultimo_hud = 0.0
        self._ultimo = time.perf_counter()

        def loop_tk():
            nonlocal ultimo_hud, foto_tk, foto_w, foto_h
            agora = time.perf_counter()
            dt = min(max(agora - self._ultimo, 0.0001), 0.25)
            self._ultimo = agora
            fps_inst = 1.0 / dt
            self.fps_atual = fps_inst if self.fps_atual == 0 else (
                self.fps_atual * 0.85 + fps_inst * 0.15
            )

            if self.ondas:
                self.tempo += dt

            if self.ondas or self.sujo:
                rgb_u8, nivel, camada = self.renderizar_quadro()
                self.sujo = False
                self.ultimo_quadro = rgb_u8

                pil_img = Image.fromarray(rgb_u8)
                if disp_w != self.out_w or disp_h != self.out_h:
                    pil_img = pil_img.resize((disp_w, disp_h), Image.Resampling.NEAREST)

                if disp_w != foto_w or disp_h != foto_h:
                    foto_w, foto_h = disp_w, disp_h
                    foto_tk = ImageTk.PhotoImage(pil_img)
                    canvas.itemconfigure(img_id, image=foto_tk)
                else:
                    foto_tk.paste(pil_img)

                if agora - ultimo_hud >= 0.25:
                    canvas.itemconfigure(hud_id, text=self._texto_hud(nivel, camada))
                    ultimo_hud = agora

            root.after(INTERVALO_MS, loop_tk)

        loop_tk()
        root.mainloop()

    # --- fallback Matplotlib caso Tkinter nao esteja disponivel --------
    def atualizar(self, _quadro):
        agora = time.perf_counter()
        dt = min(max(agora - self._ultimo, 0.0001), 0.25)
        self._ultimo = agora
        fps_inst = 1.0 / dt
        self.fps_atual = fps_inst if self.fps_atual == 0 else (
            self.fps_atual * 0.85 + fps_inst * 0.15
        )

        if self.ondas:
            self.tempo += dt
        elif not self.sujo:
            return self.im, self.hud

        rgb_u8, nivel, camada = self.renderizar_quadro()
        self.sujo = False
        self.ultimo_quadro = rgb_u8

        interp_desejada = "bilinear" if nivel >= 2 else "nearest"
        if interp_desejada != self._interp_atual:
            self.im.set_interpolation(interp_desejada)
            self._interp_atual = interp_desejada

        self.im.set_data(rgb_u8)
        if not hasattr(self, "_ultimo_hud") or agora - self._ultimo_hud >= 0.35:
            self.hud.set_text(self._texto_hud(nivel, camada))
            self._ultimo_hud = agora
        return self.im, self.hud

    def abrir(self, mostrar=True):
        if mostrar and TK_DISPONIVEL:
            self._abrir_tk()
            return

        plt.rcParams["toolbar"] = "None"
        for chave in list(plt.rcParams.keys()):
            if chave.startswith("keymap.") and chave != "keymap.quit":
                plt.rcParams[chave] = []

        self.fig = plt.figure(figsize=(8, 8), facecolor="black")
        self.fig.canvas.manager.set_window_title("TerraVision - LoD interativo")
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.axis("off")
        self.im = self.ax.imshow(
            np.zeros((self.out_h, self.out_w, 3), dtype=np.uint8),
            extent=(0, self.out_w, self.out_h, 0),
            interpolation="nearest",
            aspect="auto",
        )
        self.hud = self.ax.text(
            8, 8, "", color="white", fontsize=9.5, va="top", family="monospace",
            bbox=dict(facecolor="black", alpha=0.6, edgecolor="none", pad=5),
        )

        def on_scroll(ev):
            if ev.inaxes is self.ax and ev.xdata is not None:
                self.zoom_em(ev.xdata, ev.ydata, 1.25 if ev.button == "up" else 1 / 1.25)

        def on_press(ev):
            if ev.inaxes is self.ax and ev.button == 1:
                self.arrasto = (ev.x, ev.y)

        def on_move(ev):
            if self.arrasto is None or ev.x is None:
                return
            dxp, dyp = ev.x - self.arrasto[0], ev.y - self.arrasto[1]
            self.arrasto = (ev.x, ev.y)
            vw, vh = self.W / self.zoom, self.H / self.zoom
            self.cx -= dxp * vw / self.ax.bbox.width
            self.cy += dyp * vh / self.ax.bbox.height
            self._limitar()

        c = self.fig.canvas
        c.mpl_connect("scroll_event", on_scroll)
        c.mpl_connect("button_press_event", on_press)
        c.mpl_connect("button_release_event", lambda ev: setattr(self, "arrasto", None))
        c.mpl_connect("motion_notify_event", on_move)
        c.mpl_connect("key_press_event", lambda ev: self._processar_comando(ev.key))

        self.anim = FuncAnimation(
            self.fig,
            self.atualizar,
            init_func=lambda: (self.im, self.hud),
            interval=INTERVALO_MS,
            blit=bool(self.fig.canvas.supports_blit),
            cache_frame_data=False,
        )
        if mostrar:
            plt.show()


# ----------------------------------------------------------------------
# 5. Painel estatico (4 niveis de LoD + memoria) salvo em PNG
# ----------------------------------------------------------------------
def salvar_painel(mapa, altitudes, camadas=None):
    fig = plt.figure(figsize=(15, 9), facecolor="white")
    grade = fig.add_gridspec(2, 4, height_ratios=[1.6, 1], hspace=0.3, wspace=0.08)

    consumo = []
    for coluna, altitude in enumerate(altitudes):
        try:
            nivel = nivel_para_altitude(altitude)
            fonte = (camadas or {n: mapa for n in LOD})[nivel]
            nome, bloco = LOD[nivel]
            camada = reduzir_resolucao(fonte, bloco)
        except ValueError as erro:
            print(f"[erro] {erro}")
            continue
        h, w = camada.shape[:2]
        consumo.append((altitude, nivel, memoria_kb(camada)))

        ax = fig.add_subplot(grade[0, coluna])
        ax.imshow(camada, interpolation="bilinear" if nivel >= 2 else "nearest")
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

    fig.suptitle("TerraVision - Level of Detail aplicado a regiao costeira",
                 fontsize=15, fontweight="bold")
    fig.savefig(ARQUIVO_PAINEL, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Painel salvo em: {ARQUIVO_PAINEL}")


# ----------------------------------------------------------------------
# 6. Execucao
# ----------------------------------------------------------------------
if __name__ == "__main__":
    mapa = gerar_costa()
    camadas = preparar_camadas_altitude(mapa)

    # Testes de validacao de altitude
    for entrada_invalida in (-10, 0, "alta", 50000):
        try:
            nivel_para_altitude(entrada_invalida)
        except ValueError as erro:
            print(f"[validacao ok] {erro}")

    # Etapa da atividade: pelo menos cinco altitudes em METROS.
    altitudes_metros = [18000, 7500, 3200, 950, 200]
    carregar_camada_satelite(altitudes_metros)

    # Painel estatico de comparacao (em quilometros)
    salvar_painel(mapa, altitudes=[5000, 500, 100, 5], camadas=camadas)

    print("Abrindo janela interativa... (F11 ou F = tela cheia, scroll = zoom, arrastar = mover)")
    Visualizador(mapa, camadas=camadas).abrir()