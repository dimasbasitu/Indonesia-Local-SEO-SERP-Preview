import json
import os

import streamlit as st

from renderer import build_serp_viewer
from scraper import SerperError, run_serp_check


st.set_page_config(page_title="Indonesia SERP Preview", layout="wide")


@st.cache_data
def load_locations():
    with open("locations.json", "r", encoding="utf-8") as file:
        return json.load(file)


def get_api_key() -> str:
    env_key = os.environ.get("SERPER_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        return str(st.secrets.get("SERPER_API_KEY", "")).strip()
    except (FileNotFoundError, KeyError):
        return ""


LOCATIONS = load_locations()
API_KEY = get_api_key()

st.html("""
<style>
.stMainBlockContainer { max-width: 2000px; padding: 2rem 2.25rem 3rem; }
[data-testid="stLayoutWrapper"]:has(> .st-key-search_controls) { position: sticky; top: 3.75rem; z-index: 100; background: var(--background-color, Canvas); padding: .75rem 0; border-bottom: 1px solid #80808040; }
iframe[title="streamlit.components.v1.html"] { border-radius: 14px; }
@media (max-width: 900px) {
  .stMainBlockContainer { padding: 1.25rem 1rem 2rem; }
  [data-testid="stLayoutWrapper"]:has(> .st-key-search_controls) { position: static; }
}
</style>
""")

st.title("Indonesia SERP Preview")
st.caption("Preview hasil Google dan raw JSON yang tersinkronisasi melalui Serper.dev")

if not API_KEY:
    st.error("API key belum tersedia. Isi SERPER_API_KEY melalui environment variable atau .streamlit/secrets.toml.")

with st.container(key="search_controls"):
    col_kw, col_prov, col_city, col_btn = st.columns([3, 2, 2.5, 1.4])
    with col_kw:
        keyword = st.text_input("Search Query", value="")
    with col_prov:
        provinces = list(LOCATIONS.keys())
        default_idx = provinces.index("DI Yogyakarta") if "DI Yogyakarta" in provinces else 0
        selected_province = st.selectbox("Provinsi", provinces, index=default_idx)
    with col_city:
        cities = LOCATIONS[selected_province]
        selected_city = st.selectbox("Kota / Kabupaten", list(cities.keys()))
        location = cities[selected_city]
    with col_btn:
        st.write("")
        st.write("")
        run_button = st.button("Cek SERP", width="stretch", type="primary", disabled=not API_KEY)
    st.caption(f"Target Google: `{location['canonical']}` · gl={location['gl']} · hl={location['hl']}")

st.divider()

if run_button and not keyword.strip():
    st.warning("Isi Search Query terlebih dahulu.")

if not run_button and "serp_result" not in st.session_state:
    st.info("Belum ada hasil. Isi kata kunci dan pilih lokasi, lalu tekan Cek SERP.")

if run_button and keyword.strip():
    st.session_state.pop("serp_result", None)
    with st.spinner(f"Mengambil SERP '{keyword}' untuk {selected_city}..."):
        try:
            result = run_serp_check(
                keyword=keyword.strip(),
                canonical_loc=location["canonical"],
                gl=location["gl"],
                hl=location["hl"],
                api_key=API_KEY,
            )
            st.session_state["serp_result"] = result
        except SerperError as exc:
            st.error(str(exc))
        except Exception:
            st.error("Terjadi kesalahan yang tidak terduga saat memproses hasil.")

if "serp_result" in st.session_state:
    result = st.session_state["serp_result"]
    search_parameters = result.get("searchParameters", {})
    location_used = search_parameters.get("location")
    if location_used:
        st.caption(f"Lokasi respons Serper: {location_used}")
    st.iframe(build_serp_viewer(result), height=1038, width="stretch")
