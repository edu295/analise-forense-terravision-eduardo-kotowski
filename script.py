# script.py
# Aluno: Eduardo Gabriel da Silva Kotowski - Nº 3
# Tema: Regiões Litorâneas e Dinâmica Oceânica (Linha de Costa/Erosão)

def carregar_camada_satelite(lista_altitudes):
    """
    Função que simula o carregamento adaptativo de camadas de satélite (LoD - Level of Detail)
    com base na altitude da câmera virtual para o tema de Regiões Litorâneas e Erosão Costeira.
    """
    for altitude in lista_altitudes:
        print(f"\n[Altitude da Câmera: {altitude}m]")
        
        # Altitude maior que 10.000m: Baixa Resolução (Mosaico global)
        if altitude > 10000:
            print("-> [Baixa Resolução]: Carregando mosaico geral das bacias oceânicas e contorno continental.")
        
        # Altitude entre 1.000m e 10.000m: Média Resolução (Mosaico regional)
        elif 1000 <= altitude <= 10000:
            print("-> [Média Resolução]: Carregando mosaico regional da faixa costeira, plumas de sedimentos e tom de água rasa.")
        
        # Altitude menor que 1.000m: Alta Resolução (Detalhes finos)
        else:
            print("-> [Alta Resolução]: Carregando alta precisão da linha de praia, arrebentação de ondas, recifes e áreas de erosão litorânea.")

# Teste da função com 5 valores de altitude simulando o zoom da câmera
altitudes_teste = [18000, 7500, 3200, 950, 200]

# Executando a função
carregar_camada_satelite(altitudes_teste)
