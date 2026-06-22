# Dashboard COVID-19 com Streamlit e Snowflake

Projeto da disciplina Ciencia de Dados - UNICAMP. O aplicativo baixa dados
publicos da Our World in Data, filtra seis paises a partir de 2021, grava o
resultado no Snowflake e apresenta um dashboard interativo.

Fonte dos dados:
https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv

## Recorte utilizado

- Brazil
- United States
- India
- Germany
- South Africa
- Japan
- Periodo iniciado em 2021-01-01

## Funcionalidades

- Carga do CSV publico para `TEST_DB.PUBLIC.COVID_OWID` no Snowflake
- Consulta dos dados diretamente no Snowflake
- KPIs de casos, obitos, paises e data mais recente
- Filtros interativos por pais e periodo
- Evolucao de casos novos em grafico de linhas
- Comparacao do total de obitos em grafico de barras
- Proporcao da populacao vacinada em grafico de barras
- Relacao entre populacao e casos em grafico de dispersao
- Tabela de dados brutos e exportacao CSV

## 1. Criar e ativar o ambiente virtual

No PowerShell, dentro da pasta do projeto:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Se o PowerShell bloquear a ativacao, execute uma vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 2. Configurar as credenciais

Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`:

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Abra `.streamlit/secrets.toml` e substitua `PREENCHA_SUA_SENHA` pela senha
real do Snowflake. Nao altere o arquivo de exemplo.

O arquivo real esta no `.gitignore` e nao deve ser enviado ao GitHub.

## 3. Executar localmente

```powershell
streamlit run covid_dashboard.py
```

No aplicativo:

1. Clique em **Carregar dados no Snowflake**.
2. Aguarde a confirmacao da gravacao.
3. Clique em **Carregar dashboard**.
4. Teste os filtros, graficos e a exportacao CSV.

## 4. Publicar no GitHub

Crie um repositorio vazio no GitHub e execute, dentro do projeto:

```powershell
git init
git add .
git status
git commit -m "Cria dashboard COVID-19 com Snowflake"
git branch -M main
git remote add origin URL_DO_REPOSITORIO
git push -u origin main
```

Antes do commit, confirme em `git status` que `secrets.toml` nao aparece.

GitHub:
https://github.com

## 5. Publicar no Streamlit Community Cloud

1. Acesse https://share.streamlit.io
2. Escolha o repositorio, a branch `main` e `covid_dashboard.py`.
3. Em **Advanced settings**, abra a area **Secrets**.
4. Cole o conteudo de `.streamlit/secrets.toml`, incluindo a senha real.
5. Clique em **Deploy**.

As credenciais configuradas no painel do Streamlit nao fazem parte do
repositorio GitHub.

## Estrutura do projeto

```text
covid-snowflake-dashboard/
|-- .streamlit/
|   `-- secrets.toml.example
|-- .gitignore
|-- covid_dashboard.py
|-- README.md
|-- requirements.txt
|-- runtime.txt
`-- snowflake_setup.sql
```
