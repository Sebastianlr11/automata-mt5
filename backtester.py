import os
import json
import subprocess
import time
import shutil

def ejecutar_sistema_masivo():
    with open("config.json", "r") as f:
        conf = json.load(f)

    carpeta_final = os.path.abspath("reports")
    os.makedirs(carpeta_final, exist_ok=True)
    
    # Rutas de datos de MT5
    ruta_datos_mt5 = r"C:\Users\Administrator\AppData\Roaming\MetaQuotes\Terminal\6C3C6A11D1C3791DD4DBF45421BF8028"
    ruta_experts_fisica = os.path.join(ruta_datos_mt5, "MQL5", "Experts", conf["ea_folder"])
    ruta_mql5_files = os.path.join(ruta_datos_mt5, "MQL5", "Files")

    expertos = [f for f in os.listdir(ruta_experts_fisica) if f.endswith('.ex5')]
    print(f"📂 Expertos detectados: {len(expertos)}")

    for nombre_ea in expertos:
        print(f"\n--- ⚙️ Procesando: {nombre_ea} ---")
        
        # NOMBRE ULTRA-SIMPLE: Evitamos rutas largas en el .ini
        nombre_temp = "reporte.html"
        
        # Posibles lugares donde MT5 podría soltar el archivo
        busqueda_1 = os.path.join(ruta_mql5_files, nombre_temp)
        busqueda_2 = os.path.join(ruta_datos_mt5, nombre_temp)
        
        # Limpiar antes de empezar
        for r in [busqueda_1, busqueda_2]:
            if os.path.exists(r): os.remove(r)

        ea_relativo = f"{conf['ea_folder']}\\{nombre_ea}"
        
        # .INI: Usamos solo el nombre del reporte sin ruta
        config_mt5 = (
            "[Tester]\n"
            f"Expert=\"{ea_relativo}\"\n"
            f"Symbol={conf['common_settings']['symbol']}\n"
            f"Period={conf['common_settings']['period']}\n"
            f"Deposit={conf['common_settings']['deposit']}\n"
            f"Leverage={conf['common_settings']['leverage']}\n"
            f"Model=1\n"
            f"FromDate={conf['common_settings']['from']}\n"
            f"ToDate={conf['common_settings']['to']}\n"
            f"Report={nombre_temp}\n"
            "ReplaceReport=1\n"
            "ShutdownTerminal=1\n"
            "Visual=0\n"
        )

        ini_path = os.path.abspath("config_batch.ini")
        with open(ini_path, "w", encoding="utf-16") as f:
            f.write(config_mt5)

        print(f"🚀 Ejecutando backtest...")
        subprocess.run([conf["mt5_path"], f"/config:{ini_path}"], check=True)

        # BUSCADOR INTENSIVO
        encontrado = False
        print("⌛ Buscando reporte en el sistema...")
        for i in range(10): # 20 segundos de espera
            time.sleep(2)
            for origen in [busqueda_1, busqueda_2]:
                if os.path.exists(origen):
                    nombre_final = f"Reporte_{nombre_ea.replace('.ex5', '')}.html"
                    shutil.move(origen, os.path.join(carpeta_final, nombre_final))
                    print(f"✅ ¡LOGRADO! Reporte guardado: {nombre_final}")
                    encontrado = True
                    break
            if encontrado: break
        
        if not encontrado:
            print(f"❌ MT5 terminó pero no generó el archivo '{nombre_temp}'")
            print(f"👉 IMPORTANTE: Revisa si el experto abrió trades. Si hay 0 operaciones, no hay reporte.")

    print("\n🏁 Proceso terminado.")

if __name__ == "__main__":
    ejecutar_sistema_masivo()