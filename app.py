#!/usr/bin/env python3
# app.py
#
# Full working Flask app: sidebar and map panels, four buttons, export, concept filter.

from flask import Flask, render_template_string, request, url_for, Response
import pandas as pd
import geopandas as gpd
import folium

app = Flask(__name__, static_folder='static')

def load_tsv(path='input.tsv'):
    return pd.read_csv(path, sep='\t')

def load_geojson(path='input.geojson'):
    gdf = gpd.read_file(path)
    if gdf.geometry.is_empty.all():
        # fallback to LONG/LAT columns
        lon_col = [c for c in gdf.columns if c.lower()=='long'][0]
        lat_col = [c for c in gdf.columns if c.lower()=='lat'][0]
        gdf = gpd.GeoDataFrame(gdf,
            geometry=gpd.points_from_xy(gdf[lon_col], gdf[lat_col]), crs='EPSG:4326')
    return gdf.to_crs(epsg=4326)


from shapely.strtree import STRtree


def compare_points(radius):
    # 1) Lees TSV en clean concept-kolom
    df = load_tsv()
    df['concept_clean'] = (
        df['concepts']
        .astype(str)
        .str.split('|')
        .str[0]
        .str.strip()
    )

    # 2) Maak GeoDataFrame van TSV-punten (WGS84)
    gdf_t = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.lon, df.lat),
        crs='EPSG:4326'
    )

    # 3) Laad GeoJSON-reference (WGS84)
    gdf_geo = load_geojson()

    # 4) Projecteer beiden naar metrisch CRS (meters)
    gdf_t_m   = gdf_t.to_crs(epsg=28992)
    gdf_geo_m = gdf_geo.to_crs(epsg=28992)

    # 5) Voor elk TSV-punt: bereken de minimumafstand tot alle geojson-punten
    #    (vermijdt elke join en type-issues)
    min_dists = gdf_t_m.geometry.apply(lambda pt: gdf_geo_m.geometry.distance(pt).min())

    # 6) Markeer matched als afstand ≤ radius
    gdf_t['matched'] = min_dists <= radius

    # 7) Zet terug naar EPSG:4326 voor de kaart
    return gdf_t.to_crs(epsg=4326), gdf_geo



def generate_map_html(center, markers, radius):
    # Maak de kaart met schaalbalk
    m = folium.Map(
        location=center,
        zoom_start=11,
        tiles='OpenStreetMap',
        control_scale=True
    )
    # Voeg per marker zowel het punt als de cirkel met de echte straal toe
    for _, r in markers.iterrows():
        # de punt zelf
        folium.CircleMarker(
            location=[r.geometry.y, r.geometry.x],
            radius=6,
            color=r['color'],
            fill=True,
            fill_color=r['color']
        ).add_to(m)
        # de ring met werkelijke radius in meters, kleur = markerkleur
        folium.Circle(
            location=[r.geometry.y, r.geometry.x],
            radius=radius,          # in meters
            color=r['color'],       # ringkleur overeenkomend met marker
            weight=1,               # lijndikte
            fill=False
        ).add_to(m)
    return m._repr_html_()



# HTML template with sidebar and map panel
TEMPLATE = """<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8">
  <title>Ground-truth status checker</title>
  <style>
    html, body { margin:0; padding:0; height:100vh; }
    header { display:flex; justify-content:space-between; align-items:center; height:4em; padding:0 1em; background:#fff; }
    header img { height:2.5em; }
    .container { display:flex; height:calc(100vh - 4em); }
    .sidebar { width:500px; padding:10px; box-sizing:border-box; overflow-y:auto; border-right:1px solid #ddd; }
    .sidebar form { margin-bottom:1em; }
    form label, form select, form input { display:block; margin:0.5em 0; font-size:1em; }
    .action-btn { padding:10px 20px; margin:5px 0; width:100%; border:none; border-radius:4px; cursor:pointer; color:#fff; font-size:1em; }
    .btn-green { background:#28a745; }
    .btn-orange { background:#ff8c00; }
    .btn-red { background:#dc3545; }
    .btn-white { background:#fff; color:#000; border:1px solid #ccc; }
    .btn-export { background:#007bff; }
    table { width:100%; border-collapse:collapse; margin-top:1em; }
    th, td { padding:8px; text-align:left; }
    th { background:#ccffcc; }
    tr:nth-child(even) { background:#f9f9f9; }
    tr.total { font-weight:bold; background:#ccffcc; }
    .map-panel { flex:1; display:flex; flex-direction:column; }
    .map-container { flex:1; }
    .export-form { text-align:center; margin:10px; }
  </style>
</head>
<body>
<header>
  <div><a href="https://bylifeconnected.example.com" target="_blank"><img src="{{ url_for('static', filename='bylc_logo.png') }}" alt="By Life Connected"></a></div>
  <div>
    <a href="https://sensingclues.example.com" target="_blank"><img src="{{ url_for('static', filename='sensingclues_logo.png') }}" alt="SensingClues"></a>
    <a href="https://3edata.example.com" target="_blank"><img src="{{ url_for('static', filename='3edata_logo.png') }}" alt="3edata"></a>
  </div>
</header>
<div class="container">
  <div class="sidebar">
    <form method="post">
      <label>Radius (m): <input type="number" name="radius" value="{{ radius }}" step="0.1" required></label>
      <label>Concept:
        <select name="concept">
          <option value="All visited locations" {% if selected_concept=='All visited locations' %}selected{% endif %}>All visited locations</option>
          {% for c in concepts %}
            <option value="{{ c }}" {% if c==selected_concept %}selected{% endif %}>{{ c }}</option>
          {% endfor %}
        </select>
      </label>
      <button type="submit" name="action" value="green" class="action-btn btn-green">Show Matched (green)</button>
      <button type="submit" name="action" value="orange" class="action-btn btn-orange">Show Mapped by not matched (orange)</button>
      <button type="submit" name="action" value="red" class="action-btn btn-red">Show Not yet visited (red)</button>
      <button type="submit" name="action" value="all" class="action-btn btn-white">Show all</button>
    </form>
    <table>
      <thead><tr><th>Mapped landcover</th><th>Matched</th><th>Not matched</th></tr></thead>
      <tbody>
        {% for rec in records %}
          <tr {% if rec.concept in ['Total visited','Not yet visited'] %}class="total"{% endif %}>
            <td>{{ rec.concept }}</td><td>{{ rec.green }}</td><td>{{ rec.red }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <div class="map-panel">
    <div class="map-container">{{ map_html|safe }}</div>
<div class="export-form">
  <form method="post">
    <!-- Hidden inputs om radius en concept mee te nemen -->
    <input type="hidden" name="radius" value="{{ radius }}">
    <input type="hidden" name="concept" value="{{ selected_concept }}">
    <button type="submit" name="action" value="export"
            class="action-btn btn-export">
      Export Not yet visited location (GeoJSON)
    </button>
  </form>
</div>

    
  </div>
</div>
</body>
</html>
"""


@app.route('/', methods=['GET','POST'])
def index():
    # 0) Defaults
    radius = 10.0
    selected_concept = 'All visited locations'
    action = 'green'

    # 1) Read form overrides
    if request.form:
        radius = float(request.form.get('radius', radius))
        selected_concept = request.form.get('concept', selected_concept)
        action = request.form.get('action', action)

    # DEBUG: print selected parameters
    print("DEBUG total TSV points:", len(load_tsv()))
    print("DEBUG total geojson points:", len(load_geojson()))
    print("DEBUG Selected Radius:", radius)

    # 2) Load and project data
    gdf_t, gdf_geo = compare_points(radius)
    gdf_t_m   = gdf_t.to_crs(epsg=28992)
    gdf_geo_m = gdf_geo.to_crs(epsg=28992)

    # 3) Build union buffers
    union_geo_buffer = gpd.GeoSeries(
        gdf_geo_m.geometry.buffer(radius), crs=gdf_geo_m.crs
    ).unary_union
    union_tsv_buffer = gpd.GeoSeries(
        gdf_t_m.geometry.buffer(radius), crs=gdf_t_m.crs
    ).unary_union

    # 4) Assign matched/visited
    gdf_t['matched'] = gdf_t_m.geometry.apply(
        lambda pt: union_geo_buffer.contains(pt)
    )
    gdf_geo['visited'] = gdf_geo_m.geometry.apply(
        lambda pt: union_tsv_buffer.contains(pt)
    )

    # DEBUG: visited counts
    vc = gdf_geo['visited'].value_counts().to_dict()
    print("DEBUG visited counts:", vc)

    # 5) Build TSV summary table
    concepts = sorted(gdf_t['concept_clean'].unique())
    records = []
    total_matched = total_notmatch = 0
    for c in concepts:
        subset = gdf_t[gdf_t['concept_clean'] == c]
        m = int(subset['matched'].sum())
        nm = len(subset) - m
        records.append({'concept': c, 'green': m, 'red': nm})
        total_matched += m
        total_notmatch += nm

    # DEBUG: TSV totals
    print("DEBUG total_matched:", total_matched)
    print("DEBUG total_notmatch:", total_notmatch)

    # 6) Not yet visited count
    not_visited = int((~gdf_geo['visited']).sum())
    print("DEBUG not_visited (calc):", not_visited)
    records.append({'concept': 'Total visited', 'green': total_matched, 'red': total_notmatch})
    records.append({'concept': 'Not yet visited', 'green': '', 'red': not_visited})

       # 7) Export: gebruik de bestaande visited‐flags
    # → not_visited is al berekend als:
    not_visited = int((~gdf_geo['visited']).sum())


    # Export-sectie
    if action == 'export':
        # 1) pak alle geojson-punten die niet bezocht zijn
        unv = gdf_geo[~gdf_geo['visited']].copy()
        print("DEBUG export count (len(unv)):", len(unv))
        # 2) markeer ze geel
        unv['marker-color'] = '#FFFF00'
        # 3) bouw de bestandsnaam op basis van de telling uit je debug
        filename = f"Groundtruth_{not_visited}_points.geojson"
        # 4) return exact díe punten
        return Response(
            unv.to_json(),
            mimetype='application/geo+json',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )



    # 8) Marker selection
    if action == 'green':
        markers = gdf_t[gdf_t['matched']].copy()
        if selected_concept != 'All visited locations':
            markers = markers[markers['concept_clean'] == selected_concept]
        markers['color'] = 'green'
    elif action == 'orange':
        markers = gdf_t[~gdf_t['matched']].copy()
        if selected_concept != 'All visited locations':
            markers = markers[markers['concept_clean'] == selected_concept]
        markers['color'] = 'orange'
    elif action == 'red':
        markers = gdf_geo[~gdf_geo['visited']].copy()
        markers['color'] = 'red'
    else:
        m1 = gdf_t[gdf_t['matched']].copy(); m1['color'] = 'green'
        m2 = gdf_t[~gdf_t['matched']].copy(); m2['color'] = 'orange'
        m3 = gdf_geo[~gdf_geo['visited']].copy(); m3['color'] = 'red'
        markers = pd.concat([m1, m2, m3], ignore_index=True)

    # 9) Center & render map
    if not markers.empty:
        center = [markers.geometry.y.mean(), markers.geometry.x.mean()]
    else:
        center = [0, 0]
    map_html = generate_map_html(center, markers, radius)

    # 10) Render template
    return render_template_string(
        TEMPLATE,
        radius=radius,
        selected_concept=selected_concept,
        concepts=concepts,
        records=records,
        map_html=map_html
    )



if __name__=='__main__':
    app.run(debug=True, port=5002)
