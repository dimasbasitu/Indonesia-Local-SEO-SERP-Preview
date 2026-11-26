import json
import urllib.request

# Mapping nama Provinsi Indonesia ke standar Canonical Name Bahasa Inggris Google Ads
PROV_MAP = {
    "ACEH": ("Aceh", "Aceh"),
    "SUMATERA UTARA": ("Sumatera Utara", "North Sumatra"),
    "SUMATERA BARAT": ("Sumatera Barat", "West Sumatra"),
    "RIAU": ("Riau", "Riau"),
    "JAMBI": ("Jambi", "Jambi"),
    "SUMATERA SELATAN": ("Sumatera Selatan", "South Sumatra"),
    "BENGKULU": ("Bengkulu", "Bengkulu"),
    "LAMPUNG": ("Lampung", "Lampung"),
    "KEPULAUAN BANGKA BELITUNG": ("Kepulauan Bangka Belitung", "Bangka Belitung Islands"),
    "KEPULAUAN RIAU": ("Kepulauan Riau", "Riau Islands"),
    "DKI JAKARTA": ("DKI Jakarta", "Jakarta"),
    "JAWA BARAT": ("Jawa Barat", "West Java"),
    "JAWA TENGAH": ("Jawa Tengah", "Central Java"),
    "DI YOGYAKARTA": ("DI Yogyakarta", "Special Region of Yogyakarta"),
    "JAWA TIMUR": ("Jawa Timur", "East Java"),
    "BANTEN": ("Banten", "Banten"),
    "BALI": ("Bali", "Bali"),
    "NUSA TENGGARA BARAT": ("Nusa Tenggara Barat", "West Nusa Tenggara"),
    "NUSA TENGGARA TIMUR": ("Nusa Tenggara Timur", "East Nusa Tenggara"),
    "KALIMANTAN BARAT": ("Kalimantan Barat", "West Kalimantan"),
    "KALIMANTAN TENGAH": ("Kalimantan Tengah", "Central Kalimantan"),
    "KALIMANTAN SELATAN": ("Kalimantan Selatan", "South Kalimantan"),
    "KALIMANTAN TIMUR": ("Kalimantan Timur", "East Kalimantan"),
    "KALIMANTAN UTARA": ("Kalimantan Utara", "North Kalimantan"),
    "SULAWESI UTARA": ("Sulawesi Utara", "North Sulawesi"),
    "SULAWESI TENGAH": ("Sulawesi Tengah", "Central Sulawesi"),
    "SULAWESI SELATAN": ("Sulawesi Selatan", "South Sulawesi"),
    "SULAWESI TENGGARA": ("Sulawesi Tenggara", "Southeast Sulawesi"),
    "GORONTALO": ("Gorontalo", "Gorontalo"),
    "SULAWESI BARAT": ("Sulawesi Barat", "West Sulawesi"),
    "MALUKU": ("Maluku", "Maluku"),
    "MALUKU UTARA": ("Maluku Utara", "North Maluku"),
    "PAPUA BARAT": ("Papua Barat", "West Papua"),
    "PAPUA": ("Papua", "Papua"),
    "PAPUA SELATAN": ("Papua Selatan", "South Papua"),
    "PAPUA TENGAH": ("Papua Tengah", "Central Papua"),
    "PAPUA PEGUNUNGAN": ("Papua Pegunungan", "Highland Papua"),
    "PAPUA BARAT DAYA": ("Papua Barat Daya", "Southwest Papua")
}

def fetch_json(url: str):
    """Mengambil data JSON dengan User-Agent browser agar tidak terkena blokir 403."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=20) as res:
        return json.loads(res.read().decode("utf-8"))

def format_regency_canonical(raw_name: str, eng_prov: str) -> tuple:
    name_title = raw_name.title()
    if raw_name.upper().startswith("KABUPATEN "):
        clean_name = name_title.replace("Kabupaten ", "").strip()
        label_id = f"Kabupaten {clean_name}"
        canonical = f"{clean_name} Regency,{eng_prov},Indonesia"
    elif raw_name.upper().startswith("KOTA ADM. "):
        clean_name = name_title.replace("Kota Adm. ", "").strip()
        label_id = f"Kota {clean_name}"
        canonical = f"{clean_name},{eng_prov},Indonesia"
    elif raw_name.upper().startswith("KAB. ADM. "):
        clean_name = name_title.replace("Kab. Adm. ", "").strip()
        label_id = f"Kabupaten {clean_name}"
        canonical = f"{clean_name} Regency,{eng_prov},Indonesia"
    elif raw_name.upper().startswith("KOTA "):
        clean_name = name_title.replace("Kota ", "").strip()
        label_id = f"Kota {clean_name}"
        canonical = f"{clean_name},{eng_prov},Indonesia"
    else:
        label_id = name_title
        canonical = f"{name_title},{eng_prov},Indonesia"
    return label_id, canonical

def main():
    print("Mengunduh daftar Provinsi dan Kota/Kabupaten se-Indonesia...")
    base_url = "https://emsifa.github.io/api-wilayah-indonesia/api"
    
    provinces = fetch_json(f"{base_url}/provinces.json")
        
    locations = {
        "Indonesia (Nasional)": {
            "Seluruh Indonesia (Nasional)": {
                "canonical": "Indonesia",
                "gl": "id",
                "hl": "id"
            }
        }
    }
    
    total_cities = 0
    for prov in provinces:
        prov_id = prov["id"]
        raw_prov_name = prov["name"].upper()
        id_prov_label, eng_prov_name = PROV_MAP.get(raw_prov_name, (prov["name"].title(), prov["name"].title()))
        
        locations[id_prov_label] = {
            f"Seluruh Provinsi {id_prov_label}": {
                "canonical": f"{eng_prov_name},Indonesia",
                "gl": "id",
                "hl": "id"
            }
        }
        
        regencies = fetch_json(f"{base_url}/regencies/{prov_id}.json")
            
        for reg in sorted(regencies, key=lambda x: x["name"]):
            label_id, canonical_str = format_regency_canonical(reg["name"], eng_prov_name)
            locations[id_prov_label][label_id] = {
                "canonical": canonical_str,
                "gl": "id",
                "hl": "id"
            }
            total_cities += 1

    with open("locations.json", "w", encoding="utf-8") as f:
        json.dump(locations, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Berhasil! File 'locations.json' telah dibuat dengan {len(provinces)} Provinsi dan {total_cities} Kota/Kabupaten.")

if __name__ == "__main__":
    main()
