import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# -----------------------------------------------------------
# Configuración
# -----------------------------------------------------------
st.set_page_config(page_title="Pokédex Dashboard", layout="wide")

# ----------------------------------------------------------
# Carga de datos
# -----------------------------------------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Encabezados esperados (según guía)
    expected = ["ID","Nombre","Tipo","País","Total","HP","Ataque","Defensa","Sp. Atk","Sp. Def","Velocidad"]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en el CSV: {missing}. Encontradas: {list(df.columns)}")

    # Asegurar tipos numéricos
    numeric_cols = ["Total","HP","Ataque","Defensa","Sp. Atk","Sp. Def","Velocidad"]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Precalcular lista de tipos
    df["Tipos_list"] = df["Tipo"].fillna("").str.split("/")
    return df

csv_path = "pokedex_enriquecida.csv"
if not Path(csv_path).exists():
    st.error("No se encontró 'pokedex_enriquecida.csv' en la misma carpeta que app.py.")
    st.stop()

df = load_data(csv_path)

# -----------------------------------------------------------
# Sidebar: controles
# -----------------------------------------------------------
st.sidebar.header("Controles")
vista = st.sidebar.selectbox("Vista", ["Explorador de combate", "Geografía Pokémon", "Comparación"])

paises = sorted([p for p in df["País"].dropna().unique()])
tipos_unicos = sorted(set(t for sub in df["Tipo"].dropna().str.split("/") for t in sub))

sel_paises = st.sidebar.multiselect("País", options=paises, default=paises[:10] if len(paises) > 10 else paises)
sel_tipos = st.sidebar.multiselect("Tipo", options=tipos_unicos, default=tipos_unicos)

min_total, max_total = int(df["Total"].min()), int(df["Total"].max())
rango_total = st.sidebar.slider("Rango de Total", min_value=min_total, max_value=max_total, value=(min_total, max_total))

# -----------------------------------------------------------
# Filtrado
# -----------------------------------------------------------
mask_pais = df["País"].isin(sel_paises) if sel_paises else True
mask_total = df["Total"].between(rango_total[0], rango_total[1])

def tiene_tipo(row_tipos, seleccion):
    return any(t in seleccion for t in row_tipos) if seleccion else True

mask_tipo = df["Tipos_list"].apply(lambda ts: tiene_tipo(ts, sel_tipos))
df_f = df[mask_pais & mask_tipo & mask_total].copy()

# -----------------------------------------------------------
# Cabecera
# -----------------------------------------------------------
st.title("Pokédex Interactiva")
st.caption("Exploración y visualización de estadísticas de Pokémon")

# -----------------------------------------------------------
# Vistas
# -----------------------------------------------------------
if vista == "Explorador de combate":
    col1, col2, col3, col4 = st.columns(4)

    if df_f.empty:
        for c in (col1, col2, col3, col4):
            c.write("Sin datos con los filtros actuales.")
    else:
        idx_total = df_f["Total"].idxmax()
        idx_vel   = df_f["Velocidad"].idxmax()
        idx_atk   = df_f["Ataque"].idxmax()
        idx_def   = df_f["Defensa"].idxmax()

        col1.metric("Máx Total", f'{int(df_f.loc[idx_total, "Total"])}', help=f'Pokémon: {df_f.loc[idx_total, "Nombre"]}')
        col2.metric("Máx Velocidad", f'{int(df_f.loc[idx_vel, "Velocidad"])}', help=f'Pokémon: {df_f.loc[idx_vel, "Nombre"]}')
        col3.metric("Máx Ataque", f'{int(df_f.loc[idx_atk, "Ataque"])}', help=f'Pokémon: {df_f.loc[idx_atk, "Nombre"]}')
        col4.metric("Máx Defensa", f'{int(df_f.loc[idx_def, "Defensa"])}', help=f'Pokémon: {df_f.loc[idx_def, "Nombre"]}')

    st.subheader("Ataque vs Defensa")
    if df_f.empty:
        st.info("Sin datos para graficar.")
    else:
        fig_scatter = px.scatter(
            df_f, x="Ataque", y="Defensa", color="Tipo",
            hover_data=["Nombre","País","Total","Velocidad","HP","Sp. Atk","Sp. Def"]
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("Distribución de HP")
    if df_f.empty:
        st.info("Sin datos para graficar.")
    else:
        fig_hist = px.histogram(df_f, x="HP", nbins=30)
        st.plotly_chart(fig_hist, use_container_width=True)

    st.subheader("Tabla filtrada")
    st.dataframe(
        df_f[["ID","Nombre","Tipo","País","Total","HP","Ataque","Defensa","Sp. Atk","Sp. Def","Velocidad"]],
        use_container_width=True
    )

elif vista == "Geografía Pokémon":
    st.subheader("Promedio de 'Total' por país")
    if df_f.empty:
        st.info("Sin datos con los filtros actuales.")
        promedio_pais = pd.DataFrame(columns=["País","Total"])
    else:
        promedio_pais = (
            df_f.groupby("País", as_index=False)["Total"]
               .mean()
               .sort_values("Total", ascending=False)
        )
    if not promedio_pais.empty:
        fig_map = px.choropleth(
            promedio_pais,
            locations="País", locationmode="country names", color="Total", hover_name="País"
        )
        st.plotly_chart(fig_map, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("Top 10 Pokémon por 'Total' (según filtros)")
        if df_f.empty:
            st.info("Sin datos para graficar.")
        else:
            top10 = df_f.sort_values("Total", ascending=False).head(10)
            fig_bar = px.bar(top10, x="Total", y="Nombre", orientation="h", hover_data=["Tipo","País"])
            st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        st.markdown("Distribución de tipos (según filtros)")
        if df_f.empty:
            st.info("Sin datos para graficar.")
        else:
            tipos_series = (
                df_f["Tipo"].str.split("/").explode().dropna().astype(str).str.strip()
            )
            conteo_tipos = (
                tipos_series.value_counts().rename_axis("Tipo").reset_index(name="Conteo")
                .sort_values("Conteo", ascending=False)
            )
            if conteo_tipos.empty:
                st.info("Sin datos para graficar.")
            else:
                fig_tipos = px.bar(conteo_tipos, x="Conteo", y="Tipo", orientation="h")
                st.plotly_chart(fig_tipos, use_container_width=True)

else:  # Comparación
    st.subheader("Comparación por tipo: Ataque / Defensa / Velocidad (promedios)")
    if df_f.empty:
        st.info("Sin datos con los filtros actuales.")
    else:
        # Explota tipos para comparar correctamente por cada tipo
        df_tipo = df_f.assign(TipoUnidad=df_f["Tipo"].str.split("/")).explode("TipoUnidad")
        agg = df_tipo.groupby("TipoUnidad", as_index=False)[["Ataque","Defensa","Velocidad"]].mean()
        melt = agg.melt(id_vars="TipoUnidad", var_name="Métrica", value_name="Promedio")
        fig_group = px.bar(melt, x="TipoUnidad", y="Promedio", color="Métrica", barmode="group")
        st.plotly_chart(fig_group, use_container_width=True)

    st.subheader("Boxplot de HP por tipo")
    if df_f.empty:
        st.info("Sin datos para graficar.")
    else:
        df_tipo = df_f.assign(TipoUnidad=df_f["Tipo"].str.split("/")).explode("TipoUnidad")
        fig_box = px.box(df_tipo.dropna(subset=["TipoUnidad"]), x="TipoUnidad", y="HP", points=False)
        st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("Top-10 vs Resto vs Global (Total promedio)")
    if df_f.empty:
        st.info("Sin datos para graficar.")
    else:
        top10 = df_f.nlargest(10, "Total")
        resto = df_f[~df_f.index.isin(top10.index)]
        cmp = pd.DataFrame({
            "Grupo": ["Top10","Resto","Global"],
            "Promedio_Total": [
                top10["Total"].mean() if not top10.empty else float("nan"),
                resto["Total"].mean() if not resto.empty else float("nan"),
                df_f["Total"].mean()
            ]
        })
        cmp["Gap_vs_Global"] = cmp["Promedio_Total"] - cmp.loc[cmp["Grupo"]=="Global","Promedio_Total"].values[0]
        fig_cmp = px.bar(cmp, x="Grupo", y="Promedio_Total", text=cmp["Gap_vs_Global"].round(1))
        st.plotly_chart(fig_cmp, use_container_width=True)

    st.subheader("Fire vs Water (Total promedio)")
    if df_f.empty:
        st.info("Sin datos para comparar.")
    else:
        fire = df_f[df_f["Tipo"].str.contains("Fire", na=False)]
        water = df_f[df_f["Tipo"].str.contains("Water", na=False)]
        c1, c2, c3 = st.columns(3)
        c1.metric("Promedio Global", f'{df_f["Total"].mean():.1f}')
        c2.metric("Promedio Fire", f'{fire["Total"].mean():.1f}' if not fire.empty else "N/D")
        c3.metric("Promedio Water", f'{water["Total"].mean():.1f}' if not water.empty else "N/D")

