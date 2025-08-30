import json
import time
import random
import os
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ruta al archivo JSON
RUTA_JSON = "proveedores.json"

# Carpeta en el escritorio donde guardar descargas
escritorio = Path.home() / "Desktop"
CARPETA_DESCARGAS = escritorio / "descargas"
CARPETA_DESCARGAS.mkdir(parents=True, exist_ok=True)

# Fecha actual
fecha = datetime.now().strftime("%Y-%m-%d")

def eliminar_archivos_desactualizados():
    """Eliminar archivos en la carpeta de descargas cuya fecha no sea la actual"""
    print("🧹 Revisando archivos antiguos en la carpeta de descargas...")
    for archivo in CARPETA_DESCARGAS.iterdir():
        if archivo.is_file():
            nombre = archivo.name
            if fecha not in nombre:
                try:
                    archivo.unlink()
                    print(f"🗑️ Eliminado: {nombre}")
                except Exception as e:
                    print(f"⚠️ Error eliminando {nombre}: {e}")

def crear_driver_con_opciones():
    """Crear driver de Chrome con opciones optimizadas y minimizado"""
    chrome_options = Options()

    # Minimizado
    # chrome_options.add_argument("--window-position=32000,32000")
    # chrome_options.add_argument("--start-minimized")

    # Opciones básicas
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Opciones para SSL/TLS
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("--allow-running-insecure-content")

    # Anti-detección
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # User agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Configuración de descargas
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": str(CARPETA_DESCARGAS),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
        "profile.default_content_setting_values.automatic_downloads": 1
    })

    return chrome_options

def determinar_nombre_archivo(href, texto, index):
    href_texto = (href or "").upper()
    texto = texto.upper()
    if "POXIPOL" in href_texto or "POXIPOL" in texto or "POXI" in texto:
        return f"Fusion_POXIPOL_{fecha}.xls"
    elif "MAZFREN" in href_texto or "MAZFREN" in texto or "MAZ" in texto:
        return f"Fusion_MAZFREN_{fecha}.xls"
    else:
        return None  # ignorar archivos que no sean POXIPOL o MAZFREN

def filtrar_botones_fusion_por_nombre(driver):
    """Buscar solo los botones de descarga de Fusion que contengan POXIPOL o MAZFREN"""
    print("🔍 Buscando botones válidos de Fusion (POXIPOL o MAZFREN)...")
    botones = driver.find_elements(By.CSS_SELECTOR, 'a.elementor-button')
    botones_filtrados = []

    for boton in botones:
        href = boton.get_attribute("href") or ""
        texto = boton.text.strip()
        if texto.upper() == "LISTA" and any(x in href.upper() for x in ["POXIPOL", "MAZFREN"]):

            print(f"✅ Botón válido encontrado - Texto: '{texto}', Href: '{href}'")
            botones_filtrados.append(boton)

    if len(botones_filtrados) < 2:
        raise Exception("❌ No se encontraron ambos archivos requeridos: POXIPOL y MAZFREN")

    return botones_filtrados

def descargar_archivos_fusion(driver, wait):
    """Descargar los archivos específicos de Fusion filtrados por nombre"""
    print("📥 Iniciando descarga de archivos de Fusion...")

    archivos_iniciales = set(CARPETA_DESCARGAS.glob("*.xls")) | set(CARPETA_DESCARGAS.glob("*.xlsx"))

    botones_descarga = filtrar_botones_fusion_por_nombre(driver)
    archivos_descargados = []

    for i, boton in enumerate(botones_descarga):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton)
            time.sleep(2)
            href = boton.get_attribute("href")
            texto = boton.text.strip()
            print(f"🔗 Enlace: {href}\n📝 Texto: {texto}")

            archivos_antes = set(CARPETA_DESCARGAS.glob("*.xls")) | set(CARPETA_DESCARGAS.glob("*.xlsx"))
            driver.execute_script("arguments[0].click();", boton)
            print(f"✅ Clic realizado en botón {i+1}")

            for _ in range(60):
                time.sleep(2)
                actuales = set(CARPETA_DESCARGAS.glob("*.xls")) | set(CARPETA_DESCARGAS.glob("*.xlsx"))
                nuevos = actuales - archivos_antes
                if nuevos:
                    archivo = max(nuevos, key=lambda x: x.stat().st_ctime)
                    nombre_destino = determinar_nombre_archivo(href, texto, i)
                    if nombre_destino:
                        destino = CARPETA_DESCARGAS / nombre_destino
                        archivo.rename(destino)
                        archivos_descargados.append(destino.name)
                        print(f"✅ Archivo {i+1} descargado: {destino.name}")
                    break
        except Exception as e:
            print(f"❌ Error en descarga {i+1}: {e}")

    if not any("POXIPOL" in a.upper() for a in archivos_descargados):
        raise Exception("❌ No se descargó el archivo de POXIPOL")
    if not any("MAZFREN" in a.upper() for a in archivos_descargados):
        raise Exception("❌ No se descargó el archivo de MAZFREN")

    return archivos_descargados

# Ejecutar limpieza antes de iniciar
eliminar_archivos_desactualizados()

def obtener_archivos_actuales():
    """Obtener lista actual de archivos Excel en la carpeta de descargas"""
    return set(CARPETA_DESCARGAS.glob("*.xlsx")) | set(CARPETA_DESCARGAS.glob("*.xls"))

def obtener_todos_archivos_actuales():
    """Obtener lista actual de TODOS los archivos en la carpeta de descargas"""
    return set(CARPETA_DESCARGAS.glob("*"))

def cerrar_anuncio_fusion(driver, wait):
    """Cerrar el anuncio específico de Fusion en la página de productos"""
    print("🔍 Buscando y cerrando anuncio de Fusion en página de productos...")
    
    # Esperar un momento para que el anuncio aparezca
    time.sleep(3)
    
    # Selectores para el botón de cerrar anuncio (más amplios)
    selectores_cerrar = [
        # Selector específico proporcionado
        'a.dialog-close-button.dialog-lightbox-close-button[role="button"][aria-label="Close"]',
        # Variaciones del selector
        'a.dialog-close-button.dialog-lightbox-close-button',
        'a.dialog-close-button[aria-label="Close"]',
        'a.dialog-lightbox-close-button[aria-label="Close"]',
        # Por clase y rol
        'a[role="button"].dialog-close-button',
        'a[role="button"].dialog-lightbox-close-button',
        # Por aria-label solamente
        'a[aria-label="Close"]',
        '[aria-label="Close"]',
        'button[aria-label="Close"]',
        # Por icono dentro del botón/enlace
        'a:has(i.eicon-close)',
        'a.dialog-close-button:has(i.eicon-close)',
        'button:has(i.eicon-close)',
        # Fallbacks generales para elementos de cierre
        '.dialog-close-button',
        '.dialog-lightbox-close-button',
        'i.eicon-close',
        '.eicon-close',
        # Selectores para modales de Elementor
        '.elementor-lightbox-close-container',
        '.elementor-lightbox-close',
        '.dialog-widget-close-button',
        # Selectores genéricos de cierre
        '.close-button',
        '.modal-close',
        '.popup-close',
        '[data-dismiss="modal"]',
        # XPath para texto "Close" o "Cerrar"
        "//a[contains(text(), 'Close')]",
        "//button[contains(text(), 'Close')]",
        "//a[contains(text(), 'Cerrar')]",
        "//button[contains(text(), 'Cerrar')]",
        "//a[contains(text(), '×')]",
        "//button[contains(text(), '×')]"
    ]
    
    boton_cerrar = None
    for selector in selectores_cerrar:
        try:
            print(f"🔍 Probando selector: {selector}")
            
            if selector.startswith("//"):
                # Para selectores XPath
                elementos = driver.find_elements(By.XPATH, selector)
            elif selector == 'i.eicon-close' or selector == '.eicon-close':
                # Si es el icono, buscar el enlace/botón padre
                iconos = driver.find_elements(By.CSS_SELECTOR, selector)
                elementos = []
                for icono in iconos:
                    if icono.is_displayed():
                        # Buscar el elemento padre clickeable
                        try:
                            padre_a = icono.find_element(By.XPATH, "./ancestor::a[1]")
                            if padre_a.is_displayed():
                                elementos.append(padre_a)
                        except:
                            pass
                        try:
                            padre_button = icono.find_element(By.XPATH, "./ancestor::button[1]")
                            if padre_button.is_displayed():
                                elementos.append(padre_button)
                        except:
                            pass
            else:
                # Para otros selectores CSS
                elementos = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for elemento in elementos:
                if elemento.is_displayed():
                    texto = elemento.text.strip()
                    tag_name = elemento.tag_name
                    clases = elemento.get_attribute("class") or ""
                    aria_label = elemento.get_attribute("aria-label") or ""
                    
                    print(f"✅ Elemento encontrado - Tag: {tag_name}, Texto: '{texto}', Clases: '{clases}', Aria-label: '{aria_label}'")
                    
                    # Verificar que sea un elemento de cierre válido
                    if any(palabra in clases.lower() for palabra in ['close', 'cerrar']) or \
                       any(palabra in aria_label.lower() for palabra in ['close', 'cerrar']) or \
                       any(palabra in texto.lower() for palabra in ['close', 'cerrar', '×']):
                        boton_cerrar = elemento
                        print(f"✅ Botón de cerrar identificado con selector: {selector}")
                        break
            
            if boton_cerrar:
                break
                
        except Exception as e:
            print(f"⚠️ Error con selector {selector}: {e}")
            continue
    
    if boton_cerrar:
        try:
            print("🎯 Intentando cerrar anuncio...")
            
            # Hacer scroll al botón
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton_cerrar)
            time.sleep(2)
            
            # Intentar diferentes métodos de clic
            metodos_clic = [
                ("Clic normal", lambda: boton_cerrar.click()),
                ("Clic con JavaScript", lambda: driver.execute_script("arguments[0].click();", boton_cerrar)),
                ("Clic con offset", lambda: driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", boton_cerrar)),
                ("Forzar clic", lambda: driver.execute_script("arguments[0].click(); arguments[0].style.display='none';", boton_cerrar))
            ]
            
            for nombre_metodo, metodo_clic in metodos_clic:
                try:
                    print(f"🖱️ Intentando {nombre_metodo}...")
                    metodo_clic()
                    time.sleep(2)
                    
                    # Verificar si el anuncio se cerró
                    try:
                        # Si el elemento ya no está visible, el anuncio se cerró
                        if not boton_cerrar.is_displayed():
                            print(f"✅ Anuncio cerrado exitosamente con {nombre_metodo}")
                            return True
                    except:
                        # Si hay excepción al verificar, probablemente se cerró
                        print(f"✅ Anuncio cerrado exitosamente con {nombre_metodo}")
                        return True
                        
                except Exception as e:
                    print(f"⚠️ {nombre_metodo} falló: {e}")
                    continue
            
            print("⚠️ No se pudo cerrar el anuncio con ningún método")
            return False
            
        except Exception as e:
            print(f"⚠️ Error general al cerrar anuncio: {e}")
            return False
    else:
        print("⚠️ No se encontró el botón para cerrar el anuncio")
        
        # Intentar cerrar con tecla Escape como último recurso
        try:
            print("⌨️ Intentando cerrar con tecla Escape...")
            driver.find_element(By.TAG_NAME, "body").send_keys("\ue00c")  # Escape key
            time.sleep(2)
            print("✅ Tecla Escape enviada")
            return True
        except Exception as e:
            print(f"⚠️ No se pudo enviar tecla Escape: {e}")
            return False

def manejar_pagina_productos_fusion(driver, wait):
    """Manejar la página de productos de Fusion después del login"""
    print("🔧 Manejando página de productos de Fusion...")
    
    # Verificar si estamos en la página de productos con login=true
    url_actual = driver.current_url
    print(f"📍 URL actual: {url_actual}")
    
    if "productos" in url_actual and "login=true" in url_actual:
        print("✅ Detectada página de productos con login exitoso")
        
        # Intentar cerrar el anuncio
        anuncio_cerrado = cerrar_anuncio_fusion(driver, wait)
        
        if anuncio_cerrado:
            print("✅ Anuncio cerrado, continuando...")
        else:
            print("⚠️ No se pudo cerrar el anuncio, intentando continuar...")
        
        # Esperar un momento después de intentar cerrar el anuncio
        time.sleep(3)
        
        return True
    else:
        print("ℹ️ No se detectó la página de productos con anuncio")
        return False

def buscar_botones_descarga_fusion(driver):
    """Buscar los botones de descarga específicos de Fusion"""
    print("🔍 Buscando botones de descarga de Fusion...")
    
    # URLs específicas de los archivos a descargar
    urls_esperadas = [
        "https://www.distribuidorafusion.com.ar/wp-content/uploads/2024/07/POXIPOL-CLIENTES-2025-01-30-2.xls",
        "https://www.distribuidorafusion.com.ar/wp-content/uploads/2024/07/MAZFREN-CLIENTES-2025-04-15.xls"
    ]
    
    botones_encontrados = []
    
    # Buscar enlaces con las URLs específicas
    for url in urls_esperadas:
        try:
            # Buscar por href exacto
            enlace = driver.find_element(By.CSS_SELECTOR, f'a[href="{url}"]')
            if enlace.is_displayed():
                botones_encontrados.append(enlace)
                print(f"✅ Enlace encontrado para: {url}")
        except:
            print(f"⚠️ No se encontró enlace directo para: {url}")
    
    # Si no encontramos por URL exacta, buscar por patrones
    if len(botones_encontrados) < 2:
        print("🔍 Buscando por patrones alternativos...")
        
        selectores_alternativos = [
            # Selectores específicos para los botones de Fusion
            'a.elementor-button.elementor-button-link.elementor-size-sm[download]',
            'a.elementor-button.elementor-button-link.elementor-size-sm',
            'a.elementor-button[download]',
            'a.elementor-button-link[download]',
            # Por texto del botón
            '//a[.//span[contains(text(), "LISTA")]]',
            '//a[contains(@class, "elementor-button") and .//span[contains(text(), "LISTA")]]',
            # Por href que contenga los nombres de archivo
            'a[href*="POXIPOL-CLIENTES"]',
            'a[href*="MAZFREN-CLIENTES"]',
            'a[href*=".xls"]',
            # Fallbacks generales
            'a.elementor-button',
            'a[download*=".xls"]'
        ]
        
        for selector in selectores_alternativos:
            try:
                if selector.startswith("//"):
                    # Para selectores XPath
                    elementos = driver.find_elements(By.XPATH, selector)
                else:
                    # Para selectores CSS
                    elementos = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for elemento in elementos:
                    if elemento.is_displayed():
                        href = elemento.get_attribute("href") or ""
                        download_attr = elemento.get_attribute("download") or ""
                        texto = elemento.text.strip()
                        
                        # Verificar que sea un enlace de descarga válido
                        if (".xls" in href.lower() and 
                            ("POXIPOL" in href or "MAZFREN" in href or "CLIENTES" in href)) or \
                           ("LISTA" in texto and "elementor-button" in elemento.get_attribute("class")):
                            
                            # Evitar duplicados
                            if elemento not in botones_encontrados:
                                botones_encontrados.append(elemento)
                                print(f"✅ Botón encontrado - Texto: '{texto}', Href: '{href}'")
                                
                                # Si ya tenemos 2 botones, parar
                                if len(botones_encontrados) >= 2:
                                    break
                
                if len(botones_encontrados) >= 2:
                    break
                    
            except Exception as e:
                print(f"⚠️ Error con selector {selector}: {e}")
                continue
    
    print(f"📊 Total de botones encontrados: {len(botones_encontrados)}")
    return botones_encontrados

def descargar_archivos_fusion(driver, wait):
    """Descargar los archivos específicos de Fusion"""
    print("📥 Iniciando descarga de archivos de Fusion...")
    
    # Obtener archivos antes de las descargas
    archivos_iniciales = obtener_archivos_actuales()
    
    # Buscar botones de descarga
    botones_descarga = filtrar_botones_fusion_por_nombre(driver)
    
    if not botones_descarga:
        raise Exception("No se encontraron botones de descarga para Fusion")
    
    archivos_descargados = []
    
    for i, boton in enumerate(botones_descarga):
        try:
            print(f"\n📥 Descargando archivo {i+1}/{len(botones_descarga)}...")
            
            # Hacer scroll al botón
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton)
            time.sleep(2)
            
            # Obtener información del enlace
            href = boton.get_attribute("href") or ""
            texto = boton.text.strip()
            print(f"🔗 Enlace: {href}")
            print(f"📝 Texto: {texto}")
            
            # Obtener archivos antes de este clic
            archivos_antes_clic = obtener_archivos_actuales()
            
            # Hacer clic en el botón
            driver.execute_script("arguments[0].click();", boton)
            print(f"✅ Clic realizado en botón {i+1}")
            
            # Esperar descarga (2 minutos por archivo)
            archivo_descargado = esperar_nueva_descarga(archivos_antes_clic, timeout_minutos=2)
            
            if archivo_descargado:
                # Determinar nombre basado en el contenido del enlace
                if "POXIPOL" in href:
                    nombre_archivo = f"Fusion_POXIPOL_{fecha}.xls"
                elif "MAZFREN" in href:
                    nombre_archivo = f"Fusion_MAZFREN_{fecha}.xls"
                else:
                    nombre_archivo = f"Fusion_archivo_{i+1}_{fecha}.xls"
                
                # Renombrar archivo
                nuevo_nombre = CARPETA_DESCARGAS / nombre_archivo
                contador = 1
                while nuevo_nombre.exists():
                    base_name = nombre_archivo.replace('.xls', f'_{contador}.xls')
                    nuevo_nombre = CARPETA_DESCARGAS / base_name
                    contador += 1
                
                archivo_descargado.rename(nuevo_nombre)
                archivos_descargados.append(nuevo_nombre.name)
                print(f"✅ Archivo {i+1} descargado: {nuevo_nombre.name}")
            else:
                print(f"⚠️ No se descargó el archivo {i+1}")
            
            # Pausa entre descargas
            if i < len(botones_descarga) - 1:
                time.sleep(5)
                
        except Exception as e:
            print(f"❌ Error descargando archivo {i+1}: {e}")
            continue
    
    return archivos_descargados

def hacer_login_fusion(driver, proveedor, wait):
    """Manejar el login específico para Fusion"""
    print("🔧 Procesando login específico para Fusion...")
    
    try:
        # Buscar campos de login (usar lógica similar a otros proveedores)
        print("🔍 Buscando campos de login...")
        
        # Intentar múltiples selectores para el campo de usuario
        selectores_usuario = [
            'input[name="log"]',
            'input[name="username"]',
            'input[name="user"]',
            'input[type="text"]',
            'input[placeholder*="usuario"]',
            'input[placeholder*="Usuario"]',
            'input[placeholder*="email"]',
            'input[placeholder*="Email"]'
        ]
        
        usuario_field = None
        for selector in selectores_usuario:
            try:
                usuario_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                print(f"✅ Campo de usuario encontrado con selector: {selector}")
                break
            except:
                continue
        
        if not usuario_field:
            raise Exception("No se pudo encontrar el campo de usuario")
        
        # Buscar campo de contraseña
        selectores_password = [
            'input[name="pwd"]',
            'input[name="password"]',
            'input[type="password"]',
            'input[placeholder*="contraseña"]',
            'input[placeholder*="Contraseña"]'
        ]
        
        password_field = None
        for selector in selectores_password:
            try:
                password_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                print(f"✅ Campo de contraseña encontrado con selector: {selector}")
                break
            except:
                continue
        
        if not password_field:
            raise Exception("No se pudo encontrar el campo de contraseña")
        
        # Llenar los campos
        print("📝 Llenando campos de login...")
        
        # Limpiar y llenar campo de usuario
        try:
            usuario_field.clear()
            time.sleep(1)
            usuario_field.send_keys(proveedor["usuario"])
            print(f"✅ Usuario ingresado: {proveedor['usuario']}")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar usuario: {e}")
            driver.execute_script(f"arguments[0].value = '{proveedor['usuario']}';", usuario_field)
            print("✅ Usuario ingresado con JavaScript")
        
        # Limpiar y llenar campo de contraseña
        try:
            password_field.clear()
            time.sleep(1)
            password_field.send_keys(proveedor["contrasena"])
            print("✅ Contraseña ingresada")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar contraseña: {e}")
            driver.execute_script(f"arguments[0].value = '{proveedor['contrasena']}';", password_field)
            print("✅ Contraseña ingresada con JavaScript")
        
        # Buscar botón de submit
        print("🔍 Buscando botón de submit...")
        
        selectores_submit = [
            "button[type='submit']",
            "input[type='submit']",
            "//button[contains(text(), 'Ingresar')]",
            "//button[contains(text(), 'Login')]",
            "//button[contains(text(), 'Entrar')]",
            "//input[contains(@value, 'Ingresar')]",
            "//input[contains(@value, 'Login')]",
            ".wp-element-button",
            ".elementor-button",
            ".btn-primary",
            "button"
        ]
        
        submit_button = None
        for selector in selectores_submit:
            try:
                if selector.startswith("//"):
                    submit_button = driver.find_element(By.XPATH, selector)
                else:
                    submit_button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if submit_button and submit_button.is_displayed() and submit_button.is_enabled():
                    print(f"✅ Botón de submit encontrado con selector: {selector}")
                    break
                else:
                    submit_button = None
            except:
                continue
        
        if submit_button:
            print("🚀 Haciendo clic en botón de submit...")
            try:
                submit_button.click()
                print("✅ Clic normal exitoso")
            except Exception as e:
                print(f"⚠️ Clic normal falló: {e}, intentando con JavaScript...")
                driver.execute_script("arguments[0].click();", submit_button)
                print("✅ Clic con JavaScript exitoso")
        else:
            print("⌨️ No se encontró botón, enviando formulario con Enter...")
            password_field.send_keys("\n")
        
        time.sleep(5)
        print("✅ Login de Fusion completado")
        
    except Exception as e:
        raise Exception(f"Error en login de Fusion: {e}")

def buscar_primer_boton_excel(driver, proveedor_nombre=""):
    """Buscar el primer botón de Excel válido - adaptado para diferentes proveedores"""
    print("🔍 Buscando botón de Excel...")
    
    # Para Fusion, manejar el anuncio y luego buscar botones de descarga
    if proveedor_nombre.lower() == 'fusion':
        print("🔧 Procesamiento especial para Fusion...")
        
        # Esperar un momento para que cargue la página
        time.sleep(5)
        
        # Para Fusion, retornamos None porque usaremos la función específica de descarga
        return None
    
    # Para Expoyer, usar la función específica de descarga
    elif proveedor_nombre.lower() == 'expoyer':
        print("🔧 Procesamiento especial para Expoyer...")
        
        # Para Expoyer, retornamos None porque usaremos la función específica de descarga
        return None
    
    # Para Autocor, buscar pestaña y botón específicos de Vuetify
    elif proveedor_nombre.lower() == 'autocor':
        print("🔍 Buscando pestaña y botón de descarga específicos para Autocor...")

        # PASO 1: Buscar y hacer clic en la pestaña "Lista de precios"
        print("🔍 Paso 1: Buscando pestaña 'Lista de precios'...")
        time.sleep(2)
        selectores_tab = [
            "//div[contains(@class, 'v-tab') and contains(text(), 'Lista de precios')]",
            "//div[@role='tab' and contains(text(), 'Lista de precios')]",
            "//div[contains(@class, 'v-tab')]//i[contains(@class, 'mdi-download')]/parent::div[contains(text(), 'Lista de precios')]",
            "//div[contains(@class, 'v-tab') and contains(text(), 'Lista')]",
            "//div[contains(@class, 'v-tab') and contains(text(), 'precios')]",
            "div.v-tab:has(i.mdi-download)",
            "//div[contains(@class, 'v-tab')]//i[contains(@class, 'mdi-download')]/parent::div"
        ]

        tab_encontrada = None
        for selector in selectores_tab:
            try:
                if selector.startswith("//"):
                    elementos = driver.find_elements(By.XPATH, selector)
                else:
                    elementos = driver.find_elements(By.CSS_SELECTOR, selector)

                for elemento in elementos:
                    if elemento.is_displayed():
                        texto = elemento.text.strip()
                        clases = elemento.get_attribute("class") or ""
                        role = elemento.get_attribute("role") or ""

                        print(f"🔍 Pestaña encontrada - Texto: '{texto}', Clases: '{clases}', Role: '{role}'")

                        if "Lista de precios" in texto or ("Lista" in texto and "precios" in texto):
                            print(f"✅ Pestaña 'Lista de precios' encontrada: '{texto}'")
                            tab_encontrada = elemento
                            break
                        elif "v-tab" in clases and any(palabra in texto.lower() for palabra in ['lista', 'precios', 'download']):
                            print(f"✅ Pestaña relacionada encontrada: '{texto}'")
                            tab_encontrada = elemento
                            break

                if tab_encontrada:
                    break
            except Exception as e:
                print(f"⚠️ Error con selector de pestaña {selector}: {e}")
                continue

        if tab_encontrada:
            print("🖱️ Haciendo clic en pestaña 'Lista de precios'...")
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab_encontrada)
                time.sleep(2)
                driver.execute_script("arguments[0].click();", tab_encontrada)
                print("✅ Clic en pestaña exitoso")
                time.sleep(3)
            except Exception as e:
                print(f"⚠️ Error al hacer clic en pestaña: {e}")
        else:
            print("⚠️ No se encontró la pestaña 'Lista de precios'")

        # PASO 2: Buscar el botón de descarga
        print("🔍 Paso 2: Buscando botón 'DESCARGAR LISTA ACTUAL'...")

        selectores_autocor = [
            "//button[contains(@class, 'v-btn') and .//span[contains(text(), 'DESCARGAR LISTA ACTUAL')]]",
            "//button[contains(@class, 'v-btn')]//span[contains(text(), 'DESCARGAR LISTA ACTUAL')]/parent::button",
            "//button[contains(@class, 'v-btn') and .//span[contains(text(), 'DESCARGAR')]]",
            "//button[contains(@class, 'v-btn') and .//span[contains(text(), 'LISTA')]]",
            "//button[contains(@class, 'v-btn') and .//span[contains(text(), 'ACTUAL')]]",
            "//button[contains(@class, 'v-btn') and contains(@class, 'primary') and .//span[contains(text(), 'DESCARGAR')]]",
            "button.v-btn.primary.dark-2",
            "button.v-btn.v-btn--is-elevated.primary",
            "button.v-btn.primary",
            "//button[contains(@class, 'v-btn') and (contains(text(), 'DESCARGAR') or contains(text(), 'LISTA'))]"
        ]

        boton_descarga = None
        for selector in selectores_autocor:
            try:
                if selector.startswith("//"):
                    elementos = driver.find_elements(By.XPATH, selector)
                else:
                    elementos = driver.find_elements(By.CSS_SELECTOR, selector)

                for elemento in elementos:
                    if elemento.is_displayed() and elemento.is_enabled():
                        texto = elemento.text.strip()
                        clases = elemento.get_attribute("class") or ""

                        print(f"🔍 Botón encontrado - Texto: '{texto}', Clases: '{clases}'")

                        if "DESCARGAR LISTA ACTUAL" in texto or \
                           ("DESCARGAR" in texto and ("LISTA" in texto or "ACTUAL" in texto)) or \
                           ("DESCARGAR" in texto and "v-btn" in clases):
                            print(f"✅ Botón de descarga encontrado para Autocor: '{texto}'")
                            
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
                                time.sleep(1)
                                print("📥 Botón de descarga identificado, esperando clic desde función principal")
                                return elemento
                                time.sleep(5)
                            except Exception as e:
                                print(f"⚠️ Error al hacer clic en el botón de descarga: {e}")
                            break

                if boton_descarga:
                    break
            except Exception as e:
                print(f"⚠️ Error con selector {selector}: {e}")
                continue

    # Para Ventor, buscar enlaces de descarga específicos
    elif proveedor_nombre.lower() == 'ventor':
        print("🔍 Buscando enlace de descarga específico para Ventor...")
        
        selectores_ventor = [
            # Enlace específico con texto "FORMATO XLS"
            "//a[contains(text(), 'FORMATO XLS')]",
            "//a[contains(text(), 'XLS')]",
            # Enlaces que apunten a archivos Excel
            "a[href*='.xlsx']",
            "a[href*='.xls']",
            "a[download*='.xlsx']",
            "a[download*='.xls']",
            # Enlaces con atributo download
            "a[download]",
            # Enlaces que contengan "excel" o "formato"
            "//a[contains(text(), 'Excel')]",
            "//a[contains(text(), 'EXCEL')]",
            "//a[contains(text(), 'formato')]",
            "//a[contains(text(), 'FORMATO')]",
            "//a[contains(text(), 'descargar')]",
            "//a[contains(text(), 'DESCARGAR')]"
        ]
        
        for selector in selectores_ventor:
            try:
                if selector.startswith("//"):
                    # Para selectores XPath
                    elementos = driver.find_elements(By.XPATH, selector)
                else:
                    # Para selectores CSS
                    elementos = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for elemento in elementos:
                    if elemento.is_displayed():
                        href = elemento.get_attribute("href") or ""
                        texto = elemento.text.strip()
                        download_attr = elemento.get_attribute("download") or ""
                        
                        print(f"🔍 Enlace encontrado - Texto: '{texto}', Href: '{href}', Download: '{download_attr}'")
                        
                        # Verificar que sea un enlace de Excel válido
                        if any(ext in href.lower() for ext in ['.xlsx', '.xls']) or \
                           any(ext in download_attr.lower() for ext in ['.xlsx', '.xls']) or \
                           any(palabra in texto.lower() for palabra in ['xls', 'excel', 'formato']):
                            print(f"✅ Enlace de descarga encontrado para Ventor: '{texto}'")
                            return elemento
            except Exception as e:
                print(f"⚠️ Error con selector {selector}: {e}")
                continue
        
        print("❌ No se encontró enlace de descarga para Ventor")
        return None
    
    # Para Icepar, buscar enlaces de descarga específicos
    elif proveedor_nombre.lower() == 'icepar':
        print("🔍 Buscando enlace de descarga específico para Icepar...")
        
        selectores_icepar = [
            # Enlace específico con texto "descargar" y href que contenga "export/excel"
            "//a[contains(text(), 'descargar') and contains(@href, 'export/excel')]",
            "//a[contains(text(), 'DESCARGAR') and contains(@href, 'export/excel')]",
            "//a[contains(text(), 'Descargar') and contains(@href, 'export/excel')]",
            # Enlaces que contengan "export/excel"
            "a[href*='export/excel']",
            "a[href*='export']",
            # Enlaces con texto "descargar"
            "//a[contains(text(), 'descargar')]",
            "//a[contains(text(), 'DESCARGAR')]",
            "//a[contains(text(), 'Descargar')]",
            # Enlaces que contengan "excel"
            "//a[contains(text(), 'excel')]",
            "//a[contains(text(), 'Excel')]",
            "//a[contains(text(), 'EXCEL')]",
            "a[href*='excel']"
        ]
        
        for selector in selectores_icepar:
            try:
                if selector.startswith("//"):
                    # Para selectores XPath
                    elementos = driver.find_elements(By.XPATH, selector)
                else:
                    # Para selectores CSS
                    elementos = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for elemento in elementos:
                    if elemento.is_displayed():
                        href = elemento.get_attribute("href") or ""
                        texto = elemento.text.strip()
                        
                        print(f"🔍 Enlace encontrado - Texto: '{texto}', Href: '{href}'")
                        
                        # Verificar que sea un enlace de descarga válido para Icepar
                        if ('export/excel' in href.lower() and 'descargar' in texto.lower()) or \
                           ('export' in href.lower() and 'descargar' in texto.lower()) or \
                           ('excel' in href.lower() and 'descargar' in texto.lower()):
                            print(f"✅ Enlace de descarga encontrado para Icepar: '{texto}'")
                            return elemento
            except Exception as e:
                print(f"⚠️ Error con selector {selector}: {e}")
                continue
        
        print("❌ No se encontró enlace de descarga para Icepar")
        return None
    
    # Para Atonor, buscar enlaces de descarga específicos
    elif proveedor_nombre.lower() == 'atonor':
        print("🔍 Buscando enlace de descarga específico para Atonor...")
        
        selectores_atonor = [
            # Enlace específico con texto "Lista precios EXCEL" y href que contenga ".xlsx"
            "//a[contains(text(), 'Lista precios EXCEL') and contains(@href, '.xlsx')]",
            "//a[contains(text(), 'Lista precios') and contains(@href, '.xlsx')]",
            "//a[contains(text(), 'EXCEL') and contains(@href, '.xlsx')]",
            # Enlaces que apunten a archivos Excel en wp-content/uploads
            "a[href*='wp-content/uploads'][href*='.xlsx']",
            "a[href*='wp-content'][href*='.xlsx']",
            # Enlaces que contengan "LISTA" y ".xlsx"
            "//a[contains(@href, 'LISTA') and contains(@href, '.xlsx')]",
            "//a[contains(@href, 'lista') and contains(@href, '.xlsx')]",
            # Enlaces con texto que contenga "lista", "precios", "excel"
            "//a[contains(text(), 'lista') and contains(@href, '.xlsx')]",
            "//a[contains(text(), 'Lista') and contains(@href, '.xlsx')]",
            "//a[contains(text(), 'LISTA') and contains(@href, '.xlsx')]",
            "//a[contains(text(), 'precios') and contains(@href, '.xlsx')]",
            "//a[contains(text(), 'Precios') and contains(@href, '.xlsx')]",
            "//a[contains(text(), 'PRECIOS') and contains(@href, '.xlsx')]",
            "//a[contains(text(), 'excel') and contains(@href, '.xlsx')]",
            "//a[contains(text(), 'Excel') and contains(@href, '.xlsx')]",
            "//a[contains(text(), 'EXCEL') and contains(@href, '.xlsx')]",
            # Fallback: cualquier enlace que apunte a .xlsx
            "a[href*='.xlsx']",
            "a[href*='.xls']"
        ]
        
        for selector in selectores_atonor:
            try:
                if selector.startswith("//"):
                    # Para selectores XPath
                    elementos = driver.find_elements(By.XPATH, selector)
                else:
                    # Para selectores CSS
                    elementos = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for elemento in elementos:
                    if elemento.is_displayed():
                        href = elemento.get_attribute("href") or ""
                        texto = elemento.text.strip()
                        
                        print(f"🔍 Enlace encontrado - Texto: '{texto}', Href: '{href}'")
                        
                        # Verificar que sea un enlace de descarga válido para Atonor
                        if ('.xlsx' in href.lower() or '.xls' in href.lower()) and \
                           (any(palabra in texto.lower() for palabra in ['lista', 'precios', 'excel']) or \
                            any(palabra in href.lower() for palabra in ['lista', 'precios'])):
                            print(f"✅ Enlace de descarga encontrado para Atonor: '{texto}'")
                            return elemento
            except Exception as e:
                print(f"⚠️ Error con selector {selector}: {e}")
                continue
        
        print("❌ No se encontró enlace de descarga para Atonor")
        return None
    
    # Para Sinkromat, buscar elementos de descarga específicos
    elif proveedor_nombre.lower() == 'sinkromat':
        print("🔍 Buscando elemento de descarga específico para Sinkromat...")
        
        selectores_sinkromat = [
            # Elemento específico con texto "XLS Archivo de Excel"
            "//p[contains(text(), 'XLS Archivo de Excel')]",
            "//p[contains(text(), 'XLS')]",
            "//p[contains(text(), 'Archivo de Excel')]",
            # Elementos p con clase chakra-text que contengan "XLS" o "Excel"
            "p.chakra-text.css-896ql1",
            "//p[@class='chakra-text css-896ql1'][contains(text(), 'XLS')]",
            "//p[@class='chakra-text css-896ql1'][contains(text(), 'Excel')]",
            # Elementos p con clase chakra-text que contengan palabras clave
            "//p[contains(@class, 'chakra-text') and contains(text(), 'XLS')]",
            "//p[contains(@class, 'chakra-text') and contains(text(), 'Excel')]",
            "//p[contains(@class, 'chakra-text') and contains(text(), 'Archivo')]",
            # Fallback: cualquier elemento p que contenga "XLS" o "Excel"
            "//p[contains(text(), 'XLS')]",
            "//p[contains(text(), 'Excel')]",
            "//p[contains(text(), 'excel')]",
            # Elementos clickeables que contengan "XLS"
            "//*[contains(text(), 'XLS Archivo de Excel')]",
            "//*[contains(text(), 'XLS')]"
        ]
        
        for selector in selectores_sinkromat:
            try:
                if selector.startswith("//") or selector.startswith("//*"):
                    # Para selectores XPath
                    elementos = driver.find_elements(By.XPATH, selector)
                else:
                    # Para selectores CSS
                    elementos = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for elemento in elementos:
                    if elemento.is_displayed():
                        texto = elemento.text.strip()
                        tag_name = elemento.tag_name
                        clases = elemento.get_attribute("class") or ""
                        
                        print(f"🔍 Elemento encontrado - Tag: '{tag_name}', Texto: '{texto}', Clases: '{clases}'")
                        
                        # Verificar que sea un elemento de descarga válido para Sinkromat
                        if any(palabra in texto.lower() for palabra in ['xls', 'excel', 'archivo']):
                            print(f"✅ Elemento de descarga encontrado para Sinkromat: '{texto}'")
                            return elemento
            except Exception as e:
                print(f"⚠️ Error con selector {selector}: {e}")
                continue
        
        print("❌ No se encontró elemento de descarga para Sinkromat")
        return None
    
    else:
        # Para otros proveedores, usar la lógica original
        selectores_especificos = [
            # Botón completo con clase success y icono Excel
            "button.btn-success:has(i.mdi-file-excel)",
            "button.btn-sm.btn-success:has(i.mdi-file-excel)",
            # Botones con tooltip que contengan Excel
            "button[data-bs-toggle='tooltip']:has(i.mdi-file-excel)",
            # Fallback: buscar iconos Excel y verificar que estén en botones válidos
            "i.mdi-file-excel"
        ]
        
        for selector in selectores_especificos:
            try:
                if "i.mdi-file-excel" == selector:
                    # Para iconos, verificar que estén en botones válidos
                    iconos = driver.find_elements(By.CSS_SELECTOR, selector)
                    for icono in iconos:
                        if icono.is_displayed():
                            # Buscar el botón padre
                            try:
                                boton_padre = icono.find_element(By.XPATH, "./ancestor::button[1]")
                                if boton_padre.is_displayed() and boton_padre.is_enabled():
                                    # Verificar que sea un botón de descarga válido
                                    clases = boton_padre.get_attribute("class") or ""
                                    if "btn" in clases:
                                        print(f"✅ Botón encontrado con selector: {selector}")
                                        return boton_padre
                            except:
                                continue
                else:
                    # Para selectores de botones directos
                    elementos = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elemento in elementos:
                        if elemento.is_displayed() and elemento.is_enabled():
                            # Verificar que el botón tenga un icono Excel
                            try:
                                icono_excel = elemento.find_element(By.CSS_SELECTOR, "i.mdi-file-excel")
                                if icono_excel.is_displayed():
                                    print(f"✅ Botón encontrado con selector: {selector}")
                                    return elemento
                            except:
                                continue
            except Exception as e:
                print(f"⚠️ Error con selector {selector}: {e}")
                continue
        
        print("❌ No se encontró botón de Excel válido")
        return None

def esperar_nueva_descarga(archivos_iniciales, timeout_minutos=3):
    """Esperar a que aparezca un nuevo archivo descargado - 3 minutos"""
    print(f"Esperando nueva descarga (hasta {timeout_minutos} minutos)...")
    
    tiempo_inicio = time.time()
    timeout_segundos = timeout_minutos * 60
    ultimo_reporte = 0
    
    while time.time() - tiempo_inicio < timeout_segundos:
        tiempo_transcurrido = time.time() - tiempo_inicio
        
        # Verificar archivos descargándose
        archivos_descargando = list(CARPETA_DESCARGAS.glob("*.crdownload")) + list(CARPETA_DESCARGAS.glob("*.tmp"))
        
        # Verificar archivos completados
        archivos_actuales = obtener_archivos_actuales()
        archivos_nuevos = archivos_actuales - archivos_iniciales
        
        # Reportar progreso cada 30 segundos
        if tiempo_transcurrido - ultimo_reporte > 30:
            minutos = int(tiempo_transcurrido // 60)
            segundos = int(tiempo_transcurrido % 60)
            print(f"⏳ Esperando... {minutos}m {segundos}s")
            
            if archivos_descargando:
                print(f"📥 {len(archivos_descargando)} archivo(s) descargándose...")
            
            ultimo_reporte = tiempo_transcurrido
        
        # Si hay archivos nuevos
        if archivos_nuevos:
            print(f"📄 Detectados {len(archivos_nuevos)} archivo(s) nuevo(s)")
            
            # Si no hay archivos descargándose, la descarga se completó
            if not archivos_descargando:
                # Esperar un poco más para asegurar
                time.sleep(3)
                archivos_descargando = list(CARPETA_DESCARGAS.glob("*.crdownload")) + list(CARPETA_DESCARGAS.glob("*.tmp"))
                
                if not archivos_descargando:
                    # Encontrar el archivo más reciente
                    archivo_mas_reciente = max(archivos_nuevos, key=lambda x: x.stat().st_ctime)
                    
                    # Verificar que el archivo no esté vacío
                    if archivo_mas_reciente.stat().st_size > 1024:  # Al menos 1KB
                        print(f"✅ Descarga completada: {archivo_mas_reciente.name}")
                        return archivo_mas_reciente
                    else:
                        print(f"⚠️ Archivo muy pequeño, podría estar corrupto: {archivo_mas_reciente.name}")
        
        time.sleep(2)
    
    print(f"⚠️ Timeout después de {timeout_minutos} minutos")
    
    # Verificar si hay archivos nuevos aunque haya timeout
    archivos_actuales = obtener_archivos_actuales()
    archivos_nuevos = archivos_actuales - archivos_iniciales
    
    if archivos_nuevos:
        archivo_mas_reciente = max(archivos_nuevos, key=lambda x: x.stat().st_ctime)
        if archivo_mas_reciente.stat().st_size > 1024:
            print(f"⚠️ Encontrado archivo después de timeout: {archivo_mas_reciente.name}")
            return archivo_mas_reciente
    
    return None

def esperar_descarga_zip(archivos_iniciales, timeout_minutos=3):
    """Esperar específicamente a que aparezca un archivo ZIP descargado"""
    print(f"⏳ Esperando descarga de archivo ZIP (hasta {timeout_minutos} minutos)...")
    
    tiempo_inicio = time.time()
    timeout_segundos = timeout_minutos * 60
    ultimo_reporte = 0
    
    while time.time() - tiempo_inicio < timeout_segundos:
        tiempo_transcurrido = time.time() - tiempo_inicio
        
        # Verificar archivos descargándose (incluyendo ZIP)
        archivos_descargando = (list(CARPETA_DESCARGAS.glob("*.crdownload")) + 
                               list(CARPETA_DESCARGAS.glob("*.tmp")) +
                               list(CARPETA_DESCARGAS.glob("*.part")))
        
        # Verificar archivos completados (todos los tipos)
        archivos_actuales = obtener_todos_archivos_actuales()
        archivos_nuevos = archivos_actuales - archivos_iniciales
        
        # Filtrar solo archivos ZIP
        archivos_zip_nuevos = [archivo for archivo in archivos_nuevos 
                              if archivo.suffix.lower() in ['.zip', '.rar', '.7z']]
        
        # Reportar progreso cada 15 segundos para ZIP
        if tiempo_transcurrido - ultimo_reporte > 15:
            minutos = int(tiempo_transcurrido // 60)
            segundos = int(tiempo_transcurrido % 60)
            print(f"⏳ Esperando ZIP... {minutos}m {segundos}s")
            
            if archivos_descargando:
                print(f"📥 {len(archivos_descargando)} archivo(s) descargándose...")
            
            if archivos_zip_nuevos:
                print(f"📦 {len(archivos_zip_nuevos)} archivo(s) ZIP detectado(s)")
            
            ultimo_reporte = tiempo_transcurrido
        
        # Si hay archivos ZIP nuevos
        if archivos_zip_nuevos:
            print(f"📦 Detectados {len(archivos_zip_nuevos)} archivo(s) ZIP nuevo(s)")
            
            # Si no hay archivos descargándose, la descarga se completó
            if not archivos_descargando:
                # Esperar un poco más para asegurar
                time.sleep(3)
                archivos_descargando = (list(CARPETA_DESCARGAS.glob("*.crdownload")) + 
                                       list(CARPETA_DESCARGAS.glob("*.tmp")) +
                                       list(CARPETA_DESCARGAS.glob("*.part")))
                
                if not archivos_descargando:
                    # Encontrar el archivo ZIP más reciente
                    archivo_zip_reciente = max(archivos_zip_nuevos, key=lambda x: x.stat().st_ctime)
                    
                    # Verificar que el archivo no esté vacío
                    if archivo_zip_reciente.stat().st_size > 1024:  # Al menos 1KB
                        print(f"✅ Descarga de ZIP completada: {archivo_zip_reciente.name}")
                        return archivo_zip_reciente
                    else:
                        print(f"⚠️ Archivo ZIP muy pequeño, podría estar corrupto: {archivo_zip_reciente.name}")
        
        time.sleep(2)
    
    print(f"⚠️ Timeout después de {timeout_minutos} minutos esperando ZIP")
    
    # Verificar si hay archivos ZIP nuevos aunque haya timeout
    archivos_actuales = obtener_todos_archivos_actuales()
    archivos_nuevos = archivos_actuales - archivos_iniciales
    archivos_zip_nuevos = [archivo for archivo in archivos_nuevos 
                          if archivo.suffix.lower() in ['.zip', '.rar', '.7z']]
    
    if archivos_zip_nuevos:
        archivo_zip_reciente = max(archivos_zip_nuevos, key=lambda x: x.stat().st_ctime)
        if archivo_zip_reciente.stat().st_size > 1024:
            print(f"⚠️ Encontrado archivo ZIP después de timeout: {archivo_zip_reciente.name}")
            return archivo_zip_reciente
    
    return None

def renombrar_archivo_descargado(archivo, proveedor_nombre):
    """Renombrar archivo descargado con nombre del proveedor"""
    try:
        nuevo_nombre = CARPETA_DESCARGAS / f"{proveedor_nombre}_{fecha}.xlsx"
        
        # Evitar sobrescribir archivos existentes
        contador = 1
        while nuevo_nombre.exists():
            nuevo_nombre = CARPETA_DESCARGAS / f"{proveedor_nombre}_{fecha}_{contador}.xlsx"
            contador += 1
        
        archivo.rename(nuevo_nombre)
        print(f"✅ Archivo renombrado a: {nuevo_nombre.name}")
        return nuevo_nombre
    except Exception as e:
        print(f"❌ Error al renombrar archivo: {e}")
        return archivo

def hacer_login_ventor(driver, proveedor, wait):
    """Manejar el login especial para Ventor con modal"""
    print("🔧 Procesando login especial para Ventor...")
    
    try:
        # Buscar el enlace específico que abre el modal
        print("🔍 Buscando enlace que abre el modal de login...")
        
        # Selector específico para el enlace que abre el modal
        selector_modal = 'a.modal-action[data-target="#modalLoginUserHome"]'
        
        try:
            enlace_modal = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector_modal)))
            print("✅ Enlace del modal encontrado")
        except:
            # Fallback: buscar por partes
            enlace_modal = None
            selectores_fallback = [
                'a[data-target="#modalLoginUserHome"]',
                'a.modal-action',
                'a:has(i.fas.fa-user-circle)',
                'i.fas.fa-user-circle'
            ]
            
            for selector in selectores_fallback:
                try:
                    if selector == 'i.fas.fa-user-circle':
                        # Si es el icono, buscar el enlace padre
                        icono = driver.find_element(By.CSS_SELECTOR, selector)
                        enlace_modal = icono.find_element(By.XPATH, "./ancestor::a[1]")
                    else:
                        enlace_modal = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if enlace_modal and enlace_modal.is_displayed():
                        print(f"✅ Enlace encontrado con selector fallback: {selector}")
                        break
                except:
                    continue
            
            if not enlace_modal:
                raise Exception("No se encontró el enlace que abre el modal")
        
        # Hacer scroll al enlace
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", enlace_modal)
        time.sleep(2)
        
        # Hacer clic en el enlace para abrir el modal
        print("🖱️ Haciendo clic en enlace para abrir modal...")
        driver.execute_script("arguments[0].click();", enlace_modal)
        time.sleep(3)
        
        # Esperar a que el modal sea visible
        print("⏳ Esperando que el modal sea visible...")
        try:
            modal = wait.until(EC.visibility_of_element_located((By.ID, "modalLoginUserHome")))
            print("✅ Modal visible")
        except:
            print("⚠️ No se pudo detectar el modal, continuando...")
        
        # Esperar a que los campos de login sean interactuables
        print("⏳ Esperando campos de login...")
        
        # Esperar el campo de usuario con múltiples intentos
        usuario_field = None
        for intento in range(5):
            try:
                usuario_field = wait.until(EC.element_to_be_clickable((By.ID, "login_username")))
                print("✅ Campo de usuario encontrado y clickeable")
                break
            except:
                print(f"⏳ Intento {intento + 1}/5 - Esperando campo de usuario...")
                time.sleep(2)
        
        if not usuario_field:
            raise Exception("No se pudo encontrar el campo de usuario interactuable")
        
        # Esperar el campo de contraseña
        password_field = None
        for intento in range(5):
            try:
                password_field = wait.until(EC.element_to_be_clickable((By.ID, "login_password")))
                print("✅ Campo de contraseña encontrado y clickeable")
                break
            except:
                print(f"⏳ Intento {intento + 1}/5 - Esperando campo de contraseña...")
                time.sleep(2)
        
        if not password_field:
            raise Exception("No se pudo encontrar el campo de contraseña interactuable")
        
        # Llenar los campos con más cuidado
        print("📝 Llenando campos de login...")
        
        # Limpiar y llenar campo de usuario
        try:
            usuario_field.clear()
            time.sleep(1)
            usuario_field.send_keys(proveedor["usuario"])
            print(f"✅ Usuario ingresado: {proveedor['usuario']}")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar usuario: {e}")
            # Intentar con JavaScript
            driver.execute_script(f"arguments[0].value = '{proveedor['usuario']}';", usuario_field)
            print("✅ Usuario ingresado con JavaScript")
        
        # Limpiar y llenar campo de contraseña
        try:
            password_field.clear()
            time.sleep(1)
            password_field.send_keys(proveedor["contrasena"])
            print("✅ Contraseña ingresada")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar contraseña: {e}")
            # Intentar con JavaScript
            driver.execute_script(f"arguments[0].value = '{proveedor['contrasena']}';", password_field)
            print("✅ Contraseña ingresada con JavaScript")
        
        # Buscar y hacer clic en el botón de submit específico de Ventor
        print("🔍 Buscando botón 'Iniciar sesión'...")
        
        # Selectores específicos para el botón de Ventor
        selectores_submit = [
            # Selector específico para el botón de Ventor
            "button.button.button--primary.loginHome",
            "button.loginHome",
            ".button--primary.loginHome",
            # Fallbacks por texto
            "//button[contains(text(), 'Iniciar sesión')]",
            "//button[contains(text(), 'Iniciar')]",
            "//button[contains(text(), 'Login')]",
            # Fallbacks por clases
            "#modalLoginUserHome button.button--primary",
            "#modalLoginUserHome .loginHome",
            "#modalLoginUserHome button[type='button']",
            # Fallbacks generales en el modal
            "#modalLoginUserHome button"
        ]
        
        submit_button = None
        for selector in selectores_submit:
            try:
                if selector.startswith("//"):
                    # Para selectores XPath
                    submit_button = driver.find_element(By.XPATH, selector)
                else:
                    # Para selectores CSS
                    submit_button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if submit_button and submit_button.is_displayed() and submit_button.is_enabled():
                    print(f"✅ Botón de submit encontrado con selector: {selector}")
                    break
                else:
                    submit_button = None
            except:
                continue
        
        if not submit_button:
            # Búsqueda más exhaustiva
            print("🔍 Búsqueda exhaustiva de botón de submit...")
            try:
                # Buscar todos los botones en el modal
                botones = driver.find_elements(By.CSS_SELECTOR, "#modalLoginUserHome button")
                for boton in botones:
                    if boton.is_displayed() and boton.is_enabled():
                        texto = boton.text.strip().lower()
                        clases = boton.get_attribute("class") or ""
                        print(f"🔍 Botón encontrado - Texto: '{texto}', Clases: '{clases}'")
                        
                        if any(palabra in texto for palabra in ['iniciar', 'login', 'ingresar', 'entrar']):
                            submit_button = boton
                            print(f"✅ Botón seleccionado por texto: '{texto}'")
                            break
                        elif 'loginHome' in clases or 'button--primary' in clases:
                            submit_button = boton
                            print(f"✅ Botón seleccionado por clase: '{clases}'")
                            break
                
                # Si no encontramos por texto o clase, tomar el primer botón visible
                if not submit_button and botones:
                    for boton in botones:
                        if boton.is_displayed() and boton.is_enabled():
                            submit_button = boton
                            print(f"✅ Usando primer botón disponible")
                            break
            except Exception as e:
                print(f"⚠️ Error en búsqueda exhaustiva: {e}")
        
        if submit_button:
            print("🚀 Haciendo clic en botón de submit...")
            try:
                # Hacer scroll al botón
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                time.sleep(1)
                
                # Intentar clic normal primero
                submit_button.click()
                print("✅ Clic normal exitoso")
            except Exception as e:
                print(f"⚠️ Clic normal falló: {e}, intentando con JavaScript...")
                # Si falla el clic normal, usar JavaScript
                driver.execute_script("arguments[0].click();", submit_button)
                print("✅ Clic con JavaScript exitoso")
        else:
            # Si no hay botón, intentar enviar con Enter en el campo de contraseña
            print("⌨️ No se encontró botón, enviando formulario con Enter...")
            password_field.send_keys("\n")
        
        time.sleep(5)
        print("✅ Login de Ventor completado")
        
    except Exception as e:
        raise Exception(f"Error en login de Ventor: {e}")

def hacer_login_icepar(driver, proveedor, wait):
    """Manejar el login específico para Icepar"""
    print("🔧 Procesando login específico para Icepar...")
    
    try:
        # Buscar campo de email específico de Icepar
        print("🔍 Buscando campo de email...")
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "email")))
        print("✅ Campo de email encontrado")
        
        # Buscar campo de contraseña específico de Icepar
        print("🔍 Buscando campo de contraseña...")
        password_field = wait.until(EC.element_to_be_clickable((By.ID, "password")))
        print("✅ Campo de contraseña encontrado")
        
        # Llenar los campos
        print("📝 Llenando campos de login...")
        
        # Limpiar y llenar campo de email
        try:
            email_field.clear()
            time.sleep(1)
            email_field.send_keys(proveedor["usuario"])
            print(f"✅ Email ingresado: {proveedor['usuario']}")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar email: {e}")
            # Intentar con JavaScript
            driver.execute_script(f"arguments[0].value = '{proveedor['usuario']}';", email_field)
            print("✅ Email ingresado con JavaScript")
        
        # Limpiar y llenar campo de contraseña
        try:
            password_field.clear()
            time.sleep(1)
            password_field.send_keys(proveedor["contrasena"])
            print("✅ Contraseña ingresada")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar contraseña: {e}")
            # Intentar con JavaScript
            driver.execute_script(f"arguments[0].value = '{proveedor['contrasena']}';", password_field)
            print("✅ Contraseña ingresada con JavaScript")
        
        # Buscar botón de submit
        print("🔍 Buscando botón de submit...")
        
        selectores_submit = [
            "button[type='submit']",
            "input[type='submit']",
            "//button[contains(text(), 'Ingresar')]",
            "//button[contains(text(), 'Login')]",
            "//button[contains(text(), 'Entrar')]",
            "//input[contains(@value, 'Ingresar')]",
            "//input[contains(@value, 'Login')]",
            ".btn-primary",
            ".btn-success",
            "button"
        ]
        
        submit_button = None
        for selector in selectores_submit:
            try:
                if selector.startswith("//"):
                    # Para selectores XPath
                    submit_button = driver.find_element(By.XPATH, selector)
                else:
                    # Para selectores CSS
                    submit_button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if submit_button and submit_button.is_displayed() and submit_button.is_enabled():
                    print(f"✅ Botón de submit encontrado con selector: {selector}")
                    break
                else:
                    submit_button = None
            except:
                continue
        
        if submit_button:
            print("🚀 Haciendo clic en botón de submit...")
            try:
                submit_button.click()
                print("✅ Clic normal exitoso")
            except Exception as e:
                print(f"⚠️ Clic normal falló: {e}, intentando con JavaScript...")
                driver.execute_script("arguments[0].click();", submit_button)
                print("✅ Clic con JavaScript exitoso")
        else:
            # Si no hay botón, intentar enviar con Enter
            print("⌨️ No se encontró botón, enviando formulario con Enter...")
            password_field.send_keys("\n")
        
        time.sleep(5)
        print("✅ Login de Icepar completado")
        
    except Exception as e:
        raise Exception(f"Error en login de Icepar: {e}")

def hacer_login_atonor(driver, proveedor, wait):
    """Manejar el login específico para Atonor"""
    print("🔧 Procesando login específico para Atonor...")
    
    try:
        # Buscar campo de usuario específico de Atonor (con name="log")
        print("🔍 Buscando campo de usuario...")
        
        # Intentar múltiples selectores para el campo de usuario
        selectores_usuario = [
            'input[name="log"]',
            'input[id*="user-"]',
            'input[id*="user"]',
            'input.elementor-field-textual[type="text"]',
            'input[placeholder*="usuario"]',
            'input[placeholder*="Usuario"]'
        ]
        
        usuario_field = None
        for selector in selectores_usuario:
            try:
                usuario_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                print(f"✅ Campo de usuario encontrado con selector: {selector}")
                break
            except:
                continue
        
        if not usuario_field:
            raise Exception("No se pudo encontrar el campo de usuario")
        
        # Buscar campo de contraseña específico de Atonor (con name="pwd")
        print("🔍 Buscando campo de contraseña...")
        
        selectores_password = [
            'input[name="pwd"]',
            'input[id*="password-"]',
            'input[id*="password"]',
            'input.elementor-field-textual[type="password"]',
            'input[placeholder*="contraseña"]',
            'input[placeholder*="Contraseña"]'
        ]
        
        password_field = None
        for selector in selectores_password:
            try:
                password_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                print(f"✅ Campo de contraseña encontrado con selector: {selector}")
                break
            except:
                continue
        
        if not password_field:
            raise Exception("No se pudo encontrar el campo de contraseña")
        
        # Llenar los campos
        print("📝 Llenando campos de login...")
        
        # Limpiar y llenar campo de usuario
        try:
            usuario_field.clear()
            time.sleep(1)
            usuario_field.send_keys(proveedor["usuario"])
            print(f"✅ Usuario ingresado: {proveedor['usuario']}")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar usuario: {e}")
            # Intentar con JavaScript
            driver.execute_script(f"arguments[0].value = '{proveedor['usuario']}';", usuario_field)
            print("✅ Usuario ingresado con JavaScript")
        
        # Limpiar y llenar campo de contraseña
        try:
            password_field.clear()
            time.sleep(1)
            password_field.send_keys(proveedor["contrasena"])
            print("✅ Contraseña ingresada")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar contraseña: {e}")
            # Intentar con JavaScript
            driver.execute_script(f"arguments[0].value = '{proveedor['contrasena']}';", password_field)
            print("✅ Contraseña ingresada con JavaScript")
        
        # Buscar botón de submit
        print("🔍 Buscando botón de submit...")
        
        selectores_submit = [
            "button[type='submit']",
            "input[type='submit']",
            "//button[contains(text(), 'Ingresar')]",
            "//button[contains(text(), 'Login')]",
            "//button[contains(text(), 'Entrar')]",
            "//input[contains(@value, 'Ingresar')]",
            "//input[contains(@value, 'Login')]",
            ".elementor-button",
            ".btn-primary",
            ".btn-success",
            "button"
        ]
        
        submit_button = None
        for selector in selectores_submit:
            try:
                if selector.startswith("//"):
                    # Para selectores XPath
                    submit_button = driver.find_element(By.XPATH, selector)
                else:
                    # Para selectores CSS
                    submit_button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if submit_button and submit_button.is_displayed() and submit_button.is_enabled():
                    print(f"✅ Botón de submit encontrado con selector: {selector}")
                    break
                else:
                    submit_button = None
            except:
                continue
        
        if submit_button:
            print("🚀 Haciendo clic en botón de submit...")
            try:
                submit_button.click()
                print("✅ Clic normal exitoso")
            except Exception as e:
                print(f"⚠️ Clic normal falló: {e}, intentando con JavaScript...")
                driver.execute_script("arguments[0].click();", submit_button)
                print("✅ Clic con JavaScript exitoso")
        else:
            # Si no hay botón, intentar enviar con Enter
            print("⌨️ No se encontró botón, enviando formulario con Enter...")
            password_field.send_keys("\n")
        
        time.sleep(5)
        print("✅ Login de Atonor completado")
        
    except Exception as e:
        raise Exception(f"Error en login de Atonor: {e}")

def hacer_login_sinkromat(driver, proveedor, wait):
    """Manejar el login específico para Sinkromat"""
    print("🔧 Procesando login específico para Sinkromat...")
    
    try:
        # Buscar campo de email específico de Sinkromat (con placeholder="Email")
        print("🔍 Buscando campo de email...")
        
        # Intentar múltiples selectores para el campo de email
        selectores_email = [
            'input[placeholder="Email"]',
            'input.chakra-input.css-zncb5o[placeholder="Email"]',
            'input.chakra-input[placeholder="Email"]',
            'input[placeholder*="Email"]',
            'input[placeholder*="email"]',
            'input.chakra-input[type="text"]',
            'input.chakra-input.css-zncb5o'
        ]
        
        email_field = None
        for selector in selectores_email:
            try:
                email_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                print(f"✅ Campo de email encontrado con selector: {selector}")
                break
            except:
                continue
        
        if not email_field:
            raise Exception("No se pudo encontrar el campo de email")
        
        # Buscar campo de contraseña específico de Sinkromat (con placeholder="Contraseña")
        print("🔍 Buscando campo de contraseña...")
        
        selectores_password = [
            'input[placeholder="Contraseña"]',
            'input.chakra-input.css-zncb5o[placeholder="Contraseña"]',
            'input.chakra-input[placeholder="Contraseña"]',
            'input[placeholder*="Contraseña"]',
            'input[placeholder*="contraseña"]',
            'input.chakra-input[type="password"]',
            'input[type="password"].chakra-input.css-zncb5o'
        ]
        
        password_field = None
        for selector in selectores_password:
            try:
                password_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                print(f"✅ Campo de contraseña encontrado con selector: {selector}")
                break
            except:
                continue
        
        if not password_field:
            raise Exception("No se pudo encontrar el campo de contraseña")
        
        # Llenar los campos
        print("📝 Llenando campos de login...")
        
        # Limpiar y llenar campo de email
        try:
            email_field.clear()
            time.sleep(1)
            email_field.send_keys(proveedor["usuario"])
            print(f"✅ Email ingresado: {proveedor['usuario']}")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar email: {e}")
            # Intentar con JavaScript
            driver.execute_script(f"arguments[0].value = '{proveedor['usuario']}';", email_field)
            print("✅ Email ingresado con JavaScript")
        
        # Limpiar y llenar campo de contraseña
        try:
            password_field.clear()
            time.sleep(1)
            password_field.send_keys(proveedor["contrasena"])
            print("✅ Contraseña ingresada")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar contraseña: {e}")
            # Intentar con JavaScript
            driver.execute_script(f"arguments[0].value = '{proveedor['contrasena']}';", password_field)
            print("✅ Contraseña ingresada con JavaScript")
        
        # Buscar botón de submit específico de Sinkromat
        print("🔍 Buscando botón 'INGRESAR'...")
        
        selectores_submit = [
            # Selector específico para el botón de Sinkromat
            'button.chakra-button.css-1opa624',
            'button.chakra-button[type="button"]',
            '//button[contains(text(), "INGRESAR")]',
            '//button[contains(text(), "Ingresar")]',
            '//button[contains(text(), "ingresar")]',
            # Fallbacks por clases de Chakra UI
            'button.chakra-button',
            'button[class*="chakra-button"]',
            'button[class*="css-1opa624"]',
            # Fallbacks generales
            'button[type="button"]',
            'button'
        ]
        
        submit_button = None
        for selector in selectores_submit:
            try:
                if selector.startswith("//"):
                    # Para selectores XPath
                    submit_button = driver.find_element(By.XPATH, selector)
                else:
                    # Para selectores CSS
                    submit_button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if submit_button and submit_button.is_displayed() and submit_button.is_enabled():
                    texto = submit_button.text.strip()
                    print(f"✅ Botón de submit encontrado con selector: {selector}, texto: '{texto}'")
                    break
                else:
                    submit_button = None
            except:
                continue
        
        if not submit_button:
            # Búsqueda más exhaustiva
            print("🔍 Búsqueda exhaustiva de botón de submit...")
            try:
                # Buscar todos los botones
                botones = driver.find_elements(By.TAG_NAME, "button")
                for boton in botones:
                    if boton.is_displayed() and boton.is_enabled():
                        texto = boton.text.strip().lower()
                        clases = boton.get_attribute("class") or ""
                        print(f"🔍 Botón encontrado - Texto: '{texto}', Clases: '{clases}'")
                        
                        if any(palabra in texto for palabra in ['ingresar', 'login', 'entrar']):
                            submit_button = boton
                            print(f"✅ Botón seleccionado por texto: '{texto}'")
                            break
                        elif 'chakra-button' in clases:
                            submit_button = boton
                            print(f"✅ Botón seleccionado por clase Chakra: '{clases}'")
                            break
                
                # Si no encontramos por texto o clase, tomar el primer botón Chakra visible
                if not submit_button:
                    for boton in botones:
                        if boton.is_displayed() and boton.is_enabled():
                            clases = boton.get_attribute("class") or ""
                            if 'chakra-button' in clases:
                                submit_button = boton
                                print(f"✅ Usando primer botón Chakra disponible")
                                break
            except Exception as e:
                print(f"⚠️ Error en búsqueda exhaustiva: {e}")
        
        if submit_button:
            print("🚀 Haciendo clic en botón de submit...")
            try:
                # Hacer scroll al botón
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                time.sleep(1)
                
                # Intentar clic normal primero
                submit_button.click()
                print("✅ Clic normal exitoso")
            except Exception as e:
                print(f"⚠️ Clic normal falló: {e}, intentando con JavaScript...")
                # Si falla el clic normal, usar JavaScript
                driver.execute_script("arguments[0].click();", submit_button)
                print("✅ Clic con JavaScript exitoso")
        else:
            # Si no hay botón, intentar enviar con Enter
            print("⌨️ No se encontró botón, enviando formulario con Enter...")
            password_field.send_keys("\n")
        
        time.sleep(5)
        print("✅ Login de Sinkromat completado")
        
    except Exception as e:
        raise Exception(f"Error en login de Sinkromat: {e}")

def hacer_login_expoyer(driver, proveedor, wait):
    """Manejar el login específico para Expoyer con menú desplegable"""
    print("🔧 Procesando login específico para Expoyer...")
    
    try:
        # PASO 1: Buscar y hacer clic en el botón del menú desplegable
        print("🔍 Buscando botón del menú desplegable de login...")
        
        selectores_dropdown = [
            # Selector específico para el botón de Expoyer
            'button.btn.dropdown-toggle.btn-default.btn-sm[data-toggle="dropdown"]',
            'button.dropdown-toggle.btn-default.btn-sm',
            'button.btn.dropdown-toggle[data-toggle="dropdown"]',
            # Por icono y texto
            '//button[contains(@class, "dropdown-toggle") and .//i[contains(@class, "fa-lock")] and contains(text(), "Login")]',
            '//button[contains(@class, "dropdown-toggle") and contains(text(), "Login")]',
            # Fallbacks
            'button.dropdown-toggle',
            'button[data-toggle="dropdown"]'
        ]
        
        dropdown_button = None
        for selector in selectores_dropdown:
            try:
                if selector.startswith("//"):
                    dropdown_button = driver.find_element(By.XPATH, selector)
                else:
                    dropdown_button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if dropdown_button and dropdown_button.is_displayed() and dropdown_button.is_enabled():
                    texto = dropdown_button.text.strip()
                    clases = dropdown_button.get_attribute("class") or ""
                    print(f"✅ Botón dropdown encontrado - Texto: '{texto}', Clases: '{clases}'")
                    break
                else:
                    dropdown_button = None
            except:
                continue
        
        if not dropdown_button:
            raise Exception("No se encontró el botón del menú desplegable")
        
        # Hacer clic en el botón dropdown
        print("🖱️ Haciendo clic en botón del menú desplegable...")
        try:
            dropdown_button.click()
            print("✅ Menú desplegable abierto")
        except Exception as e:
            print(f"⚠️ Clic normal falló: {e}, intentando con JavaScript...")
            driver.execute_script("arguments[0].click();", dropdown_button)
            print("✅ Menú desplegable abierto con JavaScript")
        
        time.sleep(2)
        
        # PASO 2: Buscar campos de login que ahora deberían estar visibles
        print("🔍 Buscando campos de login...")
        
        # Buscar campo de usuario específico
        usuario_field = None
        try:
            usuario_field = wait.until(EC.element_to_be_clickable((By.ID, "login-user")))
            print("✅ Campo de usuario encontrado")
        except:
            # Fallback por selector
            try:
                usuario_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="j_username"]')))
                print("✅ Campo de usuario encontrado por name")
            except:
                raise Exception("No se pudo encontrar el campo de usuario")
        
        # Buscar campo de contraseña específico
        password_field = None
        try:
            password_field = wait.until(EC.element_to_be_clickable((By.ID, "login-password")))
            print("✅ Campo de contraseña encontrado")
        except:
            # Fallback por selector
            try:
                password_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="j_password"]')))
                print("✅ Campo de contraseña encontrado por name")
            except:
                raise Exception("No se pudo encontrar el campo de contraseña")
        
        # PASO 3: Llenar los campos
        print("📝 Llenando campos de login...")
        
        # Limpiar y llenar campo de usuario
        try:
            usuario_field.clear()
            time.sleep(1)
            usuario_field.send_keys(proveedor["usuario"])
            print(f"✅ Usuario ingresado: {proveedor['usuario']}")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar usuario: {e}")
            driver.execute_script(f"arguments[0].value = '{proveedor['usuario']}';", usuario_field)
            print("✅ Usuario ingresado con JavaScript")
        
        # Limpiar y llenar campo de contraseña
        try:
            password_field.clear()
            time.sleep(1)
            password_field.send_keys(proveedor["contrasena"])
            print("✅ Contraseña ingresada")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error al llenar contraseña: {e}")
            driver.execute_script(f"arguments[0].value = '{proveedor['contrasena']}';", password_field)
            print("✅ Contraseña ingresada con JavaScript")
        
        # PASO 4: Buscar y hacer clic en el botón INGRESAR
        print("🔍 Buscando botón 'INGRESAR'...")
        
        selectores_submit = [
            # Selector específico para el botón de Expoyer
            'button#submitButton.btn.btn-default.btn-md.pull-right.mt-20.no-marge',
            'button#submitButton',
            '#submitButton',
            # Por texto
            '//button[contains(text(), "INGRESAR")]',
            '//button[contains(text(), "Ingresar")]',
            # Fallbacks
            'button[type="submit"]',
            'button.btn.btn-default.btn-md'
        ]
        
        submit_button = None
        for selector in selectores_submit:
            try:
                if selector.startswith("//"):
                    submit_button = driver.find_element(By.XPATH, selector)
                else:
                    submit_button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if submit_button and submit_button.is_displayed() and submit_button.is_enabled():
                    texto = submit_button.text.strip()
                    print(f"✅ Botón submit encontrado - Texto: '{texto}'")
                    break
                else:
                    submit_button = None
            except:
                continue
        
        if not submit_button:
            raise Exception("No se encontró el botón INGRESAR")
        
        # Hacer clic en el botón INGRESAR
        print("🚀 Haciendo clic en botón INGRESAR...")
        try:
            submit_button.click()
            print("✅ Clic normal exitoso")
        except Exception as e:
            print(f"⚠️ Clic normal falló: {e}, intentando con JavaScript...")
            driver.execute_script("arguments[0].click();", submit_button)
            print("✅ Clic con JavaScript exitoso")
        
        time.sleep(5)
        print("✅ Login de Expoyer completado")
        
    except Exception as e:
        raise Exception(f"Error en login de Expoyer: {e}")

def descargar_archivo_expoyer(driver, wait):
    """Manejar la descarga específica de Expoyer con checkbox y confirmación"""
    print("📥 Iniciando descarga específica de Expoyer...")
    
    try:
        # Obtener archivos antes de la descarga (TODOS los archivos, no solo Excel)
        archivos_iniciales = obtener_todos_archivos_actuales()
        print(f"📁 Archivos iniciales detectados: {len(archivos_iniciales)}")
        
        # PASO 1: Marcar el checkbox para seleccionar todos
        print("🔍 Buscando switch para marcar todos...")
        
        # Primero intentar con el label (que es lo que el usuario ve y hace clic)
        selectores_label = [
            'label.switch-label[for="switch"]',
            'label[for="switch"]',
            '.switch-label'
        ]
        
        label_encontrado = None
        for selector in selectores_label:
            try:
                label_encontrado = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                if label_encontrado.is_displayed():
                    print(f"✅ Label del switch encontrado con selector: {selector}")
                    break
                else:
                    label_encontrado = None
            except:
                continue
        
        # Si encontramos el label, intentamos hacer clic en él
        if label_encontrado:
            print("☑️ Haciendo clic en el label del switch...")
            try:
                # Hacer scroll al label
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label_encontrado)
                time.sleep(1)
                
                # Intentar clic normal
                label_encontrado.click()
                print("✅ Clic en label exitoso")
            except Exception as e:
                print(f"⚠️ Clic normal en label falló: {e}, intentando con JavaScript...")
                driver.execute_script("arguments[0].click();", label_encontrado)
                print("✅ Clic en label con JavaScript exitoso")
            
            time.sleep(3)  # Dar tiempo para que se procese el cambio
        else:
            # Si no encontramos el label, intentamos con el input directamente
            print("🔍 Label no encontrado, buscando input del switch...")
            
            selectores_checkbox = [
                'input#switch.switch-input[type="checkbox"]',
                'input#switch[type="checkbox"]',
                '#switch',
                'input.switch-input[type="checkbox"]'
            ]
            
            checkbox = None
            for selector in selectores_checkbox:
                try:
                    checkbox = driver.find_element(By.CSS_SELECTOR, selector)
                    if checkbox:
                        print(f"✅ Input del switch encontrado con selector: {selector}")
                        break
                except:
                    continue
            
            if checkbox:
                # Verificar si ya está marcado
                if not checkbox.is_selected():
                    print("☑️ Marcando checkbox con JavaScript...")
                    try:
                        # Usar JavaScript para cambiar el estado directamente
                        driver.execute_script("arguments[0].checked = true; arguments[0].dispatchEvent(new Event('change', { 'bubbles': true }));", checkbox)
                        print("✅ Checkbox marcado con JavaScript")
                    except Exception as e:
                        print(f"⚠️ Error al marcar checkbox con JavaScript: {e}")
                else:
                    print("✅ Checkbox ya estaba marcado")
            else:
                print("⚠️ No se encontró ni el label ni el input del switch")
                # Intentar continuar de todos modos
        
        # Verificar si el switch se activó correctamente
        try:
            # Esperar un momento para que se procese el cambio
            time.sleep(3)
            
            # Intentar verificar si hay elementos seleccionados
            elementos_seleccionados = driver.find_elements(By.CSS_SELECTOR, '.selected, [data-selected="true"], .active')
            if elementos_seleccionados:
                print(f"✅ Se detectaron {len(elementos_seleccionados)} elementos seleccionados")
            else:
                print("⚠️ No se detectaron elementos seleccionados, pero continuando...")
        except Exception as e:
            print(f"⚠️ Error al verificar elementos seleccionados: {e}")
        
        # PASO 2: Hacer clic en el botón "Descargar XLS"
        print("🔍 Buscando botón 'Descargar XLS'...")
        
        selectores_xls = [
            # Selector específico para el botón XLS de Expoyer
            'button#xls.btn.btn-primary',
            'button#xls',
            '#xls',
            '//button[@id="xls" and .//i[contains(@class, "fa-file-excel-o")]]',
            '//button[contains(text(), "Descargar XLS")]',
            # Fallbacks
            'button.btn.btn-primary:has(i.fa-file-excel-o)',
            'button:has(i.fa-file-excel-o)',
            'button.btn.btn-primary',
            'button.btn-primary'
        ]
        
        xls_button = None
        for selector in selectores_xls:
            try:
                if selector.startswith("//"):
                    xls_button = driver.find_element(By.XPATH, selector)
                else:
                    xls_button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if xls_button and xls_button.is_displayed() and xls_button.is_enabled():
                    texto = xls_button.text.strip()
                    print(f"✅ Botón XLS encontrado - Texto: '{texto}'")
                    break
                else:
                    xls_button = None
            except:
                continue
        
        if not xls_button:
            raise Exception("No se encontró el botón 'Descargar XLS'")
        
        # Hacer clic en el botón XLS
        print("🖱️ Haciendo clic en botón 'Descargar XLS'...")
        try:
            # Hacer scroll al botón
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", xls_button)
            time.sleep(2)
            
            # Intentar clic normal
            xls_button.click()
            print("✅ Botón XLS clickeado")
        except Exception as e:
            print(f"⚠️ Clic normal falló: {e}, intentando con JavaScript...")
            driver.execute_script("arguments[0].click();", xls_button)
            print("✅ Botón XLS clickeado con JavaScript")
        
        time.sleep(3)
        
        # PASO 3: Buscar y hacer clic en el botón "Continuar" del menú de confirmación
        print("🔍 Buscando botón 'Continuar' en menú de confirmación...")
        
        selectores_continuar = [
            # Selector específico para el botón Continuar
            'button.btn.btn-sm.btn-success[title="Continuar"]',
            'button.btn.btn-success[title="Continuar"]',
            'button[title="Continuar"]',
            '//button[@title="Continuar" and contains(text(), "Continuar")]',
            '//button[contains(text(), "Continuar")]',
            # Fallbacks
            'button.btn-success',
            'button.btn.btn-sm.btn-success',
            '.btn-success',
            '.btn.btn-success'
        ]
        
        continuar_button = None
        for selector in selectores_continuar:
            try:
                if selector.startswith("//"):
                    elementos = driver.find_elements(By.XPATH, selector)
                else:
                    elementos = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for elemento in elementos:
                    if elemento.is_displayed() and elemento.is_enabled():
                        texto = elemento.text.strip()
                        title = elemento.get_attribute("title") or ""
                        print(f"✅ Botón Continuar encontrado - Texto: '{texto}', Title: '{title}'")
                        continuar_button = elemento
                        break
                
                if continuar_button:
                    break
            except Exception as e:
                print(f"⚠️ Error con selector {selector}: {e}")
                continue
        
        if not continuar_button:
            # Intentar buscar en cualquier modal o diálogo visible
            print("🔍 Buscando botón Continuar en cualquier modal visible...")
            try:
                # Buscar modales visibles
                modales = driver.find_elements(By.CSS_SELECTOR, '.modal.show, .modal[style*="display: block"], .dialog[style*="display: block"]')
                for modal in modales:
                    # Buscar botones dentro del modal
                    botones = modal.find_elements(By.CSS_SELECTOR, 'button')
                    for boton in botones:
                        if boton.is_displayed() and boton.is_enabled():
                            texto = boton.text.strip()
                            if "continuar" in texto.lower() or "aceptar" in texto.lower() or "ok" in texto.lower():
                                continuar_button = boton
                                print(f"✅ Botón encontrado en modal - Texto: '{texto}'")
                                break
                    
                    if continuar_button:
                        break
            except Exception as e:
                print(f"⚠️ Error al buscar en modales: {e}")
        
        if continuar_button:
            # Hacer clic en el botón Continuar
            print("🖱️ Haciendo clic en botón 'Continuar'...")
            try:
                # Hacer scroll al botón
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", continuar_button)
                time.sleep(1)
                
                # Intentar clic normal
                continuar_button.click()
                print("✅ Botón Continuar clickeado")
            except Exception as e:
                print(f"⚠️ Clic normal falló: {e}, intentando con JavaScript...")
                driver.execute_script("arguments[0].click();", continuar_button)
                print("✅ Botón Continuar clickeado con JavaScript")
        else:
            print("⚠️ No se encontró el botón 'Continuar', intentando continuar...")
        
        # PASO 4: Esperar y buscar el enlace de descarga final
        print("⏳ Esperando que se prepare el archivo...")
        time.sleep(5)
        
        print("🔍 Buscando enlace de descarga final...")
        
        selectores_link = [
            # Selector específico para el enlace de descarga
            'a#link[href="/catalogo/descargar/ARTICULOS-XLS.ZIP"]',
            'a#link',
            '#link',
            'a[href*="ARTICULOS-XLS.ZIP"]',
            'a[href*="/catalogo/descargar/"]',
            # Fallbacks
            'a[href*=".ZIP"]',
            'a[href*=".zip"]',
            'a:contains("aquí")',
            '//a[contains(text(), "aquí")]'
        ]
        
        download_link = None
        # Intentar encontrar el enlace con múltiples intentos
        for intento in range(15):  # 15 intentos, 45 segundos total
            for selector in selectores_link:
                try:
                    if selector.startswith("//"):
                        elementos = driver.find_elements(By.XPATH, selector)
                    elif selector.startswith("a:contains"):
                        # Caso especial para texto "aquí"
                        enlaces = driver.find_elements(By.TAG_NAME, "a")
                        elementos = [enlace for enlace in enlaces if "aquí" in enlace.text.lower()]
                    else:
                        elementos = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for elemento in elementos:
                        if elemento.is_displayed():
                            href = elemento.get_attribute("href") or ""
                            texto = elemento.text.strip()
                            print(f"✅ Enlace de descarga encontrado - Href: '{href}', Texto: '{texto}'")
                            download_link = elemento
                            break
                    
                    if download_link:
                        break
                except Exception as e:
                    print(f"⚠️ Error con selector {selector}: {e}")
                    continue
            
            if download_link:
                break
            
            print(f"⏳ Intento {intento + 1}/15 - Esperando enlace de descarga...")
            time.sleep(3)
        
        if not download_link:
            # Último intento: buscar cualquier enlace visible que pueda ser de descarga
            print("🔍 Búsqueda final de cualquier enlace de descarga...")
            try:
                enlaces = driver.find_elements(By.TAG_NAME, "a")
                for enlace in enlaces:
                    if enlace.is_displayed():
                        href = enlace.get_attribute("href") or ""
                        texto = enlace.text.strip()
                        if (".zip" in href.lower() or 
                            ".xls" in href.lower() or 
                            "descargar" in href.lower() or 
                            "download" in href.lower() or
                            "aquí" in texto.lower()):
                            print(f"✅ Posible enlace de descarga encontrado - Href: '{href}', Texto: '{texto}'")
                            download_link = enlace
                            break
            except Exception as e:
                print(f"⚠️ Error en búsqueda final: {e}")
        
        if not download_link:
            raise Exception("No se encontró el enlace de descarga final")
        
        # PASO 5: Hacer clic en el enlace de descarga
        print("📥 Haciendo clic en enlace de descarga...")
        try:
            # Hacer scroll al enlace
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_link)
            time.sleep(1)
            
            # Intentar clic normal
            download_link.click()
            print("✅ Descarga iniciada")
        except Exception as e:
            print(f"⚠️ Clic normal falló: {e}, intentando con JavaScript...")
            driver.execute_script("arguments[0].click();", download_link)
            print("✅ Descarga iniciada con JavaScript")
        
        # PASO 6: Esperar descarga del ZIP usando la función específica
        print("⏳ Esperando descarga del archivo ZIP...")
        archivo_zip = esperar_descarga_zip(archivos_iniciales, timeout_minutos=3)
        
        if not archivo_zip:
            # Verificar si hay algún archivo nuevo aunque no sea ZIP
            print("🔍 Verificando si hay archivos nuevos de cualquier tipo...")
            archivos_actuales = obtener_todos_archivos_actuales()
            archivos_nuevos = archivos_actuales - archivos_iniciales
            
            if archivos_nuevos:
                print(f"📄 Se encontraron {len(archivos_nuevos)} archivo(s) nuevo(s):")
                for archivo in archivos_nuevos:
                    print(f"   📄 {archivo.name} ({archivo.suffix}) - {archivo.stat().st_size} bytes")
                
                # Buscar archivos que podrían ser el ZIP con nombre diferente
                posibles_zip = [archivo for archivo in archivos_nuevos 
                               if archivo.suffix.lower() in ['.zip', '.rar', '.7z'] or 
                               'articulos' in archivo.name.lower() or
                               'xls' in archivo.name.lower()]
                
                if posibles_zip:
                    archivo_zip = posibles_zip[0]
                    print(f"✅ Archivo ZIP encontrado con nombre diferente: {archivo_zip.name}")
                else:
                    raise Exception("No se descargó ningún archivo ZIP")
            else:
                raise Exception("No se descargó ningún archivo")
        
        print(f"✅ Archivo ZIP descargado: {archivo_zip.name}")
        
        # PASO 7: Descomprimir el ZIP y extraer el Excel
        print("📦 Descomprimiendo archivo ZIP...")
        archivo_excel = descomprimir_zip_expoyer(archivo_zip)
        
        if archivo_excel:
            print(f"✅ Archivo Excel extraído: {archivo_excel.name}")
            return archivo_excel
        else:
            raise Exception("No se pudo extraer el archivo Excel del ZIP")
        
    except Exception as e:
        print(f"❌ Error en descarga de Expoyer: {e}")
        return None

def descomprimir_zip_expoyer(archivo_zip):
    """Descomprimir el archivo ZIP de Expoyer y extraer el Excel"""
    import zipfile
    
    try:
        print(f"📦 Descomprimiendo: {archivo_zip.name}")
        
        # Crear carpeta temporal para extraer
        carpeta_temp = archivo_zip.parent / f"temp_{archivo_zip.stem}"
        carpeta_temp.mkdir(exist_ok=True)
        
        # Descomprimir el ZIP
        with zipfile.ZipFile(archivo_zip, 'r') as zip_ref:
            zip_ref.extractall(carpeta_temp)
            archivos_extraidos = zip_ref.namelist()
            print(f"📄 Archivos extraídos: {archivos_extraidos}")
        
        # Buscar archivos Excel en la carpeta extraída
        archivos_excel = list(carpeta_temp.glob("*.xlsx")) + list(carpeta_temp.glob("*.xls"))
        
        if not archivos_excel:
            # Buscar en subcarpetas
            archivos_excel = list(carpeta_temp.rglob("*.xlsx")) + list(carpeta_temp.rglob("*.xls"))
        
        if not archivos_excel:
            print("❌ No se encontraron archivos Excel en el ZIP")
            return None
        
        # Tomar el primer archivo Excel encontrado
        archivo_excel_temp = archivos_excel[0]
        print(f"📄 Archivo Excel encontrado: {archivo_excel_temp.name}")
        
        # Mover el archivo Excel a la carpeta de descargas con nombre apropiado
        fecha = datetime.now().strftime("%Y-%m-%d")
        nombre_final = f"Expoyer_{fecha}.xlsx"
        
        # Evitar sobrescribir archivos existentes
        contador = 1
        archivo_final = CARPETA_DESCARGAS / nombre_final
        while archivo_final.exists():
            nombre_final = f"Expoyer_{fecha}_{contador}.xlsx"
            archivo_final = CARPETA_DESCARGAS / nombre_final
            contador += 1
        
        # Mover el archivo
        archivo_excel_temp.rename(archivo_final)
        print(f"✅ Archivo Excel guardado como: {archivo_final.name}")
        
        # Limpiar archivos temporales
        try:
            # Eliminar el ZIP original
            archivo_zip.unlink()
            print(f"🗑️ ZIP original eliminado: {archivo_zip.name}")
            
            # Eliminar carpeta temporal
            import shutil
            shutil.rmtree(carpeta_temp)
            print(f"🗑️ Carpeta temporal eliminada")
        except Exception as e:
            print(f"⚠️ Error al limpiar archivos temporales: {e}")
        
        return archivo_final
        
    except Exception as e:
        print(f"❌ Error al descomprimir ZIP: {e}")
        return None

def hacer_login_normal(driver, proveedor, wait):
    """Manejar el login normal para otros proveedores"""
    print("🔧 Procesando login normal...")
    
    # Buscar campo de usuario
    usuario_field = None
    selectores_usuario = ["#username", "input[name='username']", "input[type='text']", "[formcontrolname='username']"]
    
    for selector in selectores_usuario:
        try:
            usuario_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            break
        except:
            continue
    
    if not usuario_field:
        raise Exception("No se pudo encontrar el campo de usuario")
    
    # Login
    usuario_field.clear()
    time.sleep(0.5)
    usuario_field.send_keys(proveedor["usuario"])
    time.sleep(1)
    
    password_field = driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='password'], input[type='password'], input[name='password']")
    password_field.clear()
    time.sleep(0.5)
    password_field.send_keys(proveedor["contrasena"])
    time.sleep(1)
    
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
    submit_button.click()

def intentar_descarga_archivo_principal(driver, proveedor_nombre):
    """Intentar descarga del archivo principal - UN SOLO INTENTO"""
    try:
        print(f"\n🔘 Descargando archivo de {proveedor_nombre}")
        
        # Para Fusion, usar la función específica de descarga múltiple
        if proveedor_nombre.lower() == 'fusion':
            wait = WebDriverWait(driver, 30)
            archivos_descargados = descargar_archivos_fusion(driver, wait)
            
            if archivos_descargados:
                print(f"🎉 ¡{len(archivos_descargados)} archivo(s) descargado(s) exitosamente!")
                for archivo in archivos_descargados:
                    print(f"   📄 {archivo}")
                return True, f"{len(archivos_descargados)} archivos"
            else:
                print(f"⚠️ No se descargaron archivos")
                return False, None
        
        # Para Expoyer, usar la función específica de descarga
        elif proveedor_nombre.lower() == 'expoyer':
            wait = WebDriverWait(driver, 30)
            archivo_descargado = descargar_archivo_expoyer(driver, wait)
            
            if archivo_descargado:
                print(f"🎉 ¡Archivo descargado y descomprimido exitosamente!")
                print(f"   📄 {archivo_descargado.name}")
                return True, archivo_descargado.name
            else:
                print(f"⚠️ No se pudo descargar el archivo")
                return False, None
        
        # Para otros proveedores, usar la lógica original
        # Buscar el botón/enlace de Excel (adaptado para cada proveedor)
        boton_principal = buscar_primer_boton_excel(driver, proveedor_nombre)
        
        if not boton_principal:
            raise Exception("No se encontró el botón/enlace de descarga")
        
        # Hacer scroll al botón/enlace
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton_principal)
        time.sleep(2)
        
        # Obtener archivos antes de este clic específico
        archivos_antes_clic = obtener_archivos_actuales()
        
        # Hacer clic
        driver.execute_script("arguments[0].click();", boton_principal)
        print(f"✅ Clic realizado en botón/enlace de descarga")
        
        # Esperar descarga (3 minutos)
        archivo_descargado = esperar_nueva_descarga(archivos_antes_clic, timeout_minutos=3)
        
        if archivo_descargado:
            # Renombrar archivo
            archivo_final = renombrar_archivo_descargado(archivo_descargado, proveedor_nombre)
            print(f"🎉 ¡Archivo descargado exitosamente!")
            return True, archivo_final.name
        else:
            print(f"⚠️ No se descargó el archivo")
            
            # Verificar si hay archivos nuevos sin renombrar
            archivos_actuales = obtener_archivos_actuales()
            archivos_nuevos = archivos_actuales - archivos_antes_clic
            
            if archivos_nuevos:
                print(f"📄 Hay {len(archivos_nuevos)} archivo(s) nuevo(s) sin procesar")
                for archivo_nuevo in archivos_nuevos:
                    if archivo_nuevo.stat().st_size > 1024:
                        print(f"📄 Procesando archivo encontrado: {archivo_nuevo.name}")
                        archivo_final = renombrar_archivo_descargado(archivo_nuevo, proveedor_nombre)
                        print(f"🎉 ¡Archivo recuperado!")
                        return True, archivo_final.name
            
            return False, None
        
    except Exception as e:
        print(f"❌ Error en descarga: {e}")
        return False, None

def procesar_proveedor_con_reintentos(proveedor, max_intentos=2):
    """Procesar un proveedor con reintentos en caso de error"""
    for intento in range(max_intentos):
        driver = None
        try:
            print(f"▶ Procesando proveedor: {proveedor['nombre']} (Intento {intento + 1})")
            
            # Crear driver
            chrome_options = crear_driver_con_opciones()
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            driver.set_page_load_timeout(120)
            driver.implicitly_wait(20)
            
            # Configurar script para evitar detección
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            wait = WebDriverWait(driver, 30)
            
            # Login
            print(f"Navegando a: {proveedor['login_url']}")
            driver.get(proveedor["login_url"])
            time.sleep(5)
            
            # Determinar tipo de login según el proveedor
            if proveedor['nombre'].lower() == 'fusion':
                hacer_login_fusion(driver, proveedor, wait)
            elif proveedor['nombre'].lower() == 'ventor':
                hacer_login_ventor(driver, proveedor, wait)
            elif proveedor['nombre'].lower() == 'icepar':
                hacer_login_icepar(driver, proveedor, wait)
            elif proveedor['nombre'].lower() == 'atonor':
                hacer_login_atonor(driver, proveedor, wait)
            elif proveedor['nombre'].lower() == 'sinkromat':
                hacer_login_sinkromat(driver, proveedor, wait)
            elif proveedor['nombre'].lower() == 'expoyer':
                hacer_login_expoyer(driver, proveedor, wait)
            else:
                hacer_login_normal(driver, proveedor, wait)
            
            # Verificar login y manejar página de productos para Fusion
            try:
                wait.until(EC.url_contains("/dashboard"))
                print("✅ Login exitoso")
            except:
                time.sleep(5)
                # Para Fusion, verificar si estamos en la página de productos
                if proveedor['nombre'].lower() == 'fusion':
                    if manejar_pagina_productos_fusion(driver, wait):
                        print("✅ Login de Fusion exitoso - página de productos manejada")
                    elif "login" not in driver.current_url.lower():
                        print("✅ Login de Fusion exitoso (verificación alternativa)")
                    else:
                        raise Exception("Login falló")
                # Para otros proveedores especiales, verificar si ya no estamos en la página de login
                elif proveedor['nombre'].lower() in ['ventor', 'icepar', 'atonor', 'sinkromat', 'expoyer']:
                    if "login" not in driver.current_url.lower():
                        print(f"✅ Login de {proveedor['nombre']} exitoso (verificación alternativa)")
                    else:
                        raise Exception("Login falló")
                else:
                    if "/dashboard" not in driver.current_url and "login" in driver.current_url:
                        raise Exception("Login falló")
            
            # Ir a página de descarga
            print(f"Navegando a página de descarga: {proveedor['pagina_descarga']}")
            driver.get(proveedor["pagina_descarga"])
            time.sleep(10)
            
            # Obtener archivos actuales antes de intentar descargas
            archivos_iniciales = obtener_archivos_actuales()
            print(f"📁 Archivos iniciales en carpeta: {len(archivos_iniciales)}")
            
            # LÓGICA PRINCIPAL: Un solo intento de descarga
            print(f"\n🎯 ESTRATEGIA: Un solo intento de descarga por proveedor")
            
            # Intentar descarga del archivo principal
            exitoso, nombre_archivo = intentar_descarga_archivo_principal(driver, proveedor['nombre'])
            
            # Resumen de descargas para este proveedor
            print(f"\n📊 Resumen para {proveedor['nombre']}:")
            if exitoso:
                print(f"   ✅ Archivo(s) descargado(s) exitosamente")
                print(f"   📄 Archivo(s): {nombre_archivo}")
                return True
            else:
                print(f"   ❌ No se pudo descargar el archivo")
                raise Exception(f"Descarga falló")
                
        except Exception as e:
            print(f"❌ Error en intento {intento + 1} con {proveedor['nombre']}: {e}")
            
            if intento < max_intentos - 1:
                print(f"Reintentando en 15 segundos...")
                time.sleep(15)
            else:
                print(f"❌ Falló después de {max_intentos} intentos")
                return False
        finally:
            if driver:
                driver.quit()
            time.sleep(5)
    
    return False

# Cargar proveedores desde el archivo
try:
    with open(RUTA_JSON, "r", encoding="utf-8") as f:
        proveedores = json.load(f)
except FileNotFoundError:
    print(f"❌ No se encontró el archivo {RUTA_JSON}")
    exit(1)

# Procesar cada proveedor
exitosos = 0
fallidos = 0

print(f"📁 Carpeta de descargas: {CARPETA_DESCARGAS}")
print(f"📅 Fecha: {fecha}")
print(f"🔢 Total de proveedores: {len(proveedores)}")
print(f"⏰ Timeout por intento: 3 minutos")
print(f"🔄 Intentos por proveedor: 1 (un solo intento)")
print(f"🎯 Estrategia: Un intento por proveedor")
print(f"🔧 Especial: Fusion (anuncio + 2 archivos), Ventor (modal), Icepar (#email/#password), Atonor (name=log/pwd), Sinkromat (Chakra UI), Expoyer (dropdown + ZIP)")

for i, proveedor in enumerate(proveedores):
    print(f"\n{'='*80}")
    print(f"Procesando {i+1}/{len(proveedores)}: {proveedor['nombre']}")
    print(f"{'='*80}")
    
    if procesar_proveedor_con_reintentos(proveedor):
        exitosos += 1
    else:
        fallidos += 1
    
    # Pausa entre proveedores
    if i < len(proveedores) - 1:
        tiempo_espera = random.uniform(20, 40)
        print(f"⏳ Esperando {tiempo_espera:.1f} segundos antes del siguiente proveedor...")
        time.sleep(tiempo_espera)

print(f"\n{'='*80}")
print(f"📊 RESUMEN FINAL:")
print(f"✅ Proveedores exitosos: {exitosos}")
print(f"❌ Proveedores fallidos: {fallidos}")
print(f"📁 Archivos guardados en: {CARPETA_DESCARGAS}")
print(f"{'='*80}")

# Mostrar archivos descargados hoy
archivos_hoy = list(CARPETA_DESCARGAS.glob(f"*_{fecha}*.xlsx")) + list(CARPETA_DESCARGAS.glob(f"*_{fecha}*.xls"))
if archivos_hoy:
    print(f"\n📋 Archivos descargados hoy:")
    for archivo in archivos_hoy:
        tamaño = archivo.stat().st_size / 1024
        print(f"   📄 {archivo.name} ({tamaño:.1f} KB)")

    print(f"\n📈 Total: {len(archivos_hoy)} archivo(s)")