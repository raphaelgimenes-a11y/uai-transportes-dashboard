import pandas as pd
from pathlib import Path

# Caminhos
dir_atual = Path(__file__).parent

print("=" * 60)
print("DIAGNÓSTICO DOS DADOS")
print("=" * 60)

try:
    print("\n📊 DADOS CADASTRAIS")
    print("-" * 60)
    dados_cadastrais = pd.read_excel(dir_atual / 'DadosCadastrais.xlsx')
    print(f"Shape: {dados_cadastrais.shape}")
    print(f"\nColunas: {list(dados_cadastrais.columns)}")
    print(f"\nTipos de dados:")
    print(dados_cadastrais.dtypes)
    print(f"\nPrimeiras linhas:")
    print(dados_cadastrais.head())
except Exception as e:
    print(f"❌ Erro ao carregar DadosCadastrais.xlsx: {e}")

try:
    print("\n\n📊 DADOS FRETE")
    print("-" * 60)
    dados_frete = pd.read_excel(dir_atual / 'DadosFrete.xlsx')
    print(f"Shape: {dados_frete.shape}")
    print(f"\nColunas: {list(dados_frete.columns)}")
    print(f"\nTipos de dados:")
    print(dados_frete.dtypes)
    print(f"\nPrimeiras linhas:")
    print(dados_frete.head())
except Exception as e:
    print(f"❌ Erro ao carregar DadosFrete.xlsx: {e}")

try:
    print("\n\n📊 DIÁRIO DE BORDO")
    print("-" * 60)
    dados_viagens = pd.read_csv(dir_atual / 'Diário de Bordo.txt', delimiter=';')
    print(f"Shape: {dados_viagens.shape}")
    print(f"\nColunas: {list(dados_viagens.columns)}")
    print(f"\nTipos de dados:")
    print(dados_viagens.dtypes)
    print(f"\nPrimeiras linhas:")
    print(dados_viagens.head())
except Exception as e:
    print(f"❌ Erro ao carregar Diário de Bordo.txt: {e}")

print("\n" + "=" * 60)
print("FIM DO DIAGNÓSTICO")
print("=" * 60)
