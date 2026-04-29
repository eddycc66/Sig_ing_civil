import os
import time
import processing
from qgis.core import (QgsProject, QgsRasterLayer, QgsSingleBandPseudoColorRenderer, 
                       QgsColorRampShader, QgsRasterShader, QgsCoordinateReferenceSystem)
from qgis.PyQt.QtGui import QColor

def run_flood_model_final_v5(base_path, dem_name, watershed_name, roads_name):
    print("🚀 Iniciando Proceso con Reproyección Automática...")
    
    base_path = os.path.normpath(base_path)
    if not os.path.exists(base_path): os.makedirs(base_path)

    # 1. CAPAS DE ENTRADA
    try:
        lyr_dem = QgsProject.instance().mapLayersByName(dem_name)[0]
        lyr_cuenca = QgsProject.instance().mapLayersByName(watershed_name)[0]
        lyr_vias = QgsProject.instance().mapLayersByName(roads_name)[0]
    except:
        print("❌ Error: No se encontraron las capas. Revisa los nombres.")
        return

    # Definir rutas
    out_dem = os.path.join(base_path, "1_dem_clip.tif")
    out_slope = os.path.join(base_path, "2_slope.tif")
    out_vias_rep = os.path.join(base_path, "3a_vias_reproyectadas.gpkg") # Capa intermedia
    out_vias_ras = os.path.join(base_path, "3b_vias_raster.tif")
    out_risk = os.path.join(base_path, "RESULTADO_RIESGO.tif")

    # --- PASO 1: RECORTE DEL DEM ---
    print("✂️ 1. Recortando DEM...")
    processing.run("gdal:cliprasterbymasklayer", {
        'INPUT': lyr_dem, 'MASK': lyr_cuenca, 'NODATA': -9999, 'OUTPUT': out_dem
    })

    # --- PASO 2: PENDIENTE ---
    print("📉 2. Calculando Pendiente...")
    processing.run("gdal:slope", {
        'INPUT': out_dem, 'OUTPUT': out_slope
    })

    # --- PASO 3: REPROYECTAR VÍAS (CRÍTICO) ---
    print("🔄 3. Reproyectando Vías al CRS del DEM...")
    # Forzamos que las vías tengan el mismo CRS que el DEM (EPSG:32719)
    processing.run("native:reprojectlayer", {
        'INPUT': lyr_vias,
        'TARGET_CRS': lyr_dem.crs(),
        'OUTPUT': out_vias_rep
    })

    # --- PASO 4: RASTERIZAR VÍAS ---
    print("🛣️ 4. Rasterizando Vías Reproyectadas...")
    ref = QgsRasterLayer(out_dem, "ref")
    res = ref.rasterUnitsPerPixelX()
    ext = ref.extent()
    # Usamos el objeto extent directamente para evitar errores de texto
    ext_str = f"{ext.xMinimum()},{ext.xMaximum()},{ext.yMinimum()},{ext.yMaximum()} [{lyr_dem.crs().authid()}]"
    
    # Intentamos rasterizar usando la capa reproyectada
    params_ras = {
        'INPUT': out_vias_rep,
        'FIELD': None, 'BURN': 5, 'INIT': 0,
        'UNITS': 1, 'WIDTH': res, 'HEIGHT': res,
        'EXTENT': ext_str,
        'DATA_TYPE': 5, # Float32
        'OUTPUT': out_vias_ras
    }
    processing.run("gdal:rasterize", params_ras)

    # Espera de seguridad
    time.sleep(1)

    if not os.path.exists(out_vias_ras):
        print("❌ Error: No se pudo crear el raster de vías. Intentando método nativo...")
        # Si falla GDAL, usamos el rasterizador nativo de QGIS
        processing.run("native:rasterize", {
            'INPUT': out_vias_rep, 'FIELD': None, 'BURN': 5,
            'UNITS': 1, 'WIDTH': res, 'HEIGHT': res, 'EXTENT': ext,
            'NODATA': 0, 'OUTPUT': out_vias_ras
        })

    # --- PASO 5: CÁLCULO DE RIESGO ---
    if os.path.exists(out_vias_ras):
        print("🧮 5. Ejecutando Álgebra de Mapas...")
        formula = '((A<3)*10 + (A>=3)*(A<10)*5 + (A>=10)*1) + B'
        
        processing.run("gdal:rastercalculator", {
            'INPUT_A': out_slope, 'BAND_A': 1,
            'INPUT_B': out_vias_ras, 'BAND_B': 1,
            'FORMULA': formula, 'NO_DATA': -9999, 'OUTPUT': out_risk
        })

        # --- PASO 6: CARGAR Y DAR ESTILO ---
        layer = iface.addRasterLayer(out_risk, "⚠️ RIESGO DE INUNDACIÓN")
        
        fcn = QgsColorRampShader()
        fcn.setColorRampType(QgsColorRampShader.Interpolated)
        fcn.setColorRampItemList([
            QgsColorRampShader.ColorRampItem(1, QColor("#2b83ba"), 'Bajo'),
            QgsColorRampShader.ColorRampItem(7, QColor("#ffffbf"), 'Medio'),
            QgsColorRampShader.ColorRampItem(15, QColor("#d7191c"), 'ALTO')
        ])
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(fcn)
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
        layer.setRenderer(renderer)
        layer.triggerRepaint()
        
        iface.zoomToActiveLayer()
        print(f"✅ ¡PROCESO COMPLETADO! Resultado en: {out_risk}")
    else:
        print("❌ El proceso falló en la etapa de rasterización.")

# --- EJECUCIÓN ---
run_flood_model_final_v5(r"D:\inundacion", "dem", "cuenca", "Vías_OSM_2018")