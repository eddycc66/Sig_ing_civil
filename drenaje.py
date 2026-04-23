import processing

# ----------------------------------
# 1. Obtener la capa DEM cargada
# ----------------------------------
dem = QgsProject.instance().mapLayersByName('dem')[0]

# ----------------------------------
# 2. Carpeta de salida
# ----------------------------------
out = r"D:\goldproyect\mcp-deepseck\procutosmcp"

# ----------------------------------
# 3. Generar red de drenaje
# ----------------------------------
resultado = processing.run("grass7:r.stream.extract", {
    'elevation': dem,              # DEM de entrada
    'threshold': 1000,             # 🔥 ajustar si es necesario
    'stream_raster': out + r"\rios.tif",
    'stream_vector': out + r"\rios.shp",
    'direction': out + r"\flow_dir.tif"
})

# ----------------------------------
# 4. Cargar resultados en QGIS
# ----------------------------------
QgsProject.instance().addMapLayer(QgsRasterLayer(out + r"\rios.tif", "Rios Raster"))
QgsProject.instance().addMapLayer(QgsVectorLayer(out + r"\rios.shp", "Rios Vector", "ogr"))

print("✅ Drenaje generado correctamente")