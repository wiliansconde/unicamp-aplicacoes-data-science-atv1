from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from snowflake.snowpark import Session


st.set_page_config(
    page_title="Dashboard COVID-19",
    page_icon=":bar_chart:",
    layout="wide",
)

CSV_URL = (
    "https://raw.githubusercontent.com/owid/covid-19-data/"
    "master/public/data/owid-covid-data.csv"
)

LOCAL_CSV = Path(__file__).with_name("owid-covid-data.csv")
TABLE_NAME = "COVID_OWID"
START_DATE = "2021-01-01"

DEFAULT_COUNTRIES = [
    "Brazil",
    "United States",
    "India",
    "Germany",
    "South Africa",
    "Japan",
]

REQUIRED_COLUMNS = [
    "location",
    "continent",
    "date",
    "total_cases",
    "new_cases",
    "total_deaths",
    "new_deaths",
    "population",
    "people_vaccinated",
    "people_fully_vaccinated",
]

NUMERIC_COLUMNS = [
    "total_cases",
    "new_cases",
    "total_deaths",
    "new_deaths",
    "population",
    "people_vaccinated",
    "people_fully_vaccinated",
]

CUMULATIVE_COLUMNS = [
    "total_cases",
    "total_deaths",
    "population",
    "people_vaccinated",
    "people_fully_vaccinated",
]


def connection_parameters() -> dict:
    try:
        config = st.secrets["snowflake"]

        return {
            "user": config["user"],
            "password": config["password"],
            "account": config["account"],
            "warehouse": config["warehouse"],
            "database": config["database"],
            "schema": config["schema"],
            "role": config["role"],
        }
    except (KeyError, FileNotFoundError):
        st.error("Credenciais do Snowflake não encontradas.")
        st.stop()


def open_session() -> Session:
    return Session.builder.configs(connection_parameters()).create()


def open_read_only_session() -> Session:
    parameters = connection_parameters()
    parameters["role"] = st.secrets["snowflake"].get(
        "query_role",
        "COVID_READONLY_ROLE",
    )
    return Session.builder.configs(parameters).create()


def is_read_only_query(query: str) -> bool:
    statement = query.strip().rstrip(";").strip()

    if not statement or ";" in statement:
        return False

    return statement.split(maxsplit=1)[0].upper() in {"SELECT", "WITH"}


def prepare_downloaded_data() -> pd.DataFrame:
    source = LOCAL_CSV if LOCAL_CSV.exists() else CSV_URL

    df = pd.read_csv(
        source,
        usecols=REQUIRED_COLUMNS,
        low_memory=False,
    )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = df[
        df["location"].isin(DEFAULT_COUNTRIES)
        & (df["date"] >= pd.Timestamp(START_DATE))
    ].copy()

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["location", "date"])
    df = df.sort_values(["location", "date"]).reset_index(drop=True)

    df[CUMULATIVE_COLUMNS] = (
        df.groupby("location")[CUMULATIVE_COLUMNS].ffill()
    )

    df["date"] = df["date"].dt.date
    df.columns = [column.upper() for column in df.columns]

    return df


def normalize_snowflake_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [column.lower() for column in df.columns]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return (
        df.dropna(subset=["location", "date"])
        .sort_values(["location", "date"])
    )


def load_into_snowflake() -> None:
    session = None

    try:
        with st.spinner("Baixando e preparando os dados da OWID..."):
            df = prepare_downloaded_data()

        with st.spinner("Gravando a tabela no Snowflake..."):
            session = open_session()
            config = connection_parameters()

            session.write_pandas(
                df,
                table_name=TABLE_NAME,
                database=config["database"],
                schema=config["schema"],
                auto_create_table=True,
                overwrite=True,
            )

        total_records = f"{len(df):,}".replace(",", ".")

        st.sidebar.success(
            f"{total_records} registros gravados em {TABLE_NAME}."
        )
    except Exception as error:
        st.sidebar.error(f"Falha na carga: {error}")
    finally:
        if session is not None:
            session.close()


def load_from_snowflake() -> None:
    session = None

    try:
        with st.spinner("Consultando o Snowflake..."):
            session = open_session()
            config = connection_parameters()

            full_name = (
                f'{config["database"]}.'
                f'{config["schema"]}.'
                f"{TABLE_NAME}"
            )

            df = session.table(full_name).to_pandas()

            st.session_state["covid_data"] = normalize_snowflake_data(df)

        st.sidebar.success("Dashboard carregado com sucesso.")
    except Exception as error:
        st.sidebar.error(
            "Não foi possível carregar a tabela. "
            f"Detalhes: {error}"
        )
    finally:
        if session is not None:
            session.close()


def format_integer(value: float) -> str:
    if pd.isna(value):
        return "0"

    return f"{int(value):,}".replace(",", ".")


st.title("Dashboard COVID-19")
st.caption(
    "Dados da Our World in Data armazenados e consultados no Snowflake"
)

st.sidebar.header("Snowflake")
st.sidebar.caption(f"Tabela: TEST_DB.PUBLIC.{TABLE_NAME}")

if st.sidebar.button(
    "Carregar dados no Snowflake",
    type="primary",
    use_container_width=True,
):
    load_into_snowflake()

if st.sidebar.button(
    "Carregar dashboard",
    use_container_width=True,
):
    load_from_snowflake()

if "covid_data" not in st.session_state:
    st.info(
        "Carregue os dados no Snowflake e depois carregue o dashboard."
    )
    st.stop()

data = st.session_state["covid_data"]

available_countries = sorted(
    data["location"].dropna().unique().tolist()
)

st.sidebar.divider()
st.sidebar.header("Filtros")

selected_countries = st.sidebar.multiselect(
    "Países",
    options=available_countries,
    default=available_countries,
)

minimum_date = data["date"].min().date()
maximum_date = data["date"].max().date()

selected_period = st.sidebar.date_input(
    "Período",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date,
)

if not selected_countries:
    st.warning("Selecione ao menos um país.")
    st.stop()

if (
    not isinstance(selected_period, (tuple, list))
    or len(selected_period) != 2
):
    st.warning("Selecione as datas inicial e final.")
    st.stop()

start_filter, end_filter = selected_period

filtered = data[
    data["location"].isin(selected_countries)
    & (data["date"].dt.date >= start_filter)
    & (data["date"].dt.date <= end_filter)
].copy()

if filtered.empty:
    st.warning("Não existem dados para os filtros selecionados.")
    st.stop()

latest = (
    filtered.sort_values("date")
    .groupby(
        "location",
        as_index=False,
        group_keys=False,
    )
    .tail(1)
    .copy()
)

total_cases = latest["total_cases"].fillna(0).sum()
total_deaths = latest["total_deaths"].fillna(0).sum()

kpi_cases, kpi_deaths, kpi_countries, kpi_latest = st.columns(4)

kpi_cases.metric(
    "Total de casos",
    format_integer(total_cases),
)

kpi_deaths.metric(
    "Total de óbitos",
    format_integer(total_deaths),
)

kpi_countries.metric(
    "Países analisados",
    latest["location"].nunique(),
)

kpi_latest.metric(
    "Data mais recente",
    latest["date"].max().strftime("%d/%m/%Y"),
)

tab_cases, tab_deaths, tab_vaccines, tab_scatter, tab_raw, tab_sql = st.tabs(
    [
        "Casos",
        "Óbitos",
        "Vacinação",
        "População x casos",
        "Dados brutos",
        "Query SQL",
    ]
)

with tab_cases:
    st.subheader("Evolução de casos novos por país")

    cases_chart = px.line(
        filtered,
        x="date",
        y="new_cases",
        color="location",
        labels={
            "date": "Data",
            "new_cases": "Novos casos",
            "location": "País",
        },
    )

    cases_chart.update_layout(legend_title_text="País")
    st.plotly_chart(cases_chart, use_container_width=True)

with tab_deaths:
    st.subheader("Total de óbitos por país")

    deaths_chart = px.bar(
        latest.sort_values(
            "total_deaths",
            ascending=False,
        ),
        x="location",
        y="total_deaths",
        color="location",
        text_auto=".3s",
        labels={
            "location": "País",
            "total_deaths": "Total de óbitos",
        },
    )

    deaths_chart.update_layout(showlegend=False)
    st.plotly_chart(deaths_chart, use_container_width=True)

with tab_vaccines:
    st.subheader(
        "Proporção da população vacinada com ao menos uma dose"
    )

    vaccination = latest.copy()

    vaccination["vaccinated_pct"] = (
        vaccination["people_vaccinated"]
        / vaccination["population"]
        * 100
    ).clip(lower=0, upper=100)

    vaccine_chart = px.bar(
        vaccination.sort_values(
            "vaccinated_pct",
            ascending=False,
        ),
        x="location",
        y="vaccinated_pct",
        color="location",
        text_auto=".1f",
        range_y=[0, 100],
        labels={
            "location": "País",
            "vaccinated_pct": "População vacinada (%)",
        },
    )

    vaccine_chart.update_layout(showlegend=False)
    st.plotly_chart(vaccine_chart, use_container_width=True)

with tab_scatter:
    st.subheader("Relação entre população e total de casos")

    scatter_chart = px.scatter(
        latest,
        x="population",
        y="total_cases",
        color="location",
        size="population",
        hover_name="location",
        size_max=55,
        labels={
            "population": "População",
            "total_cases": "Total de casos",
            "location": "País",
        },
    )

    st.plotly_chart(scatter_chart, use_container_width=True)

with tab_raw:
    st.subheader("Dados brutos filtrados")

    display_data = filtered.sort_values(
        ["date", "location"],
        ascending=[False, True],
    )

    st.dataframe(
        display_data,
        use_container_width=True,
        hide_index=True,
    )

    csv_bytes = display_data.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Exportar CSV",
        data=csv_bytes,
        file_name=(
            f"covid_owid_"
            f"{date.today().isoformat()}_filtrado.csv"
        ),
        mime="text/csv",
    )

with tab_sql:
    st.subheader("Consulta SQL no Snowflake")
    st.caption(
        "Por segurança, apenas uma instrução SELECT ou WITH é permitida."
    )

    sql_query = st.text_area(
        "SQL",
        value=(
            "SELECT LOCATION, MAX(TOTAL_CASES) AS TOTAL_CASES\n"
            "FROM TEST_DB.PUBLIC.COVID_OWID\n"
            "GROUP BY LOCATION\n"
            "ORDER BY TOTAL_CASES DESC"
        ),
        height=180,
    )

    if st.button("Executar consulta SQL"):
        if not is_read_only_query(sql_query):
            st.error(
                "Digite uma única consulta iniciada por SELECT ou WITH."
            )
        else:
            query_session = None

            try:
                with st.spinner("Executando consulta no Snowflake..."):
                    query_session = open_read_only_session()
                    query_result = query_session.sql(
                        sql_query
                    ).to_pandas()

                st.success(
                    f"Consulta concluída: {len(query_result)} linha(s)."
                )

                st.dataframe(
                    query_result,
                    use_container_width=True,
                    hide_index=True,
                )
            except Exception as error:
                st.error(f"Falha na consulta SQL: {error}")
            finally:
                if query_session is not None:
                    query_session.close()

st.caption(
    "Fonte: Our World in Data - "
    "https://github.com/owid/covid-19-data/tree/master/public/data"
)
