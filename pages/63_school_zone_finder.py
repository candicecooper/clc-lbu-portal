"""
63_school_zone_finder.py
CLC-LBU Staff Portal — School Zone Finder

Enter a South Australian address → shows which government PRIMARY and
HIGH school zones (catchments) the address falls inside, on a map.

DATA
  Official DfE school zone shapefiles (CC BY 4.0) from data.sa.gov.au:
    Primary: https://data.sa.gov.au/data/dataset/school-zones-for-south-australian-govt-primary-schools
    High:    https://data.sa.gov.au/data/dataset/school-zones-for-south-australian-government-high-schools-2015
  Upload the .zip files UNCHANGED into the repo folder  data/school_zones/
  (GitHub web UI → Add file → Upload files). The year and type are read from
  the file name, e.g. PrimarySchoolZones2025EY.zip / highschoolzones2023ey.zip.

PRIVACY
  The typed address is sent to OpenStreetMap (Nominatim) to get coordinates.
  Nothing is saved, cached or logged by this tool.

REQUIREMENTS (add to requirements.txt)
  pyshp
  shapely
  pyproj
  requests
  (pydeck ships with Streamlit)
"""

import io
import re
import zipfile
from datetime import date
from pathlib import Path

import pydeck as pdk
import requests
import shapefile  # pyshp
import streamlit as st
from pyproj import CRS, Transformer
from shapely.geometry import Point, mapping, shape
from shapely.ops import transform as shp_transform
from shapely.prepared import prep

try:
    st.set_page_config(page_title="School Zone Finder", page_icon="🏫", layout="wide")
except Exception:
    pass  # already set by the portal shell

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "CLC-LBU-Staff-Portal/1.0 (clc.digitalstaffmeeting@gmail.com)"
SA_VIEWBOX = "129.0,-25.9,141.0,-38.2"  # lon/lat box around South Australia
DFE_FIND_TOOL = (
    "https://www.education.sa.gov.au/parents-and-families/enrol-school-or-preschool/"
    "find-school-zone-or-catchment-area"
)
NAME_FIELD_HINTS = ("SCHOOL_NAM", "SCHOOLNAME", "SCHOOL", "SITE_NAME", "SITENAME", "NAME")


def zones_dir() -> Path:
    """Find data/school_zones whether this page lives in /pages or the repo root."""
    here = Path(__file__).resolve().parent
    for base in (here, here.parent, Path.cwd()):
        cand = base / "data" / "school_zones"
        if cand.is_dir():
            return cand
    return here.parent / "data" / "school_zones"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def classify_zip(name: str):
    """Return (kind, year) from a DfE zip file name, or (None, None)."""
    low = name.lower()
    kind = "primary" if ("primary" in low or "prim" in low) else "high" if ("high" in low or "secondary" in low) else None
    m = re.search(r"(20\d{2})", low)
    return kind, (int(m.group(1)) if m else None)


def pick_name_field(field_names):
    upper = [f.upper() for f in field_names]
    for hint in NAME_FIELD_HINTS:
        for i, f in enumerate(upper):
            if f == hint:
                return field_names[i]
    for hint in NAME_FIELD_HINTS:
        for i, f in enumerate(upper):
            if hint in f:
                return field_names[i]
    return field_names[0] if field_names else None


def _collect_shapefiles(data: bytes, found=None, depth=0):
    """Find every shapefile in a zip, including zips nested inside the zip."""
    found = [] if found is None else found
    zf = zipfile.ZipFile(io.BytesIO(data))
    names = [n for n in zf.namelist() if not n.startswith("__MACOSX")]
    for n in names:
        low = n.lower()
        if low.endswith(".zip") and depth < 3:
            _collect_shapefiles(zf.read(n), found, depth + 1)
        elif low.endswith(".shp"):
            stem = n[:-4]
            parts = {}
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                m = next((x for x in names if x.lower() == (stem + ext).lower()), None)
                if m:
                    parts[ext] = zf.read(m)
            found.append((n, parts))
    return found


def load_zip_bytes(data: bytes):
    """Read a zipped shapefile → dict with polygons (in native CRS) + CRS info."""
    candidates = []
    for shp_name, parts in _collect_shapefiles(data):
        if ".dbf" not in parts:
            continue
        try:
            r = shapefile.Reader(shp=io.BytesIO(parts[".shp"]), dbf=io.BytesIO(parts[".dbf"]),
                                 shx=io.BytesIO(parts[".shx"]) if ".shx" in parts else None)
            if r.shapeType in (shapefile.POLYGON, shapefile.POLYGONZ, shapefile.POLYGONM):
                candidates.append((len(r), shp_name, r, parts))
        except Exception:
            continue
    if not candidates:
        raise ValueError("No polygon shapefile found inside the zip (checked nested zips too)")
    _, shp, reader, parts = max(candidates, key=lambda c: c[0])
    prj_wkt = parts.get(".prj", b"").decode("utf-8", "ignore")
    fields = [f[0] for f in reader.fields[1:]]
    name_field = pick_name_field(fields)

    # CRS handling: point → native CRS for the test; matched polygons → WGS84 for the map
    to_native = to_wgs84 = None
    if prj_wkt:
        crs = CRS.from_wkt(prj_wkt)
        if crs.is_projected or crs.to_epsg() not in (4326, 4283, 7844, None):
            to_native = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
            to_wgs84 = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)

    zones = []
    for sr in reader.iterShapeRecords():
        if not sr.shape.points:
            continue
        geom = shape(sr.shape.__geo_interface__)
        if not geom.is_valid:
            geom = geom.buffer(0)
        attrs = {k: (v.strip() if isinstance(v, str) else v) for k, v in zip(fields, sr.record)}
        zones.append({
            "name": str(attrs.get(name_field, "Unnamed zone")).strip() or "Unnamed zone",
            "attrs": attrs,
            "geom": geom,
            "prepared": prep(geom),
        })
    return {"zones": zones, "fields": fields, "name_field": name_field,
            "to_native": to_native, "to_wgs84": to_wgs84, "shp": shp,
            "crs_note": (CRS.from_wkt(prj_wkt).name if prj_wkt else "no .prj — assumed lat/lon")}


@st.cache_resource(show_spinner="Loading school zone boundaries…")
def load_dataset(path_str: str, mtime: float):
    return load_zip_bytes(Path(path_str).read_bytes())


def available_datasets():
    """{'primary': {2025: Path, ...}, 'high': {...}, 'unrecognised': [names]}"""
    out = {"primary": {}, "high": {}, "unrecognised": []}
    d = zones_dir()
    if not d.is_dir():
        return out
    for p in sorted(d.iterdir()):
        if p.name.lower() == "readme.md" or p.is_dir():
            continue
        kind, year = classify_zip(p.name)
        if p.suffix.lower().rstrip("_") == ".zip" and kind and year:
            out[kind][year] = p
        else:
            out["unrecognised"].append(p.name)
    return out


def safe_load(p: Path):
    try:
        return load_dataset(str(p), p.stat().st_mtime), None
    except Exception as e:
        return None, f"{e.__class__.__name__}: {e}"


def zones_containing(ds, lon, lat):
    x, y = (ds["to_native"].transform(lon, lat) if ds["to_native"] else (lon, lat))
    pt = Point(x, y)
    return [z for z in ds["zones"] if z["prepared"].covers(pt)]


def to_wgs84_geojson(ds, zone):
    g = zone["geom"]
    if ds["to_wgs84"]:
        g = shp_transform(ds["to_wgs84"].transform, g)
    return mapping(g.simplify(0.00005, preserve_topology=True))


# ---------------------------------------------------------------------------
# Geocoding (not cached, not stored)
# ---------------------------------------------------------------------------
def geocode(address: str):
    q = address.strip()
    if "south australia" not in q.lower() and not re.search(r"\bSA\b", q):
        q += ", South Australia"
    r = requests.get(
        NOMINATIM_URL,
        params={"q": q, "format": "jsonv2", "countrycodes": "au", "limit": 5,
                "viewbox": SA_VIEWBOX, "bounded": 1, "addressdetails": 0},
        headers={"User-Agent": USER_AGENT},
        timeout=15,
    )
    r.raise_for_status()
    return [{"label": h["display_name"], "lat": float(h["lat"]), "lon": float(h["lon"]),
             "type": h.get("addresstype") or h.get("type", "")} for h in r.json()]


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("🏫 School Zone Finder")
st.caption("Find the government primary and high school zones an SA address sits inside.")

datasets = available_datasets()
if not datasets["primary"] and not datasets["high"]:
    st.error(
        f"No school zone files found in `{zones_dir()}`.\n\n"
        "Download the zone .zip files from data.sa.gov.au and upload them (unchanged) "
        "into `data/school_zones/` in the GitHub repo."
    )
    st.stop()

with st.sidebar:
    st.subheader("Zone data")
    chosen = {}
    for kind, label in (("primary", "Primary zones"), ("high", "High school zones")):
        years = sorted(datasets[kind], reverse=True)
        if years:
            chosen[kind] = st.selectbox(f"{label} — enrolment year", years, index=0, key=f"yr_{kind}")
        else:
            st.caption(f"{label}: no file uploaded")
    st.caption("Source: SA Department for Education via data.sa.gov.au (CC BY 4.0)")
    with st.expander("Data check"):
        st.caption(f"Folder: `{zones_dir()}`")
        for kind, label in (("primary", "Primary"), ("high", "High school")):
            if kind not in chosen:
                st.markdown(f"**{label}:** ❌ no recognised file")
                continue
            p = datasets[kind][chosen[kind]]
            ds_chk, err = safe_load(p)
            if err:
                st.markdown(f"**{label}:** ❌ `{p.name}` failed to load")
                st.code(err)
            else:
                st.markdown(f"**{label}:** ✅ `{p.name}` — {len(ds_chk['zones'])} zones  \n"
                            f"Name field: `{ds_chk['name_field']}` · CRS: {ds_chk['crs_note']}")
        if datasets["unrecognised"]:
            st.markdown("**Ignored files** (name must be a .zip containing a year and "
                        "'primary' or 'high'):")
            for n in datasets["unrecognised"]:
                st.markdown(f"- `{n}`")

this_year = date.today().year
stale = [f"{'Primary' if k == 'primary' else 'High school'} zones are for {y}"
         for k, y in chosen.items() if y < this_year]
if stale:
    st.warning(
        "Heads up: " + "; ".join(stale) + ". Zones are redrawn most years, so treat results "
        f"as a guide and confirm with the [DfE Find a school zone tool]({DFE_FIND_TOOL}) "
        "before advising a family."
    )

st.info("The address is sent to OpenStreetMap to find its location. Nothing is saved.", icon="🔒")

with st.form("zone_search", clear_on_submit=False):
    address = st.text_input("Address", placeholder="e.g. 12 Example Street, Cowandilla")
    submitted = st.form_submit_button("Find zones", type="primary")

if submitted:
    st.session_state.pop("szf_hits", None)
    st.session_state.pop("szf_pick", None)
    if not address.strip():
        st.warning("Enter an address first.")
    else:
        try:
            with st.spinner("Finding address…"):
                st.session_state["szf_hits"] = geocode(address)
        except requests.RequestException as e:
            st.error(f"Couldn't reach the address lookup service ({e.__class__.__name__}). Try again in a moment.")

hits = st.session_state.get("szf_hits")
if hits is not None and not hits:
    st.error("No South Australian match for that address. Check the spelling and include the suburb.")

if hits:
    if len(hits) > 1:
        idx = st.radio("Several matches found — pick the right one:",
                       range(len(hits)), format_func=lambda i: hits[i]["label"], key="szf_pick")
    else:
        idx = 0
    hit = hits[idx]
    if hit["type"] not in ("house", "building", "place", "road", ""):
        st.caption(f"Matched to a {hit['type']} (not an exact house) — "
                   "results near a zone boundary may be off.")
    else:
        st.caption(f"📍 {hit['label']}")

    lon, lat = hit["lon"], hit["lat"]
    layers, result_cols = [], st.columns(2)
    colours = {"primary": [37, 99, 235], "high": [22, 163, 74]}

    for col, kind, label in ((result_cols[0], "primary", "Primary school zone"),
                             (result_cols[1], "high", "High school zone")):
        with col:
            st.subheader(label)
            if kind not in chosen:
                st.caption("No zone file uploaded for this level.")
                continue
            p = datasets[kind][chosen[kind]]
            ds, err = safe_load(p)
            if err:
                st.error(f"Couldn't read `{p.name}` — see Data check in the sidebar.")
                continue
            matches = zones_containing(ds, lon, lat)
            if not matches:
                st.markdown(
                    "**Not inside a zoned school.** Only some SA schools have a zone "
                    f"({len(ds['zones'])} {'primary' if kind == 'primary' else 'high school'} zones in this file). In SA, schools without a zone take students "
                    "from any area — usually the closest school is the local option. "
                    f"Check the [DfE tool]({DFE_FIND_TOOL}) for the closest school."
                )
            for z in matches:
                st.markdown(f"### {z['name']}")
                with st.expander("Zone record details"):
                    st.json({k: str(v) for k, v in z["attrs"].items()})
                layers.append(pdk.Layer(
                    "GeoJsonLayer",
                    {"type": "Feature", "geometry": to_wgs84_geojson(ds, z), "properties": {"name": z["name"]}},
                    stroked=True, filled=True,
                    get_fill_color=colours[kind] + [45], get_line_color=colours[kind] + [220],
                    line_width_min_pixels=2, pickable=True,
                ))
            if len(matches) > 1:
                st.caption("The address sits inside more than one zone (shared or overlapping zones) — "
                           "the family has priority at each.")

    layers.append(pdk.Layer(
        "ScatterplotLayer", [{"lon": lon, "lat": lat}], get_position="[lon, lat]",
        get_fill_color=[220, 38, 38, 255], get_radius=40, radius_min_pixels=6,
    ))
    st.pydeck_chart(pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=12),
        tooltip={"text": "{name}"},
    ))
    st.caption("🔵 Primary zone   🟢 High school zone   🔴 Address")

st.divider()
st.caption(
    "Government schools only — independent and Catholic schools set their own enrolment areas. "
    "Living in a zone gives priority enrolment; it doesn't guarantee a particular program or class. "
    f"Always confirm current zones with the [Department for Education]({DFE_FIND_TOOL})."
)
