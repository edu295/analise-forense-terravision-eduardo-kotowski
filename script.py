
# script.py
# Aluno: Eduardo Gabriel da Silva Kotowski - Nº 3
# Tema: Regiões Litorâneas e Dinâmica Oceânica
# Projeto: TerraVision - Level of Detail (LoD)

import numpy as np
import matplotlib.pyplot as plt


def gerar_imagem_litoranea(altitude, tamanho=600):
    """Gera uma visualização simulada de uma região litorânea."""

    rng = np.random.default_rng(42)

    altura = tamanho
    largura = tamanho

    y, x = np.mgrid[0:altura, 0:largura]

    # Linha de costa irregular
    costa = (
        altura * 0.58
        + 25 * np.sin(x / 65)
        + 12 * np.sin(x / 23)
    )

    # Simulação de erosão costeira
    erosao = 65 * np.exp(-((x - largura * 0.55) / 55) ** 2)
    costa += erosao

    distancia = y - costa

    # Criação das cores da imagem
    imagem = np.zeros((altura, largura, 3))

    # Oceano profundo
    imagem[distancia < -35] = [0.025, 0.18, 0.34]

    # Água rasa
    rasa = (distancia >= -35) & (distancia < 0)
    imagem[rasa] = [0.12, 0.53, 0.62]

    # Faixa de areia
    areia = (distancia >= 0) & (distancia < 15)
    imagem[areia] = [0.88, 0.76, 0.52]

    # Vegetação e continente
    terra = distancia >= 15
    imagem[terra] = [0.22, 0.39, 0.20]

    # Textura natural
    ruido = rng.normal(0, 0.025, (altura, largura, 1))
    imagem = np.clip(imagem + ruido, 0, 1)

    # Ondas
    ondas = (
        (np.abs(np.sin(x / 13 + y / 9)) < 0.07)
        & (distancia < -3)
        & (distancia > -30)
    )
    imagem[ondas] = [0.72, 0.89, 0.91]

    # Recifes
    if altitude <= 1000:
        recifes = [
            (180, 300, 35),
            (390, 270, 28),
            (490, 340, 22)
        ]

        for cx, cy, raio in recifes:
            mascara = (
                (x - cx) ** 2 + (y - cy) ** 2
                < raio ** 2
            ) & (distancia < 0)

            imagem[mascara] = [0.43, 0.57, 0.38]

    return imagem


def carregar_camada_satelite(lista_altitudes):

    try:
        if not isinstance(lista_altitudes, list):
            raise ValueError("A entrada precisa ser uma lista.")

        if len(lista_altitudes) < 5:
            raise ValueError("Informe pelo menos 5 altitudes.")

        fig, eixos = plt.subplots(
            2, 3,
            figsize=(15, 9)
        )

        eixos = eixos.flatten()

        for indice, altitude in enumerate(lista_altitudes[:5]):

            if not isinstance(altitude, (int, float)) or altitude < 0:
                print(f"Altitude inválida: {altitude}")
                continue

            print(f"\nAltitude da câmera: {altitude}m")

            if altitude > 10000:
                resolucao = "Baixa resolução"
                fator = 12

            elif altitude >= 1000:
                resolucao = "Média resolução"
                fator = 4

            else:
                resolucao = "Alta resolução"
                fator = 1

            print(f"Carregando: {resolucao}")

            # Gera a imagem
            imagem = gerar_imagem_litoranea(altitude)

            # Simula a redução de detalhes conforme a altitude
            imagem_reduzida = imagem[::fator, ::fator]

            eixos[indice].imshow(
                imagem_reduzida,
                interpolation="nearest"
            )

            eixos[indice].set_title(
                f"{altitude} metros\n{resolucao}",
                fontsize=12
            )

            eixos[indice].axis("off")

        # Remove o sexto espaço vazio
        eixos[5].axis("off")

        fig.suptitle(
            "TERRAVISION - REGIÕES LITORÂNEAS E EROSÃO COSTEIRA",
            fontsize=16,
            fontweight="bold"
        )

        plt.tight_layout()

        # Salva a imagem
        plt.savefig(
            "terravision_litoral.png",
            dpi=150,
            bbox_inches="tight"
        )

        print("\nImagem salva como terravision_litoral.png")

        # Exibe a imagem na tela
        plt.show()

    except Exception as erro:
        print(f"Erro no processamento: {erro}")


# Teste do projeto
altitudes_teste = [18000, 7500, 3200, 950, 200]

carregar_camada_satelite(altitudes_teste)
